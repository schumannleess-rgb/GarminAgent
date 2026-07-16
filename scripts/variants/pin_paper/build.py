#!/usr/bin/env python3
"""
build.py — 将 kpi_today.json 注入 recovery_pin_paper.html 的 STATIC_DATA。

对齐标准版 recovery_standard.html 的加载约定：
  · file://（Hermes / 离线 / 无服务）→ 以内嵌 STATIC_DATA 静态快照为本源数据直接渲染；
  · http(s)://（实时）→ fetch kpi_today.json，失败一律走固定失败页，绝不回退内嵌旧数据。

STATIC_DATA 注入的是「完整 kpi_today.json」；HTML 内的 adaptKpi() 负责把 28d 序列切成图表所需的 7d。

产物写入 output/html/recovery_pin_paper.html（与其他交付物同处 served）。

用法:
    python scripts/variants/pin_paper/build.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

# ─── 路径配置 ───
# __file__ = <GarminAgent>/scripts/variants/pin_paper/build.py
# SCRIPT_DIR = <GarminAgent>/scripts/variants/pin_paper
SCRIPT_DIR = Path(__file__).resolve().parent          # scripts/variants/pin_paper
PROJECT_ROOT = SCRIPT_DIR.parents[2]                  # scripts/variants/pin_paper -> variants -> scripts -> GarminAgent
SRC_HTML = SCRIPT_DIR / "src.html"
OUT_HTML = PROJECT_ROOT / "output" / "html" / "recovery_pin_paper.html"
KPI_PATH = PROJECT_ROOT / "output" / "kpi_today.json"


def main() -> int:
    print("=" * 60)
    print(f"pin-paper/build.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # ─── 检查输入文件 ───
    if not KPI_PATH.exists():
        print(f"ERROR: {KPI_PATH} not found")
        print("  请先运行 rebuild_kpi_today.py 生成 kpi_today.json（务必带 GARMIN_OUTPUT_DIR 覆盖）")
        return 1

    if not SRC_HTML.exists():
        print(f"ERROR: {SRC_HTML} not found")
        return 1

    # ─── 读取 kpi_today.json（完整，作为 STATIC_DATA 注入）───
    with open(KPI_PATH, encoding="utf-8") as f:
        kpi = json.load(f)

    print(f"\n[1] Loaded kpi_today.json (date: {kpi['date']})")
    print(f"    recovery_score: {kpi['composite']['recovery_score']}")
    print(f"    grade: {kpi['composite']['grade']}")

    # ─── 构建 STATIC_DATA（完整 kpi；JSON 即合法 JS 对象字面量）───
    new_static_js = json.dumps(kpi, ensure_ascii=False, indent=2)

    # ─── 读取源 HTML ───
    with open(SRC_HTML, encoding="utf-8") as f:
        html = f.read()

    # ─── 替换 STATIC_DATA 块 ───
    pattern = r"const STATIC_DATA = \{[\s\S]*?\};"
    match = re.search(pattern, html, re.DOTALL)

    if not match:
        print("ERROR: Could not find STATIC_DATA object in source HTML")
        return 1

    new_static_block = f"const STATIC_DATA = {new_static_js};"
    new_html = html[:match.start()] + new_static_block + html[match.end():]

    # ─── 写入输出 ───
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"\n[3] Generated: {OUT_HTML}")
    print(f"    Size: {len(new_html):,} bytes (was {len(html):,})")

    # ─── 验证关键值 ───
    print(f"\n[4] Verification — key values in injected STATIC_DATA:")
    print(f"    recovery_score: {kpi['composite']['recovery_score']}")
    print(f"    HRV last_night: {kpi['dimension_scores']['hrv']['last_night_ms']} ms")
    print(f"    RHR current: {kpi['dimension_scores']['rhr']['current_bpm']} bpm")
    print(f"    Sleep score: {kpi['dimension_scores']['sleep']['score']}")
    print(f"    Readiness: {kpi['dimension_scores']['readiness']['score']}")
    print(f"    Grade: {kpi['composite']['grade']} {kpi['composite']['label']}")
    print(f"    History: sleep_28d={len(kpi['history'].get('sleep_28d', []))} "
          f"readiness_28d={len(kpi['history'].get('readiness_28d', []))} "
          f"rhr_28d={len(kpi['history'].get('rhr_28d', []))} "
          f"hrv_14d={len(kpi['history'].get('hrv_14d', []))})")

    print("\nDone! Open output/html/recovery_pin_paper.html to verify.")
    return 0


if __name__ == "__main__":
    exit(main() or 0)
