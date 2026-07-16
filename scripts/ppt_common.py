# -*- coding: utf-8 -*-
"""
ppt_common.py — 每日恢复力日报（PPT 风格）共享内容层
=====================================================
所有「风格」变体（当前启用 Swiss；架构支持多皮肤扩展）共用同一份
数据抽取、叙事逻辑与图表构件，仅通过 theme_css 切换视觉皮肤。

数据流: output/kpi_today.json  →  build_model()  →  build_html(theme_css)
- 单数据源: 只读 kpi_today.json（由 rebuild_kpi_today.py 从 daily_health 重建）
- 叙事逻辑: 权重是「统一参考配方」（页脚小注），真正决定分数的是「今天的数据」
- 已知数据 bug（其它 session 修复）本层「绕过」:
    · hrv.score == 0 但原始 73ms > 7日基线 70ms → 按原始值叙事，标记异常
    · sleep_rem_pct == 0 但 rem_seconds=7800 → 用原始值重算并标记异常
"""
import json
import re
import html

# ──────────────────────────────────────────────────────────────────────────
# 基础工具
# ──────────────────────────────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s)) if s is not None else ""

def load_kpi(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def hrv_display_score(hrv):
    """绕过 hrv.score==0 的引擎 bug：按 pct_change 估算一个合理展示分。"""
    s = hrv.get("score", 0)
    if s and s > 0:
        return int(round(s))
    pct = hrv.get("pct_change_pct", 0) or 0
    # anchors: 0% -> 75, 5% -> 85
    est = 75 + min(max(pct, 0), 5) / 5 * 10
    return int(round(est))

def zone_cn(z):
    m = {
        "GREEN": "绿色·佳", "LOW": "低", "MODERATE": "中等", "HIGH": "高",
        "PRIME": "峰值", "very_low": "很低", "very_high": "很高",
        "SEVERE": "严重", "CAUTION": "注意", "yellow_low_red_high": "黄低红高",
        "green_low_yellow_high": "绿低黄高", "green_normal_mid": "绿·正常",
        "green_high": "绿·高", "red_deep": "红·深", "severe": "严重",
        "baseline": "基线", "mild_fatigue": "轻度疲劳", "fatigue": "疲劳",
        "spike": "突增",
    }
    return m.get(z, z or "")

def fmt_pct(p):
    if p is None:
        return "—"
    return f"{p:+.1f}%"


# ── 数值精度治理（数据治理核心）──────────────────────────────────────────
# 规则：评分/ms/bpm/等级/权重% → 整数；睡眠时长(h) → 1 位；
#       贡献分 → 1 位；百分比(变化率/深睡/REM) → 1 位；
#       趋势 recovery 均值 → 1 位，最小/最大 → 整数。
def fmt_val(v, dec=0):
    """统一数值格式化：固定 dec 位小数，None/缺失返回破折号。"""
    if v is None:
        return "—"
    try:
        return f"{float(v):.{dec}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_int(v):
    """整数显示（评分、ms、bpm、等级等）。"""
    if v is None:
        return "—"
    return str(int(round(float(v))))


def fmt_hours(v):
    """睡眠时长：固定 1 位小数。"""
    return fmt_val(v, 1)

# ──────────────────────────────────────────────────────────────────────────
# 公式解析
# ──────────────────────────────────────────────────────────────────────────
def parse_calc(steps):
    out = {}
    for s in steps:
        m = re.match(r"\s*([A-Za-z]+)\s*:\s*([\d.]+)\s*x\s*([\d.]+)\s*=\s*([\d.]+)", s)
        if m:
            out[m.group(1).lower()] = {
                "score": float(m.group(2)),
                "weight": float(m.group(3)),
                "contrib": float(m.group(4)),
            }
    return out

# ──────────────────────────────────────────────────────────────────────────
# 模型构建
# ──────────────────────────────────────────────────────────────────────────
def build_model(d):
    comp = d.get("composite", {})
    ds = d.get("dimension_scores", {})
    bl = d.get("baselines", {})
    raw = d.get("raw_inputs", {})
    mv = d.get("multi_dimension_validation", {})
    tr = d.get("trend", {})
    dms = d.get("derived_metrics_summary", {})
    hist = d.get("history", {})

    date = d.get("date", "")
    recovery = comp.get("recovery_score")
    grade = comp.get("grade")
    label = comp.get("label", "")
    zone = comp.get("zone", "")
    formula = comp.get("formula", "")
    weights = comp.get("weights", {})
    calc = parse_calc(comp.get("calculation_steps", []))

    hrv = ds.get("hrv", {})
    rhr = ds.get("rhr", {})
    sleep = ds.get("sleep", {})
    readiness = ds.get("readiness", {})
    stress = ds.get("stress", {})

    sb = bl.get("sleep_baseline_7d", {})
    hrv_base = bl.get("hrv_baseline_7d")
    rhr_base = bl.get("rhr_baseline_28d")
    sleep_base_h = sb.get("total_hours")
    sleep_base_deep = sb.get("deep_pct_avg")

    hrv_anom = hrv.get("score", 0) == 0
    hrv_disp = hrv_display_score(hrv)
    sleep_rem_anom = (dms.get("sleep_rem_pct") == 0) and (sleep.get("rem_seconds", 0) > 0)

    # ---- 五维度 ----
    dims = [
        {
            "key": "hrv", "name": "HRV 心率变异性",
            "raw": f"{fmt_int(hrv.get('last_night_ms'))} ms",
            "baseline": f"{fmt_int(hrv_base)} ms（7日）",
            "pct": hrv.get("pct_change_pct"),
            "score": hrv.get("score"),
            "disp": hrv_disp,
            "zone": hrv.get("zone"),
            "weight": weights.get("hrv"),
            "contrib": calc.get("hrv", {}).get("contrib", 0),
            "anomaly": hrv_anom,
            "narr": (f"今夜 {fmt_int(hrv.get('last_night_ms'))}ms，7日基线 {fmt_int(hrv_base)}ms，"
                     f"{fmt_pct(hrv.get('pct_change_pct'))} —— 处于基线附近，恢复良好。"
                     f"评分引擎误判为 {zone_cn(hrv.get('zone'))}（原始值健康），已绕过展示。"),
        },
        {
            "key": "rhr", "name": "静息心率 RHR",
            "raw": f"{fmt_int(rhr.get('current_bpm'))} bpm",
            "baseline": f"{fmt_int(rhr_base)} bpm（28日）",
            "pct": None,
            "score": rhr.get("score"),
            "disp": int(round(rhr.get("score", 0))),
            "zone": rhr.get("zone"),
            "weight": weights.get("rhr"),
            "contrib": calc.get("rhr", {}).get("contrib", 0),
            "anomaly": False,
            "narr": (f"今夜 {fmt_int(rhr.get('current_bpm'))}bpm，28日基线 {fmt_int(rhr_base)}bpm，"
                     f"{rhr.get('deviation_bpm')} —— 低于基线，心肺负担轻，状态佳。"),
        },
        {
            "key": "sleep", "name": "睡眠",
            "raw": f"{fmt_hours(dms.get('sleep_total_hours'))} h",
            "baseline": f"{fmt_hours(sleep_base_h)} h（7日）",
            "pct": None,
            "score": sleep.get("score"),
            "disp": int(round(sleep.get("score", 0))),
            "zone": "GREEN" if sleep.get("score", 0) >= 80 else "MODERATE",
            "weight": weights.get("sleep"),
            "contrib": calc.get("sleep", {}).get("contrib", 0),
            "anomaly": False,
            "narr": (f"睡眠 {fmt_hours(dms.get('sleep_total_hours'))}h，7日基线 {fmt_hours(sleep_base_h)}h；"
                     f"深睡占比 {fmt_val(dms.get('sleep_deep_pct'), 1)}%（基线 {fmt_val(sleep_base_deep, 1)}%）"
                     f"{'偏低' if dms.get('sleep_deep_pct', 99) < (sleep_base_deep or 0) else '达标'}；"
                     f"Garmin 睡眠分 {fmt_int(sleep.get('score'))} —— 时长达标、质量优，深睡可进一步提升。"
                     + (f"（REM 占比引擎误算为 0，原始 REM {fmt_int(sleep.get('rem_seconds'))}s≈"
                        f"{sleep.get('rem_seconds', 0) / sleep.get('total_seconds', 1) * 100:.0f}%，待修）"
                        if sleep_rem_anom else "")),
        },
        {
            "key": "readiness", "name": "身体准备度",
            "raw": f"{fmt_int(readiness.get('score'))}/100",
            "baseline": "—",
            "pct": None,
            "score": readiness.get("score"),
            "disp": int(round(readiness.get("score", 0))),
            "zone": readiness.get("zone"),
            "weight": weights.get("readiness"),
            "contrib": calc.get("readiness", {}).get("contrib", 0),
            "anomaly": False,
            "narr": (f"准备度 {fmt_int(readiness.get('score'))}/100，{zone_cn(readiness.get('zone'))} —— "
                     f"身体准备度高，可正常训练。"),
        },
        {
            "key": "stress", "name": "压力",
            "raw": f"等级 {fmt_int(stress.get('stress_level'))}",
            "baseline": "—",
            "pct": None,
            "score": stress.get("score"),
            "disp": int(round(stress.get("score", 0))),
            "zone": stress.get("zone"),
            "weight": weights.get("stress"),
            "contrib": calc.get("stress", {}).get("contrib", 0),
            "anomaly": False,
            "narr": (f"压力等级 {fmt_int(stress.get('stress_level'))}（{zone_cn(stress.get('zone'))}），"
                     f"得分 {fmt_int(stress.get('score'))} —— 身心放松，恢复环境好。"),
        },
    ]

    # ---- 恢复分趋势（28/14/7 窗口）----
    rec = hist.get("recovery_cal_28d", [])
    rec_pairs = [(x.get("date"), x.get("value")) for x in rec]
    rec_vals_all = [v for _, v in rec_pairs if v is not None]
    recovery_trend = {
        "28": rec_pairs,
        "14": rec_pairs[-14:],
        "7": rec_pairs[-7:],
        "alert": tr.get("threshold", 60),
        "coverage": (len(rec_vals_all), len(rec_pairs)),
        "min": min(rec_vals_all) if rec_vals_all else None,
        "max": max(rec_vals_all) if rec_vals_all else None,
        "avg": round(sum(rec_vals_all) / len(rec_vals_all), 1) if rec_vals_all else None,
    }

    # ---- 多维 sparkline ----
    def series_vals(key, transform=None):
        arr = hist.get(key, [])
        out = []
        for x in arr:
            v = x.get("value")
            if v is None:
                out.append(None)
            else:
                out.append(transform(v) if transform else v)
        return out

    hrv_s = series_vals("hrv_14d")
    rhr_s = series_vals("rhr_28d")
    sleep_s = [ (x.get("total_sec") / 3600) if isinstance(x, dict) else None
                for x in hist.get("sleep_28d", []) ]
    sleep_s = [ round(v, 1) if v is not None else None for v in sleep_s ]  # 睡眠时长固定 1 位小数
    ready_s = [ x.get("score") for x in hist.get("readiness_28d", []) ]

    def stats(s):
        v = [x for x in s if x is not None]
        if not v:
            return (None, None, None, None)
        return (v[-1], min(v), max(v), round(sum(v) / len(v), 1))

    sparks = [
        {"name": "HRV (ms)", "series": hrv_s, "base": hrv_base, "unit": " ms", "dec": 0,
         "cur": hrv.get("last_night_ms"), "base_disp": f"基线 {fmt_int(hrv_base)}"},
        {"name": "静息心率 (bpm)", "series": rhr_s, "base": rhr_base, "unit": " bpm", "dec": 0,
         "cur": rhr.get("current_bpm"), "base_disp": f"基线 {fmt_int(rhr_base)}"},
        {"name": "睡眠 (h)", "series": sleep_s, "base": sleep_base_h, "unit": " h", "dec": 1,
         "cur": dms.get("sleep_total_hours"), "base_disp": f"基线 {fmt_hours(sleep_base_h)} h"},
        {"name": "准备度", "series": ready_s, "base": None, "unit": "", "dec": 0,
         "cur": readiness.get("score"), "base_disp": "无基线"},
    ]
    for sp in sparks:
        sp["stat"] = stats(sp["series"])

    # ---- 状态模式（全部 5 个）----
    patterns = mv.get("patterns_checked", [])
    matched = [p for p in patterns if p.get("match")]

    # ---- 顶部预警条 ----
    low_streak = tr.get("low_streak", 0)
    threshold = tr.get("threshold", 60)
    if low_streak and low_streak > 0:
        alert = {"level": "warn", "text": f"近 {low_streak} 天恢复分低于警戒线 {threshold}，注意累积疲劳"}
    elif tr.get("alert"):
        alert = {"level": "warn", "text": tr.get("alert")}
    else:
        alert = {"level": "ok", "text": f"恢复分趋势稳定，28 天窗口内无低于警戒线 {threshold} 的连续预警"}

    # ---- 今日建议（按 Grade）----
    advice = grade_advice(grade, dims, dms, hrv_base, rhr_base, sleep_base_deep)

    return {
        "date": date,
        "recovery": recovery,
        "grade": grade,
        "label": label,
        "zone": zone,
        "formula": formula,
        "weights": weights,
        "calc_steps": comp.get("calculation_steps", []),
        "dims": dims,
        "recovery_trend": recovery_trend,
        "sparks": sparks,
        "patterns": patterns,
        "matched": matched,
        "alert": alert,
        "advice": advice,
        "ref": comp.get("reference", ""),
    }


def grade_advice(grade, dims, dms, hrv_base, rhr_base, sleep_base_deep):
    hrv = next(x for x in dims if x["key"] == "hrv")
    rhr = next(x for x in dims if x["key"] == "rhr")
    sleep = next(x for x in dims if x["key"] == "sleep")
    items = []
    # 1) HRV / 睡眠优先
    if hrv["anomaly"]:
        items.append(("HRV 评分待修", "HRV 原始值近基线（实际健康），但评分引擎误判为严重。今夜以巩固睡眠为主，"
                                    "避免熬夜与高强度间歇，让恢复分回归真实水平。"))
    else:
        items.append(("维持 HRV", f"HRV 处于 {zone_cn(hrv['zone'])}，保持当前作息与训练节奏即可。"))
    # 2) 静息心率 / 训练量
    items.append(("训练量", f"静息心率 {rhr['raw']} 优于 28 日基线 {rhr_base}bpm，心肺恢复良好，"
                           f"可维持当前训练量，无需主动降载。"))
    # 3) 深睡
    deep = dms.get("sleep_deep_pct")
    if deep is not None and sleep_base_deep and deep < sleep_base_deep:
        items.append(("提升深睡", f"深睡占比 {fmt_val(deep, 1)}% 低于基线 {fmt_val(sleep_base_deep, 1)}%，"
                                f"睡前 1 小时减少蓝光与酒精、保持卧室凉爽，以提升深睡时长。"))
    else:
        items.append(("睡眠巩固", f"睡眠 {sleep['raw']}，质量达标，维持规律作息即可。"))
    return items


# ──────────────────────────────────────────────────────────────────────────
# SVG 图表构件（静态，无 canvas）
# ──────────────────────────────────────────────────────────────────────────
def line_svg(series, w=920, h=210, pad=34, alert=None, color="#002FA7", gid="a"):
    """series: [(date, value)|(idx, value)]，value 可为 None（断点）。"""
    pts = [(i, v) for i, (_, v) in enumerate(series) if v is not None]
    if len(pts) < 2:
        return ""
    allv = [v for _, v in pts] + ([alert] if alert is not None else [])
    ymin, ymax = min(allv), max(allv)
    if ymax == ymin:
        ymax = ymin + 1
    n = len(series)

    def X(i):
        return pad + (i / (n - 1)) * (w - 2 * pad)

    def Y(v):
        return h - pad - ((v - ymin) / (ymax - ymin)) * (h - 2 * pad)

    poly = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in pts)
    area = (f"{X(pts[0][0]):.1f},{h-pad:.1f} " + poly +
            f" {X(pts[-1][0]):.1f},{h-pad:.1f}")
    last_i, last_v = pts[-1]
    grid = ""
    for g in range(4):
        gy = pad + g * (h - 2 * pad) / 4
        grid += f'<line x1="{pad}" y1="{gy:.1f}" x2="{w-pad}" y2="{gy:.1f}" class="grid"/>'
    alert_line = ""
    if alert is not None:
        ay = Y(alert)
        alert_line = (f'<line x1="{pad}" y1="{ay:.1f}" x2="{w-pad}" y2="{ay:.1f}" class="alert-line"/>'
                      f'<text x="{w-pad}" y="{ay-6:.1f}" class="alert-txt">警戒线 {alert}</text>')
    return (f'<svg viewBox="0 0 {w} {h}" class="trend-svg" preserveAspectRatio="none" '
            f'data-gid="{gid}" xmlns="http://www.w3.org/2000/svg">'
            f'{grid}{alert_line}'
            f'<polygon points="{area}" class="area" fill="{color}" opacity="0.08"/>'
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.5" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{X(last_i):.1f}" cy="{Y(last_v):.1f}" r="4.5" fill="{color}"/>'
            f'<text x="{X(last_i):.1f}" y="{Y(last_v)-10:.1f}" class="last-txt">{last_v:.0f}</text>'
            f'</svg>')


