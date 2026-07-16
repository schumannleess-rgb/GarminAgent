#!/usr/bin/env python3
"""Regenerate output/kpi_today.json with full history from daily_health.json + advisor scores."""
import json, sys, math, logging
from datetime import date, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("rebuild_kpi")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from garmin_agent.config import DATA_DIR, OUTPUT_DIR

# ── Score configs (from morning_advisor.py) ──
HRV_ANCHORS = [(0.10,70,"spike"),(0.05,85,"green_high"),(0.00,75,"green_normal_mid"),
               (-0.05,60,"green_low_yellow_high"),(-0.08,40,"yellow_low_red_high"),
               (-0.15,10,"red_deep"),(-0.20,0,"severe")]
RHR_ANCHORS = [(-3,95,"very_low"),(0,75,"baseline"),(3,55,"mild_fatigue"),(6,30,"fatigue"),(10,0,"severe")]
SLEEP_WEIGHTS = {"duration":0.30,"deep":0.35,"rem":0.15,"awake":0.20}
RECOVERY_WEIGHTS = {"hrv":0.30,"sleep":0.25,"rhr":0.20,"readiness":0.15,"stress":0.10}
_SLEEP_DURATION_ANCHORS = [(5,10),(6,45),(7,80),(9,100)]
_SLEEP_DEEP_ANCHORS = [(5,20),(10,60),(25,100)]
_SLEEP_REM_ANCHORS = [(10,30),(18,50),(25,100)]
_AWAKE_SCORES = {0:100, 1:80, 2:60}
_AWAKE_FRAG_BASE, _AWAKE_FRAG_STEP, _AWAKE_FRAG_MIN = 45, 15, 0
_SLEEP_DURATION_EXCESS_DECAY = 20
_SLEEP_DEEP_MAX_SCORE = 90
_SLEEP_REM_MAX_SCORE = 85
_SECS_PER_HOUR = 3600
_HRV_HISTORY_DAYS, _RHR_HISTORY_DAYS, _SLEEP_HISTORY_DAYS, _READINESS_HISTORY_DAYS = 14, 28, 7, 7
_STRESS_ANCHORS = [(0,95,"very_low"),(25,85,"low"),(50,60,"moderate"),(75,25,"high"),(100,0,"severe")]

GRADE_THRESHOLDS = [(85,"A","状态极佳","EXCELLENT"),(70,"B","状态良好","GOOD"),
                    (55,"C","需要注意","CAUTION"),(40,"D","恢复不足","POOR")]

def _safe_mean(values):
    return round(sum(values)/len(values)) if values else 0

def _segments(anchors):
    segs = []
    for i in range(len(anchors)-1):
        p1,s1,l1 = anchors[i]; p2,s2,l2 = anchors[i+1]
        segs.append({"p_min":p1,"p_max":p2,"score_at_min":s1,"slope":(s2-s1)/(p2-p1),"zone":l2})
    return segs

# HRV_ANCHORS 是降序(p 从高到低),_segments 需升序才能生成有效分段;
# 排序后用升序副本建分段,否则正区间分段 p_min>p_max 永不命中 -> 兜底 score=0。
_HRV_SEGS = _segments(sorted(HRV_ANCHORS, key=lambda a: a[0]))
_RHR_SEGS = _segments(RHR_ANCHORS); _STRESS_SEGS = _segments(_STRESS_ANCHORS)

