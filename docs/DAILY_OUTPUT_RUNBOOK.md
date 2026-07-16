# 每日健康报告产出 Runbook（Agent 操作指南）

> 目的：让 agent（或任何人）能独立、可重复地生成每日健康报告交付物，无需翻代码。
> 所有命令在 `GarminAgent/` 目录（项目根）下执行。
> 本文件由 2026-07-16 梳理时新建——此前 `README.md` 只讲项目总览，没有每日产出流程；`docs/KPI_DATA_CONTRACT.md` 是数据规范而非操作手册。

---

## 1. 数据流（一眼看懂）

```
.local/data/daily_health.json        (唯一源, ~649天历史, 不提交)
   ↓  scripts/rebuild_kpi_today.py
output/kpi_today.json                (★权威数据, 所有交付物读取, 不提交)
   ↓  被以下交付物消费（一次数据更新 → 4 个脚本 HTML + 1 个手工标准版 = 5 个交付物）:
   ├─ output/html/deep_diagnosis_latest.html    (标准版 · 双模式 · 手工维护, 不随脚本生成)
   ├─ output/html/deep_diagnosis_pin_and_paper.html  (风格1: pin & paper)
   ├─ output/html/wellness_zine.html            (风格2: zine / Retro)
   ├─ output/html/trend_tracker_data.html       (数字版 · 无样式全字段数据页)
   └─ output/html/recovery_deck_swiss.html      (风格3: 每日恢复力日报 · Swiss deck, 由 scripts/ppt_common.py 共享内容层驱动)
```

要点：`kpi_today.json` 是唯一的"真相源"。HTML 都是它的视图，本身不存数据。
**每日一次数据更新 = 脚本重生成 4 个 HTML（3 风格 + 1 数字版），另加 1 个手工维护的标准版，共 5 个交付物。** 标准版 `deep_diagnosis_latest.html` 是手工维护的基准，不随脚本生成，但 file:// 下的 STATIC_DATA 快照需手动重嵌。

---

## 2. 每日命令链（顺序执行）

```bash
cd GarminAgent

# 0) (可选) 同步当天 Garmin 数据；若已有最新数据可跳过
python scripts/sync_data.py --health

# 1) 生成权威 JSON —— ⚠️ 必须覆盖 GARMIN_OUTPUT_DIR 到公开 output/
#    ⚠️ 用「相对路径 output」，不要用 $(pwd)/output（Windows 原生 Python 不认 MSYS 路径 /d/...）
GARMIN_OUTPUT_DIR=output python scripts/rebuild_kpi_today.py

# 2) 重新生成无样式数据页（刷新内嵌 EMBEDDED 快照）
python scripts/gen_trend_data_view.py

# 3) 生成 3 个风格变体 + 1 个数字版（统一在 scripts/variants/ 下，产物都写到 output/html/）
python scripts/variants/pin-paper/build.py          # → output/html/deep_diagnosis_pin_and_paper.html
python scripts/variants/zine/build.py               # → output/html/wellness_zine.html
python scripts/variants/recovery-deck/build.py      # → output/html/recovery_deck_swiss.html (Swiss deck, 依赖 scripts/ppt_common.py)
#    （morning_card.html 已于 2026-07-16 归档至 output/html/archive/，不再纳入每日流程）
```

### 为什么第 1 步必须带 `GARMIN_OUTPUT_DIR`
`config.OUTPUT_DIR` 默认是 `.local/output`，但交付物读取的是公开目录 `output/kpi_today.json`。
若不带覆盖，rebuild 会把新数据写进 `.local/output/`，而 HTML 仍读旧的公开 `output/kpi_today.json` → 页面显示过期数据。
`gen_trend_data_view.py`、`scripts/variants/recovery-deck/build.py`、以及 `scripts/variants/*/build.py` 都直接读公开 `output/kpi_today.json`，无需额外覆盖。

