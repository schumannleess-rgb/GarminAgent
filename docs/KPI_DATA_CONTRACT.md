# 数据契约 / 标准版说明（KPI Data Contract）

本文件是 **标准版 `output/html/recovery_standard.html`** 对外暴露的数据契约。
任何「风格变体」(不同 style 的 html) 只需读取同一份 `kpi_today.json`、遵循本契约，
即可自行决定样式与布局，**无需复制任何数据或绘图逻辑**。

---

## 1. 标准版定位

- **标准版文件**：`output/html/recovery_standard.html`
  - 数据加载 + 绘图 + 7/14/28 天标签切换 + 失败展示 的**唯一逻辑来源**。
  - 文件头带 `<!-- 标准版 STANDARD ... -->` 注释标识。
- **风格变体**：只改 CSS / 布局；数据一律来自下面的 `kpi_today.json`，逻辑复用标准版（直接引用或自行读取 JSON）。
- **加载策略（双模式）**：
  - `file://`（Hermes / 离线 / 无服务环境）→ 以内嵌 `STATIC_DATA` 静态快照为**本源数据**直接渲染，不做 fetch，也不存在「fetch 失败回退」——内嵌数据即权威快照。
  - `http(s)://`（实时）→ `fetch('../kpi_today.json')`；失败一律进入固定失败展示页（文案固定，仅「失败原因」按实情输出），**绝不回退内嵌旧数据**。
  - 任何模式加载失败 → 固定失败展示，绝不渲染占位/过期数据。

---

## 2. 权威数据源

| 项 | 值 |
|----|----|
| 数据文件（HTTP 相对路径） | `../kpi_today.json`（即 `output/kpi_today.json`） |
| 生成脚本 | `scripts/rebuild_kpi_today.py` |
| 重建命令 | `GARMIN_OUTPUT_DIR="<绝对路径>/output" python3 scripts/rebuild_kpi_today.py` |
| 底层源 | `data/daily_health.json`（649 天历史） |
| 日期字段格式 | `YYYY-MM-DD` |

> 风格变体 html 若与标准版同处 `output/html/`，同样用 `fetch('../kpi_today.json')` 即可。

---

## 2.1 静态快照 `STATIC_DATA`（Hermes / 离线专用）

标准版在文件内嵌入了一份 `const STATIC_DATA = {...}`，内容即某一时刻的 `kpi_today.json` 全量。

- **用途**：仅 `file://` 模式读取，作为该环境下的权威数据快照（无服务、浏览器拦截本地 fetch）。
- **不是回退**：HTTP 模式 fetch 失败时**不会**用它，而是直接失败展示。二者边界由 `window.location.protocol` 判定，逻辑互不干扰。
- **数据新鲜度透明**：`file://` 渲染时页头显示「静态快照（file:// 主源）· 数据日期 YYYY-MM-DD」黄色徽标，明确这是快照而非实时数据。
- **重新生成后需同步重嵌**：运行 `rebuild_kpi_today.py` 产出新 `kpi_today.json` 后，必须重新把该 JSON 内嵌进 `STATIC_DATA`（否则 file:// 下看到的是旧快照）。重嵌方式见仓库 `scripts/` 或本契约「构建」约定。

---

## 3. 趋势数据 schema（重点：`history.*_cal_28d`）

四个趋势各有 **28 个日历日** 的序列，键名固定：

```
history.recovery_cal_28d   // 恢复分（composite，0-100）
history.hrv_cal_28d        // HRV（ms）
history.rhr_cal_28d        // 静息心率（bpm）
history.sleep_cal_28d      // 睡眠（对象，含 total_sec）
history.readiness_cal_28d  // 训练准备度（score）
```

**每个序列的结构（长度恒为 28，按日期升序）：**

```json
[
  { "date": "2026-06-19", "value": null },
  { "date": "2026-06-20", "value": { "total_sec": 25200 } },  // sleep 用对象
  { "date": "2026-06-21", "value": 73 }                        // 其它用标量
]
```

### 语义约定（契约核心）

