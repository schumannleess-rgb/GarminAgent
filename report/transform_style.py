import re

with open(r'd:\Garmin\Garmin\garmin-agent\GarminAgent\output\html\deep_diagnosis.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Google Fonts links after viewport meta
content = content.replace(
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">'
)

# 2. Replace title
content = content.replace(
    '<title>深度诊断</title>',
    '<title>深度诊断 · Pin & Paper</title>'
)

# 3. Replace CSS block
old_css_start = content.find('<style>')
old_css_end = content.find('</style>', old_css_start) + len('</style>')

new_css = '''<style>
  /* === Pin & Paper Style · deep_diagnosis v2.0 === */
  /* Style: pin-and-paper */
  :root {
    --paper:    #EFE56A;
    --paper-2:  #F5ECA0;
    --cream:    #F8F1D6;
    --kraft:    #C9A66B;
    --ink:      #1F3A8A;
    --ink-soft: #2D4FB8;
    --ink-line: #3457C4;
    --black:    #0E1430;
    --red:      #C2342B;
    --olive:    #6B7A2E;
    --orange:   #D8702A;

    --bg:              var(--paper);
    --card:            var(--cream);
    --card-border:     var(--ink);
    --primary:         var(--ink);
    --text:            var(--ink);
    --text-dim:        var(--ink-soft);
    --text-dark:       var(--ink-line);
    --code-bg:         var(--paper-2);

    --excellent:       #2d6a4f;
    --good:            var(--ink);
    --caution:         var(--orange);
    --poor:            #c1121f;
    --critical:        var(--red);

    --dim-hrv:         var(--olive);
    --dim-rhr:         #8b4513;
    --dim-sleep:       #2d6a4f;
    --dim-readiness:   var(--orange);
    --dim-stress:      #7c6a2f;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--paper);
    color: var(--text);
    font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  /* Paper grain texture */
  body::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    opacity: .35;
    mix-blend-mode: multiply;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='1.4' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.5  0 0 0 0 0.45  0 0 0 0 0.2  0 0 0 .25 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
    z-index: 0;
  }

  .container {
    position: relative;
    z-index: 1;
    max-width: 900px;
    margin: 0 auto;
    padding: 24px 16px 80px;
  }

  /* Loading */
  .loading {
    text-align: center;
    padding: 60px 20px;
    color: var(--ink-soft);
  }
  .spinner {
    width: 32px; height: 32px;
    border: 3px solid var(--ink-line);
    border-top-color: var(--ink);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 16px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .hidden { display: none !important; }

  /* Header - top chrome */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 16px 4px;
    margin-bottom: 16px;
    border-bottom: 2px solid var(--ink);
  }
  .header-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: var(--ink);
    letter-spacing: -0.02em;
  }
  .header-date {
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    color: var(--ink-soft);
    text-align: right;
  }
  .header-source {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: var(--ink-line);
    margin-top: 2px;
    text-align: right;
  }

  /* Alert bar */
  .alert-bar {
    border: 2px solid var(--ink);
    border-radius: 4px;
    padding: 12px 16px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    font-weight: 600;
  }
  .alert-bar.ok {
    background: rgba(45,106,79,0.1);
    border-color: var(--excellent);
    color: var(--excellent);
  }
  .alert-bar.warn {
    background: rgba(193,18,31,0.08);
    border-color: var(--critical);
    color: var(--critical);
  }

  /* Section cards - pinned note style */
  .section {
    background: var(--cream);
    border: 2px solid var(--ink);
    border-radius: 4px;
    padding: 20px;
    margin-bottom: 16px;
    position: relative;
    box-shadow: 5px 6px 0 0 var(--ink);
  }

  /* Push pin decoration */
  .section::before {
    content: "";
    position: absolute;
    top: -9px;
    left: 20px;
    width: 16px;
    height: 16px;
    background: var(--red);
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0,0,0,0.25);
    z-index: 2;
  }
  .section::after {
    content: "";
    position: absolute;
    top: 5px;
    left: 27px;
    width: 3px;
    height: 14px;
    background: var(--red);
    z-index: 1;
  }

  .section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 15px;
    font-weight: 700;
    color: var(--ink);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .section-num {
    font-family: 'Caveat', cursive;
    font-weight: 700;
    font-size: 26px;
    color: var(--red);
    line-height: 1;
    min-width: 32px;
  }

  /* Hero score ring */
  .hero-row {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 14px;
  }
  .score-ring {
    width: 110px; height: 110px;
    position: relative;
    flex-shrink: 0;
  }
  .score-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
  .score-ring-bg {
    fill: none;
    stroke: var(--ink-line);
    stroke-width: 7;
    opacity: 0.2;
  }
  .score-ring-fill {
    fill: none;
    stroke-width: 7;
    stroke-linecap: round;
    transition: stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .score-value {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transform: rotate(0deg);
  }
  .score-number {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 38px;
    font-weight: 700;
    line-height: 1;
    color: var(--ink);
  }
  .grade-badge {
    display: inline-block;
    padding: 5px 14px;
    border: 3px solid var(--red);
    border-radius: 4px;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: var(--red);
    transform: rotate(-3deg);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .score-label {
    font-family: 'Caveat', cursive;
    font-size: 16px;
    color: var(--ink-soft);
    margin-top: 4px;
  }

  /* Contribution bar */
  .contrib-bar {
    display: flex;
    height: 28px;
    border-radius: 4px;
    overflow: hidden;
    margin: 10px 0;
    border: 1.5px solid var(--ink);
  }
  .contrib-seg {
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    color: var(--ink);
    transition: width 0.8s ease;
  }
  .contrib-legend {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-top: 8px;
  }
  .contrib-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    padding: 4px 0;
  }
  .contrib-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .contrib-label { color: var(--ink-soft); flex: 1; }
  .contrib-val {
    font-family: 'DM Mono', monospace;
    font-weight: 600;
    color: var(--ink);
  }

  /* Formula box */
  .formula-box {
    background: var(--paper-2);
    border: 1.5px solid var(--ink);
    border-radius: 4px;
    padding: 14px;
    margin: 10px 0;
    font-size: 13px;
    line-height: 1.7;
  }
  .formula-box .hl {
    color: var(--ink);
    font-weight: 700;
  }
  .formula-box .d-hrv { color: var(--dim-hrv); }
  .formula-box .d-sleep { color: var(--dim-sleep); }
  .formula-box .d-rhr { color: var(--dim-rhr); }
  .formula-box .d-ready { color: var(--dim-readiness); }
  .formula-box .d-stress { color: var(--dim-stress); }

  /* KPI Grid */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }
  .kpi-card {
    background: var(--paper-2);
    border: 1.5px solid var(--ink);
    border-radius: 4px;
    padding: 14px;
    box-shadow: 3px 4px 0 0 var(--ink);
  }
  .kpi-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
  }
  .kpi-icon { font-size: 16px; }
  .kpi-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 12px;
    color: var(--ink-soft);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .kpi-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: var(--ink);
  }
  .kpi-unit {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: var(--ink-soft);
    font-weight: 400;
    margin-left: 2px;
  }
  .kpi-delta {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    margin-top: 4px;
    font-weight: 600;
  }
  .kpi-delta.up { color: var(--excellent); }
  .kpi-delta.down { color: var(--critical); }
  .kpi-delta.neutral { color: var(--ink-soft); }
  .kpi-desc {
    font-size: 11px;
    color: var(--ink-soft);
    margin-top: 6px;
    line-height: 1.5;
  }
  .kpi-bar {
    height: 4px;
    background: var(--ink-line);
    opacity: 0.2;
    border-radius: 2px;
    margin-top: 8px;
    overflow: hidden;
  }
  .kpi-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.8s ease;
  }

  /* Chart cards */
  .chart-card {
    background: var(--cream);
    border: 1.5px solid var(--ink);
    border-radius: 4px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 5px 6px 0 0 var(--ink);
  }
  .chart-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: var(--ink);
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .chart-subtitle {
    font-family: 'Caveat', cursive;
    font-size: 15px;
    color: var(--ink-soft);
    margin-bottom: 10px;
  }
  .chart-wrap {
    position: relative;
    width: 100%;
    height: 200px;
  }
  .chart-wrap canvas {
    width: 100%;
    height: 100%;
    display: block;
  }
  .chart-tooltip {
    position: absolute;
    pointer-events: none;
    background: var(--cream);
    border: 1.5px solid var(--ink);
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 12px;
    line-height: 1.5;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 10;
    white-space: nowrap;
    box-shadow: 2px 3px 0 0 var(--ink);
  }
  .chart-tooltip.show { opacity: 1; }
  .chart-tooltip .tt-date {
    font-family: 'DM Mono', monospace;
    color: var(--ink-soft);
    font-size: 11px;
  }
  .chart-tooltip .tt-val {
    font-weight: 700;
    font-family: 'DM Mono', monospace;
  }
  .chart-legend {
    display: flex;
    gap: 16px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--ink-soft);
  }
  .chart-legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .legend-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
  }

  /* Info rows */
  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1.5px dashed var(--ink-line);
    font-size: 13px;
  }
  .info-row:last-child { border-bottom: none; }
  .info-label {
    color: var(--ink-soft);
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'Space Grotesk', sans-serif;
  }
  .info-value {
    font-family: 'DM Mono', monospace;
    font-weight: 600;
    color: var(--ink);
  }
  .info-value.better { color: var(--excellent); }
  .info-value.warn { color: var(--caution); }
  .info-value.bad { color: var(--critical); }

  /* Text analysis */
  .analysis-text {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    line-height: 1.8;
    color: var(--ink-soft);
  }
  .analysis-text strong {
    color: var(--ink);
    font-weight: 600;
  }
  .analysis-text .good { color: var(--excellent); }
  .analysis-text .warn { color: var(--caution); }
  .analysis-text .bad { color: var(--critical); }

  /* Pattern items */
  .pattern-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 8px;
    background: var(--paper-2);
    border: 1.5px solid var(--ink);
    box-shadow: 2px 3px 0 0 var(--ink);
  }
  .pattern-item.matched {
    background: rgba(45,106,79,0.08);
    border-color: var(--excellent);
    box-shadow: 2px 3px 0 0 var(--excellent);
  }
  .pattern-icon { font-size: 16px; flex-shrink: 0; margin-top: 2px; }
  .pattern-content { flex: 1; }
  .pattern-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 2px;
  }
  .pattern-desc {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    color: var(--ink-soft);
    line-height: 1.5;
  }
  .pattern-meaning {
    font-family: 'Caveat', cursive;
    font-size: 13px;
    color: var(--ink-soft);
    margin-top: 4px;
    padding-top: 4px;
    border-top: 1px dashed var(--ink-line);
  }

  /* Advice items */
  .advice-item {
    display: flex;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1.5px dashed var(--ink-line);
  }
  .advice-item:last-child { border-bottom: none; }
  .advice-icon { font-size: 18px; flex-shrink: 0; }
  .advice-content {
    flex: 1;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    line-height: 1.6;
    color: var(--ink);
  }
  .advice-content strong {
    color: var(--red);
    font-weight: 600;
  }

  /* Sleep grid */
  .sleep-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 12px;
  }
  .sleep-stat {
    background: var(--paper-2);
    border: 1.5px solid var(--ink);
    border-radius: 4px;
    padding: 12px;
    text-align: center;
    box-shadow: 2px 3px 0 0 var(--ink);
  }
  .sleep-stat-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    color: var(--ink-soft);
    margin-bottom: 4px;
  }
  .sleep-stat-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: var(--ink);
  }
  .sleep-stat-unit {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: var(--ink-soft);
  }

  /* Sleep note */
  #sleepNote {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 12px;
    margin-bottom: 10px;
    padding: 8px 12px;
    border-radius: 4px;
    border: 1.5px solid var(--ink);
  }

  /* Raw data toggle */
  .raw-toggle {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    background: var(--ink);
    color: var(--paper);
    border: none;
    border-top: 3px solid var(--black);
    padding: 12px 16px;
    z-index: 100;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }
  .raw-content {
    display: none;
    margin-bottom: 60px;
  }
  .raw-content.show { display: block; }
  .raw-content pre {
    background: var(--paper-2);
    border: 1.5px solid var(--ink);
    border-radius: 4px;
    padding: 12px;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    line-height: 1.5;
    overflow-x: auto;
    color: var(--ink-soft);
    max-height: 300px;
    overflow-y: auto;
  }

  /* Responsive */
  @media (max-width: 700px) {
    .kpi-grid { grid-template-columns: 1fr; }
    .hero-row { flex-direction: column; text-align: center; }
  }
}
</style>'''

content = content[:old_css_start] + new_css + content[old_css_end:]

# 4. Update sleep grid HTML
content = content.replace(
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">',
    '<div class="sleep-grid">'
)
content = content.replace(
    '<div style="background:rgba(0,0,0,0.2);padding:12px;border-radius:10px;text-align:center;">',
    '<div class="sleep-stat">'
)
content = content.replace(
    '<div style="font-size:11px;color:var(--text-dim);margin-bottom:4px;">总睡眠</div>',
    '<div class="sleep-stat-label">总睡眠</div>'
)
content = content.replace(
    '<div style="font-size:11px;color:var(--text-dim);">小时</div>',
    '<div class="sleep-stat-unit">小时</div>'
)
content = content.replace(
    '<div style="font-size:11px;color:var(--text-dim);margin-bottom:4px;">深睡占比</div>',
    '<div class="sleep-stat-label">深睡占比</div>'
)
content = content.replace(
    '<div style="font-size:11px;color:var(--text-dim);">正常 10-25%</div>',
    '<div class="sleep-stat-unit">正常 10-25%</div>'
)

# 5. Update JS colors

# GRADE_COLORS - exact strings from original file
content = content.replace(
    "'A': { color: '#22c55e', glow: 'rgba(34,197,94,0.15)', border: 'rgba(34,197,94,0.3)', label: '状态极佳' }",
    "'A': { color: '#2d6a4f', glow: 'rgba(45,106,79,0.15)', border: 'rgba(45,106,79,0.3)', label: '状态极佳' }"
)
content = content.replace(
    "'B': { color: '#3b82f6', glow: 'rgba(59,130,246,0.15)', border: 'rgba(59,130,246,0.3)', label: '状态良好' }",
    "'B': { color: '#1F3A8A', glow: 'rgba(31,58,138,0.12)', border: 'rgba(31,58,138,0.25)', label: '状态良好' }"
)
content = content.replace(
    "'C': { color: '#eab308', glow: 'rgba(234,179,8,0.15)', border: 'rgba(234,179,8,0.3)', label: '需要注意' }",
    "'C': { color: '#D8702A', glow: 'rgba(216,112,42,0.12)', border: 'rgba(216,112,42,0.25)', label: '需要注意' }"
)
content = content.replace(
    "'D': { color: '#f97316', glow: 'rgba(249,115,22,0.15)', border: 'rgba(249,115,22,0.3)', label: '恢复不足' }",
    "'D': { color: '#c1121f', glow: 'rgba(193,18,31,0.12)', border: 'rgba(193,18,31,0.25)', label: '恢复不足' }"
)
content = content.replace(
    "'F': { color: '#ef4444', glow: 'rgba(239,68,68,0.15)', border: 'rgba(239,68,68,0.3)', label: '需要休息' }",
    "'F': { color: '#C2342B', glow: 'rgba(194,52,43,0.15)', border: 'rgba(194,52,43,0.3)', label: '需要休息' }"
)

# Chart line colors in render() and drawAllCharts()
# Note: these appear with || fallback, so we match the literal strings
content = content.replace("color: '#38bdf8'", "color: '#1F3A8A'")
content = content.replace("fillColor: 'rgba(56,189,248,0.08)'", "fillColor: 'rgba(31,58,138,0.1)'")
content = content.replace("color: '#818cf8'", "color: '#6B7A2E'")
content = content.replace("fillColor: 'rgba(129,140,248,0.06)'", "fillColor: 'rgba(107,122,46,0.08)'")
content = content.replace("color: '#f472b6'", "color: '#8b4513'")
content = content.replace("fillColor: 'rgba(244,114,182,0.06)'", "fillColor: 'rgba(139,69,19,0.08)'")
content = content.replace("color: '#34d399'", "color: '#2d6a4f'")
content = content.replace("fillColor: 'rgba(52,211,153,0.08)'", "fillColor: 'rgba(45,106,79,0.1)'")
content = content.replace("color: '#fb923c'", "color: '#D8702A'")
content = content.replace("fillColor: 'rgba(251,146,60,0.08)'", "fillColor: 'rgba(216,112,42,0.1)'")

# Canvas drawing colors
content = content.replace("strokeStyle = '#0f172a'", "strokeStyle = '#F8F1D6'")
content = content.replace("fillStyle = 'rgba(148,163,184,0.6)'", "fillStyle = 'rgba(31,58,138,0.5)'")
content = content.replace("strokeStyle = 'rgba(239,68,68,0.3)'", "strokeStyle = 'rgba(194,52,43,0.35)'")
content = content.replace("fillStyle = 'rgba(239,68,68,0.6)'", "fillStyle = 'rgba(194,52,43,0.8)'")

# Tooltip background (CSS)
content = content.replace(
    "background: rgba(15,23,42,0.95);",
    "background: rgba(248,241,214,0.95);"
)

# Sleep note JS inline styles
content = content.replace(
    "sleepNote.style.background = 'rgba(34,197,94,0.1)'",
    "sleepNote.style.background = 'rgba(45,106,79,0.1)'"
)
content = content.replace(
    "sleepNote.style.background = 'rgba(148,163,184,0.1)'",
    "sleepNote.style.background = 'rgba(31,58,138,0.08)'"
)

# Pattern matched JS colors
content = content.replace('background: rgba(34,197,94,0.08)', 'background: rgba(45,106,79,0.1)')
content = content.replace('border: 1px solid rgba(34,197,94,0.2)', 'border: 1.5px solid rgba(45,106,79,0.3)')

# KPI card JS inline background
content = content.replace(
    "background: rgba(0,0,0,0.2)",
    "background: var(--paper-2)"
)

with open(r'd:\Garmin\Garmin\garmin-agent\GarminAgent\output\html\deep_diagnosis.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Transform complete')