### ⚠️ Windows 原生 Python 路径坑
`GARMIN_OUTPUT_DIR="$(pwd)/output"` **会失败**：Git Bash 的 `$(pwd)` 返回 `/d/Garmin/...`（MSYS 路径），而本项目用的是原生 Windows Python，把它当成 `\d\...` 导致 `FileNotFoundError`。
**一律用相对路径**：`GARMIN_OUTPUT_DIR=output`（相对 cwd 解析，跨平台安全）。

---

## 3. ⚠️ 关键坑（踩过一次就记住）

- **OUTPUT_DIR 双副本**：见上。第 1 步务必带 `GARMIN_OUTPUT_DIR=output`。
- **标准版是唯一逻辑源**：`deep_diagnosis_latest.html` 带 `STANDARD` 标记，是数据/逻辑基准。风格变体只改 CSS、复用同一份 `kpi_today.json`，失败走固定失败页、绝不回退内嵌旧数据。改逻辑只改标准版。
- **file:// 静态快照需手动重嵌**：标准版与三个风格变体在 `file://`（Hermes 免服务）下都读内嵌 `STATIC_DATA`；`kpi_today.json` 更新后需重跑对应 `build.py` 重嵌 `STATIC_DATA`，否则 file:// 看到旧快照。HTTP 模式自动取最新，无需动。
- **trend_tracker.html 已归档**：内容不符合要求，已移至 `output/html/archive/trend_tracker.html`。其配对 `trend_tracker_data.html`（无样式数据页）保留，作为每日 4 HTML 之一。若要彻底退役，把 `trend_tracker_data.html` 也归档。
- **dated 历史回看不可用**：URL `?date=YYYY-MM-DD` → `kpi_<date>.json` 目前未自动归档，仅有零星几份，历史回看基本不可用。
- **风格变体统一收口在 `scripts/variants/`**：每个风格自带 `src.html`（源模板）+ `build.py`（生成器）+ `tests/test_build.py`（校验）。生成器都读公开 `output/kpi_today.json`、注入 `STATIC_DATA`、写到 `output/html/<name>.html`。新增第 4/5 个风格只需在 `scripts/variants/` 下加子目录。deck（recovery-deck）也收口在此，但它是「共享内容层 + 皮肤」架构：`build.py` 只提供 `SWISS_CSS` 并调用 `scripts/ppt_common.py`（数据/叙事/SVG/组装，跨 deck 皮肤共享），故 `ppt_common.py` 留在 `scripts/` 级别、不随变体移动。
- **zine 已对齐标准版双模式（2026-07-16 修复）**：`scripts/variants/zine/build.py` 注入完整 `kpi_today.json` 作为 `STATIC_DATA`；`file://` 直接渲染静态快照，`http(s)` 失败走固定 `showFailure`，不再静默回退旧数据。同日修复趋势取数 bug：history 中 `hrv_14d/rhr_28d/readiness_28d` 为降序（最新在前），原 `slice(-7)` 取到最旧 7 天，改为按日期升序取最近 7 天；睡眠趋势改用 `sleep_cal_28d` 的真实 `garmin_score`（原 `sleep_28d` 仅含 `total_sec/deep_sec`，无分数）。

---

## 4. 交付物清单（output/）

| 路径 | 角色 | 生成方式 |
|---|---|---|
| `output/kpi_today.json` | 权威数据源 | `rebuild_kpi_today.py`（带 `GARMIN_OUTPUT_DIR=output`） |
| `output/html/deep_diagnosis_latest.html` | 标准版深度诊断（file:// 静态 + http 实时/失败页） | 手工维护（标准版） |
| `output/html/deep_diagnosis_pin_and_paper.html` | 风格1：pin & paper（已对齐 STATIC_DATA 双模式） | `scripts/variants/pin-paper/build.py` |
| `output/html/wellness_zine.html` | 风格2：zine / Retro（仍用旧 FALLBACK 回退） | `scripts/variants/zine/build.py` |
| `output/html/trend_tracker_data.html` | 无样式全字段数据页 | `gen_trend_data_view.py` |
| `output/html/recovery_deck_swiss.html` | 每日恢复力日报 PPT（Swiss 皮肤，RECOVERY-DECK-STANDARD v2） | `scripts/variants/recovery-deck/build.py` + `scripts/ppt_common.py`（共享内容层） |
| `output/html/archive/` | 已归档旧交付物（trend_tracker / 旧 ppt / DEEP DIAGNOSIS v2.0） | — |

