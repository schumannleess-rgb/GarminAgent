# -*- coding: utf-8 -*-
"""
build.py — 每日恢复力日报 · Swiss 风格（recovery-deck 变体）
============================================================
数据源: output/kpi_today.json（单数据源，由 rebuild_kpi_today.py 重建）
输出  : output/html/recovery_swiss.html

位置: scripts/variants/recovery_deck/build.py
  · 与 output/html/recovery_standard.html（标准版）共用同一份内容逻辑
    （scripts/ppt_common.py，共享内容层：数据抽取 / 叙事 / SVG / 组装，主题无关）。
  · 本生成器只负责「Swiss 皮肤」：提供 SWISS_CSS（设计令牌）并调用
    ppt_common.build_html(model, theme_css, "Swiss")。
  · ppt_common.py 位于 scripts/ 级别，跨 deck 皮肤共享，不随变体移动。
"""
import os
import sys
from pathlib import Path

# __file__ = <PROJECT_ROOT>/scripts/variants/recovery_deck/build.py
PROJECT_ROOT = Path(__file__).resolve().parents[3]   # GarminAgent 根
SCRIPTS_DIR = Path(__file__).resolve().parents[2]    # GarminAgent/scripts（共享内容层 ppt_common.py 所在）

sys.path.insert(0, str(SCRIPTS_DIR))
import ppt_common as P

SWISS_CSS = """
:root{
  --paper:#ffffff; --ink:#0a0a0a; --muted:#6b7280; --line:#e5e7eb;
  --accent:#002FA7; --good:#16a34a; --bad:#dc2626;
  --card:#ffffff; --card-2:#f7f8fa; --bg:#e9eaee;
}
"""

def main():
    kpi = PROJECT_ROOT / "output" / "kpi_today.json"
    out_dir = PROJECT_ROOT / "output" / "html"
    os.makedirs(out_dir, exist_ok=True)
    d = P.load_kpi(str(kpi))
    m = P.build_model(d)
    html = P.build_html(m, SWISS_CSS, "Swiss")
    out = out_dir / "recovery_swiss.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[swiss] wrote {out}  ({len(html)} bytes)  recovery={m['recovery']} grade={m['grade']}")


if __name__ == "__main__":
    main()
