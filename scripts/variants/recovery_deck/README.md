# recovery-deck（Swiss）— recovery_swiss.html 风格变体

> Swiss 皮肤的「每日恢复力日报」。内容逻辑与标准版共用 `scripts/ppt_common.py` 共享内容层，
> 本变体只负责 Swiss 视觉皮肤。

## 目录结构

```
scripts/variants/recovery_deck/
├── README.md              # 本文件
└── build.py               # 生成脚本：提供 SWISS_CSS 皮肤，调用 ppt_common.build_html(model, theme_css, "Swiss")
```

> 注意：`recovery_swiss.html` 的 HTML 由 `scripts/ppt_common.py` 的 `build_html()` 统一生成（共享内容层），
> 不在本目录维护 `src.html`。本目录 `build.py` 仅注入 Swiss 设计令牌（SWISS_CSS）并驱动组装。

## 数据链路

```
output/kpi_today.json
         ↓
  scripts/variants/recovery_deck/build.py
    · 调用 scripts/ppt_common.py（共享内容层：数据抽取 / 叙事 / SVG / 组装，主题无关）
    · 注入 SWISS_CSS 设计令牌，产出 Swiss 皮肤
         ↓ 写入
  output/html/recovery_swiss.html
```

## 使用方式

```bash
# 0. (前置) 生成权威 kpi_today.json
GARMIN_OUTPUT_DIR=output python scripts/rebuild_kpi_today.py

# 1. 生成 recovery-deck (Swiss) 版
python scripts/variants/recovery_deck/build.py

# 2. 在浏览器中打开
#    output/html/recovery_swiss.html
#     · file:// 双击 → 内嵌 STATIC_DATA 静态快照
#     · http:// 访问 → 实时 fetch；失败走固定失败页（不回退旧数据）
```

## 加载约定（对齐标准版）

- `file://`：内嵌 `STATIC_DATA` 静态快照渲染。
- `http(s)://`：fetch 实时数据，失败走固定失败页，绝不回退内嵌旧数据。
- `<body data-style="recovery-deck">` 由 `ppt_common.py` 模板统一设置（跨皮肤一致）。

## 注意事项

- `ppt_common.py` 位于 `scripts/` 级别，跨 deck 皮肤共享，**不随变体移动**。
- 改 Swiss 视觉 → 改本目录 `build.py` 的 `SWISS_CSS`；改内容/逻辑 → 改 `ppt_common.py`（会影响所有 deck 皮肤）。
- 无独立 `tests/` 目录；校验见 `docs/DAILY_OUTPUT_RUNBOOK.md` 自检清单。
