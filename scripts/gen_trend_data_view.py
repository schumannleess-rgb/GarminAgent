# -*- coding: utf-8 -*-
"""生成无样式高密度数据页 recovery_data.html（铺满 kpi_today.json 全部字段）。"""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "output", "kpi_today.json")
DST = os.path.join(BASE, "output", "html", "recovery_data.html")

with open(SRC, encoding="utf-8") as f:
    d = json.load(f)

data_json = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")

# ---- JS render：尽量铺满全部字段 ----
RENDER = r"""
function esc(v){ if(v===null||v===undefined) return '—'; return String(v); }
function num(v){ return (typeof v==='number') ? v : (v===null||v===undefined?'—':v); }
function pct(v,dgt){ if(typeof v!=='number') return '—'; return v.toFixed(dgt===undefined?1:dgt)+'%'; }
function secToH(s){ if(typeof s!=='number') return '—'; return (s/3600).toFixed(2)+' h'; }
function secToHM(s){ if(typeof s!=='number') return '—'; var h=Math.floor(s/3600), m=Math.round((s%3600)/60); return h+'h'+String(m).padStart(2,'0')+'m'; }
function kvTable(rows){ var h='<table border="1" cellspacing="0" cellpadding="4"><tbody>'; for(var i=0;i<rows.length;i++){ h+='<tr><th align="left">'+esc(rows[i][0])+'</th><td>'+esc(rows[i][1])+'</td></tr>'; } return h+'</tbody></table>'; }
function grid(headers, rows){ var h='<table border="1" cellspacing="0" cellpadding="4"><thead><tr>'; for(var i=0;i<headers.length;i++) h+='<th>'+esc(headers[i])+'</th>'; h+='</tr></thead><tbody>'; for(var r=0;r<rows.length;r++){ h+='<tr>'; for(var c=0;c<rows[r].length;c++) h+='<td>'+esc(rows[r][c])+'</td>'; h+='</tr>'; } return h+'</tbody></table>'; }
function sec(title, inner){ return '<section><h2>'+esc(title)+'</h2>'+inner+'</section>'; }
function ol(items){ var h='<ol>'; for(var i=0;i<items.length;i++) h+='<li>'+esc(items[i])+'</li>'; return h+'</ol>'; }

function render(d){
  d = d || {};
  var H = '';

  // 1) 元信息
  H += sec('元信息', kvTable([
    ['日期', d.date],
    ['生成时间', d.generated_at],
    ['引擎版本', d.engine_version],
    ['设计文档', d.design_doc],
    ['引用条数', d.references_count],
    ['数据源', d.data_source],
    ['最新数据日期', d.latest_db_date],
  ]));

  // 2) 综合恢复分
  var c = d.composite || {};
  var w = c.weights || {};
  var compInner = kvTable([
    ['恢复分', c.recovery_score],
    ['等级', c.grade],
    ['标签', c.label],
    ['区间', c.zone],
    ['公式', c.formula],
    ['参考', c.reference],
  ]);
  compInner += '<h3>权重</h3>' + kvTable([
    ['HRV', w.hrv],['睡眠', w.sleep],['RHR', w.rhr],['准备度', w.readiness],['压力', w.stress],
  ]);
  if(Array.isArray(c.calculation_steps)) compInner += '<h3>计算步骤</h3>' + ol(c.calculation_steps);
  H += sec('综合恢复分', compInner);

  // 3) 各维度评分（含锚点表）
  var ds = d.dimension_scores || {};
  var dimInner = '';
  // HRV
  if(ds.hrv){ var x=ds.hrv;
    dimInner += '<h3>HRV 心率变异性</h3>' + kvTable([
      ['昨夜(ms)', x.last_night_ms],['7天均(ms)', x.weekly_avg_ms],
      ['ln(昨夜)', x.ln_last_night],['ln(基线)', x.ln_baseline],
      ['变化率', typeof x.pct_change==='number'?(x.pct_change*100).toFixed(2)+'%':'—'],
      ['变化率(%)', typeof x.pct_change_pct==='number'?x.pct_change_pct+'%':'—'],
      ['是否回退', x.fallback_used],['评分', x.score],['区间', x.zone],
    ]);
    if(Array.isArray(x.anchors)) dimInner += grid(['变化率','评分','标签'], x.anchors.map(function(a){return [a.pct_change, a.score, a.label];}));
  }
  // RHR
  if(ds.rhr){ var y=ds.rhr;
    dimInner += '<h3>静息心率 RHR</h3>' + kvTable([
      ['当前(bpm)', y.current_bpm],['基线(bpm)', y.baseline_bpm],
      ['偏差', y.deviation],['偏差(文本)', y.deviation_bpm],['评分', y.score],['区间', y.zone],
    ]);
    if(Array.isArray(y.anchors)) dimInner += grid(['偏差(bpm)','评分','标签'], y.anchors.map(function(a){return [a.deviation_bpm, a.score, a.label];}));
  }
  // Sleep
  if(ds.sleep){ var s=ds.sleep;
    dimInner += '<h3>睡眠</h3>' + kvTable([
      ['总时长', secToHM(s.total_seconds)+' ('+num(s.total_seconds)+'s)'],
      ['深睡', secToHM(s.deep_seconds)+' ('+num(s.deep_seconds)+'s)'],
      ['REM', secToHM(s.rem_seconds)+' ('+num(s.rem_seconds)+'s)'],
      ['清醒次数', s.awake_count],['用 Garmin 分', s.garmin_score_used],['评分', s.score],
    ]);
    if(s.sub_scores && Object.keys(s.sub_scores).length) dimInner += kvTable(Object.keys(s.sub_scores).map(function(k){return [k, s.sub_scores[k]];}));
  }
  // Readiness
  if(ds.readiness){ var rd=ds.readiness;
    dimInner += '<h3>训练准备度</h3>' + kvTable([
      ['原始分', rd.original_score],['评分', rd.score],['区间', rd.zone],
    ]);
  }
  // Stress
  if(ds.stress){ var st=ds.stress;
    dimInner += '<h3>压力</h3>' + kvTable([
      ['压力等级', st.stress_level],['评分', st.score],['区间', st.zone],
    ]);
    if(Array.isArray(st.anchors)) dimInner += grid(['压力等级','评分','标签'], st.anchors.map(function(a){return [a.stress_level, a.score, a.label];}));
  }
  H += sec('各维度评分', dimInner);

  // 4) 派生指标
  var der = d.derived_metrics_summary || {};
  H += sec('派生指标', kvTable([
    ['HRV 变化率(%)', der.hrv_pct_change],['HRV ln 变化', der.hrv_ln_change],
    ['RHR 偏差(bpm)', der.rhr_deviation_bpm],['睡眠总时长(h)', der.sleep_total_hours],
    ['深睡占比(%)', der.sleep_deep_pct],['REM 占比(%)', der.sleep_rem_pct],
    ['压力等级', der.stress_level],['压力评分', der.stress_score],['压力区间', der.stress_zone],
    ['训练负荷', der.training_load],['ACWR(%)', der.acwr_percent],['准备度原始分', der.readiness_score_original],
  ]));

  // 5) 基线
  var b = d.baselines || {};
  var sb = b.sleep_baseline_7d || {};
  var baseInner = kvTable([
    ['HRV 7天基线(ms)', b.hrv_baseline_7d],
    ['RHR 28天基线(bpm)', b.rhr_baseline_28d],
    ['睡眠 7天基线', secToHM(sb.total_seconds)+' / '+num(sb.total_hours)+'h / 深睡'+num(sb.deep_pct_avg)+'%'],
  ]);
  if(b.formulas) baseInner += '<h3>公式</h3>' + kvTable(Object.keys(b.formulas).map(function(k){return [k, b.formulas[k]];}));
  H += sec('基线', baseInner);

  // 6) 原始输入
  var ri = d.raw_inputs || {};
  var riInner = '';
  if(ri.hrv) riInner += '<h3>HRV</h3>' + kvTable([['昨夜', ri.hrv.last_night],['周均', ri.hrv.weekly_avg],['状态', ri.hrv.status]]);
  if(ri.rhr) riInner += '<h3>RHR</h3>' + kvTable([['当前(bpm)', ri.rhr.current_bpm]]);
  if(ri.sleep) riInner += '<h3>睡眠</h3>' + kvTable([['总(s)', ri.sleep.total_seconds],['深睡(s)', ri.sleep.deep_seconds],['REM(s)', ri.sleep.rem_seconds],['清醒次数', ri.sleep.awake_count],['Garmin 睡眠分', ri.sleep.garmin_sleep_score]]);
  if(ri.readiness) riInner += '<h3>准备度</h3>' + kvTable([['分数', ri.readiness.score],['等级', ri.readiness.level]]);
  if(ri.profile){ var p=ri.profile;
    riInner += '<h3>档案 Profile</h3>' + kvTable([
      ['设备', p.device],['VO2max', p.vo2max],['BMI', p.bmi],['体能年龄', p.fitness_age],['实际年龄', p.chronological_age],
      ['训练状态', p.training_status_phrase],['ACWR(%)', p.acwr_percent],['总步数', p.total_steps],['总距离(m)', p.total_distance_m],
      ['活动热量', p.active_calories],['平均压力', p.avg_stress],['最大压力', p.max_stress],['最低心率', p.min_hr],['最高心率', p.max_hr],
      ['身体电量充', p.body_battery_charged],['身体电量耗', p.body_battery_drained],['平均血氧', p.avg_spo2],
    ]);
  }
  if(ri.stress_raw) riInner += '<h3>压力原始</h3>' + kvTable([['平均', ri.stress_raw.avg_stress_level],['最大', ri.stress_raw.max_stress_level]]);
  if(ri.race_predictions && Object.keys(ri.race_predictions).length) riInner += '<h3>比赛预测</h3>' + kvTable(Object.keys(ri.race_predictions).map(function(k){return [k, ri.race_predictions[k]];}));
  H += sec('原始输入', riInner);

  // 7) 趋势（恢复分近期走势，带日期）
  var tr = d.trend || {};
  var trInner = kvTable([
    ['窗口天数', tr.window_checked],['警戒线', tr.threshold],['低分连续天数', tr.low_streak],['预警', tr.alert===null?'无':tr.alert],
  ]);
  var scores = tr.recent_scores_in_window || [];
  // 用 readiness_28d 的日期倒序映射（升序：最旧->最新）
  var rdHist = (d.history && d.history.readiness_28d) || [];
  var rdDatesAsc = rdHist.map(function(r){return r.date;}).slice().reverse();
  var offset = rdDatesAsc.length - scores.length;
  var trRows = scores.map(function(s,i){
    var ago = scores.length-1-i;
    var date = rdDatesAsc[offset+i] || '';
    var lbl = ago===0?'今日':(ago+'天前');
    var flag = s < (tr.threshold||60) ? '⚠ 低于警戒' : '';
    return [i+1, date, lbl, s, flag];
  });
  trInner += '<p>共 '+scores.length+' 个数据点（升序：最旧 → 最新）：</p>' + grid(['#','日期','相对','恢复分','标记'], trRows);
  H += sec('趋势 · 恢复分近期走势', trInner);

  // 8) 多维校验
  var mv = d.multi_dimension_validation || {};
  var pats = mv.patterns_checked || [];
  var mvInner = kvTable([['检查模式数', mv.num_patterns_checked],['命中数', mv.num_matched]]);
  mvInner += grid(['ID','名称','条件','参考','是否命中'], pats.map(function(p){return [p.id, p.label, p.condition_desc, p.ref, p.match?'✓ 命中':'—'];}));
  H += sec('多维校验模式', mvInner);

  // 9) 历史序列（四条完整表）
  var hist = d.history || {};
  var histInner = '';
  if(Array.isArray(hist.hrv_14d)) histInner += '<h3>HRV（近 '+hist.hrv_14d.length+' 天）</h3>' + grid(['日期','HRV(ms)'], hist.hrv_14d.map(function(r){return [r.date, r.value];}));
  if(Array.isArray(hist.rhr_28d)) histInner += '<h3>RHR（近 '+hist.rhr_28d.length+' 天）</h3>' + grid(['日期','RHR(bpm)'], hist.rhr_28d.map(function(r){return [r.date, r.value];}));
  if(Array.isArray(hist.sleep_28d)) histInner += '<h3>睡眠（近 '+hist.sleep_28d.length+' 天）</h3>' + grid(['日期','总时长','深睡','深睡%'], hist.sleep_28d.map(function(r){var dp=(r.total_sec?(r.deep_sec/r.total_sec*100):0); return [r.date, secToHM(r.total_sec), secToHM(r.deep_sec), dp.toFixed(1)+'%'];}));
  if(Array.isArray(hist.readiness_28d)) histInner += '<h3>训练准备度（近 '+hist.readiness_28d.length+' 天）</h3>' + grid(['日期','分数','等级'], hist.readiness_28d.map(function(r){return [r.date, r.score, r.level];}));
  H += sec('历史序列', histInner);

  // 10) 原始 JSON
  H += sec('原始 JSON', '<pre>'+JSON.stringify(d,null,2)+'</pre>');

  document.getElementById('app').innerHTML = H;
}

async function load(){
  var data;
  try{
    var r = await fetch('../kpi_today.json', {cache:'no-store'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    data = await r.json();
  }catch(e){
    data = EMBEDDED;
    console.warn('fetch 失败，使用内嵌数据:', e.message);
  }
  render(data);
}
document.addEventListener('DOMContentLoaded', load);
"""

html = (
    "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
    "<title>恢复趋势 · 数据视图（无样式 · 全字段）</title>\n</head>\n<body>\n"
    "<h1>恢复趋势追踪 · 数据视图（无样式 · 全字段）</h1>\n"
    "<div id=\"app\">加载中…</div>\n"
    "<script>\nconst EMBEDDED = " + data_json + ";\n" + RENDER + "\n</script>\n"
    "</body>\n</html>\n"
)

with open(DST, "w", encoding="utf-8") as f:
    f.write(html)
print("written", DST, "bytes=", len(html))