def score_hrv(last_night, weekly):
    r = {"last_night_ms":last_night,"weekly_avg_ms":weekly,"fallback_used":False,
         "ln_last_night":None,"ln_baseline":None,"pct_change":None,"pct_change_pct":None,
         "anchors":[{"pct_change":a,"score":s,"label":l} for a,s,l in HRV_ANCHORS]}
    if last_night <= 0 or weekly <= 0:
        r.update({"score":75,"zone":"FALLBACK"}); return r
    cl = math.log(last_night); bl = math.log(weekly); p = (cl-bl)/bl
    r["ln_last_night"]=round(cl,4); r["ln_baseline"]=round(bl,4)
    r["pct_change"]=round(p,6); r["pct_change_pct"]=round(p*100,2)
    if p > HRV_ANCHORS[0][0]: s,z = 70,"spike"
    else:
        for seg in _HRV_SEGS:
            if seg["p_min"]<=p<=seg["p_max"]:
                s=seg["score_at_min"]+(p-seg["p_min"])*seg["slope"]; z=seg["zone"]; break
        else: s,z = 0,"SEVERE"
    # 0.05<p<0.10 落在 (0.05->0.10) 分段, zone 取自上锚 spike, 实为健康高位, 纠回 green_high
    if z == "spike" and p <= HRV_ANCHORS[0][0]:
        z = "green_high"
    r["score"]=round(min(100,max(0,s))); r["zone"]=z; return r

def score_rhr(current, baseline):
    d = current - baseline
    r = {"current_bpm":current,"baseline_bpm":baseline,"deviation":d,
         "deviation_bpm":f"{d:+d} bpm",
         "anchors":[{"deviation_bpm":a,"score":s,"label":l} for a,s,l in RHR_ANCHORS]}
    for seg in _RHR_SEGS:
        if seg["p_min"]<=d<=seg["p_max"]:
            s=seg["score_at_min"]+(d-seg["p_min"])*seg["slope"]; break
    else: s = RHR_ANCHORS[0][1]
    r["score"]=round(min(100,max(0,s))); r["zone"]=RHR_ANCHORS[[a for a,_,_ in RHR_ANCHORS].index(d if d in [a for a,_,_ in RHR_ANCHORS] else 0)][2] if d in [a for a,_,_ in RHR_ANCHORS] else "baseline"
    # Simple zone from deviation
    if d <= -3: r["zone"] = "very_low"
    elif d <= 0: r["zone"] = "baseline"
    elif d <= 3: r["zone"] = "mild_fatigue"
    elif d <= 6: r["zone"] = "fatigue"
    else: r["zone"] = "severe"
    return r

def score_sleep(total_sec, deep_sec, rem_sec, awake_cnt, garmin_score=None):
    r = {"total_seconds":total_sec,"deep_seconds":deep_sec,"rem_seconds":rem_sec,
         "awake_count":awake_cnt,"garmin_score_used":False}
    if garmin_score is not None:
        r["garmin_score_used"]=True; r["score"]=garmin_score; r["sub_scores"]={}; return r
    r["garmin_score_used"]=False
    th=total_sec/_SECS_PER_HOUR; dp=(deep_sec/total_sec*100) if total_sec>0 else 0
    rp=(rem_sec/total_sec*100) if total_sec>0 else 0
    r["total_hours"]=round(th,2); r["deep_pct"]=round(dp,2); r["rem_pct"]=round(rp,2)
    # duration
    da=_SLEEP_DURATION_ANCHORS
    if th<da[0][0]: ds,dz=da[0][1],"SEVERE_SHORT"
    elif th<da[1][0]: ds=round(da[0][1]+(th-da[0][0])*35,1);dz="SHORT"
    elif th<da[2][0]: ds=round(da[1][1]+(th-da[1][0])*35,1);dz="MODERATE"
    elif th<=da[3][0]: ds=round(da[2][1]+(th-da[2][0])*10,1);dz="IDEAL"
    else: ds=round(max(50,100-(th-da[3][0])*_SLEEP_DURATION_EXCESS_DECAY),1);dz="EXCESS"
    # deep
    dda=_SLEEP_DEEP_ANCHORS
    if dp<dda[0][0]: des,dez=20,"SEVERE_LOW"
    elif dp<dda[1][0]: des=round(dda[0][1]+(dp-dda[0][0])*8,1);dez="LOW"
    elif dp<=dda[2][0]: des=round(dda[1][1]+(dp-dda[1][0])*(40/15),1);dez="IDEAL"
    else: des=_SLEEP_DEEP_MAX_SCORE;dez="HIGH"
    # rem
    ra=_SLEEP_REM_ANCHORS
    if rp<ra[0][0]: res,rez=round(30+rp*2,1),"LOW"
    elif rp<ra[1][0]: res=round(ra[0][1]+(rp-ra[0][0])*2.5,1);rez="MODERATE"
    elif rp<=ra[2][0]: res=round(ra[1][1]+(rp-ra[1][0])*(30/7),1);rez="IDEAL"
    else: res=_SLEEP_REM_MAX_SCORE;rez="HIGH"
    # awake
    if awake_cnt in _AWAKE_SCORES: aws,az=_AWAKE_SCORES[awake_cnt],["NONE","ONCE","TWICE"][awake_cnt]
    else: aws=round(max(_AWAKE_FRAG_MIN,_AWAKE_FRAG_BASE-(awake_cnt-3)*_AWAKE_FRAG_STEP),1);az="FRAGMENTED"
    r["sub_scores"]={"duration":{"value":ds,"zone":dz,"weight":SLEEP_WEIGHTS["duration"]},
                     "deep":{"value":des,"zone":dez,"weight":SLEEP_WEIGHTS["deep"]},
                     "rem":{"value":res,"zone":rez,"weight":SLEEP_WEIGHTS["rem"]},
                     "awake":{"value":aws,"zone":az,"weight":SLEEP_WEIGHTS["awake"]}}
    r["weights"]=dict(SLEEP_WEIGHTS)
    score=ds*SLEEP_WEIGHTS["duration"]+des*SLEEP_WEIGHTS["deep"]+res*SLEEP_WEIGHTS["rem"]+aws*SLEEP_WEIGHTS["awake"]
    r["score"]=round(score); return r

