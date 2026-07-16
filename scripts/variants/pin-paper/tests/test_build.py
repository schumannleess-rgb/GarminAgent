#!/usr/bin/env python3
"""
tests/test_build.py — 验证 pin-paper/build.py 的输出完整性。

对齐实现：
  · 内嵌静态快照名为 STATIC_DATA（即完整 kpi_today.json），不再是旧版 FALLBACK；
  · 双模式加载：file:// 直接用 STATIC_DATA，http(s):// 走 fetch(getDataUrl())；
  · 加载失败一律 showFailure()，绝不回退内嵌旧数据。

产物位置：output/html/deep_diagnosis_pin_and_paper.html
"""

import json
import re
import sys
from pathlib import Path

# 路径：tests/ -> pin-paper/ -> variants/ -> scripts/ -> PROJECT_ROOT
HERE = Path(__file__).resolve().parent
VARIANT_ROOT = HERE.parent
PROJECT_ROOT = HERE.parents[3]
OUT_HTML = PROJECT_ROOT / "output" / "html" / "deep_diagnosis_pin_and_paper.html"
KPI_PATH = PROJECT_ROOT / "output" / "kpi_today.json"


def _load_kpi():
    with open(KPI_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_html():
    with open(OUT_HTML, encoding="utf-8") as f:
        return f.read()


def test_output_exists():
    assert OUT_HTML.exists(), f"Output HTML not found: {OUT_HTML}"
    print("[PASS] output HTML exists")


def test_static_data_sync():
    """内嵌 STATIC_DATA 必须和 kpi_today.json 完全一致（且不是占位符）。"""
    kpi = _load_kpi()
    html = _load_html()

    match = re.search(r"const STATIC_DATA = \{", html)
    assert match, "STATIC_DATA block not found in output HTML"

    # 不能是源模板里的占位符（date 为 '--'）
    assert '"date": "--"' not in html, "STATIC_DATA is still the placeholder, build did not inject"

    # 关键标量必须随 kpi_today.json 同步
    assert kpi["date"] in html, "date mismatch"
    assert str(kpi["composite"]["recovery_score"]) in html, "recovery_score mismatch"
    assert str(kpi["dimension_scores"]["hrv"]["last_night_ms"]) in html, "hrv mismatch"
    assert str(kpi["dimension_scores"]["rhr"]["current_bpm"]) in html, "rhr mismatch"
    assert str(kpi["dimension_scores"]["sleep"]["total_seconds"]) in html, "sleep total mismatch"
    assert str(kpi["dimension_scores"]["readiness"]["score"]) in html, "readiness mismatch"
    # 趋势序列必须存在（28d 数组已注入）
    assert '"hrv_cal_28d"' in html, "hrv_cal_28d missing"
    assert '"sleep_cal_28d"' in html, "sleep_cal_28d missing"
    print(f"[PASS] STATIC_DATA sync: date={kpi['date']}, "
          f"recovery_score={kpi['composite']['recovery_score']}, "
          f"grade={kpi['composite']['grade']}")


def test_html_structure():
    """输出 HTML 必须包含所有关键 section。"""
    html = _load_html()
    required_ids = [
        "dateDisplay", "scoreNum", "gradeBadge", "contribBar", "formulaBox",
        "kpiGrid", "trendChart", "dualChart", "sleepChart", "readyChart",
        "hrvFormula", "rhrFormula", "sleepAnalysis", "patternsList", "adviceList",
        "failReasonText", "sourceDisplay",
    ]
    for sid in required_ids:
        assert f'id="{sid}"' in html, f"Missing element id={sid}"
    print(f"[PASS] All {len(required_ids)} required DOM elements present")


def test_loadData_function():
    """loadData 必须双模式加载：file:// 用 STATIC_DATA，http(s):// 走 fetch，失败走 showFailure。"""
    html = _load_html()
    assert "async function loadData()" in html, "loadData function missing"
    assert "const STATIC_DATA" in html, "STATIC_DATA block missing"
    assert "function adaptKpi(" in html, "adaptKpi() missing"
    assert "window.location.protocol === 'file:'" in html, "file:// branch missing (dual-mode)"
    assert "fetch(getDataUrl()" in html, "fetch call missing"
    assert "function showFailure(" in html, "showFailure() missing"
    # 反向约束：不得回退到旧 FALLBACK 约定
    assert "FALLBACK" not in html, "obsolete FALLBACK token still present"
    assert "render(FALLBACK)" not in html, "obsolete FALLBACK render path present"
    print("[PASS] loadData dual-mode intact (STATIC_DATA + fetch + showFailure, no FALLBACK)")


def main():
    tests = [
        test_output_exists,
        test_static_data_sync,
        test_html_structure,
        test_loadData_function,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
