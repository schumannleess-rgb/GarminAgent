# pin-paper — recovery_pin_paper.html 风格变体

> 本目录是 `scripts/variants/` 下的一个风格变体（原 `dev-pinpaper/` 已并入此处，目录层级下沉）。

## 目录结构

```
scripts/variants/pin_paper/
├── README.md              # 本文件
├── src.html               # 源模板（STATIC_DATA 占位，由 build.py 注入完整 kpi_today.json）
├── build.py               # 生成脚本：读 output/kpi_today.json → 注入 STATIC_DATA → 写 output/html/
└── tests/
    └── test_build.py      # 校验：输出存在 / 数据同步 / 双模式加载
```

## 数据链路

```
scripts/rebuild_kpi_today.py   (须 GARMIN_OUTPUT_DIR=output 覆盖，相对路径，Windows 安全)
         ↓ 生成
  output/kpi_today.json              ← 数据源头（公开目录，被所有交付物读取）
         ↓
  scripts/variants/pin_paper/build.py   ← 读取完整 kpi_today.json → 注入 STATIC_DATA
         ↓ 写入
  output/html/recovery_pin_paper.html
```

注意：build.py 只读公开 `output/kpi_today.json`，与标准版一致；不碰默认 `.local/output`。

## 使用方式

```bash
# 0. (前置) 生成权威 kpi_today.json —— 必须覆盖 OUTPUT_DIR 到公开 output/（相对路径）
GARMIN_OUTPUT_DIR=output python scripts/rebuild_kpi_today.py

# 1. 生成 pin & paper 版（读取公开 output/kpi_today.json，注入 STATIC_DATA）
python scripts/variants/pin_paper/build.py

# 2. 在浏览器中打开
#    output/html/recovery_pin_paper.html
#     · file:// 双击 → 用内嵌 STATIC_DATA 静态快照（Hermes 免服务）
#     · http:// 访问 → 实时 fetch kpi_today.json；失败显示固定失败页（不回退旧数据）

# 3. (可选) 跑校验
python scripts/variants/pin_paper/tests/test_build.py
```

## 加载约定（对齐标准版 recovery_standard.html）
- file://：以内嵌 STATIC_DATA 静态快照为本源渲染，不做 fetch。
- http(s)://：fetch kpi_today.json，失败一律固定失败页，绝不回退内嵌旧数据。
- STATIC_DATA 注入的是完整 kpi_today.json；页面内 adaptKpi() 把 28d 序列切成图表所需的 7d。

## 注意事项

- **不要手动修改 output/html/ 下的 HTML** — 它是生成物，每次 build 都会覆盖。
- 改样式或结构，改 `src.html` 源模板；改生成逻辑改 `build.py`。
- STATIC_DATA 静态快照由脚本从完整 kpi_today.json 自动注入；kpi 更新后需重新 build 才能让 file:// 看到新数据。