def score_readiness(garmin_score):
    capped=min(garmin_score,100)
    if capped>=80: zone="GREEN"
    elif capped>=60: zone="YELLOW"
    else: zone="RED"
    return {"original_score":garmin_score,"score":capped,"zone":zone}

def score_stress(stress_level):
    s=max(0,min(100,int(stress_level)))
    r={"stress_level":s,"anchors":[{"stress_level":a,"score":sc,"label":l} for a,sc,l in _STRESS_ANCHORS]}
    for seg in _STRESS_SEGS:
        if seg["p_min"]<=s<=seg["p_max"]:
            score=seg["score_at_min"]+(s-seg["p_min"])*seg["slope"]; zone=seg.get("zone",""); break
    else: score,zone=0,"SEVERE"
    r["score"]=round(min(100,max(0,score))); r["zone"]=zone; return r

def compute_recovery(hrv_s, sleep_s, rhr_s, ready_s, stress_s=0):
    score=round(hrv_s*RECOVERY_WEIGHTS["hrv"]+sleep_s*RECOVERY_WEIGHTS["sleep"]+
                rhr_s*RECOVERY_WEIGHTS["rhr"]+ready_s*RECOVERY_WEIGHTS["readiness"]+
                stress_s*RECOVERY_WEIGHTS["stress"])
    score=max(0,min(100,score))
    for th,grade,label,zone in GRADE_THRESHOLDS:
        if score>=th: break
    else: grade,label,zone="F","需要休息","CRITICAL"
    steps=[f"HRV: {hrv_s} x 0.30 = {hrv_s*0.30:.2f}",
           f"Sleep: {sleep_s} x 0.25 = {sleep_s*0.25:.2f}",
           f"RHR: {rhr_s} x 0.20 = {rhr_s*0.20:.2f}",
           f"Readiness: {ready_s} x 0.15 = {ready_s*0.15:.2f}",
           f"Stress: {stress_s} x 0.10 = {stress_s*0.10:.2f}",
           f"Total: {hrv_s*0.30+sleep_s*0.25+rhr_s*0.20+ready_s*0.15+stress_s*0.10:.2f} -> {score}"]
    return {"recovery_score":score,"weights":dict(RECOVERY_WEIGHTS),"grade":grade,
            "label":label,"zone":zone,"calculation_steps":steps,
            "formula":"recovery = HRV x 0.30 + Sleep x 0.25 + RHR x 0.20 + Readiness x 0.15 + Stress x 0.10",
            "reference":"§4.6, [R2] Buchheit 2014, [R16] Ohayon 2004, [R12] Bosquet 2003, [R21] Garmin"}

