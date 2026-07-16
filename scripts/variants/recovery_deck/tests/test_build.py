#!/usr/bin/env python3
"""
tests/test_build.py — 验证 recovery_deck/build.py 的输出完整性。

架构说明（与其它变体不同）：
  · recovery_deck 走共享内容层 scripts/ppt_common.build_html(model, SWISS_CSS, "Swiss")；
  · 数据是**构建时烤入**的（f-string 拼装，无 STATIC_DATA / 无 fetch / 无 file:// 分支）；
  · 运行时只有轮播 JS（setRange / go / wheel / touch），无网络依赖；
  · <body data-style="recovery-deck"> 已在收口阶段补齐。

因此本测试聚焦：产物存在、data-style 标记、关键诊断数据已正确烤入、关键 DOM 结构齐全。

产物位置：output/html/recovery_swiss.html
"""

import json
import sys
from pathlib import Path

# 路径：tests/ -> recovery_deck/ -> variants/ -> scripts/ -> PROJECT_ROOT
HERE = Path(__file__).resolve().parent
VARIANT_ROOT = HERE.parent
PROJECT_ROOT = HERE.parents[3]
OUT_HTML = PROJECT_ROOT / "output" / "html" / "recovery_swiss.html"
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


def test_data_style_mark():
    """收口标记：<body data-style="recovery-deck"> 必须存在。"""
    html = _load_html()
    assert '<body data-style="recovery-deck">' in html, "data-style=recovery-deck missing"
    print("[PASS] <body data-style=\"recovery-deck\"> present")


def test_baked_data_sync():
    """关键诊断数据必须在构建时烤入 HTML（与 kpi_today.json 对齐）。"""
    kpi = _load_kpi()
    html = _load_html()

    # 头部关键标量
    assert kpi["date"] in html, "date not baked in"
    assert str(kpi["composite"]["recovery_score"]) in html, "recovery_score not baked in"
    assert str(kpi["composite"]["grade"]) in html, "grade not baked in"

    # 五维度名称齐全（ppt_common 的 calc_map）
    for nm in ["HRV", "睡眠", "RHR", "准备度", "压力"]:
        assert nm in html, f"dimension '{nm}' not baked in"

    # 趋势 SVG 三档视图 id 齐全
    for i in ["t28", "t14", "t7"]:
        assert f'id="{i}"' in html, f"trend svg id={i} missing"

    # 诊断叙事 / 公式符号存在（证明内容层已组装）
    assert "综合恢复" in html, "diagnostic narrative missing"
    assert "×" in html, "formula (weight product) missing"

    print(f"[PASS] baked data sync: date={kpi['date']}, "
          f"recovery_score={kpi['composite']['recovery_score']}, "
          f"grade={kpi['composite']['grade']}")


def test_html_structure():
    """输出 HTML 必须包含 recovery-deck 的关键结构 id。"""
    html = _load_html()
    required_ids = ["deck", "nav", "t28", "t14", "t7", "cdate"]
    for sid in required_ids:
        assert f'id="{sid}"' in html, f"Missing element id={sid}"
    print(f"[PASS] All {len(required_ids)} required DOM elements present")


def main():
    tests = [
        test_output_exists,
        test_data_style_mark,
        test_baked_data_sync,
        test_html_structure,
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
