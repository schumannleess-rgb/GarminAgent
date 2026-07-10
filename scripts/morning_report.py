"""
晨起健康指南报告生成器
基于 Garmin Connect 数据 + 循证医学算法

Usage:
    python scripts/morning_report.py
"""
import sys
import json
import math
import logging
from pathlib import Path
from datetime import date, timedelta

from dotenv import load_dotenv

# 项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

load_dotenv(_PROJECT_ROOT / ".env")

from garmin_agent.client import GarminClient

logger = logging.getLogger(__name__)


# ===================== SCORING FUNCTIONS =====================

def score_hrv(last_night, weekly):
    """HRV 恢复评分，基于对数偏差"""
    if last_night <= 0 or weekly <= 0:
        return 75
    cl = math.log(last_night)
    bl = math.log(weekly)
    p = (cl - bl) / bl
    if p > 0.10:
        s = 70
    elif p > 0.05:
        s = 85 + (p - 0.05) * (-300)
    elif p >= 0:
        s = 75 + p * 200
    elif p >= -0.05:
        s = 75 + p * 300
    elif p > -0.08:
        s = 60 + (p + 0.05) * (2000 / 3)
    elif p > -0.15:
        s = 40 + (p + 0.08) * (3000 / 7)
    elif p >= -0.20:
        s = 10 + (p + 0.15) * 200
    else:
        s = 0
    return round(min(100, max(0, s)))


def score_rhr(c, b):
    """静息心率评分，基于与基线偏差"""
    d = c - b
    if d < -3:
        s = 95
    elif d <= 0:
        s = 95 + (d + 3) * (-20 / 3)
    elif d <= 3:
        s = 75 + d * (-20 / 3)
    elif d <= 6:
        s = 55 + (d - 3) * (-25 / 3)
    elif d <= 10:
        s = 30 + (d - 6) * (-7.5)
    else:
        s = 0
    return round(min(100, max(0, s)))


def score_sleep(total_sec, deep_sec, rem_sec, awake_cnt, gs=None):
    """睡眠质量评分，四维度加权"""
    if gs is not None:
        return gs
    th = total_sec / 3600
    dp = (deep_sec / total_sec * 100) if total_sec > 0 else 0
    rp = (rem_sec / total_sec * 100) if total_sec > 0 else 0
    if th < 5:
        ds = 10
    elif th < 6:
        ds = 10 + (th - 5) * 35
    elif th < 7:
        ds = 45 + (th - 6) * 35
    elif th <= 9:
        ds = 80 + (th - 7) * 10
    else:
        ds = max(50, 100 - (th - 9) * 20)
    if dp < 5:
        des = 20
    elif dp < 10:
        des = 20 + (dp - 5) * 8
    elif dp <= 25:
        des = 60 + (dp - 10) * (40 / 15)
    else:
        des = 90
    if rp < 10:
        res = 30 + rp * 2
    elif rp < 18:
        res = 50 + (rp - 10) * 2.5
    elif rp <= 25:
        res = 70 + (rp - 18) * (30 / 7)
    else:
        res = 85
    if awake_cnt == 0:
        aws = 100
    elif awake_cnt == 1:
        aws = 80
    elif awake_cnt == 2:
        aws = 60
    else:
        aws = max(0, 45 - (awake_cnt - 3) * 15)
    return round(ds * 0.30 + des * 0.35 + res * 0.15 + aws * 0.20)


today = date.today()
t = today.strftime("%Y-%m-%d")