def compute_baselines(hrv_14d, rhr_28d, sleep_28d):
    hrv_vals=[h["value"] for h in hrv_14d if h.get("value",0)>0]
    rhr_vals=[h["value"] for h in rhr_28d if h.get("value",0)>0]
    # 基线用最近 7 天（输入含 28 天）
    sleep_recent = sleep_28d[:7]
    sleep_tots=[h["total_sec"] for h in sleep_recent if h.get("total_sec",0)>0]
    deep_pcts=[]
    for h in sleep_recent:
        ts=h.get("total_sec",0); ds=h.get("deep_sec",0)
        if ts>0: deep_pcts.append(ds/ts*100)
    return {
        "hrv_baseline_7d": _safe_mean(hrv_vals) if hrv_vals else 0,
        "rhr_baseline_28d": _safe_mean(rhr_vals) if rhr_vals else 0,
        "sleep_baseline_7d": {
            "total_seconds": _safe_mean(sleep_tots),
            "total_hours": round(_safe_mean(sleep_tots)/_SECS_PER_HOUR,2) if sleep_tots else 0,
            "deep_pct_avg": round(sum(deep_pcts)/len(deep_pcts),1) if deep_pcts else 0,
        },
        "formulas": {
            "hrv_baseline": "rolling_mean(last_7_nights_HRV), Plews 2014 [R7]",
            "rhr_baseline": "rolling_mean(last_28_days_RHR), Bosquet 2003 [R12]",
            "sleep_baseline": "rolling_mean(last_7_days_total_sleep), Ohayon 2004 [R16]",
        }
    }

def cross_dimension_validation(hrv_pct, rhr_dev, sleep_h, awake_cnt, deep_pct):
    patterns = [
        {"id":"IDEAL_RECOVERY","label":"理想恢复","condition_desc":"HRV↑↑ RHR↓→ 睡眠优",
         "ref":"[R2] Buchheit 2014","match":hrv_pct>=-5 and abs(rhr_dev)<=3 and sleep_h>=7 and awake_cnt<=1},
        {"id":"SYMPATHETIC_FATIGUE","label":"交感疲劳","condition_desc":"HRV↓↓ RHR↑↑ 睡眠差",
         "ref":"[R10] Plews 2013","match":hrv_pct<-8 and rhr_dev>3 and (sleep_h<6 or awake_cnt>=3)},
        {"id":"PARASYMPATHETIC_REBOUND","label":"副交感反弹","condition_desc":"HRV↑↑↑ RHR↓↓ 睡眠中",
         "ref":"[R9] Recovery Tower Spike","match":hrv_pct>10 and rhr_dev<-3},
        {"id":"SLEEP_DEBT","label":"睡眠债务疲劳","condition_desc":"HRV↓ RHR→ 睡眠差·短",
         "ref":"[R16] Ohayon 2004","match":-8<=hrv_pct<-5 and abs(rhr_dev)<=3 and (sleep_h<6 or deep_pct<10)},
        {"id":"HIGH_LOAD_ADAPTATION","label":"高负荷适应","condition_desc":"HRV↓ RHR↑ 睡眠中",
         "ref":"[R22] Chalencon 2012","match":hrv_pct<-5 and 0<rhr_dev<=3},
    ]
    matched=[p for p in patterns if p["match"]]
    return {"num_patterns_checked":len(patterns),"patterns_checked":patterns,
            "num_matched":len(matched),"matched_patterns":matched}

def check_trend(recent_scores, window=28, threshold=60, streak=3):
    ws=recent_scores[-window:] if len(recent_scores)>=window else list(recent_scores)
    low_streak=max_streak=0
    for s in ws:
        if s<threshold: low_streak+=1; max_streak=max(max_streak,low_streak)
        else: low_streak=0
    alert=None
    if max_streak>=streak:
        alert=f"连续 {max_streak} 天恢复评分 < {threshold} — NFOR 高风险，建议安排主动恢复日。"
    return {"low_streak":max_streak,"window_checked":len(ws),"threshold":threshold,
            "alert":alert,"recent_scores_in_window":ws}

