#!/usr/bin/env python3
"""
build.py — 将 kpi_today.json 注入 morning_card.html 的 STATIC_DATA。

对齐标准版 deep_diagnosis_latest.html 的加载约定：
  · file://（Hermes / 离线 / 无服务）→ 以内嵌 STATIC_DATA 静态快照为本源数据直接渲染；
  · http(s)://（实时）→ fetch kpi_today.json，失败一律走固定失败页，绝不回退内嵌旧数据。

STATIC_DATA 注入的是「完整 kpi_today.json」；render() 直接读取其中的维度字段。

产物写入 output/html/morning_card.html（与其他交付物同处 served）。

用法:
    python scripts/variants/morning-card/build.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

# __file__ = <GarminAgent>/scripts/variants/morning-card/build.py
# SCRIPT_DIR = <GarminAgent>/scripts/variants/morning-card
SCRIPT_DIR = Path(__file__).resolve().parent          # scripts/variants/morning-card
PROJECT_ROOT = SCRIPT_DIR.parents[2]                  # scripts/variants/morning-card -> variants -> scripts -> GarminAgent
SRC_HTML = SCRIPT_DIR / "src.html"
OUT_HTML = PROJECT_ROOT / "output" / "html" / "morning_card.html"
KPI_PATH = PROJECT_ROOT / "output" / "kpi_today.json"


def main() -> int:
    print("=" * 60)
    print(f"morning-card/build.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    if not KPI_PATH.exists():
        print(f"ERROR: {KPI_PATH} not found")
        print("  请先运行 rebuild_kpi_today.py 生成 kpi_today.json（务必带 GARMIN_OUTPUT_DIR 覆盖）")
        return 1

    if not SRC_HTML.exists():
        print(f"ERROR: {SRC_HTML} not found")
        return 1

    with open(KPI_PATH, encoding="utf-8") as f:
        kpi = json.load(f)

    print(f"\n[1] Loaded kpi_today.json (date: {kpi['date']})")
    print(f"    recovery_score: {kpi['composite']['recovery_score']}")
    print(f"    grade: {kpi['composite']['grade']}")

    new_static_js = json.dumps(kpi, ensure_ascii=False, indent=2)

    with open(SRC_HTML, encoding="utf-8") as f:
        html = f.read()

    # 占位 STATIC_DATA = {} → 注入完整 kpi
    pattern = r"const STATIC_DATA = \{[\s\S]*?\};"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        print("ERROR: Could not find STATIC_DATA placeholder in source HTML")
        return 1

    new_html = html[:match.start()] + f"const STATIC_DATA = {new_static_js};" + html[match.end():]

    if OUT_HTML.exists():
        backup_path = OUT_HTML.with_suffix(".html.bak")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(OUT_HTML.read_text(encoding="utf-8"))
        print(f"\n[2] Backed up old output to: {backup_path.name}")

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"\n[3] Generated: {OUT_HTML}")
    print(f"    Size: {len(new_html):,} bytes")

    print(f"\n[4] Verification:")
    print(f"    recovery_score: {kpi['composite']['recovery_score']}")
    print(f"    HRV last_night: {kpi['dimension_scores']['hrv']['last_night_ms']} ms")
    print(f"    RHR current: {kpi['dimension_scores']['rhr']['current_bpm']} bpm")
    print(f"    Sleep: {kpi['dimension_scores']['sleep']['score']} (total {kpi['dimension_scores']['sleep']['total_seconds']/3600:.1f}h)")
    print(f"    Readiness: {kpi['dimension_scores']['readiness']['score']}")
    print(f"    Stress: {kpi['dimension_scores']['stress']['stress_level']}")

    print("\nDone! Open output/html/morning_card.html to verify.")
    return 0


if __name__ == "__main__":
    exit(main() or 0)
