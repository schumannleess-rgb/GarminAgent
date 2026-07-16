# 每日恢复力日报（PPT 风格）生成标准 · RECOVERY-DECK-STANDARD v2

> 适用范围：每天生成的「恢复力日报」PPT 风格 HTML（当前启用 **Swiss** 一种；架构支持多皮肤扩展，共用同一份数据/叙事）
> 共享内容层（数据/叙事/SVG/组装）：`scripts/ppt_common.py`；Swiss 生成器：`scripts/variants/recovery_deck/build.py`（与 HTML 风格变体统一收口于 scripts/variants/）
> 数据源（唯一标准）：`output/kpi_today.json` —— 由 `scripts/rebuild_kpi_today.py` 从 `daily_health.json` 重建。

## 1. 数据来源（强制）

- 所有风格生成器**只读** `output/kpi_today.json`，不读写任何其他文件。
- 每天流水线：`rebuild_kpi_today.py` → 各风格生成器。
- 禁止把数值硬编码进 HTML。KPI / 分数 / 趋势 / 模式 / 建议全部由 `kpi_today.json` 驱动。
- 校验：生成后 HTML 的日期、`recovery_score`、`grade` 必须与 `kpi_today.json` 一致。

## 2. 架构：一份内容，多种皮肤

`ppt_common.py` 负责**全部**数据抽取、叙事逻辑、SVG 图表与 HTML 组装（主题无关）。
每个风格脚本只提供一段 `theme_css`（设计令牌皮肤）并调用 `build_html(model, theme_css, name)`。

| 风格 | 生成器 | 输出文件 | 皮肤 |
|------|--------|----------|------|
| Swiss（国际主义蓝）★当前启用 | `scripts/variants/recovery_deck/build.py` | `output/html/recovery_swiss.html` | 白底 · 国际蓝 `#002FA7` |
| 深度诊断标准版（参考，非 deck 皮肤） | 既有 `output/html/recovery_standard.html` | `output/html/recovery_standard.html` | 见原文件 |

> Swiss 风格的「内容与分析」对齐 `recovery_standard.html`（标准版）的数据口径。
> 旧版 `output/ppt/`、`output/ppt_swiss/` 及 **DEEP DIAGNOSIS v2.0** 已归档至 `output/html/archive/`（脚本在 `scripts/archive/`），不再用于每日生成。

## 3b. 数值精度治理（数据治理，强制）

所有数值经 `ppt_common` 的 `fmt_int` / `fmt_val(v, dec)` / `fmt_hours` / `fmt_pct` 统一格式化，
**禁止**在模板里直接 `f"{x}"` 拼原始值。规则：

| 指标类别 | 小数位 | 示例 | 函数 |
|----------|--------|------|------|
| 恢复分 / 各维度原始评分 / 准备度 / 压力 | 整数 | `89` `97` | `fmt_int` |
| HRV (ms) / 静息心率 (bpm) / 压力等级 | 整数 | `73` `43` `14` | `fmt_int` |
| 权重 | 整数百分比 | `30%` | `int(w*100)` |
| 睡眠时长 (h) | **1 位** | `7.8 h` | `fmt_hours` |
| 贡献分 (contrib) | **1 位** | `23.1` `19.0` | `fmt_val(v,1)` |
| 百分比（变化率 / 深睡 / REM） | **1 位** | `+3.5%` `17.9%` | `fmt_pct` / `fmt_val(v,1)` |
| 趋势 recovery 均值 | **1 位** | `52.9` | `fmt_val(v,1)` |
| 趋势 recovery 最小 / 最大 | 整数 | `38`–`90` | `fmt_val(v,0)` |

> 设计意图：消除 `19.00` / `8.90` / `77.0` 这类尾零与 `7.47` vs `43` 的精度漂移，
> 让每日 deck 数值口径稳定、可比对。新增任何数值展示都必须走上述格式化函数。

## 3. 设计令牌（CSS 变量，禁止私自改色）

共享组件样式在 `ppt_common.SHARED_BASE_CSS`，颜色全部走变量，由 `theme_css` 注入：

| 令牌 | 值（Swiss） |
|------|------------|
| `--paper` | `#ffffff` |
| `--ink` | `#0a0a0a` |
| `--accent` | `#002FA7` |
| `--good` / `--bad` | `#16a34a` / `#dc2626` |
| 字体 | Inter + JetBrains Mono + Noto Sans SC（Google Fonts） |

## 4. 版式规则（10 张 slide，顺序固定）

1. 封面（accent 底，大 GRADE + 恢复分 + 「权重是参考配方，数据说了算」）
2. 诊断总览 + 综合公式（含计算步骤 + 顶部趋势预警条 + 权重=参考配方小注）
3. 五维度 KPI 总览（今晚值 / 基线 / 原始分）
4. 今日各维度**实际贡献**（条形=今日贡献值，权重仅灰色小字——叙事重点在数据而非权重）
5. 恢复分 28 天走势（SVG，7/14/28 切换，警戒线 60，标注「非准备度」）
6. HRV & 静息心率 文字分析（今晚值/基线/变化/得分/一句结论）
7. 睡眠质量 + 准备度/压力 分析
8. 多维趋势明细（HRV/RHR/睡眠/准备度 28 天 sparkline）
9. 状态模式（全部 5 个，命中高亮 + 含义）
10. 今日建议（按 Grade 结构化 3 条）+ Split 收尾

- 每张 slide 含 `chrome` 页眉（品牌 / 日期）与 `foot` 页脚（`Slide NN / 10`）。
- 导航：底部圆点 + 方向键/滚轮/触摸翻页（共享 JS）。
- 图表：**静态 inline SVG，无 canvas**；趋势 7/14/28 用纯 JS 切换预渲染 SVG。
- 图标：lucide（`unpkg`）。

## 5. 叙事逻辑（关键约束）

- **权重是统一参考配方**（`HRV 30% · 睡眠 25% · RHR 20% · 准备度 15% · 压力 10%`），
  仅用于横向对比，**不是叙事主角**；真正决定分数的是「今晚的真实数据 vs 你的基线」。
- 增删 slide / 改文案，只能在 `ppt_common.py` 内完成，保证所有皮肤一致。
- 数据质量 bug（如 `hrv.score`、REM 占比误算）在内容层**绕过**：用原始值叙事并标注，
  不依赖错误 score；修复由数据源侧（`rebuild_kpi_today.py`）负责。

## 6. 每日生成流程

```bash
python scripts/rebuild_kpi_today.py   # 1) 重建 kpi_today.json
python scripts/variants/recovery_deck/build.py     # 2) output/html/recovery_swiss.html
# recovery_standard.html 由既有流程生成（详细标准版，非 deck 皮肤）
```

## 7. 一致性约束

- 样式/文案修改**只能**在 `ppt_common.py` 或对应 `theme_css` 内完成。
- 新增风格：复制 `scripts/variants/recovery_deck/build.py`，仅换 `theme_css` 与输出文件名，复用 `scripts/ppt_common.py`。
- 所有每日 deck 必须落在 `output/html/`，与标准版同目录。