# ── Load daily_health.json ──
with open(DATA_DIR / "daily_health.json", encoding="utf-8") as f:
    raw = json.load(f)
days = raw.get("days", {})
valid_dates = sorted(days.keys(), reverse=True)
target_date = valid_dates[0]  # latest
logger.info(f"Using latest date: {target_date} ({len(valid_dates)} days available)")

day = days[target_date]

# ── Raw inputs ──
awake_cnt = day.get("awake_count") or 0
hrv_raw = {"last_night": day.get("hrv_last_night_avg") or 0,
           "weekly_avg": day.get("hrv_weekly_avg") or 0,
           "status": day.get("hrv_status") or ""}

# ── History ──
def _filter_valid(field, max_days):
    items = [{"date":d,"value":v[field]} for d,v in days.items()
             if isinstance(v,dict) and v.get(field) is not None]
    items.sort(key=lambda x:x["date"], reverse=True)
    return items[:max_days]

hrv_14d = _filter_valid("hrv_last_night_avg", 14)
rhr_28d = _filter_valid("resting_hr", 28)
sleep_28d = [{"date":d,"total_sec":int(v["sleep_seconds"]),"deep_sec":int(v.get("deep_sleep_seconds") or 0)}
            for d,v in sorted(days.items(), reverse=True)[:28]
            if isinstance(v,dict) and v.get("sleep_seconds")]
rd_28d = _filter_valid("training_readiness_score", 30)
rd_28d_full = [{"date":r["date"],"score":r["value"],
               "level":days[r["date"]].get("training_readiness_level","")} for r in rd_28d]

# ── Calendar-window 28d series (B 口径: 严格 28 个日历日, 缺测为 null) ──
# 固定以 target_date 为终点, 向前数 27 天, 共 28 个日历日; 当天无数据则 value=null。
# 顺序: 最新在前(降序), 与 hrv_14d / rhr_28d 约定一致。
def _build_cal_28d(extract):
    latest = date.fromisoformat(target_date)
    out = []
    for i in range(27, -1, -1):
        d = (latest - timedelta(days=i)).isoformat()
        e = days.get(d)
        out.append({"date": d, "value": extract(e) if e else None})
    return out

hrv_cal_28d = _build_cal_28d(
    lambda e: (e.get("hrv_last_night_avg") if (e.get("hrv_last_night_avg") or 0) >= 1 else None))
rhr_cal_28d = _build_cal_28d(
    lambda e: (e.get("resting_hr") if (e.get("resting_hr") or 0) >= 1 else None))
sleep_cal_28d = _build_cal_28d(
    lambda e: ({"total_sec": int(e.get("sleep_seconds") or 0),
                "deep_sec": int(e.get("deep_sleep_seconds") or 0),
                "garmin_score": e.get("sleep_score")}
               if (e.get("sleep_seconds") or 0) >= 1 else None))
readiness_cal_28d = _build_cal_28d(
    lambda e: ({"score": e.get("training_readiness_score"),
                "level": e.get("training_readiness_level")}
               if (e.get("training_readiness_score") or 0) >= 1 else None))

history = {"hrv_14d":hrv_14d,"rhr_28d":rhr_28d,"sleep_28d":sleep_28d,"readiness_28d":rd_28d_full,
           "hrv_cal_28d":hrv_cal_28d,"rhr_cal_28d":rhr_cal_28d,
           "sleep_cal_28d":sleep_cal_28d,"readiness_cal_28d":readiness_cal_28d}

# ── Baselines ──
baselines = compute_baselines(hrv_14d, rhr_28d, sleep_28d)

