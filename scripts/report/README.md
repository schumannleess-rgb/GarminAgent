# dev-pinpaper — recovery_pin_paper.html 开发目录

## 目录结构

```
dev-pinpaper/
├── README.md              # 本文件
├── src/
│   └── recovery_pin_paper.html    # 源模板（FALLBACK 数据可被脚本替换）
├── scripts/
│   └── build_pinpaper.py  # 生成脚本：从 kpi_today.json 注入 FALLBACK → output/
└── output/
    └── recovery_pin_paper.html    # 生成产物（浏览器打开用）
```

## 数据链路

```
scripts/compute_kpis_v4.py 或 morning_advisor.py
         ↓ 生成
  output/kpi_today.json              ← 数据源头
         ↓
  scripts/build_pinpaper.py          ← 读取 kpi_today.json → 注入 FALLBACK
         ↓ 写入
  dev-pinpaper/output/recovery_pin_paper.html
```

## 使用方式

```bash
# 1. 确保 kpi_today.json 已更新（由 morning_advisor.py 生成）
python scripts/build_pinpaper.py

# 2. 在浏览器中打开
#    dev-pinpaper/output/recovery_pin_paper.html
```

## 注意事项

- **不要手动修改 output/ 下的 HTML** — 它是生成物，每次 build 都会覆盖
- 如果需要改样式或结构，改 `src/` 下的源模板
- FALLBACK 数据由脚本从 kpi_today.json 自动生成