| 规则 | 说明 |
|------|------|
| `length === 28` | 严格 28 个**日历日**槽位，缺测日也占位。 |
| `value === null` | **该日无数据**。渲染：断线 + 不插值 + 浅灰竖条标记缺口。**不要**补零、不要跳连伪造。 |
| 标量字段 | `recovery / hrv / rhr / readiness` 的 `value` 为数字。 |
| 对象字段 | `sleep` 的 `value` 为对象，`value.total_sec` 为秒；小时 = `total_sec / 3600`。 |
| 窗口切片 | 取最近 `win` 天：`slice(-win)`（win ∈ {7,14,28}）。28 即全量。 |
| 覆盖率 | 有效点数 / 28；低于 60% 时标准版标红。 |

---

## 4. 四个图表 → 字段映射

| 图表 | 序列 | 单位/阈值 | 备注 |
|------|------|----------|------|
| 恢复分趋势 | `recovery_cal_28d` | 警戒线 60 | 与 `latest_metrics.recovery_score` 一致 |
| HRV + 静息心率（双轴） | `hrv_cal_28d` + `rhr_cal_28d` | HRV 越高越好 / RHR 越低越好 | 双数据集同图 |
| 睡眠时长 | `sleep_cal_28d` | 目标 7h，`value.total_sec/3600` | 缺测为 null |
| 训练准备度 | `readiness_cal_28d` | 训练线 80 | 28/28 通常最满 |

---

## 5. 加载与失败约定（变体必须遵循）

标准版按 `window.location.protocol` 分流：

```js
async function loadData() {
  const fileProto = window.location.protocol === 'file:';

  // ── file:// 静态模式：内嵌 STATIC_DATA 即本源，不 fetch、不回退 ──
  if (fileProto) {
    const data = STATIC_DATA;
    if (!data?.history) throw new Error('内嵌静态数据缺失');
    const need = ['recovery_cal_28d','hrv_cal_28d','rhr_cal_28d','sleep_cal_28d','readiness_cal_28d'];
    if (need.some(k => !Array.isArray(data.history[k]))) throw new Error('内嵌静态数据缺少序列');
    render(data, 'static');   // 页头显示静态快照徽标
    return;
  }

  // ── http(s):// 实时模式：fetch，失败一律失败展示，绝不回退 ──
  const resp = await fetch('../kpi_today.json', { cache: 'no-store' });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);     // 具体原因①
  const data = await resp.json();                            // 解析失败 → 具体原因②
  if (!data.history) throw new Error('缺少 history');        // 契约不符 → 具体原因③
  if (!Array.isArray(data.history.hrv_cal_28d)) throw ...;   // 缺序列 → 具体原因④
  render(data, 'live');                                       // 成功才渲染
}
// 任一异常 → 进入固定失败展示，仅"失败原因"随异常 message 变化
```

- **file:// 双击打开（Hermes/离线）**：直接渲染内嵌静态快照，页头显示黄色「静态快照」徽标。**这是预期且正确的行为**（无需 HTTP 服务）。
- **http(s):// 打开**：经 HTTP 服务，例如 `python3 -m http.server` 指向 `output/` 后访问 `html/recovery_standard.html`；fetch 失败 → 固定失败页。

---

## 6. 变体html 自检清单

- [ ] 若需离线/file:// 使用：内嵌 `STATIC_DATA` 快照，file:// 下作为主源直接渲染
- [ ] 若走 HTTP：数据来源指向 `../kpi_today.json`（同目录约定）
- [ ] 加载失败进入固定失败展示，无占位数据（HTTP 模式绝不回退内嵌）
- [ ] 消费 `history.*_cal_28d`，`null` 按"缺口"渲染
- [ ] 窗口切片用 `slice(-win)`，win ∈ {7,14,28}
- [ ] 睡眠取 `value.total_sec / 3600`
- [ ] 重建数据后：HTTP 变体自动生效；file:// 变体需重新内嵌 STATIC_DATA 快照
- [ ] 契约稳定，重建数据无需改任何变体代码逻辑