# ── Recovery score per-day (calendar window) ──
# 用全局基线在 28 个日历日上重建每日恢复分 composite, 缺测日(无 HRV)为 null。
def _recovery_of(e):
    if not e or (e.get("hrv_last_night_avg") or 0) < 1:
        return None
    return compute_recovery(
        score_hrv(e.get("hrv_last_night_avg") or 0, baselines["hrv_baseline_7d"])["score"],
        score_sleep(int(e.get("sleep_seconds") or 0), int(e.get("deep_sleep_seconds") or 0),
                    int(e.get("rem_sleep_seconds") or 0), e.get("awake_count") or 0, e.get("sleep_score"))["score"],
        score_rhr(e.get("resting_hr") or 0, baselines["rhr_baseline_28d"])["score"],
        score_readiness(e.get("training_readiness_score") or 0)["score"],
        score_stress(e.get("avg_stress_level") or 0)["score"]
    )["recovery_score"]
recovery_cal_28d = _build_cal_28d(_recovery_of)
history["recovery_cal_28d"] = recovery_cal_28d

# ── Dimension scores ──
hrv_result = score_hrv(hrv_raw["last_night"] or hrv_raw["weekly_avg"] or 0, baselines["hrv_baseline_7d"])
rhr_result = score_rhr(day.get("resting_hr") or 0, baselines["rhr_baseline_28d"])
sleep_result = score_sleep(
    int(day.get("sleep_seconds") or 0), int(day.get("deep_sleep_seconds") or 0),
    int(day.get("rem_sleep_seconds") or 0), awake_cnt, day.get("sleep_score"))
ready_result = score_readiness(day.get("training_readiness_score") or 0)
stress_result = score_stress(day.get("avg_stress_level") or 0)

dimension_scores = {"hrv":hrv_result,"rhr":rhr_result,"sleep":sleep_result,
                    "readiness":ready_result,"stress":stress_result}

# ── Composite ──
recovery = compute_recovery(hrv_result["score"], sleep_result["score"], rhr_result["score"],
                            ready_result["score"], stress_result["score"])

# ── Validation ──
hrv_pct = hrv_result.get("pct_change_pct") or 0
rhr_dev = rhr_result["deviation"]
sleep_h = (day.get("sleep_seconds") or 0) / _SECS_PER_HOUR
deep_pct = (day.get("deep_sleep_seconds") or 0) / (day.get("sleep_seconds") or 1) * 100 if day.get("sleep_seconds") else 0
validation = cross_dimension_validation(hrv_pct, rhr_dev, sleep_h, awake_cnt, deep_pct)

# ── Trend ──
# rd_28d_full 为降序(最新在前); check_trend 期望升序(最旧在前、最新在末尾),
# 因此先剔除“当日”避免重复, 再按日期升序排列, 最后追加当日,
# 确保窗口取的是最近 28 天, 而非数据里最旧的 28 天(断点所在)。
rd_hist = [r for r in rd_28d_full if r["date"] != target_date]
rd_sorted = sorted(rd_hist, key=lambda r: r["date"])  # 升序: 最旧 -> 最新
rd_scores = [r["score"] for r in rd_sorted]
rd_scores.append(ready_result["score"])  # 当日(最新)置于末尾
trend = check_trend(rd_scores, window=28)

# ── Derived ──
derived = {
    "hrv_pct_change": hrv_pct, "hrv_ln_change": hrv_result.get("pct_change"),
    "rhr_deviation_bpm": rhr_dev,
    "sleep_total_hours": round(sleep_h, 2), "sleep_deep_pct": round(deep_pct, 2),
    "sleep_rem_pct": sleep_result.get("rem_pct", 0),
    "stress_level": day.get("avg_stress_level") or 0,
    "stress_score": stress_result["score"], "stress_zone": stress_result["zone"],
    "training_load": day.get("training_load"), "acwr_percent": day.get("acwr_percent", 0),
    "readiness_score_original": day.get("training_readiness_score") or 0,
}

