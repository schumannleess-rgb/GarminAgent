#!/usr/bin/env python3
"""
tests/test_build.py — 验证 zine/build.py 的输出完整性。

对齐实现：
  · 内嵌静态快照名为 STATIC_DATA（即完整 kpi_today.json，由 build.py 的
    `to_js(kpi)` 注入到 `{{STATIC_DATA_JS}}` 占位符）；
  · 双模式加载：file:// 直接用 STATIC_DATA，http(s):// 走 fetch(getDataUrl())；
  · 加载失败一律 showFailure()，绝不回退内嵌旧数据（产物中不得残留 FALLBACK 死代码）。

产物位置：output/html/recovery_zine.html
"""

import json
import re
import sys
from pathlib import Path

# 路径：tests/ -> zine/ -> variants/ -> scripts/ -> PROJECT_ROOT
HERE = Path(__file__).resolve().parent
VARIANT_ROOT = HERE.parent
PROJECT_ROOT = HERE.parents[3]
OUT_HTML = PROJECT_ROOT / "output" / "html" / "recovery_zine.html"
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
    """内嵌 STATIC_DATA 必须和 kpi_today.json 一致（双模式本源）。"""
    kpi = _load_kpi()
    html = _load_html()

    assert "const STATIC_DATA = {" in html, "STATIC_DATA block not found in output HTML"

    # 关键标量必须随 kpi_today.json 同步
    assert kpi["date"] in html, "date mismatch"
    assert str(kpi["composite"]["recovery_score"]) in html, "recovery_score mismatch"
    assert str(kpi["composite"]["grade"]) in html, "grade mismatch"
    assert str(kpi["dimension_scores"]["hrv"]["score"]) in html, "hrv score mismatch"
    assert str(kpi["dimension_scores"]["rhr"]["score"]) in html, "rhr score mismatch"
    assert str(kpi["dimension_scores"]["sleep"]["score"]) in html, "sleep score mismatch"
    assert str(kpi["dimension_scores"]["readiness"]["score"]) in html, "readiness score mismatch"
    assert str(kpi["dimension_scores"]["stress"]["score"]) in html, "stress score mismatch"
    # 趋势序列必须存在（28d 数组已注入；to_js 输出单引号 JS 字面量，故用单引号键名）
    assert "'hrv_cal_28d'" in html, "hrv_cal_28d missing"
    assert "'sleep_cal_28d'" in html, "sleep_cal_28d missing"
    print(f"[PASS] STATIC_DATA sync: date={kpi['date']}, "
          f"recovery_score={kpi['composite']['recovery_score']}, "
          f"grade={kpi['composite']['grade']}")


def test_html_structure():
    """输出 HTML 必须包含 zine 风格的关键 section / 元素 id。"""
    html = _load_html()
    required_ids = [
        "heroScore", "heroGrade", "heroDate", "adviceList", "trendChart",
        "dualChart", "patternList", "hrvValue", "rhrValue", "readyValue",
        "hrvFormula", "readyFormula", "dataSourceBadge", "scrollHint",
    ]
    for sid in required_ids:
        assert f'id="{sid}"' in html, f"Missing element id={sid}"
    print(f"[PASS] All {len(required_ids)} required DOM elements present")


def test_loadData_function():
    """loadData 必须双模式加载：file:// 用 STATIC_DATA，http(s):// 走 fetch，失败走 showFailure。"""
    html = _load_html()
    assert "async function loadData()" in html, "loadData function missing"
    assert "const STATIC_DATA" in html, "STATIC_DATA block missing"
    assert "window.location.protocol === 'file:'" in html, "file:// branch missing (dual-mode)"
    assert "fetch(getDataUrl()" in html, "fetch call missing"
    assert "function showFailure(" in html, "showFailure() missing"
    # 反向约束：不得残留废弃的 FALLBACK 回退路径（zine 已对齐"绝不回退"契约）
    assert "const FALLBACK" not in html, "obsolete FALLBACK token still present"
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
