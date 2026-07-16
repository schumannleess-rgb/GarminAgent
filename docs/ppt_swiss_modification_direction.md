# ppt_swiss 修改方向（对照 deep_diagnosis_latest.html 标准版）

> 目标：把 `output/ppt_swiss/index.html` 从「英文标签 + 轻量展示」升级为「全中文 + 对齐标准版数据与深度分析」的每日标准 deck，并修正叙事逻辑——**权重是参考，每天的数据才是主角**。

---

## 一、三条基本原则

1. **全中文内容**：标题、说明、分析结论一律中文；技术缩写 `HRV / RHR / REM / Garmin` 保留（标准版也保留，属于通用术语）。
2. **数据与分析对齐标准版**：`deep_diagnosis_latest.html` 里出现的每一项数据字段与文字分析，`ppt_swiss` 都要覆盖。
3. **叙事逻辑重构**：权重是「固定配方 / 参考」，真正决定今天恢复分的是你昨晚的真实数据。弱化权重的视觉权重，强化「今日值 → 你的基线 → 结论」这条主线。

---

## 二、覆盖差距对照表（标准版 vs 当前 ppt_swiss）

| 标准版内容 | 当前 ppt_swiss | 差距 |
|---|---|---|
| 顶部趋势预警条（alert） | 无 | **缺** |
| 综合诊断 + 公式（权重是参考 + 今日贡献） | Slide 2 只放大字号展示 66 + Grade + 权重 | **缺公式 / 今日贡献叙事** |
| 核心指标概览（4 KPI + delta vs 基线） | Slide 3 有，但部分 delta 文案偏英文 | 基本具备，需统一中文 |
| 恢复分近期走势（折线 + 警戒线 + 7/14/28 切换 + 覆盖率） | Slide 5 是「准备度」14 天柱图 | **语义错位 + 缺恢复分走势 + 缺覆盖率** |
| HRV 文字分析（评分逻辑 + 昨晚/基线/变化率/得分 + 结论） | Slide 6 仅「73ms last night」 | **缺** |
| 静息心率 文字分析（当前/基线/偏差/得分 + 结论） | 仅「43bpm current」 | **缺** |
| 睡眠质量 分析（深睡/REM/清醒次数/Garmin 分 + 结论） | Slide 6 有深睡/REM 数字，无分析、无清醒次数、无 Garmin 分 | **缺分析** |
| 状态模式识别（全部 5 个 + 含义） | Slide 7 仅 1 个命中徽标 | **缺其余 4 个 + 含义** |
| 今日建议（按 Grade 给 3 条结构化建议） | Slide 7 仅 1 条「HRV 极低」 | **缺结构化 3 条** |
| 各维度得分条（kpi-bar） | 无 | 可补 |

---

## 三、叙事逻辑重构（你的核心关注点）

**当前问题**：Slide 2 把权重做成 hero 大字号（30% / 25% / 20% / 15% / 10%），Slide 4 每行标「×30%」「×25%」——视觉上暗示「权重决定一切」。这与你强调的「权重是参考，每天的数据重要」相悖。

**重构方向**：

- **Slide 2（综合恢复分）**：保留大数字 `66` + `Grade C · 需要注意` + 一句话结论。把权重从 hero 视觉**降级为页脚小注**：
  > 恢复分 = 五维度按固定权重加权汇总。权重是一套统一配方（仅作参考），今天真正决定分数的是你昨晚的数据。
- **Slide 4（维度贡献分解）**：改名「**今天各维度实际贡献**」。主导视觉是**今日贡献值**（睡眠 24.2 / 静息心率 19.0 / 准备度 13.7 / 压力 8.9 / HRV 0.0），权重只作为每行右侧灰色小字「(权重 25%)」弱化呈现。配一句话：
  > 权重每天都一样，但你的数据每天都在变，所以各维度的贡献也随之变化。
- **每个维度解读 slide** 统一叙事模板：`今天的值 → 你的基线 → 结论`。
  例：HRV 73ms（7 天基线 70，+1%）→ 接近基线，恢复状态一般。

---

## 四、拟定的新 Slide 结构（全中文，建议 9 张）