# ── Profile ──
profile = {
    "vo2max": day.get("vo2_max") or "", "bmi": day.get("bmi"),
    "device": "Forerunner 955 Solar", "fitness_age": "", "chronological_age": "",
    "training_status_phrase": day.get("training_status", "") or "RECOVERY",
    "acwr_percent": day.get("acwr_percent", 0),
    "total_steps": day.get("total_steps"), "total_distance_m": day.get("total_distance_m"),
    "active_calories": day.get("active_calories"),
    "avg_stress": day.get("avg_stress_level"), "max_stress": day.get("max_stress_level"),
    "min_hr": day.get("min_hr"), "max_hr": day.get("max_hr"),
    "body_battery_charged": day.get("body_battery_charged"),
    "body_battery_drained": day.get("body_battery_drained"), "avg_spo2": day.get("avg_spo2"),
}

raw_inputs = {
    "hrv": hrv_raw, "rhr": {"current_bpm": day.get("resting_hr") or 0},
    "sleep": {"total_seconds":int(day.get("sleep_seconds") or 0),
              "deep_seconds":int(day.get("deep_sleep_seconds") or 0),
              "rem_seconds":int(day.get("rem_sleep_seconds") or 0),
              "awake_count":awake_cnt, "garmin_sleep_score":day.get("sleep_score")},
    "readiness": {"score":day.get("training_readiness_score") or 0,
                  "level":day.get("training_readiness_level") or ""},
    "profile": profile, "race_predictions": {},
    "stress_raw": {"avg_stress_level":day.get("avg_stress_level") or 0,
                   "max_stress_level":day.get("max_stress_level") or 0},
}

# ── Assemble ──
result = {
    "date": target_date,
    "generated_at": date.today().strftime("%Y-%m-%d %H:%M:%S"),
    "engine_version": "2.0",
    "design_doc": "docs/design-morning-advisor.md",
    "references_count": 24,
    "data_source": f"local_db ({raw.get('latest_sync','')})",
    "latest_db_date": valid_dates[0],
    "raw_inputs": raw_inputs,
    "history": history,
    "baselines": baselines,
    "dimension_scores": dimension_scores,
    "composite": recovery,
    "multi_dimension_validation": validation,
    "trend": trend,
    "derived_metrics_summary": derived,
}

OUTPUT_DIR.mkdir(exist_ok=True)
out_path = OUTPUT_DIR / "kpi_today.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

logger.info(f"Written: {out_path}")
print(f"\n=== {out_path} ===")
print(f"  date: {result['date']}")
print(f"  recovery_score: {recovery['recovery_score']} ({recovery['grade']} {recovery['label']})")
print(f"  HRV: {hrv_result['score']} ({hrv_result['zone']})")
print(f"  RHR: {rhr_result['score']} ({rhr_result['zone']})")
print(f"  Sleep: {sleep_result['score']} (garmin={sleep_result['garmin_score_used']})")
print(f"  Readiness: {ready_result['score']} ({ready_result['zone']})")
print(f"  Stress: {stress_result['score']} ({stress_result['zone']})")
print(f"  history.hrv_14d: {len(history['hrv_14d'])} entries")
print(f"  history.rhr_28d: {len(history['rhr_28d'])} entries")
print(f"  history.sleep_28d: {len(history['sleep_28d'])} entries")
print(f"  history.readiness_28d: {len(history['readiness_28d'])} entries")
print(f"  history.hrv_cal_28d: {sum(1 for x in history['hrv_cal_28d'] if x['value'] is not None)}/{len(history['hrv_cal_28d'])} valid")
print(f"  history.rhr_cal_28d: {sum(1 for x in history['rhr_cal_28d'] if x['value'] is not None)}/{len(history['rhr_cal_28d'])} valid")
print(f"  history.sleep_cal_28d: {sum(1 for x in history['sleep_cal_28d'] if x['value'] is not None)}/{len(history['sleep_cal_28d'])} valid")
print(f"  history.readiness_cal_28d: {sum(1 for x in history['readiness_cal_28d'] if x['value'] is not None)}/{len(history['readiness_cal_28d'])} valid")
print(f"  history.recovery_cal_28d: {sum(1 for x in history['recovery_cal_28d'] if x['value'] is not None)}/{len(history['recovery_cal_28d'])} valid")
print(f"  trend.alert: {trend['alert']}")
