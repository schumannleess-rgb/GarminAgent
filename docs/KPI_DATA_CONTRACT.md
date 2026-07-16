# 数据契约 / 标准版说明（KPI Data Contract）

本文件是 **标准版 `output/html/deep_diagnosis_latest.html`** 对外暴露的数据契约。
任何「风格变体」(不同 style 的 html) 只需读取同一份 `kpi_today.json`、遵循本契约，
即可自行决定样式与布局，**无需复制任何数据或绘图逻辑**。

---

## 1. 标准版定位

- **标准版文件**：`output/html/deep_diagnosis_latest.html`
  - 数据加载 + 绘图 + 7/14/28 天标签切换 + 失败展示 的**唯一逻辑来源**。
  - 文件头带 `<!-- 标准版 STANDARD ... -->` 注释标识。
- **风格变体**：只改 CSS / 布局；数据一律来自下面的 `kpi_today.json`，逻辑复用标准版（直接引用或自行读取 JSON）。
- **失败策略**：标准版**不内嵌任何数据**。加载失败 → 固定失败展示页（文案固定，仅「失败原因」按实情输出）。绝不回退到占位/过期数据。

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

```js
async function loadData() {
  const resp = await fetch('../kpi_today.json', { cache: 'no-store' });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);     // 具体原因①
  const data = await resp.json();                            // 解析失败 → 具体原因②
  if (!data.history) throw new Error('缺少 history');        // 契约不符 → 具体原因③
  if (!Array.isArray(data.history.hrv_cal_28d)) throw ...;   // 缺序列 → 具体原因④
  render(data);                                              // 成功才渲染
}
// 任一异常 → 进入固定失败展示，仅"失败原因"随异常 message 变化
```

- **file:// 双击打开**：浏览器拦截本地 `fetch`，一律失败展示（这是预期行为，不是 bug）。
- **正确打开方式**：经 HTTP 服务，例如 `python3 -m http.server` 指向 `output/` 后访问 `html/deep_diagnosis_latest.html`。

---

## 6. 变体html 自检清单

- [ ] 数据来源指向 `../kpi_today.json`（同目录约定）
- [ ] 加载失败进入固定失败展示，无占位数据
- [ ] 消费 `history.*_cal_28d`，`null` 按"缺口"渲染
- [ ] 窗口切片用 `slice(-win)`，win ∈ {7,14,28}
- [ ] 睡眠取 `value.total_sec / 3600`
- [ ] 重建数据后无需改任何变体代码（契约稳定）