| # | 中文标题 | 内容要点 | 数据字段 |
|---|---|---|---|
| 1 | 每日健康诊断 · 2026-07-16 | 副标题：HRV · 静息心率 · 睡眠 · 准备度 · 压力 五维综合评估 | `date` |
| 2 | 综合恢复分 | 66 / Grade C「需要注意」+ 结论 + 权重参考小注 | `composite.recovery_score` / `grade` / `label` / `weights` / `formula` |
| 3 | 核心指标概览 | 4 KPI 卡：HRV 73ms ↑+3（vs 7天基线70）；RHR 43bpm ↓-3（vs 28天基线46）；睡眠 7.8h（vs 7天基线7.47）；准备度 91/100 | `dimension_scores.*` / `baselines.*` / `derived.*` |
| 4 | 今天各维度实际贡献 | 主导=今日贡献值；权重弱化小注；公式一行 | `composite.calculation_steps` / `weights` |
| 5 | 恢复分近期走势 | 28 天折线（警戒线 60）+ 覆盖率徽标「有效 X/28 天」 | `history.recovery_cal_28d` / `trend.threshold` |
| 6 | 指标深度解读 | 6 格：HRV 文字分析 + 静息心率 文字分析 + 睡眠质量 分析（各含「今晚值 / 基线 / 变化率 / 得分 / 一句结论」） | `dimension_scores.hrv/rhr/sleep` / `baselines` / `derived` |
| 7 | 状态模式识别 | 5 个模式全部列出（命中高亮 + 含义说明） | `multi_dimension_validation.patterns_checked` |
| 8 | 今日建议 | 按 Grade C 给 3 条：低强度有氧/主动恢复；≤30 分钟；心率区间 1 | `composite.grade` |
| 9 | 收尾总结 | 3 条关键结论（恢复分 / 核心生理 / 睡眠） | 汇总 |

> 若希望更细，可把 Slide 6 拆成「HRV + 静息心率」「睡眠质量」两张 → 共 10 张。建议先按 9 张（合并）控制翻页成本。

---

## 五、关键技术要点

- **数据源无需改动**：`composite / dimension_scores / baselines / derived_metrics_summary / trend / history.*_cal_28d / multi_dimension_validation` 全部已在 `kpi_today.json` 可用，生成器 `scripts/variants/recovery-deck/build.py` 继续只读这个文件。
- **折线图实现**：标准版用 canvas + 交互标签页；`ppt_swiss` 是静态横向 deck。建议改用**预渲染纯 SVG 折线**（28 天，含警戒线 60 / 目标 7h 参考线），放弃 7/14/28 切换，改为固定 28 天 + 覆盖率徽标。如需交互，再引入 JS canvas（增加复杂度）。
- **⚠️ 数据质量 bug 1（直接影响叙事）**：`dimension_scores.hrv.score = 0`（zone SEVERE），但 HRV 73ms > 7 天基线 70ms、变化率 +0.99%，本应得 ~75 分。这是 `rebuild_kpi_today.py` 的 `score_hrv` 锚点/插值 bug，导致 HRV 贡献 0.0、综合恢复分被从约 88 硬压到 66。若坚持「每天数据重要」的叙事，这个 0 分恰恰会误导读者。→ **建议先修数据引擎**，或在 deck 内改用「原始 HRV 值 + 变化率」叙事、不直接用 score=0。
- **⚠️ 数据质量 bug 2**：`derived.sleep_rem_pct = 0`（错），实际 `sleep.rem_seconds 7800 / 27900 ≈ 28%`。deck 内用原始 `rem_seconds` 计算，不用这个派生字段。
- **⚠️ 标准版疑似误标**：`trend.recent_scores_in_window` 实际等于 `readiness_28d`（末值 91，即准备度），并非综合恢复分；标准版「恢复分走势」图绘制的其实是准备度。本 deck 的「恢复分走势」应改用 `history.recovery_cal_28d`（真实综合恢复分序列，末值 66），做到名副其实。

---

## 六、待你确认的决策

1. **Slide 张数**：9 张（指标解读合并）还是 10 张（HRV/心率 与睡眠拆开）？
2. **趋势图形式**：静态 SVG 28 天（轻量、推荐）还是保留 7/14/28 交互切换（需 canvas + JS）？
3. **HRV score=0 bug**：先修 `rebuild_kpi_today.py` 再出 deck，还是 deck 内绕过（用原始值叙事）？
4. **顺带处理**：`ppt/index.html`（硬编码、不遵从标准）与 `ppt/test.html`（测试页）是否一并处理？

确认后我按此方向重写 `scripts/variants/recovery-deck/build.py` 模板并重新生成 `output/html/recovery_deck_swiss.html`。