def main():
    y = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    client = GarminClient()
    if not client.connect():
        print("❌ 连接 Garmin 失败，请检查 .env 中的 GARMIN_EMAIL / GARMIN_PASSWORD 配置")
        sys.exit(1)

    # ===================== DATA =====================
    hrv = client.get_hrv_data(t)
    hs = hrv.get("hrvSummary", {})
    ln = hs.get("lastNightAvg") or 0
    wa = hs.get("weeklyAvg") or 0
    st = hs.get("status", "")

    # 如果昨晚HRV无数据，尝试用最近的有效数据
    if not ln:
        for days_back in range(1, 4):
            d = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
            h_bak = client.get_hrv_data(d)
            h_bak_s = h_bak.get("hrvSummary", {})
            if h_bak_s.get("lastNightAvg"):
                ln = h_bak_s["lastNightAvg"]
                if not wa:
                    wa = h_bak_s.get("weeklyAvg") or 0
                st = h_bak_s.get("status", st)
                break
    if not wa:
        wa = ln  # fallback

    rhr_data = client.get_rhr_day(t)
    rhr = 0
    for m in rhr_data.get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", []):
        if m.get("value"):
            rhr = int(m["value"])

    sd = client.get_sleep_data(y)
    if isinstance(sd, list):
        sd = sd[0] if sd else {}
    ds = sd.get("dailySleepDTO", {})
    ts = ds.get("sleepTimeSeconds", 0) or 0
    deep = ds.get("deepSleepSeconds", 0) or 0
    rem = ds.get("remSleepSeconds", 0) or 0
    awake = ds.get("awakeCount", 0) or 0
    ss = ds.get("overallSleepScore", {})
    if isinstance(ss, dict):
        ss = ss.get("value")
    # 如果昨天睡眠数据缺失，向前推最多3天找最近的有效数据
    _sleep_search_days = 0
    while not ts and _sleep_search_days < 3:
        _sleep_search_days += 1
        d_bak = (today - timedelta(days=1 + _sleep_search_days)).strftime("%Y-%m-%d")
        sd_bak = client.get_sleep_data(d_bak)
        if isinstance(sd_bak, list):
            sd_bak = sd_bak[0] if sd_bak else {}
        ds_bak = sd_bak.get("dailySleepDTO", {})
        ts = ds_bak.get("sleepTimeSeconds", 0) or 0
        deep = ds_bak.get("deepSleepSeconds", 0) or 0
        rem = ds_bak.get("remSleepSeconds", 0) or 0
        awake = ds_bak.get("awakeCount", 0) or 0
        ss_bak = ds_bak.get("overallSleepScore", {})
        if isinstance(ss_bak, dict):
            ss = ss_bak.get("value")
        if ts:
            y = d_bak  # 更新日期引用

    rd = client.get_training_readiness(t)
    if isinstance(rd, list):
        rd = rd[0] if rd else {}
    rscore = rd.get("score", 0) or 0
    rlevel = rd.get("level", "")

    # 14天HRV
    hrv_list = []
    for i in range(14, 0, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        h = client.get_hrv_data(d)
        s = h.get("hrvSummary", {})
        val = s.get("lastNightAvg")
        if val:
            hrv_list.append((d, val))

    # 7天RHR
    rhr_list = []
    for i in range(7, 0, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        r = client.get_rhr_day(d)
        for m in r.get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", []):
            if m.get("value"):
                rhr_list.append((d, int(m["value"])))

    # 7天睡眠
    sleep_list = []
    for i in range(7, 0, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        s = client.get_sleep_data(d)
        if isinstance(s, list):
            s = s[0] if s else {}
        sds = s.get("dailySleepDTO", {})
        total = sds.get("sleepTimeSeconds", 0) or 0
        if total:
            sleep_list.append((d, total, sds.get("deepSleepSeconds", 0) or 0, sds.get("awakeCount", 0) or 0))

    # 7天准备度
    rd_list = []
    for i in range(7, 0, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        r = client.get_training_readiness(d)
        if isinstance(r, list):
            r = r[0] if r else {}
        sc = r.get("score", 0)
        lv = r.get("level", "")
        if sc:
            rd_list.append((d, sc, lv))

    # 训练状态
    ts_data = client.get_training_status(t)
    if ts_data is None:
        ts_data = {"mostRecentTrainingStatus": {}, "mostRecentVO2Max": {}}
    sd = ts_data.get("mostRecentTrainingStatus", {}) or {}
    sd = sd.get("latestTrainingStatusData", {}) or {}
    status_phrase = "RECOVERY"
    acwr = 0
    if isinstance(sd, dict):
        for did, d in sd.items():
            status_phrase = d.get("trainingStatusFeedbackPhrase", "RECOVERY") if isinstance(d, dict) else "RECOVERY"
            a = d.get("acuteTrainingLoadDTO", {}) if isinstance(d, dict) else {}
            acwr = a.get("acwrPercent", 0) if isinstance(a, dict) else 0

    vo2_data = ts_data.get("mostRecentVO2Max", {}) or {}
    if isinstance(vo2_data, dict):
        vo2 = vo2_data.get("generic", {}) or {}
    else:
        vo2 = {}
    vo2max = vo2.get("vo2MaxValue", "") if isinstance(vo2, dict) else ""

    try:
        fa = client.get_fitnessage_data()
        fage = fa.get("fitnessAge", "")
        cage = fa.get("chronologicalAge", "")
    except Exception as e:
        logger.warning("Failed to get fitness age data: %s", e)
        fage = cage = ""

    # ===================== BODY COMPOSITION & DEVICE =====================
    bmi = None
    device_name = "Garmin"
    try:
        body = client.get_daily_weigh_ins(t)
        if body:
            bmi = body.get("bmi") or body.get("weight", {}).get("bmi")
    except Exception as e:
        logger.warning("Failed to get body composition data: %s", e)
    try:
        devices = client.get_devices()
        if devices:
            first = devices[0]
            device_name = first.get("modelName") or first.get("deviceName") or device_name
    except Exception as e:
        logger.warning("Failed to get device info: %s", e)

    # ===================== SCORING =====================
    # score_hrv / score_rhr / score_sleep 定义在模块级别

    rhr_baseline = round(sum(v for _, v in rhr_list) / len(rhr_list)) if rhr_list else rhr
    rv = [v for _, v in hrv_list if v > 0]
    hrv_baseline = round(sum(rv) / len(rv)) if rv else wa

    hrv_score = score_hrv(ln if ln else wa, hrv_baseline)
    rhr_score = score_rhr(rhr, rhr_baseline)
    sleep_score = score_sleep(ts, deep, rem, awake, ss)
    readiness_score = min(rscore, 100)
    recovery = round(hrv_score * 0.35 + sleep_score * 0.30 + rhr_score * 0.20 + readiness_score * 0.15)

    hrv_pct = ((ln if ln else wa) - hrv_baseline) / hrv_baseline * 100
    rhr_dev = rhr - rhr_baseline
    dp = deep / ts * 100 if ts > 0 else 0
    rp = rem / ts * 100 if ts > 0 else 0

    # ===================== ROOT CAUSE =====================
    issues = []
    if hrv_pct < -5:
        issues.append(f"HRV 低于基线 {abs(hrv_pct):.0f}%，自主神经恢复不足")
    elif hrv_pct > 10:
        issues.append(f"HRV 异常升高（>+10%），需关注是否副交感反弹")
    if rhr_dev > 3:
        issues.append(f"RHR 高于基线 {rhr_dev}bpm，交感活性偏高")
    if rhr_dev < -3:
        issues.append(f"RHR 显著低于基线，副交感占优 — 若伴随疲劳感需排查")
    if ts < 6 * 3600:
        issues.append(f"睡眠时长不足（{ts // 60}分钟）")
    if awake >= 3:
        issues.append(f"夜间清醒 {awake} 次，睡眠碎片化")
    if dp < 10 and ts > 0:
        issues.append(f"深睡占比仅 {dp:.0f}%，低于理想范围 10-25%")
    if dp < 5 and ts > 0:
        issues.append(f"深睡严重不足（{dp:.0f}%），可能是压力或浅睡过多")
    if rscore < 60:
        issues.append(f"训练准备度偏低（{rscore}/100）")
    if recovery < 60 and recovery >= 40:
        if len([x for x in issues if x]) >= 2:
            issues.append("多项指标共同指向恢复不足")
    elif recovery < 40:
        issues.append("Plews(2013) 框架下 NFOR 风险 — 建议调整训练周期")

    positives = []
    if hrv_pct >= -5 and hrv_pct <= 5:
        positives.append("HRV 在正常波动范围内，自主神经平衡")
    if hrv_pct > 5 and hrv_pct <= 10:
        positives.append("HRV 高于基线，恢复状态良好")
    if rhr_dev >= -3 and rhr_dev <= 3:
        positives.append("RHR 稳定，无异常交感激活")
    if rhr_dev >= -3 and rhr_dev < 0:
        positives.append("RHR 略低于基线，副交感占优有益恢复")
    if ts >= 7 * 3600:
        positives.append(f"睡眠时长充足（{ts // 60}分钟）")
    if dp >= 10 and dp <= 25:
        positives.append(f"深睡占比 {dp:.0f}% 在理想范围 10-25%")
    if dp >= 15:
        positives.append(f"深睡占比 {dp:.0f}%，恢复性睡眠质量高")
    if rscore >= 80:
        positives.append(f"训练准备度高（{rscore}/100），身体状态在线")
    if rscore >= 60 and rscore < 80:
        positives.append(f"训练准备度中等（{rscore}/100），基础状态尚可")
    if rhr <= 50:
        positives.append(f"静息心率 {rhr}bpm，心血管系统效率良好")

    # ===================== ADVICE =====================
    if recovery >= 85:
        adv = "今天状态在线！可以安排高强度训练或者试试冲击个人最佳。身体告诉你：准备好了 💪"
        if rhr_dev < -3:
            adv += "\n一个提醒：RHR 偏低，排除过度训练后期副交感反弹可能，如果感觉异常疲劳就悠着点。"
    elif recovery >= 70:
        adv = "状态不错，身体基本恢复到位，按计划正常训练就好。"
        if awake >= 3:
            adv += "\n不过昨晚醒的次数有点多，如果今天感觉疲劳就降低一点强度，听听身体的信号。"
        if ts < 6 * 3600:
            adv += "\n昨晚睡得偏少，热身时多留意身体反应，别硬上强度。"
        if rhr_dev >= 3 and rhr_dev < 5:
            adv += "\nRHR 略有偏高，热身时多花几分钟，感觉好了再上强度。"
        if rhr_dev >= 5:
            adv += "\nRHR 偏高明显，今天建议做轻松有氧，不要做高强度间歇。"
        if not awake >= 3 and not ts < 6 * 3600 and not (rhr_dev >= 3):
            adv += "\n各项指标都在正常范围，享受训练吧！"
    elif recovery >= 55:
        adv = "身体传达了一些需要注意的信号，不急着冲，稳住节奏。建议："
        if hrv_pct < -5:
            adv += "\n  • HRV 偏低 → 把今天的训练降为轻松跑或交叉训练（60-75% 强度）"
        if awake >= 3:
            adv += "\n  • 睡眠碎片化 → 今晚提前 30 分钟放下手机，试试冥想或阅读"
        if ts < 6 * 3600:
            adv += "\n  • 睡眠时长不足 → 今晚重点补觉，争取睡满 8 小时"
        if rhr_dev >= 3:
            adv += "\n  • RHR 升高 → 交感神经还有点兴奋，避免高强度刺激"
        if rscore < 60:
            adv += "\n  • 准备度偏低 → 信任身体的信号，今天休息或做恢复跑"
        if not issues:
            adv += "\n  • 各项指标都在边缘，今天做轻松有氧活动最稳妥"
        adv += "\n  • 优先保证今晚的睡眠质量，这是最快最有效的恢复途径"
    elif recovery >= 40:
        adv = "身体在说：我需要休息。认真对待这个信号："
        if hrv_pct < -8:
            adv += "\n  • HRV 显著偏低 → 今天彻底休息，不要安排任何训练"
        if rhr_dev >= 5:
            adv += "\n  • RHR 明显升高 → 交感神经负荷较重，休息是最好的恢复方式"
        if ts < 6 * 3600:
            adv += "\n  • 睡眠不足 → 今晚争取睡满 8 小时，这是硬指标"
        if awake >= 3:
            adv += "\n  • 睡眠碎片化 → 检查睡眠环境（温度、光线、噪音），确保安静黑暗"
        if not issues:
            adv += "\n  • 多项指标偏低 → 建议只做轻度拉伸或散步，不要跑步"
        adv += "\n  • 明天再评估，不要连续两天硬撑"
    else:
        adv = ("需要认真对待的恢复警报。建议：\n"
               "  • 今天全天休息，不做任何训练\n"
               "  • 关注 HRV 和 RHR 是否明天回升\n"
               "  • 如果连续 2 天此状态，建议调整训练周期\n"
               "  • 考虑检查是否有其他压力源（工作、生活、饮食）")

    # ===================== TREND =====================
    recent_rd = [sc for _, sc, _ in rd_list[-3:]]
    trend_text = ""
    if len(recent_rd) >= 3:
        if recent_rd[0] < recent_rd[-1] - 10:
            trend_text = "📈 训练准备度呈上升趋势，身体状态在改善 👍"
        elif recent_rd[0] > recent_rd[-1] + 10:
            trend_text = "📉 训练准备度呈下降趋势，注意恢复节奏"
        else:
            trend_text = "➡️ 训练准备度趋于稳定，波动在正常范围内"

    hrv_recent = [v for _, v in hrv_list[-5:]]
    if len(hrv_recent) >= 3:
        if hrv_recent[-1] > hrv_recent[0]:
            trend_text += "  |  HRV 回升中"
        elif hrv_recent[-1] < hrv_recent[0]:
            trend_text += "  |  HRV 持续走低，注意恢复"

    # ===================== OUTPUT =====================
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           🌅  晨 起 健 康 指 南  ·  G A R M I N            ║")
    print(f"║               {today.strftime('%Y-%m-%d')}                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # 综合评分
    bar = "█" * (recovery // 5) + "░" * (20 - recovery // 5)
    print(f"  {bar}  {recovery}/100")
    print()

    if recovery >= 85:
        label = "🟢 状态极佳"
    elif recovery >= 70:
        label = "🔵 状态良好"
    elif recovery >= 55:
        label = "🟡 需要注意"
    elif recovery >= 40:
        label = "🟠 恢复不足"
    else:
        label = "🔴 需要休息"
    print(f"  {label}")
    print()

    # 主建议
    print("  💬 建议")
    print("  ─────────────────────────────────────────────")
    for line in adv.split("\n"):
        print(f"  {line}")
    print()

    # 四个维度表
    print("  ┌──────────────────────┬──────────┬───────────┬──────────────┐")
    print("  │ 维度                 │  评分     │  数据     │  与基线比较   │")
    print("  ├──────────────────────┼──────────┼───────────┼──────────────┤")

    hrv_ic = "🟢" if hrv_pct >= -5 else "🟡" if hrv_pct >= -8 else "🔴"
    hrv_arrow = "🔺" if hrv_pct > 5 else "🔻" if hrv_pct < -5 else "➡️"
    hrv_val = ln if ln else wa
    hrv_line = f"  │ {hrv_ic} HRV 心率变异性     │  {hrv_score:>2}/100    │  {hrv_val}ms      │  {hrv_pct:+.0f}% vs {hrv_baseline}ms"
    space = 14 - len(str(hrv_val)) - 3
    hrv_line += " " * space + f" {hrv_arrow}   │"
    print(hrv_line)

    rhr_ic = "🟢" if abs(rhr_dev) <= 3 else "🟡" if rhr_dev <= 5 else "🔴"
    rhr_arrow = "🔺" if rhr_dev < -3 else "🔻" if rhr_dev > 3 else "➡️"
    rhr_label = f"  │ {rhr_ic} 静息心率          │  {rhr_score:>2}/100    │  {rhr}bpm     │  {rhr_dev:+d} vs {rhr_baseline}bpm"
    rhr_label += " " * (12 - len(str(rhr_baseline))) + f" {rhr_arrow}   │"
    print(rhr_label)

    sleep_h = ts / 3600
    sleep_ic = "🟢" if ts >= 7 * 3600 and awake <= 1 else "🟡" if ts >= 6 * 3600 else "🔴"
    sleep_str = f"{ts // 60}min"
    sleep_label = f"  │ {sleep_ic} 睡眠质量          │  {sleep_score:>2}/100    │  {sleep_str}"
    sleep_label += " " * (10 - len(sleep_str)) + f" 深睡{dp:.0f}%"
    sleep_label += " " * (8 - len(f"{dp:.0f}")) + "   │"
    print(sleep_label)

    rd_ic = "🟢" if rscore >= 80 else "🟡" if rscore >= 60 else "🔴"
    rd_str = f"{rscore}/100"
    rd_label = f"  │ {rd_ic} 训练准备度        │  {readiness_score:>2}/100    │  {rd_str}"
    rd_label += " " * (12 - len(rd_str)) + f" {rlevel}"
    rd_label += " " * (11 - len(rlevel)) + "   │"
    print(rd_label)

    print("  └──────────────────────┴──────────┴───────────┴──────────────┘")
    print()

    # 昨晚睡眠详情
    print("  😴 昨晚睡眠质量")
    print("  ─────────────────────────────────────────────")
    total_h = ts // 3600
    total_m = (ts % 3600) // 60
    print(f"   总时长:  {total_h}h{total_m}min  ", end="")
    if ts >= 7 * 3600:
        print("✅ 充足（>7h）")
    elif ts >= 6 * 3600:
        print("⚠️ 偏少（6-7h）")
    else:
        print("🔴 严重不足（<6h）")
    print(f"   深睡:    {deep // 60}min ({dp:.0f}%)  ", end="")
    if dp >= 10 and dp <= 25:
        print("✅ 理想范围 10-25%")
    elif dp >= 5:
        print("⚠️ 偏低")
    else:
        print("🔴 严重不足")
    print(f"   REM:     {rem // 60}min ({rp:.0f}%)  ", end="")
    if rp >= 18 and rp <= 25:
        print("✅ 正常")
    elif rp >= 10:
        print("⚠️ 偏低")
    else:
        print("🔴 偏低")
    print(f"   清醒:    {awake}次  ", end="")
    if awake <= 1:
        print("✅ 正常（<2次）")
    elif awake == 2:
        print("⚠️ 略多（2次）")
    else:
        print("🔴 碎片化（≥3次）")
    print()

    # 趋势表
    print("  📈 近 7 天趋势")
    print("  ─────────────────────────────────────────────────────")
    print("   日期    HRV  RHR  睡眠   深睡  清醒  准备度")
    print("  ─────────────────────────────────────────────────────")
    for i in range(7, 0, -1):
        d = (today - timedelta(days=i)).strftime("%m-%d")
        hrv_val = "--"
        for dd, v in hrv_list:
            if dd.endswith(d):
                hrv_val = str(v)
                break
        rhr_val = "--"
        for dd, v in rhr_list:
            if dd.endswith(d):
                rhr_val = str(v)
                break
        sleep_val = "--"
        sleep_deep = "--"
        sleep_awake = "--"
        for dd, total, dp_v, aw in sleep_list:
            if dd.endswith(d):
                sleep_val = f"{total // 60}min"
                sleep_deep = f"{dp_v // 60}min"
                sleep_awake = str(aw)
                break
        rd_val = "--"
        rd_lv = ""
        for dd, sc, lv in rd_list:
            if dd.endswith(d):
                rd_val = f"{sc}"
                rd_lv = lv[:4]
                break
        print(f"   {d}  {hrv_val:>3}  {rhr_val:>3}  {sleep_val:>6} {sleep_deep:>4}  {sleep_awake:>2}    {rd_val:>3} {rd_lv}")
    print("  ─────────────────────────────────────────────────────")
    print(f"  {trend_text}")
    print()

    # 根因分析
    print("  🔍 根因分析")
    print("  ─────────────────────────────────────────────────────")
    if positives:
        print("  ✅ 表现良好的方面:")
        for p in positives:
            print(f"    • {p}")
    if issues:
        print()
        print("  ⚠️ 需要关注的方面:")
        for i, issue in enumerate(issues, 1):
            print(f"    • {issue}")
    print()

    # 个人档案
    print("  📋 个人档案")
    print("  ─────────────────────────────────────────────────────")
    fage_str = f"{fage:.0f}" if isinstance(fage, (int, float)) else str(fage)
    cage_str = str(cage) if cage else "?"
    print(f"   年龄: {cage_str}岁  |  健身年龄: {fage_str}岁")
    bmi_str = f"BMI: {bmi:.1f}" if bmi else "BMI: 无数据"
    print(f"   VO₂Max: {vo2max}  |  静息心率: {rhr}bpm  |  {bmi_str}")
    print(f"   设备: {device_name}  |  ACWR: {acwr}%（偏低）")
    print()

    # 比赛预测
    try:
        rp = client.get_race_predictions()
        race_predictions = {}
        for k in ["time5K", "time10K", "timeHalfMarathon", "timeMarathon"]:
            if k in rp and rp[k]:
                race_predictions[k] = int(rp[k] / 60)
        if race_predictions:
            print("  🏃 比赛预测（基于当前体能）")
            print("  ─────────────────────────────────────────────────────")
            distances = {
                "time5K": 5,
                "time10K": 10,
                "timeHalfMarathon": 21.0975,
                "timeMarathon": 42.195,
            }
            names = {
                "time5K": "5K",
                "time10K": "10K",
                "timeHalfMarathon": "半马",
                "timeMarathon": "全马",
            }
            for k, v in race_predictions.items():
                h = v // 60
                m = v % 60
                pace_km = round(v / distances[k], 1)
                pace_m = int(pace_km)
                pace_s = round((pace_km - pace_m) * 60)
                print(f"   {names[k]}:  {h}:{m:02d}  ·  {pace_m}:{pace_s:02d}/km")
            print()
    except Exception as e:
        logger.warning("Failed to get race predictions: %s", e)

    # 底部
    print("  ─────────────────────────────────────────────────────")
    print(f"  📡 数据来源: {device_name}")
    print(f"  ⏰ 报告生成: {today.strftime('%Y-%m-%d %H:%M')}")
    print("  🤖 分析引擎: Morning Advisor v1.0 (基于 24 篇文献)"
          "\n       Buchheit 2014 · Plews 2013 · Kiviniemi 2007"
          "\n       Ohayon 2004 · Boudreau 2013 · Dijk 2009")
    print()


if __name__ == "__main__":
    main()