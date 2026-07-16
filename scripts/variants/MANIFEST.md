# Variants 注册表（模块收口清单）

> 单一事实源：本文件枚举所有风格变体及其产物、标记、构建命令、测试与状态。
> 维护变体时先更新本表，再改代码 / 文档。

## 命名约定

- **目录**：多词用下划线（`pin_paper` / `recovery_deck`）；单字无分隔（`zine`）；**禁止使用连字符 `-`**。
- **产物**：风格变体统一 `recovery_<name>.html` 前缀；标准版 `recovery_standard.html`、数字版 `recovery_data.html` 例外。
- **DOM 标记**：每个 HTML 的 `<body>` 带 `data-style="<风格名>"`，风格名用小写连字符（`pin-paper` / `zine` / `recovery-deck` / `standard`）。

## 变体清单

| 变体 | 目录 | 产物 | `data-style` | build 命令 | tests | 状态 |
|---|---|---|---|---|---|---|
| pin & paper | `scripts/variants/pin_paper/` | `output/html/recovery_pin_paper.html` | `pin-paper` | `python scripts/variants/pin_paper/build.py` | ✅ `tests/test_build.py` | 活跃 |
| zine / Retro | `scripts/variants/zine/` | `output/html/recovery_zine.html` | `zine` | `python scripts/variants/zine/build.py` | ✅ `tests/test_build.py` | 活跃 |
| recovery-deck (Swiss) | `scripts/variants/recovery_deck/` | `output/html/recovery_swiss.html` | `recovery-deck` | `python scripts/variants/recovery_deck/build.py` | ✅ `tests/test_build.py` | 活跃 |
| 标准版（逻辑基准） | （手工维护，无源目录） | `output/html/recovery_standard.html` | `standard` | 手工维护 | — | 活跃（基准） |
| 数字版（无样式） | `scripts/gen_trend_data_view.py` | `output/html/recovery_data.html` | （无） | `python scripts/gen_trend_data_view.py` | — | 活跃 |
| morning-card | `scripts/variants/archive/morning-card/` | （已归档，不再产出） | — | — | ✅（归档） | 已归档 2026-07-16 |

## 共享层

- `scripts/ppt_common.py`：`recovery-deck` 的内容层（数据抽取 / 叙事 / SVG / 组装），主题无关，跨皮肤共享。
- `output/kpi_today.json`：唯一数据源，所有交付物读取，不提交（隐私/可重建）。
- `recovery_standard.html` 是唯一逻辑源（带 `STANDARD` 标记）；风格变体只改 CSS / 布局，复用同一份数据。

## 加载约定（全部风格统一）

- `file://`：内嵌 `STATIC_DATA` 静态快照渲染，不做 fetch。
- `http(s)://`：fetch `kpi_today.json`，失败走固定失败页，**绝不回退内嵌旧数据**。

## 收口记录

- 2026-07-16：统一 `data-style` 标记到 3 个活跃风格变体 + 标准版；归档 `morning-card`（目录移至 `scripts/variants/archive/`）；补 `zine` / `recovery_deck` README；建立本注册表。
