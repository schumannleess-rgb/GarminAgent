# -*- coding: utf-8 -*-
"""
build_ppt_v2.py — 每日恢复力日报 · DEEP DIAGNOSIS v2.0 风格
============================================================
数据源: output/kpi_today.json（单数据源）
输出  : output/html/recovery_deck_v2.html

设计令牌（DEEP DIAGNOSIS v2.0 / 暗色 + 金）:
  纸黑底 · 米白字 · 金 accent #C8A24B · 暗卡
与 output/ppt/index.html（原硬编码 v2.0）同一套视觉语言，但改为数据驱动。
与 Swiss 版共用 ppt_common 的内容逻辑，仅皮肤不同。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ppt_common as P

V2_CSS = """
:root{
  --paper:#0c0c0e; --ink:#f5f5f0; --muted:#9aa0a6; --line:#2a2a2e;
  --accent:#C8A24B; --good:#5fcf80; --bad:#ff6b6b;
  --card:#16161a; --card-2:#1d1d22; --bg:#050506;
}
.slide-inner{box-shadow:0 10px 40px rgba(0,0,0,.6)}
.kpi-val{letter-spacing:-.02em}
.trend-svg .grid{stroke:#2a2a2e}
.advice{border-left:4px solid var(--accent)}
"""

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    kpi = os.path.join(base, "..", "output", "kpi_today.json")
    out_dir = os.path.join(base, "..", "output", "html")
    os.makedirs(out_dir, exist_ok=True)
    d = P.load_kpi(kpi)
    m = P.build_model(d)
    html = P.build_html(m, V2_CSS, "DEEP DIAGNOSIS v2.0")
    out = os.path.join(out_dir, "recovery_deck_v2.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[v2]    wrote {out}  ({len(html)} bytes)  recovery={m['recovery']} grade={m['grade']}")


if __name__ == "__main__":
    main()
