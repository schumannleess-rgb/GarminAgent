#!/usr/bin/env python3
"""
tests/test_build.py — 验证 morning-card/build.py 的输出完整性。

对齐实现：
  · 内嵌静态快照名为 STATIC_DATA（即完整 kpi_today.json），不再是旧版死值 FALLBACK；
  · 双模式加载：file:// 直接用 STATIC_DATA，http(s):// 走 fetch(getDataUrl())；
  · 加载失败一律 showFailure()，绝不回退内嵌旧数据。

产物位置：output/html/morning_card.html
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
OUT_HTML = PROJECT_ROOT / "output" / "html" / "morning_card.html"
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
    kpi = _load_kpi()
    html = _load_html()
    assert re.search(r"const STATIC_DATA = \{", html), "STATIC_DATA block not found"
    # 不能是占位符（空对象）
    assert '"date": "--"' not in html or '"composite"' in html, "STATIC_DATA looks empty/uninjected"
    assert kpi["date"] in html, "date mismatch"
    assert str(kpi["composite"]["recovery_score"]) in html, "recovery_score mismatch"
    assert str(kpi["dimension_scores"]["hrv"]["last_night_ms"]) in html, "hrv mismatch"
    assert str(kpi["dimension_scores"]["rhr"]["current_bpm"]) in html, "rhr mismatch"
    assert str(kpi["dimension_scores"]["readiness"]["score"]) in html, "readiness mismatch"
    print(f"[PASS] STATIC_DATA sync: date={kpi['date']}, "
          f"recovery_score={kpi['composite']['recovery_score']}")


def test_loadData_function():
    html = _load_html()
    assert "async function loadData()" in html, "loadData missing"
    assert "const STATIC_DATA" in html, "STATIC_DATA missing"
    assert "window.location.protocol === 'file:'" in html, "file:// branch missing (dual-mode)"
    assert "fetch(getDataUrl()" in html, "fetch missing"
    assert "function showFailure(" in html, "showFailure missing"
    assert "FALLBACK" not in html, "obsolete FALLBACK token still present"
    assert "render(FALLBACK)" not in html, "obsolete FALLBACK render path present"
    print("[PASS] loadData dual-mode intact (STATIC_DATA + fetch + showFailure, no FALLBACK)")


def main():
    tests = [test_output_exists, test_static_data_sync, test_loadData_function]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*40}\nResults: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
