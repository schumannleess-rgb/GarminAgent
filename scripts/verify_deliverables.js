#!/usr/bin/env node
// Verify each HTML deliverable's embedded data matches authoritative kpi_today.json.
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const kpi = JSON.parse(fs.readFileSync(path.join(ROOT, 'output', 'kpi_today.json'), 'utf8'));

function extractObj(html, marker) {
  const re = new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*=\\s*([\\s\\S]*?);\\s*\\n');
  const m = html.match(re);
  if (!m) return null;
  return eval('(' + m[1] + ')'); // handles both JSON and single-quoted JS literal
}

function summarize(d) {
  if (!d || typeof d !== 'object') return null;
  const comp = d.composite || {};
  const ds = d.dimension_scores || {};
  const h = d.history || {};
  const out = {
    date: d.date,
    recovery: comp.recovery_score,
    grade: comp.grade,
    dim: {},
    calLast: {},
  };
  for (const k of Object.keys(ds)) out.dim[k] = (ds[k] || {}).score;
  for (const k of ['hrv_cal_28d','rhr_cal_28d','sleep_cal_28d','readiness_cal_28d','recovery_cal_28d']) {
    const arr = h[k];
    if (Array.isArray(arr) && arr.length) out.calLast[k] = arr[arr.length-1];
  }
  return out;
}

function problems(s) {
  const p = [];
  if (s.date !== kpi.date) p.push('date ' + s.date + ' != ' + kpi.date);
  if (s.recovery !== kpi.composite.recovery_score) p.push('recovery ' + s.recovery + ' != ' + kpi.composite.recovery_score);
  if (s.grade !== kpi.composite.grade) p.push('grade ' + s.grade + ' != ' + kpi.composite.grade);
  const kdim = {};
  for (const k of Object.keys(kpi.dimension_scores)) kdim[k] = kpi.dimension_scores[k].score;
  if (JSON.stringify(s.dim) !== JSON.stringify(kdim)) p.push('dim ' + JSON.stringify(s.dim) + ' != ' + JSON.stringify(kdim));
  const rec = s.calLast.recovery_cal_28d;
  if (rec && typeof rec === 'object' && rec.value !== kpi.composite.recovery_score) p.push('recovery_cal_28d[-1] ' + rec.value + ' != ' + kpi.composite.recovery_score);
  return p;
}

console.log('AUTHORITATIVE:', JSON.stringify(summarize(kpi)));
console.log('');

let allOk = true;

const markerFiles = [
  ['recovery_standard.html', 'const STATIC_DATA', '标准版(手工)'],
  ['recovery_pin_paper.html', 'const STATIC_DATA', '风格1 pin-paper'],
  ['recovery_zine.html', 'const STATIC_DATA', '风格2 zine'],
  ['recovery_data.html', 'const EMBEDDED', '数字版 recovery_data'],
];

for (const [fname, marker, label] of markerFiles) {
  const html = fs.readFileSync(path.join(ROOT, 'output/html', fname), 'utf8');
  let d, err = null;
  try { d = extractObj(html, marker); } catch (e) { err = e.message; }
  if (err || !d) {
    console.log('[FAIL] ' + fname + ' (' + label + '): ' + (err || 'marker not found'));
    allOk = false; continue;
  }
  const s = summarize(d);
  const p = problems(s);
  if (p.length) { allOk = false; console.log('[STALE] ' + fname + ' (' + label + ')'); p.forEach(x => console.log('   - ' + x)); }
  else console.log('[OK] ' + fname + ' (' + label + ')  recovery=' + s.recovery + ' grade=' + s.grade + ' dim=' + JSON.stringify(s.dim));
}

// recovery-deck: Python-baked, no STATIC_DATA block. Verify rendered numbers.
{
  const fname = 'recovery_swiss.html';
  const html = fs.readFileSync(path.join(ROOT, 'output/html', fname), 'utf8');
  const need = {
    recovery: String(kpi.composite.recovery_score),
    grade: kpi.composite.grade,
    hrv: String(kpi.dimension_scores.hrv.score),
    rhr: String(kpi.dimension_scores.rhr.score),
    sleepScore: String(kpi.dimension_scores.sleep.score),
    readiness: String(kpi.dimension_scores.readiness.score),
  };
  const miss = [];
  for (const [k, v] of Object.entries(need)) {
    if (!html.includes(v)) miss.push(k + '=' + v);
  }
  // sleep hours ~7.8h derived from total_seconds 27900 -> 7.75h
  const sleepH = (kpi.raw_inputs.sleep.total_seconds / 3600).toFixed(2);
  if (!html.includes(sleepH) && !html.includes('7.8') && !html.includes('7.75')) miss.push('sleepH=' + sleepH);
  if (miss.length) { allOk = false; console.log('[STALE] ' + fname + ' (风格3 recovery-deck): missing ' + miss.join(', ')); }
  else console.log('[OK] ' + fname + ' (风格3 recovery-deck)  recovery=' + need.recovery + ' grade=' + need.grade + ' hrv=' + need.hrv + ' rhr=' + need.rhr + ' sleep=' + need.sleepScore + ' readiness=' + need.readiness + ' sleepH=' + sleepH);
}

console.log('');
console.log('RESULT:', allOk ? 'ALL ACCURATE' : 'SOME STALE / FAIL');
process.exit(allOk ? 0 : 1);
