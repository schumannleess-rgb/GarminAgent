#!/usr/bin/env python3
"""
fix_fallback.py — 将 deep_diagnosis.html 的 FALLBACK 数据从 kpi_today.json 重新生成。

解决: 手动修好数据后又被覆盖的问题。
方案: FALLBACK 直接对齐 kpi_today.json，不再手动改 HTML。

用法:
    python fix_fallback.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(r"d:\Garmin\Garmin\garmin-agent\GarminAgent")
HTML_PATH = BASE / "output" / "html" / "deep_diagnosis.html"
KPI_PATH = BASE / "output" / "kpi_today.json"


def to_js(obj, indent=2):
    """Convert Python dict/list to JS object string."""
    if isinstance(obj, dict):
        lines = ["{"]
        for k, v in obj.items():
            key = f"'{k}'" if isinstance(k, str) else str(k)
            val = to_js(v, indent + 2)
            lines.append(f"{' ' * indent}{key}: {val},")
        lines.append(f"{' ' * (indent - 2)}" + "}")
        return "\n".join(lines)
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        items = [to_js(item, indent + 2) for item in obj]
        return "[\n" + ",\n".join(" " * indent + item for item in items) + "\n" + " " * (indent - 2) + "]"
    elif isinstance(obj, str):
        return f"'{obj}'"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif obj is None:
        return "null"
    else:
        return str(obj)


def build_fallback(kpi: dict) -> str:
    """从 kpi_today.json 构建 FALLBACK JS 对象字符串。"""
    composite = kpi["composite"]
    dims = kpi["dimension_scores"]
    raw = kpi["raw_inputs"]
    history = kpi["history"]
    derived = kpi["derived_metrics_summary"]
    validation = kpi["multi_dimension_validation"]
    baselines = kpi["baselines"]

    hrv_dim = dims["hrv"]
    rhr_dim = dims["rhr"]
    sleep_dim = dims["sleep"]
    rd_dim = dims["readiness"]
    stress_dim = dims["stress"]

    sleep_score = sleep_dim["score"]
    sleep_zone = (
        "GOOD" if sleep_score >= 80
        else ("MODERATE" if sleep_score >= 60 else "POOR")
    )

    fallback = {
        "date": kpi["date"],
        "composite": {
            "recovery_score": composite["recovery_score"],
            "grade": composite["grade"],
            "label": composite["label"],
            "weights": composite["weights"],
            "calculation_steps": composite["calculation_steps"],
        },
        "dimension_scores": {
            "hrv": {
                "last_night_ms": hrv_dim["last_night_ms"],
                "weekly_avg_ms": hrv_dim.get("weekly_avg_ms", 0),
                "score": hrv_dim["score"],
                "zone": hrv_dim["zone"],
            },
            "rhr": {
                "current_bpm": rhr_dim["current_bpm"],
                "baseline_bpm": rhr_dim["baseline_bpm"],
                "deviation_bpm": rhr_dim["deviation_bpm"],
                "score": rhr_dim["score"],
                "zone": rhr_dim["zone"],
            },
            "sleep": {
                "total_seconds": raw["sleep"]["total_seconds"],
                "deep_seconds": raw["sleep"]["deep_seconds"],
                "rem_seconds": raw["sleep"]["rem_seconds"],
                "awake_count": raw["sleep"]["awake_count"],
                "garmin_score_used": sleep_dim.get("garmin_score_used", False),
                "score": sleep_dim["score"],
                "zone": sleep_zone,
            },
            "readiness": {
                "score": rd_dim["score"],
                "original_score": rd_dim.get("original_score", rd_dim["score"]),
                "zone": rd_dim["zone"],
            },
            "stress": {
                "stress_level": stress_dim["stress_level"],
                "score": stress_dim["score"],
                "zone": stress_dim["zone"],
            },
        },
        "baselines": {
            "hrv_baseline_7d": baselines["hrv_baseline_7d"],
            "rhr_baseline_28d": baselines["rhr_baseline_28d"],
            "sleep_baseline_7d": {
                "total_seconds": baselines["sleep_baseline_7d"]["total_seconds"],
                "total_hours": baselines["sleep_baseline_7d"]["total_hours"],
                "deep_pct_avg": baselines["sleep_baseline_7d"]["deep_pct_avg"],
            },
        },
        "derived_metrics_summary": derived,
        "trend": kpi["trend"],
        "history": {
            "hrv_14d": [
                {"date": h["date"], "value": h["value"]}
                for h in history["hrv_14d"]
            ],
            "rhr_28d": [
                {"date": h["date"], "value": h["value"]}
                for h in history["rhr_28d"]
            ],
            "sleep_7d": [
                {
                    "date": h["date"],
                    "total_sec": h["total_sec"],
                    "deep_sec": h["deep_sec"],
                }
                for h in history["sleep_28d"][:7]
            ],
            "readiness_7d": [
                {
                    "date": h["date"],
                    "score": h["score"],
                    "level": h["level"],
                }
                for h in history["readiness_28d"][:7]
            ],
        },
        "multi_dimension_validation": {
            "num_patterns_checked": validation["num_patterns_checked"],
            "patterns_checked": validation["patterns_checked"],
            "num_matched": validation["num_matched"],
            "matched_patterns": validation["matched_patterns"],
        },
    }

    return to_js(fallback)


def main():
    print("=" * 60)
    print(f"fix_fallback.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Load kpi_today.json
    if not KPI_PATH.exists():
        print(f"ERROR: {KPI_PATH} not found")
        return 1

    with open(KPI_PATH, encoding="utf-8") as f:
        kpi = json.load(f)

    print(f"\n[1] Loaded kpi_today.json (date: {kpi['date']})")
    print(f"    recovery_score: {kpi['composite']['recovery_score']}")
    print(f"    grade: {kpi['composite']['grade']}")

    # Build new FALLBACK
    new_fallback_js = build_fallback(kpi)

    # Read current HTML
    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()

    # Find and replace FALLBACK object
    # Match: const FALLBACK = { ... };  (possibly with whitespace)
    pattern = r"const FALLBACK = \{[^;]+\};"
    match = re.search(pattern, html, re.DOTALL)

    if not match:
        print("ERROR: Could not find FALLBACK object in HTML")
        return 1

    old_fallback = match.group(0)
    new_fallback_block = f"const FALLBACK = {new_fallback_js};"

    # Verify the replacement would work
    if len(new_fallback_block) > 10000:
        print(f"WARNING: New FALLBACK is {len(new_fallback_block)} chars (old was {len(old_fallback)})")

    # Replace
    new_html = html[:match.start()] + new_fallback_block + html[match.end():]

    # Backup current HTML before overwriting
    backup_path = BASE / "output" / "html" / "deep_diagnosis_backup.html"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n[2] Backed up current HTML to: {backup_path}")

    # Write fixed HTML
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"\n[3] Fixed FALLBACK data in: {HTML_PATH}")
    print(f"    File size: {len(new_html)} bytes (was {len(html)})")

    # Verify key values
    print(f"\n[4] Verification — key values in new FALLBACK:")
    print(f"    recovery_score: {kpi['composite']['recovery_score']}")
    print(f"    HRV last_night: {kpi['dimension_scores']['hrv']['last_night_ms']} ms")
    print(f"    RHR current: {kpi['dimension_scores']['rhr']['current_bpm']} bpm")
    print(f"    Sleep score: {kpi['dimension_scores']['sleep']['score']}")
    print(f"    Sleep total: {kpi['raw_inputs']['sleep']['total_seconds']}s ({kpi['raw_inputs']['sleep']['total_seconds']/3600:.2f}h)")
    print(f"    Sleep deep: {kpi['raw_inputs']['sleep']['deep_seconds']}s ({kpi['raw_inputs']['sleep']['deep_seconds']/kpi['raw_inputs']['sleep']['total_seconds']*100:.1f}%)")
    print(f"    Awake count: {kpi['raw_inputs']['sleep']['awake_count']}")
    print(f"    Readiness: {kpi['dimension_scores']['readiness']['score']}")
    print(f"    Stress: {kpi['dimension_scores']['stress']['score']}")
    print(f"    Grade: {kpi['composite']['grade']} {kpi['composite']['label']}")

    print(f"\n[5] Data history:")
    print(f"    sleep_28d entries: {len(kpi['history']['sleep_28d'])} days")
    print(f"    readiness_28d entries: {len(kpi['history']['readiness_28d'])} days")
    print(f"    rhr_28d entries: {len(kpi['history']['rhr_28d'])} days")
    print(f"    hrv_14d entries: {len(kpi['history']['hrv_14d'])} days")

    print("\nDone! Open deep_diagnosis.html to verify.")
    print(f"Backup available at: {backup_path}")
    return 0


if __name__ == "__main__":
    exit(main())