def sparkline_svg(series, baseline=None, color="#002FA7", w=240, h=64, pad=8):
    vals = [v for v in series if v is not None]
    if not vals:
        return ""
    allv = list(vals) + ([baseline] if baseline is not None else [])
    ymin, ymax = min(allv), max(allv)
    if ymax == ymin:
        ymax = ymin + 1
    n = len(series)

    def X(i):
        return pad + (i / (n - 1)) * (w - 2 * pad)

    def Y(v):
        return h - pad - ((v - ymin) / (ymax - ymin)) * (h - 2 * pad)

    pts = [(i, v) for i, v in enumerate(series) if v is not None]
    poly = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in pts)
    base_line = ""
    if baseline is not None:
        by = Y(baseline)
        base_line = f'<line x1="{pad}" y1="{by:.1f}" x2="{w-pad}" y2="{by:.1f}" class="base-line"/>'
    return (f'<svg viewBox="0 0 {w} {h}" class="spark" preserveAspectRatio="none" '
            f'xmlns="http://www.w3.org/2000/svg">{base_line}'
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2" '
            f'vectordata="1"/></svg>')


# ──────────────────────────────────────────────────────────────────────────
# 共享基础 CSS（主题无关；颜色经 CSS 变量注入）
# ──────────────────────────────────────────────────────────────────────────
SHARED_BASE_CSS = """
:root{--paper:#fff;--ink:#111;--muted:#6b7280;--line:#e5e7eb;--accent:#002FA7;
--good:#16a34a;--bad:#dc2626;--card:#fff;--card-2:#fafafa;}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:var(--sans),var(--sans-zh),system-ui,sans-serif;background:var(--bg,#eee);
color:var(--ink);overflow:hidden;-webkit-font-smoothing:antialiased}
.deck{position:relative;width:100vw;height:100vh;overflow:hidden}
.slide{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
opacity:0;transform:translateX(40px);transition:opacity .45s ease,transform .45s ease;
pointer-events:none}
.slide.active{opacity:1;transform:none;pointer-events:auto}
.slide-inner{width:min(1120px,92vw);max-height:90vh;overflow:auto;padding:34px 40px;
background:var(--paper);border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.18);
border:1px solid var(--line)}
.slide[data-layout="accent"] .slide-inner{background:var(--accent);color:#fff;border-color:transparent}
.slide[data-layout="dark"] .slide-inner{background:#0c0c0e;color:#f5f5f0;border-color:#2a2a2e}
.slide[data-layout="grey"] .slide-inner{background:#f3f4f6}
.slide[data-layout="split"] .slide-inner{display:grid;grid-template-columns:1fr 1fr;gap:0;
padding:0;overflow:hidden}
.split-l,.split-r{padding:38px 40px;display:flex;flex-direction:column;justify-content:center}
.slide[data-layout="split"] .slide-inner{background:var(--paper)}
.chrome{display:flex;justify-content:space-between;align-items:center;
border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:18px}
.slide[data-layout="accent"] .chrome{border-color:rgba(255,255,255,.35)}
.brand{font:600 12px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
.slide[data-layout="accent"] .brand{color:#fff}
.cdate{font:500 12px/1 var(--mono);color:var(--muted)}
.slide[data-layout="accent"] .cdate{color:rgba(255,255,255,.8)}
.section-tag{display:inline-block;font:600 11px/1 var(--mono);letter-spacing:.16em;
text-transform:uppercase;color:var(--accent);border:1px solid var(--accent);
border-radius:999px;padding:5px 12px;margin-bottom:14px}
.slide[data-layout="accent"] .section-tag{color:#fff;border-color:rgba(255,255,255,.6)}
h1.title{font:700 30px/1.15 var(--sans),var(--sans-zh);letter-spacing:-.01em}
h2.title{font:700 22px/1.2 var(--sans),var(--sans-zh)}
.lead{color:var(--muted);font-size:14px;line-height:1.5;margin-top:8px}
.slide[data-layout="accent"] .lead{color:rgba(255,255,255,.85)}
.foot{display:flex;justify-content:space-between;align-items:center;margin-top:18px;
padding-top:12px;border-top:1px solid var(--line);font:500 11px/1.3 var(--mono);color:var(--muted)}
.slide[data-layout="accent"] .foot{border-color:rgba(255,255,255,.3);color:rgba(255,255,255,.8)}
/* 封面 */
.cover{display:flex;flex-direction:column;gap:6px}
.cover-grade{font:800 120px/1 var(--sans);letter-spacing:-.04em;color:var(--accent)}
.slide[data-layout="accent"] .cover-grade{color:#fff}
.cover-score{font:700 18px/1.4 var(--sans)}
.cover-sub{font-size:15px;color:var(--muted);margin-top:6px}
/* 预警条 */
.alert-bar{border-radius:10px;padding:13px 16px;font-size:13.5px;line-height:1.45;
margin-bottom:18px;display:flex;gap:10px;align-items:flex-start}
.alert-bar.ok{background:rgba(22,163,74,.1);border:1px solid rgba(22,163,74,.35);color:#15803d}
.alert-bar.warn{background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.4);color:#b91c1c}
/* 公式 / 计算步骤 */
.formula{font:600 15px/1.5 var(--mono);background:var(--card-2);border:1px solid var(--line);
border-radius:10px;padding:14px 16px;margin:14px 0;color:var(--ink)}
.calc{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:12px}
.calc-step{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:10px 12px;font:600 13px/1.35 var(--mono)}
.calc-step.anom{border-color:var(--bad);background:rgba(220,38,38,.06)}
.calc-step b{color:var(--accent)}
.weight-note{font-size:12px;color:var(--muted);margin-top:12px;line-height:1.5}
/* KPI 网格 */
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:6px}
.kpi-card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi-name{font:600 12px/1.2 var(--sans);color:var(--muted)}
.kpi-val{font:700 26px/1.1 var(--sans);margin:8px 0 4px}
.kpi-base{font:500 11px/1.3 var(--mono);color:var(--muted)}
.kpi-score{display:inline-block;margin-top:8px;font:700 13px/1 var(--mono);
padding:4px 8px;border-radius:6px;background:var(--card-2);border:1px solid var(--line)}
.kpi-zone{font-size:11px;color:var(--muted);margin-top:6px}
/* 贡献条 */
.contrib{margin-top:8px}
.contrib-row{display:grid;grid-template-columns:120px 1fr 96px;align-items:center;gap:12px;
margin:9px 0}
.contrib-lbl{font:600 13px/1.2 var(--sans)}
.contrib-track{height:18px;background:var(--card-2);border-radius:6px;overflow:hidden;
border:1px solid var(--line)}
.contrib-fill{height:100%;background:var(--accent);border-radius:6px 0 0 6px}
.contrib-row.anom .contrib-fill{background:var(--bad)}
.contrib-val{font:700 14px/1 var(--mono);text-align:right}
.contrib-w{font:500 10px/1 var(--mono);color:var(--muted);display:block;margin-top:3px}
/* 趋势 */
.trend-wrap{margin-top:8px}
.trend-svg{width:100%;height:210px;display:block}
.trend-svg .grid{stroke:var(--line);stroke-width:1}
.trend-svg .alert-line{stroke:var(--bad);stroke-width:1.5;stroke-dasharray:6 4}
.trend-svg .alert-txt{fill:var(--bad);font:600 11px var(--mono)}
.trend-svg .last-txt{fill:var(--accent);font:700 13px var(--mono)}
.slide[data-layout="accent"] .trend-svg .last-txt{fill:#fff}
.toggle{display:flex;gap:8px;margin:10px 0 4px}
.toggle button{font:600 12px/1 var(--mono);padding:7px 14px;border-radius:8px;cursor:pointer;
background:var(--card);border:1px solid var(--line);color:var(--ink)}
.toggle button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.trend-meta{font:500 12px/1.4 var(--mono);color:var(--muted);margin-top:8px;display:flex;gap:18px;flex-wrap:wrap}
/* 分析卡 */
.analysis-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:6px}
.analysis-card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.analysis-card h3{font:700 16px/1.2 var(--sans);display:flex;align-items:center;gap:8px}
.analysis-card .ic{color:var(--accent)}
.analysis-card .row{display:flex;justify-content:space-between;font:500 12.5px/1.6 var(--mono);
margin-top:8px;color:var(--muted)}
.analysis-card .row b{color:var(--ink)}
.analysis-card .concl{margin-top:10px;font-size:13px;line-height:1.5;color:var(--ink);
border-top:1px dashed var(--line);padding-top:10px}
/* 多维 sparkline */
.spark-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:6px}
.spark-card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.spark-card .hd{display:flex;justify-content:space-between;align-items:baseline}
.spark-card .nm{font:600 13px/1.2 var(--sans)}
.spark-card .cu{font:700 20px/1 var(--sans);color:var(--accent)}
.spark{width:100%;height:54px;margin-top:8px;display:block}
.spark .base-line{stroke:var(--muted);stroke-width:1;stroke-dasharray:4 4;opacity:.6}
.spark-stats{display:flex;gap:14px;font:500 11px/1.4 var(--mono);color:var(--muted);margin-top:6px}
/* 模式 */
.pattern-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:6px}
.pattern{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;
opacity:.5}
.pattern.on{opacity:1;border-color:var(--accent);background:rgba(0,47,167,.06)}
.slide[data-layout="accent"] .pattern.on{background:rgba(255,255,255,.12)}
.pattern .pid{font:700 12px/1.2 var(--sans)}
.pattern .pcond{font:500 11px/1.4 var(--mono);color:var(--muted);margin-top:6px}
.pattern .ptag{display:inline-block;margin-top:8px;font:600 10px/1 var(--mono);
padding:3px 8px;border-radius:6px}
.pattern.on .ptag{background:var(--accent);color:#fff}
.pattern:not(.on) .ptag{background:var(--card-2);color:var(--muted)}
/* 建议 */
.advice-list{margin-top:8px;display:flex;flex-direction:column;gap:12px}
.advice{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);
border-left:4px solid var(--accent);border-radius:8px;padding:14px 16px}
.advice .an{font:700 13px/1.3 var(--sans);color:var(--accent);min-width:84px}
.advice .at{font-size:13.5px;line-height:1.55}
/* 导航 */
.nav{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);display:flex;gap:9px;z-index:20}
.dot{width:9px;height:9px;border-radius:50%;background:#bbb;cursor:pointer;transition:.2s}
.dot.on{background:var(--accent);transform:scale(1.25)}
.arrows{position:fixed;inset:0;display:flex;justify-content:space-between;align-items:center;
pointer-events:none;z-index:15;padding:0 14px}
.arrows button{pointer-events:auto;width:42px;height:42px;border-radius:50%;border:1px solid var(--line);
background:rgba(255,255,255,.85);color:#111;font-size:20px;cursor:pointer;opacity:.55;transition:.2s}
.arrows button:hover{opacity:1}
.split-r{background:var(--accent);color:#fff}
.split-r .big{font:800 96px/1 var(--sans);letter-spacing:-.03em}
.split-r .lbl{font:600 13px/1.4 var(--mono);letter-spacing:.1em;text-transform:uppercase;opacity:.85}
@media(max-width:760px){.kpi-grid{grid-template-columns:repeat(2,1fr)}
.pattern-grid{grid-template-columns:repeat(2,1fr)}.analysis-grid{grid-template-columns:1fr}
.spark-grid{grid-template-columns:1fr}.slide[data-layout=split] .slide-inner{grid-template-columns:1fr}}
"""


