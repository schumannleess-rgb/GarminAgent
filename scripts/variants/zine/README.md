# zine — recovery_zine.html 风格变体

> 本目录是 `scripts/variants/` 下的一个风格变体（zine / Retro 复古杂志风格）。

## 目录结构

```
scripts/variants/zine/
├── README.md              # 本文件
└── build.py               # 生成脚本：内嵌 recovery_zine.html 模板 + 注入 STATIC_DATA → 写 output/html/
```

> 与 pin_paper 不同，zine 的 HTML 模板直接内嵌在 `build.py` 中（以 `{{KEY}}` 占位符 + `{{STATIC_DATA_JS}}` 形式），
> 不单独维护 `src.html`。改样式/结构即改 `build.py` 中的模板字符串。

## 数据链路

```
scripts/rebuild_kpi_today.py   (须 GARMIN_OUTPUT_DIR=output 覆盖，相对路径，Windows 安全)
         ↓ 生成
  output/kpi_today.json              ← 数据源头（公开目录，被所有交付物读取）
         ↓
  scripts/variants/zine/build.py    ← 读取完整 kpi_today.json，注入 STATIC_DATA（{{STATIC_DATA_JS}}）
         ↓ 写入
  output/html/recovery_zine.html
```

注意：build.py 只读公开 `output/kpi_today.json`，与标准版一致；不碰默认 `.local/output`。

## 使用方式

```bash
# 0. (前置) 生成权威 kpi_today.json —— 必须覆盖 OUTPUT_DIR 到公开 output/（相对路径）
GARMIN_OUTPUT_DIR=output python scripts/rebuild_kpi_today.py

# 1. 生成 zine 版
python scripts/variants/zine/build.py
#    可选：python scripts/variants/zine/build.py --output path/to/output.html

# 2. 在浏览器中打开
#    output/html/recovery_zine.html
#     · file:// 双击 → 用内嵌 STATIC_DATA 静态快照（Hermes 免服务）
#     · http:// 访问 → 实时 fetch kpi_today.json；失败显示固定失败页（不回退旧数据）
```

## 加载约定（对齐标准版 recovery_standard.html）

- `file://`：以内嵌 `STATIC_DATA` 静态快照为本源渲染，不做 fetch。
- `http(s)://`：fetch `kpi_today.json`，失败一律 `showFailure` 固定失败页，绝不回退内嵌旧数据。
- 模板使用 `{{KEY}}` 占位符 + `FALLBACK` 精简字段兜底；完整数据经 `{{STATIC_DATA_JS}}` 注入。

## 注意事项

- **不要手动修改 `output/html/recovery_zine.html`** — 它是生成物，每次 build 都会覆盖。
- 改样式或结构，改 `build.py` 内嵌模板；改数据逻辑同标准版（先改标准版，再同步此处）。
- 无独立 `tests/` 目录；双模式由内嵌模板保障，校验见 `docs/DAILY_OUTPUT_RUNBOOK.md` 自检清单。