**每日数据更新产出的 5 个交付物** = 1 个手工标准版 + 1 个数字版 + 3 个风格 HTML：
- 标准版（手工）：`deep_diagnosis_latest.html`
- 数字版（脚本）：`trend_tracker_data.html`
- 风格1（脚本）：`deep_diagnosis_pin_and_paper.html`
- 风格2（脚本）：`wellness_zine.html`
- 风格3（脚本）：`recovery_deck_swiss.html`

其中 4 个由脚本生成（pin-paper / zine / recovery-deck 三个风格 + 数字版），标准版手工维护。（`morning_card.html` 已归档，不再产出。）

### 风格变体目录结构（`scripts/variants/`）

```
scripts/variants/
  pin-paper/
    src.html            # 源模板（STATIC_DATA 占位 + 双模式加载）
    build.py            # 读 output/kpi_today.json → 注入 → 写 output/html/deep_diagnosis_pin_and_paper.html
    tests/test_build.py # 校验：输出存在 / 数据同步 / 双模式
    README.md
  zine/
    build.py            # 自包含（模板内嵌），写 output/html/wellness_zine.html
  recovery-deck/
    build.py            # Swiss 皮肤生成器；依赖 scripts/ppt_common.py（共享内容层：数据/叙事/SVG/组装）
    # 注：ppt_common.py 留在 scripts/ 级别，跨 deck 皮肤共享，不随变体移动
```

> 注：源模板（src.html / build.py / tests）放在 `scripts/` 下是为了能被 git 跟踪——`.gitignore` 忽略了整个 `output/`，若把源也放 `output/` 下会变成未跟踪、无法版本管理。产物（生成的 HTML）落在被忽略的 `output/html/`，符合"产物不入库"的约定。

---

## 5. 相关规范

- `docs/KPI_DATA_CONTRACT.md` — 数据契约：权威源 / `*_cal_28d` 字段语义 / 加载与失败约定 / 变体自检清单。
- `docs/swiss_ppt_standard.md` — PPT 标准：数据流 / 设计令牌 / 版式 / 每日流水线。

---

## 6. 生成后自检

- `output/kpi_today.json` 的 `date` 字段是否为今日。
- 打开三个风格变体（`file://` 或 http）：
  - http 模式 → 显示今日实时数据；
  - file:// 模式 → 显示静态快照，页头含「静态快照」标识。
- 跑变体测试确认数据已注入：
  ```bash
  python scripts/variants/pin-paper/tests/test_build.py
  python scripts/variants/morning-card/tests/test_build.py
  ```
- `output/html/recovery_deck_swiss.html` 的 KPI（HRV / RHR / 睡眠 / 准备度 / 综合分）与 `kpi_today.json` 一致。

---

## 7. 常见操作

**只刷新某风格**：跑对应 `scripts/variants/<name>/build.py`。
**只刷新数据页**：跑第 2 步。
**只刷新 PPT（deck）**：跑 `python scripts/variants/recovery-deck/build.py`。
**Hermes 离线看标准版**：重嵌 `STATIC_DATA` 到 `deep_diagnosis_latest.html`（见 KPI_DATA_CONTRACT.md §2.1），无需起服务；风格变体离线看则重跑对应 `build.py`。
**回滚某交付物**：历史版本在 git（`git log -- output/html/...`）；归档文件在 `output/html/archive/`。
**新增一个风格**：在 `scripts/variants/<new-name>/` 下放 `src.html` + `build.py`（参考 pin-paper），build.py 读 `output/kpi_today.json`、注入 `STATIC_DATA`、写 `output/html/<new-name>.html`，并加 `tests/test_build.py`。