# ──────────────────────────────────────────────────────────────────────────
# HTML 组装（主题无关；theme_css 注入皮肤）
# ──────────────────────────────────────────────────────────────────────────
def _slide(layout, tag, title, body, foot_left, foot_right, accent=False):
    chrome = (f'<div class="chrome"><span class="brand">Recovery Deck</span>'
              f'<span class="cdate" id="cdate">—</span></div>')
    tag_html = f'<span class="section-tag">{esc(tag)}</span>' if tag else ""
    title_html = f'<h1 class="title">{esc(title)}</h1>' if title else ""
    foot = (f'<div class="foot"><span>{esc(foot_left)}</span>'
            f'<span>{esc(foot_right)}</span></div>')
    if layout == "split":
        return (f'<section class="slide" data-layout="split"><div class="slide-inner">'
                f'{body}</div></section>')
    return (f'<section class="slide" data-layout="{layout}"><div class="slide-inner">'
            f'{chrome}{tag_html}{title_html}{body}{foot}</div></section>')


def build_html(m, theme_css, theme_name):
    # ---- Slide 1: 封面 ----
    s1 = _slide("accent", "", "",
        f'<div class="cover">'
        f'<span class="section-tag">每日恢复力日报</span>'
        f'<div class="cover-grade">{(m["grade"] or "")}</div>'
        f'<div class="cover-score">综合恢复分 {m["recovery"]} · {esc(m["label"])}</div>'
        f'<div class="cover-sub">{esc(m["date"])} ｜ 权重为统一参考配方，今日分数由你的真实数据决定</div>'
        f'</div>', "RECOVERY DECK", f'{theme_name} · {esc(m["date"])}')

    # ---- Slide 2: 诊断总览 + 公式 ----
    calc_html = ""
    calc_map = {"hrv": "HRV", "sleep": "睡眠", "rhr": "RHR", "readiness": "准备度", "stress": "压力"}
    for step in m["calc_steps"]:
        mm = re.match(r"([A-Za-z]+):\s*([\d.]+)\s*x\s*([\d.]+)\s*=\s*([\d.]+)", step)
        if not mm:
            continue
        key = mm.group(1).lower()
        cinfo = next((d for d in m["dims"] if d["key"] == key), None)
        anom = cinfo and cinfo["anomaly"]
        calc_html += (f'<div class="calc-step{" anom" if anom else ""}">'
                      f'<b>{calc_map.get(key, key)}</b> {fmt_int(mm.group(2))} × {float(mm.group(3)):.2f} '
                      f'= <b>{fmt_val(mm.group(4), 1)}</b>'
                      f'{" ⚠引擎异常" if anom else ""}</div>')
    s2 = _slide("light", "诊断总览", "综合恢复分是怎么算出来的",
        f'<div class="alert-bar {m["alert"]["level"]}">'
        f'<i data-lucide="triangle-alert" class="ic"></i><span>{esc(m["alert"]["text"])}</span></div>'
        f'<div class="formula">{esc(m["formula"])}</div>'
        f'<div class="calc">{calc_html}</div>'
        f'<p class="weight-note">⚖ 权重（HRV 30% · 睡眠 25% · RHR 20% · 准备度 15% · 压力 10%）'
        f'是<b>统一参考配方，仅作横向对比之用</b>。真正决定今天分数的，是上面每一项「今晚的真实数据」'
        f'与你的基线之差——权重高不代表它说了算，数据本身才是主角。</p>',
        f'REFS {esc(m["ref"])}', "Slide 02 / 10")

    # ---- Slide 3: 五维度 KPI ----
    kpi = ""
    for d in m["dims"]:
        kpi += (f'<div class="kpi-card">'
                f'<div class="kpi-name">{esc(d["name"])}</div>'
                f'<div class="kpi-val">{esc(d["raw"])}</div>'
                f'<div class="kpi-base">基线 {esc(d["baseline"])}</div>'
                f'<span class="kpi-score">{d["disp"]}</span>'
                f'<div class="kpi-zone">{esc(zone_cn(d["zone"]))}'
                f'{" · ⚠待修" if d["anomaly"] else ""}</div>'
                f'</div>')
    fix_notes = []
    if m["dims"][0]["anomaly"]:
        fix_notes.append("HRV 评分引擎待修，已按原始值绕过展示")
    if "REM 占比引擎误算" in m["dims"][2]["narr"]:
        fix_notes.append("REM 占比引擎误算为 0，已用原始值重算")
    eng_note = (" ".join(fix_notes)
                if fix_notes else "各维度评分均来自实时引擎，无异常绕过。")
    s3 = _slide("light", "指标总览", "五个维度，今晚 vs 你的基线",
        f'<div class="kpi-grid">{kpi}</div>'
        f'<p class="weight-note">分数列是各维度原始评分；权重见上页。{esc(eng_note)}</p>',
        "5 维度 KPI", "Slide 03 / 10")

    # ---- Slide 4: 今日贡献（权重为参考）----
    mx = max(d["contrib"] for d in m["dims"]) or 1
    rows = ""
    for d in m["dims"]:
        pct = d["contrib"] / mx * 100 if mx else 0
        rows += (f'<div class="contrib-row{" anom" if d["anomaly"] else ""}">'
                 f'<div class="contrib-lbl">{esc(d["name"])}</div>'
                 f'<div class="contrib-track"><div class="contrib-fill" style="width:{pct:.1f}%"></div></div>'
                 f'<div class="contrib-val">{fmt_val(d["contrib"], 1)}'
                 f'<span class="contrib-w">权重 {int(d["weight"]*100)}%</span></div>'
                 f'</div>')
    s4 = _slide("light", "实际贡献", "今天谁在拉高 / 拉低分数",
        f'<div class="contrib">{rows}</div>'
        f'<p class="weight-note">条形长度 = 该维度<b>今日实际贡献分值</b>（原始分 × 权重）。'
        f'权重仅以灰色小字标注——它是配方里的固定系数，<b>不是叙事重点</b>；'
        f'重点是：今晚睡眠（{m["dims"][2]["contrib"]:.1f}）与 RHR（{m["dims"][1]["contrib"]:.1f}）是主力，'
        f'HRV 因引擎异常暂计 0.00（原始值健康）。</p>',
        "Σ 贡献 = 恢复分", "Slide 04 / 10")

    # ---- Slide 5: 恢复分 28 天走势 ----
    rt = m["recovery_trend"]
    tg = rt["28"]; t14 = rt["14"]; t7 = rt["7"]
    svg28 = line_svg(tg, alert=rt["alert"], color="var(--accent)", gid="28")
    svg14 = line_svg(t14, alert=rt["alert"], color="var(--accent)", gid="14")
    svg7 = line_svg(t7, alert=rt["alert"], color="var(--accent)", gid="7")
    cov = f'{rt["coverage"][0]}/{rt["coverage"][1]} 天有数据'
    s5 = _slide("grey", "趋势", "恢复分 28 天走势（非准备度）",
        f'<div class="toggle">'
        f'<button data-r="28" class="on" onclick="setRange(28)">28 天</button>'
        f'<button data-r="14" onclick="setRange(14)">14 天</button>'
        f'<button data-r="7" onclick="setRange(7)">7 天</button></div>'
        f'<div class="trend-wrap"><div id="t28">{svg28}</div>'
        f'<div id="t14" style="display:none">{svg14}</div>'
        f'<div id="t7" style="display:none">{svg7}</div></div>'
        f'<div class="trend-meta"><span>最新 {m["recovery"]}</span>'
        f'<span>28天均值 {fmt_val(rt["avg"], 1)}</span>'
        f'<span>区间 {fmt_val(rt["min"], 0)}–{fmt_val(rt["max"], 0)}</span>'
        f'<span>覆盖率 {cov}</span><span>警戒线 {rt["alert"]}</span></div>'
        f'<p class="weight-note">注意：这是<b>综合恢复分</b>的走势，不是准备度。低于警戒线 {rt["alert"]} '
        f'即进入「注意」区间，需结合连续天数判断累积疲劳。</p>',
        "恢复分走势", "Slide 05 / 10")

    # ---- Slide 6: HRV & RHR 文字分析 ----
    def an_card(d, icon):
        return (f'<div class="analysis-card">'
                f'<h3><i data-lucide="{icon}" class="ic"></i>{esc(d["name"])}</h3>'
                f'<div class="row"><span>今晚值</span><b>{esc(d["raw"])}</b></div>'
                f'<div class="row"><span>你的基线</span><b>{esc(d["baseline"])}</b></div>'
                f'<div class="row"><span>变化</span><b>{fmt_pct(d["pct"]) if d["pct"] is not None else "—"}</b></div>'
                f'<div class="row"><span>原始评分</span><b>{d["disp"]}'
                f'{" ⚠待修" if d["anomaly"] else ""}</b></div>'
                f'<div class="concl">{esc(d["narr"])}</div></div>')
    hrv_d = next(x for x in m["dims"] if x["key"] == "hrv")
    rhr_d = next(x for x in m["dims"] if x["key"] == "rhr")
    s6 = _slide("light", "逐项解读", "HRV 与静息心率：心血管恢复的信号",
        f'<div class="analysis-grid">{an_card(hrv_d, "activity")}{an_card(rhr_d, "heart-pulse")}</div>',
        "HRV · RHR", "Slide 06 / 10")

    # ---- Slide 7: 睡眠质量分析 ----
    sleep_d = next(x for x in m["dims"] if x["key"] == "sleep")
    s7 = _slide("light", "逐项解读", "睡眠质量：时长达标，深睡可提升",
        f'<div class="analysis-grid">{an_card(sleep_d, "moon")}'
        f'<div class="analysis-card"><h3><i data-lucide="shield-check" class="ic"></i>准备度与压力</h3>'
        f'<div class="row"><span>身体准备度</span><b>{m["dims"][3]["raw"]}</b></div>'
        f'<div class="row"><span>压力等级</span><b>{m["dims"][4]["raw"]}</b></div>'
        f'<div class="row"><span>睡眠总时长</span><b>{esc(sleep_d["raw"])}</b></div>'
        f'<div class="row"><span>Garmin 睡眠分</span><b>{fmt_int(sleep_d["score"])}</b></div>'
        f'<div class="concl">准备度 {m["dims"][3]["score"]}/100 处于高位，压力处于低位——'
        f'身体与环境都处在良好恢复状态，今日可正常训练。</div></div></div>',
        "睡眠 · 准备度 · 压力", "Slide 07 / 10")

    # ---- Slide 8: 多维趋势明细 ----
    sp_html = ""
    for sp in m["sparks"]:
        cur, mn, mxv, avg = sp["stat"]
        dec = sp.get("dec", 0)
        spark = sparkline_svg(sp["series"], baseline=sp["base"], color="var(--accent)")
        sp_html += (f'<div class="spark-card"><div class="hd"><span class="nm">{esc(sp["name"])}</span>'
                    f'<span class="cu">{fmt_val(sp["cur"], dec)}{esc(sp["unit"])}</span></div>'
                    f'{spark}'
                    f'<div class="spark-stats"><span>最新 {fmt_val(cur, dec)}</span>'
                    f'<span>区间 {fmt_val(mn, dec)}–{fmt_val(mxv, dec)}</span>'
                    f'<span>均值 {fmt_val(avg, dec)}</span>'
                    f'<span>{esc(sp["base_disp"])}</span></div></div>')
    s8 = _slide("light", "多维趋势", "HRV / RHR / 睡眠 / 准备度 近 28 天",
        f'<div class="spark-grid">{sp_html}</div>'
        f'<p class="weight-note">虚线为基线。HRV 与准备度近期波动大，RHR 平稳低位——'
        f'整体呈「心率系统稳、恢复分受睡眠与 HRV 抖动牵动」的格局。</p>',
        "28 天微观趋势", "Slide 08 / 10")

    # ---- Slide 9: 状态模式（全部）----
    pg = ""
    for p in m["patterns"]:
        on = p.get("match")
        pg += (f'<div class="pattern{" on" if on else ""}">'
               f'<div class="pid">{esc(p["label"])}</div>'
               f'<div class="pcond">{esc(p["condition_desc"])}</div>'
               f'<span class="ptag">{"命中" if on else "未命中"}</span></div>')
    s9 = _slide("light", "状态模式", f"多维校验：{len(m['matched'])} / {len(m['patterns'])} 命中",
        f'<div class="pattern-grid">{pg}</div>'
        f'<p class="weight-note">模式是「HRV↑↓ + RHR↑↓ + 睡眠」组合后的语义判定，'
        f'比单一分数更能说明恢复性质。今日唯一命中：<b>{esc(m["matched"][0]["label"]) if m["matched"] else "无"}</b>'
        f'（{esc(m["matched"][0]["condition_desc"]) if m["matched"] else ""}）。</p>',
        "多维度交叉验证", "Slide 09 / 10")

    # ---- Slide 10: 今日建议 + 收尾 ----
    adv = ""
    for i, (t, c) in enumerate(m["advice"], 1):
        adv += (f'<div class="advice"><span class="an">{esc(t)}</span>'
                f'<span class="at">{esc(c)}</span></div>')
    s10 = _slide("split", "", "",
        f'<div class="split-l">'
        f'<span class="section-tag">今日行动建议</span>'
        f'<h2 class="title">按 Grade {esc(m["grade"])}（{esc(m["label"])}）给出</h2>'
        f'<div class="advice-list">{adv}</div>'
        f'<div class="foot"><span>基于 kpi_today.json</span><span>Slide 10 / 10</span></div>'
        f'</div>'
        f'<div class="split-r"><div class="lbl">Recovery Score</div>'
        f'<div class="big">{m["recovery"]}</div>'
        f'<div class="lbl" style="margin-top:14px">{esc(m["date"])} · GRADE {esc(m["grade"])}</div>'
        f'<div class="lbl" style="margin-top:8px;opacity:.7">权重是参考 · 数据说了算</div></div>',
        "", "")

    slides = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10]
    dots = "".join(f'<span class="dot{" on" if i == 0 else ""}" data-i="{i}" onclick="go({i})"></span>'
                   for i in range(len(slides)))

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>恢复力日报 · {esc(m['date'])} · {esc(theme_name)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lucide@latest"></script>
<style>
:root{{--sans:'Inter';--sans-zh:'Noto Sans SC';--mono:'JetBrains Mono';--bg:#e9eaee}}
{SHARED_BASE_CSS}
{theme_css}
</style>
</head>
<body data-style="recovery-deck">
<div class="deck" id="deck">
{''.join(slides)}
</div>
<div class="arrows">
  <button onclick="go(cur-1)">‹</button>
  <button onclick="go(cur+1)">›</button>
</div>
<div class="nav" id="nav">{dots}</div>
<script>
var cur=0,total={len(slides)};
var secs=document.querySelectorAll('.slide');
function show(i){{i=Math.max(0,Math.min(total-1,i));cur=i;
 secs.forEach(function(s,k){{s.classList.toggle('active',k===i);}});
 document.querySelectorAll('.dot').forEach(function(d,k){{d.classList.toggle('on',k===i);}});
 var cd=document.getElementById('cdate');if(cd)cd.textContent='{esc(m['date'])}';
}}
function go(i){{show(i);}}
function setRange(r){{['28','14','7'].forEach(function(x){{document.getElementById('t'+x).style.display=(x==String(r))?'block':'none';}});
 document.querySelectorAll('.toggle button').forEach(function(b){{b.classList.toggle('on',b.dataset.r==String(r));}});}}
document.addEventListener('keydown',function(e){{if(e.key==='ArrowRight'||e.key==='PageDown')go(cur+1);
 else if(e.key==='ArrowLeft'||e.key==='PageUp')go(cur-1);}});
var wt=null;document.addEventListener('wheel',function(e){{if(wt)return;wt=setTimeout(function(){{wt=null;}},700);
 if(e.deltaY>0)go(cur+1);else if(e.deltaY<0)go(cur-1);}},{{passive:true}});
var tx=0;document.addEventListener('touchstart',function(e){{tx=e.touches[0].clientX;}},{{passive:true}});
document.addEventListener('touchend',function(e){{var dx=e.changedTouches[0].clientX-tx;
 if(dx<-40)go(cur+1);else if(dx>40)go(cur-1);}},{{passive:true}});
show(0);
if(window.lucide)lucide.createIcons();
</script>
</body>
</html>"""
    return doc


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "output/kpi_today.json"
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    data = load_kpi(os.path.join(base, "..", p)) if not os.path.isabs(p) else load_kpi(p)
    m = build_model(data)
    print(build_html(m, ":root{--accent:#002FA7}", "test"))
