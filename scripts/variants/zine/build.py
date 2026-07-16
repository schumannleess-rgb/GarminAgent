#!/usr/bin/env python3
"""
build.py — 从 kpi_today.json 生成 wellness_zine.html

流程:
    1. 读取 output/kpi_today.json
    2. 提取 FALLBACK 数据（与 JSON 完全对齐，不再手写硬编码）
    3. 写入 output/html/wellness_zine.html

用法:
    python scripts/variants/zine/build.py
    python scripts/variants/zine/build.py --output path/to/output.html  # 自定义输出路径

前置条件:
    output/kpi_today.json 必须存在（由 rebuild_kpi_today.py 或 merge_kpi.py 生成）
"""

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

# __file__ = <PROJECT_ROOT>/scripts/variants/zine/build.py  → parents[3] = GarminAgent 根
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# ── Zine 模板 ──────────────────────────────────────────────────────────────
# 这是定稿的 wellness_zine.html 骨架，从 HTML 提取后固化到这里。
# 数据占位符用 {{KEY}} 语法，渲染时替换。

ZINE_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>每日健康手账 — Retro Zine v1.0</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Caveat:wght@400;700&family=Space+Grotesk:wght@300;400;500;600;700&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    /* ============================================
       RETRO ZINE DESIGN SYSTEM — 7页紧凑版
       scroll-snap vertical / mobile-first
       ============================================ */

    :root {
      --bg: #C8B99A;
      --bg_dark: #B8A98A;
      --green: #008F4D;
      --green_light: #00A85D;
      --black: #1A1A1A;
      --white: #F4EFE6;
      --white_ink: #E8E0D0;

      --display: 'Bebas Neue', 'Space Grotesk', sans-serif;
      --script: 'Caveat', 'Space Grotesk', sans-serif;
      --body: 'Space Grotesk', 'Noto Serif SC', sans-serif;
      --mono: 'Space Grotesk', monospace;
      --serif: 'Noto Serif SC', serif;

      --pad: clamp(16px, 4vw, 48px);
      --gap: clamp(12px, 3vw, 24px);
      --line: 3px;
      --rotate: -1.2deg;
      --rotate2: 0.8deg;
    }

    *, *::before, *::after {
      margin: 0; padding: 0; box-sizing: border-box;
    }

    html {
      font-size: 16px;
      -webkit-font-smoothing: antialiased;
      scroll-snap-type: y mandatory;
      overflow-y: scroll;
      scroll-behavior: smooth;
    }

    body {
      font-family: var(--body);
      background-color: var(--bg);
      color: var(--black);
      line-height: 1.55;
      overflow-x: hidden;
    }

    /* grain */
    .grain-overlay {
      position: fixed; inset: 0;
      pointer-events: none; z-index: 9999;
      opacity: 0.06; mix-blend-mode: multiply;
    }
    .grain-overlay svg { width: 100%; height: 100%; }

    /* slide */
    .slide {
      scroll-snap-align: start;
      min-height: 100dvh;
      width: 100%;
      padding: var(--pad);
      display: flex; flex-direction: column;
      position: relative;
    }

    /* chrome */
    .slide-chrome {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: var(--gap); flex-shrink: 0;
    }
    .section-number {
      font-family: var(--display);
      font-size: clamp(1.8rem, 5vw, 3.5rem);
      line-height: 1; letter-spacing: 0.05em;
    }
    .section-label {
      font-family: var(--script);
      font-size: clamp(1rem, 2.5vw, 1.4rem);
      color: var(--green);
      transform: rotate(-2deg);
      display: inline-block;
    }

    /* stamp */
    .stamp-mark {
      display: inline-block;
      font-family: var(--display);
      font-size: clamp(0.65rem, 1.8vw, 0.85rem);
      letter-spacing: 0.12em;
      padding: 5px 14px;
      border: var(--line) solid var(--black);
      color: var(--black);
      text-transform: uppercase;
      position: relative;
      transform: rotate(2deg);
      background: var(--white);
      white-space: nowrap;
    }
    .stamp-mark::before {
      content: ''; position: absolute;
      top: 3px; left: 3px; right: 3px; bottom: 3px;
      border: 1.5px dashed var(--black);
      pointer-events: none;
    }
    .stamp-mark.green { background: var(--green); color: var(--white); }
    .stamp-mark.green::before { border-color: var(--white); }

    /* ribbon */
    .ribbon-bar {
      width: 100%;
      padding: 10px 16px;
      background: var(--green); color: var(--white);
      font-family: var(--display);
      font-size: clamp(0.8rem, 2.2vw, 1.1rem);
      letter-spacing: 0.18em;
      text-transform: uppercase;
      margin: var(--gap) 0;
      border: var(--line) solid var(--black);
      position: relative; flex-shrink: 0;
    }
    .ribbon-bar::after {
      content: ''; position: absolute;
      bottom: 5px; right: 5px;
      width: 24px; height: 24px;
      background: repeating-linear-gradient(45deg, var(--black) 0px, var(--black) 2px, transparent 2px, transparent 5px);
      border: 1.5px solid var(--black);
    }

    /* card-offset */
    .card-offset {
      background: var(--white);
      border: var(--line) solid var(--black);
      padding: var(--pad);
      position: relative;
      transform: rotate(var(--rotate));
      transition: transform 0.3s ease;
    }
    .card-offset:hover { transform: rotate(0deg); }
    .card-offset::before {
      content: ''; position: absolute;
      top: 6px; left: 6px; right: -6px; bottom: -6px;
      background: var(--bg_dark);
      border: var(--line) solid var(--black);
      z-index: -1;
      transform: rotate(var(--rotate2));
    }

    .inline-highlight {
      background: var(--green); color: var(--white);
      padding: 2px 8px;
      font-family: var(--display); letter-spacing: 0.05em;
    }

    .drop-cap::first-letter {
      font-family: var(--display);
      font-size: 3.2em; line-height: 0.85;
      float: left; margin-right: 10px; margin-top: 4px;
      color: var(--green);
    }

    /* ========== SLIDE 1 — HERO ========== */
    #slide-1 {
      justify-content: center; align-items: center; text-align: center;
    }
    .hero-edition {
      font-family: var(--script);
      font-size: clamp(1rem, 2.8vw, 1.3rem);
      color: var(--green); transform: rotate(-3deg);
      margin-bottom: 12px;
    }
    .hero-title {
      font-family: var(--display);
      font-size: clamp(2.8rem, 13vw, 9rem);
      line-height: 0.9; letter-spacing: 0.03em;
      text-transform: uppercase; margin-bottom: 12px;
    }
    .hero-subtitle {
      font-family: var(--script);
      font-size: clamp(1.2rem, 3.5vw, 2rem);
      color: var(--green); transform: rotate(-2deg);
      display: inline-block;
    }
    .hero-grade {
      margin-top: 24px;
      font-family: var(--display);
      font-size: clamp(2.2rem, 7vw, 5.5rem);
      line-height: 1; color: var(--green);
      border: var(--line) solid var(--black);
      padding: 12px 36px; background: var(--white);
      display: inline-block; transform: rotate(1deg);
      position: relative;
    }
    .hero-grade::before {
      content: ''; position: absolute;
      top: 5px; left: 5px; right: -5px; bottom: -5px;
      background: var(--black); z-index: -1;
    }
    .hero-date {
      margin-top: 16px;
      font-family: var(--script); font-size: 1rem;
    }

    /* ========== SLIDE 2 — 今日概览 ========== */
    #slide-2 {
      justify-content: center;
    }
    .overview-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--gap);
      flex: 1; align-content: center;
    }
    .score-ring-wrap {
      display: flex; justify-content: center;
    }
    #scoreRing { max-width: min(260px, 65vw); height: auto; }
    .daily-msg {
      font-family: var(--script);
      font-size: clamp(1.4rem, 3.5vw, 2rem);
      color: var(--green); line-height: 1.4;
      transform: rotate(-1deg); text-align: center;
    }
    .daily-msg strong {
      font-family: var(--display); font-size: 1.3em; color: var(--black);
    }
    .statement-mini {
      background: var(--white);
      border: var(--line) solid var(--black);
      padding: var(--pad);
      text-align: center;
      position: relative; transform: rotate(-0.8deg);
    }
    .statement-mini::before {
      content: ''; position: absolute;
      top: 6px; left: 6px; right: -6px; bottom: -6px;
      background: var(--black); z-index: -1;
      transform: rotate(0.6deg);
    }
    .statement-mini-quote {
      font-family: var(--display);
      font-size: clamp(1.6rem, 5vw, 3.5rem);
      line-height: 1.1; color: var(--green);
      text-transform: uppercase; letter-spacing: 0.03em;
    }
    .statement-mini-attr {
      margin-top: 12px;
      font-family: var(--script); font-size: 1rem;
    }

    /* ========== SLIDE 3 — 关键指标 ========== */
    #slide-3 {
      justify-content: center;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--gap);
      flex: 1; align-content: center;
    }
    .kpi-card {
      background: var(--white);
      border: var(--line) solid var(--black);
      padding: var(--pad);
      position: relative;
      transform: rotate(var(--rotate));
      transition: transform 0.3s ease;
    }
    .kpi-card:nth-child(even) { transform: rotate(var(--rotate2)); }
    .kpi-card:hover { transform: rotate(0deg); }
    .kpi-header {
      display: flex; justify-content: space-between; align-items: baseline;
      margin-bottom: 6px;
    }
    .kpi-label {
      font-family: var(--display);
      font-size: clamp(1rem, 2.8vw, 1.4rem);
      letter-spacing: 0.12em;
      color: var(--green); text-transform: uppercase;
    }
    .kpi-score-tag {
      font-family: var(--display);
      font-size: clamp(0.7rem, 2vw, 0.9rem);
      letter-spacing: 0.1em;
      padding: 3px 10px;
      border: 2px solid var(--black);
      background: var(--bg);
    }
    .kpi-score-tag.good { background: var(--green); color: var(--white); }
    .kpi-score-tag.warn { background: #f59e0b; }
    .kpi-value {
      font-family: var(--display);
      font-size: clamp(2rem, 6vw, 3.5rem);
      line-height: 1; margin-bottom: 2px;
    }
    .kpi-unit {
      font-family: var(--script); font-size: 0.95rem;
    }
    .kpi-delta {
      margin-top: 4px;
      font-family: var(--mono); font-size: 0.8rem;
      color: var(--green);
    }
    .kpi-delta.negative { color: #b91c1c; }
    .kpi-formula {
      margin-top: 8px;
      font-family: var(--serif); font-size: 0.8rem;
      color: #555; line-height: 1.5;
      padding: 8px; background: var(--bg);
      border: 2px solid var(--black);
    }
    .kpi-detail {
      margin-top: 8px;
      font-size: 0.85rem; color: #444; line-height: 1.6;
    }
    .kpi-detail strong { color: var(--black); }

    /* sleep mini bar */
    .sleep-mini-bar {
      display: flex; height: 22px;
      border: 2px solid var(--black);
      margin: 8px 0; overflow: hidden;
    }
    .sleep-mini-seg {
      height: 100%; display: flex; align-items: center; justify-content: center;
      font-family: var(--display);
      font-size: clamp(0.55rem, 1.5vw, 0.7rem);
      color: var(--white); letter-spacing: 0.08em;
    }
    .sleep-mini-deep  { background: var(--green); flex: 1; }
    .sleep-mini-rem   { background: var(--green_light); flex: 1; }
    .sleep-mini-awake { background: var(--black); flex: 0.3; }

    /* ========== SLIDE 4 — 趋势总览 ========== */
    #slide-4 {
      justify-content: center;
    }
    .charts-stack {
      display: flex; flex-direction: column;
      gap: var(--gap);
      flex: 1; align-content: center;
    }
    .chart-box {
      background: var(--white);
      border: var(--line) solid var(--black);
      padding: var(--pad);
      position: relative;
      transform: rotate(-0.4deg);
    }
    .chart-box canvas {
      width: 100%; height: clamp(100px, 16vh, 180px);
      display: block;
      border-top: 2px solid var(--black);
      margin-top: 6px;
    }
    .chart-box-title {
      font-family: var(--display);
      font-size: clamp(1rem, 3vw, 1.6rem);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .chart-box-sub {
      font-family: var(--script);
      font-size: clamp(0.75rem, 1.8vw, 0.95rem);
      color: var(--green); margin-top: 2px;
    }

    /* ========== SLIDE 5 — 深度分析 ========== */
    #slide-5 {
      justify-content: center;
    }
    .analysis-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--gap);
      flex: 1; align-content: center;
    }
    .analysis-card {
      background: var(--white);
      border: var(--line) solid var(--black);
      padding: var(--pad);
      position: relative;
    }
    .analysis-card h3 {
      font-family: var(--display);
      font-size: clamp(1.3rem, 4vw, 2.2rem);
      letter-spacing: 0.08em;
      color: var(--green); text-transform: uppercase;
      margin-bottom: 10px;
    }
    .formula-box {
      font-family: var(--serif); font-size: 0.82rem;
      color: #444; line-height: 1.6;
      padding: 10px; background: var(--bg);
      border: 2px solid var(--black);
      margin: 8px 0;
    }
    .analysis-text {
      font-size: 0.88rem; color: var(--black); line-height: 1.7;
    }
    .analysis-text .inline-highlight { font-size: 0.85em; }
    .analysis-score {
      margin-top: 10px;
      display: flex; gap: 12px; flex-wrap: wrap;
    }
    .score-chip {
      font-family: var(--display);
      font-size: 0.8rem; letter-spacing: 0.08em;
      padding: 4px 12px;
      border: 2px solid var(--black);
      background: var(--bg);
    }
    .score-chip.good { background: var(--green); color: var(--white); }

    /* ========== SLIDE 6 — 睡眠与洞察 ========== */
    #slide-6 {
      justify-content: center;
    }
    .insight-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--gap);
      flex: 1; align-content: center;
    }
    .insight-card {
      background: var(--white);
      border: var(--line) solid var(--black);
      padding: var(--pad);
      position: relative;
    }
    .insight-card h3 {
      font-family: var(--display);
      font-size: clamp(1.2rem, 3.5vw, 1.8rem);
      letter-spacing: 0.08em;
      color: var(--green); text-transform: uppercase;
      margin-bottom: 10px;
    }
    .insight-item {
      display: flex; gap: 12px; align-items: flex-start;
      padding: 10px 0;
      border-bottom: 2px solid var(--black);
    }
    .insight-item:last-child { border-bottom: none; }
    .insight-tag {
      font-family: var(--display);
      font-size: 0.75rem; letter-spacing: 0.1em;
      padding: 3px 10px;
      border: 2px solid var(--black);
      background: var(--bg);
      text-transform: uppercase;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .insight-tag.good { background: var(--green); color: var(--white); }
    .insight-tag.warn { background: #f59e0b; }
    .insight-text {
      font-size: 0.88rem; color: #333; line-height: 1.5;
    }
    .advice-list {
      list-style: none;
    }
    .advice-list li {
      font-size: clamp(0.82rem, 2.2vw, 0.95rem);
      padding: 10px 0;
      border-bottom: 2px solid var(--black);
      display: flex; align-items: flex-start; gap: 10px;
    }
    .advice-list li::before {
      content: '>';
      font-family: var(--display);
      font-size: 1.1rem; color: var(--green);
      flex-shrink: 0;
    }
    .advice-list li:last-child { border-bottom: none; }

    /* ========== SLIDE 7 — 收尾 ========== */
    #slide-7 {
      justify-content: center; align-items: center; text-align: center;
    }
    .closing-block {
      max-width: min(650px, 88vw);
      padding: var(--pad);
      background: var(--white);
      border: var(--line) solid var(--black);
      position: relative;
    }
    .closing-quote {
      font-family: var(--display);
      font-size: clamp(1.6rem, 6vw, 3.5rem);
      line-height: 1.1; color: var(--green);
      text-transform: uppercase; letter-spacing: 0.03em;
    }
    .closing-text {
      margin-top: 14px;
      font-family: var(--script);
      font-size: clamp(0.95rem, 2.5vw, 1.3rem);
    }
    .closing-sig {
      margin-top: 20px;
      font-family: var(--display);
      font-size: 0.85rem; letter-spacing: 0.25em;
      text-transform: uppercase;
    }
    .closing-stamp { margin-top: 16px; }

    /* scroll hint */
    .scroll-hint {
      position: fixed;
      bottom: max(10px, env(safe-area-inset-bottom));
      left: 50%; transform: translateX(-50%);
      font-family: var(--script); font-size: 0.8rem;
      color: var(--black); opacity: 0.5;
      z-index: 1000; pointer-events: none;
      transition: opacity 0.6s ease; text-align: center;
    }
    .scroll-hint.hidden { opacity: 0; }
    .scroll-hint::after {
      content: ''; display: block;
      margin: 3px auto 0;
      width: 18px; height: 18px;
      border-right: 2px solid var(--black);
      border-bottom: 2px solid var(--black);
      transform: rotate(45deg);
      animation: scrollBounce 2s ease-in-out infinite;
    }
    @keyframes scrollBounce {
      0%, 100% { transform: rotate(45deg) translateY(0); }
      50%      { transform: rotate(45deg) translateY(5px); }
    }

    /* responsive */
    @media (min-width: 769px) {
      .overview-grid { grid-template-columns: 280px 1fr; }
      .kpi-grid { grid-template-columns: repeat(2, 1fr); }
      .analysis-grid { grid-template-columns: 1fr 1fr; }
      .insight-grid { grid-template-columns: 1fr 1fr; }
      .insight-item { padding: 8px 0; }
    }
    @media (min-width: 1024px) {
      :root { --pad: 48px; --gap: 28px; }
      .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>

  <div class="grain-overlay" aria-hidden="true">
    <svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
      <filter id="noise">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="4" stitchTiles="stitch"/>
        <feColorMatrix type="saturate" values="0"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#noise)" opacity="0.5"/>
    </svg>
  </div>

  <!-- ===== 01 首页 ===== -->
  <section class="slide" id="slide-1">
    <div class="hero-edition">健康版</div>
    <div><span class="stamp-mark green" id="heroGrade">{{GRADE}}</span></div>
    <h1 class="hero-title">每日<br>健康<br>手账</h1>
    <div class="hero-subtitle">每日健康报告</div>
    <div class="hero-grade" id="heroScore">{{SCORE}}</div>
    <div class="hero-date" id="heroDate">{{DATE_ZH}}</div>
    <div id="dataSourceBadge" style="margin-top:10px; display:none;">
      <span class="stamp-mark" style="font-size:0.65rem;">演示数据</span>
    </div>
  </section>

  <!-- ===== 02 今日概览 ===== -->
  <section class="slide" id="slide-2">
    <div class="slide-chrome">
      <span class="section-number">02</span>
      <span class="section-label">今日概览</span>
    </div>
    <div class="ribbon-bar">每日健康分数</div>
    <div class="overview-grid">
      <div class="score-ring-wrap">
        <canvas id="scoreRing" width="300" height="300"></canvas>
      </div>
      <div style="display:flex; flex-direction:column; gap:var(--gap); justify-content:center;">
        <p class="daily-msg drop-cap" id="dailyMessage">{{DAILY_MSG}}</p>
        <div style="text-align:center;"><span class="stamp-mark" id="scoreStamp">{{SCORE_STAMP}}</span></div>
        <div class="statement-mini">
          <div class="statement-mini-quote" id="statementQuote">{{STATEMENT_QUOTE}}</div>
          <div class="statement-mini-attr" id="statementAttr">{{STATEMENT_ATTR}}</div>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== 03 关键指标 ===== -->
  <section class="slide" id="slide-3">
    <div class="slide-chrome">
      <span class="section-number">03</span>
      <span class="section-label">关键指标</span>
    </div>
    <div class="ribbon-bar">五大核心指标</div>
    <div class="kpi-grid">
      <!-- HRV -->
      <div class="kpi-card">
        <div class="kpi-header">
          <div class="kpi-label">HRV</div>
          <span class="kpi-score-tag" id="hrvTag">{{HRV_TAG}}</span>
        </div>
        <div class="kpi-value" id="hrvValue">{{HRV_VALUE}}</div>
        <div class="kpi-unit">毫秒</div>
        <div class="kpi-delta" id="hrvDelta">{{HRV_DELTA}}</div>
        <div class="kpi-formula" id="hrvFormula">{{HRV_FORMULA}}</div>
        <div class="kpi-detail" id="hrvDetail">{{HRV_DETAIL}}</div>
      </div>
      <!-- RHR -->
      <div class="kpi-card">
        <div class="kpi-header">
          <div class="kpi-label">RHR</div>
          <span class="kpi-score-tag" id="rhrTag">{{RHR_TAG}}</span>
        </div>
        <div class="kpi-value" id="rhrValue">{{RHR_VALUE}}</div>
        <div class="kpi-unit">次/分</div>
        <div class="kpi-delta" id="rhrDelta">{{RHR_DELTA}}</div>
        <div class="kpi-formula" id="rhrFormula">{{RHR_FORMULA}}</div>
        <div class="kpi-detail" id="rhrDetail">{{RHR_DETAIL}}</div>
      </div>
      <!-- SLEEP -->
      <div class="kpi-card">
        <div class="kpi-header">
          <div class="kpi-label">SLEEP</div>
          <span class="kpi-score-tag" id="sleepTag">{{SLEEP_TAG}}</span>
        </div>
        <div class="kpi-value" id="sleepValue">{{SLEEP_VALUE}}</div>
        <div class="kpi-unit">小时</div>
        <div class="kpi-delta" id="sleepDelta">{{SLEEP_DELTA}}</div>
        <div class="kpi-formula" id="sleepFormula">{{SLEEP_FORMULA}}</div>
        <div class="sleep-mini-bar">
          <div class="sleep-mini-seg sleep-mini-deep" id="sleepDeepPct">{{SLEEP_DEEP_PCT}}</div>
          <div class="sleep-mini-seg sleep-mini-rem" id="sleepRemPct">{{SLEEP_REM_PCT}}</div>
          <div class="sleep-mini-seg sleep-mini-awake" id="sleepAwake">{{SLEEP_AWAKE}}</div>
        </div>
        <div class="kpi-detail">
          深睡 <strong id="sleepDeepTime">{{SLEEP_DEEP_TIME}}</strong> 小时 | REM <strong id="sleepRemTime">{{SLEEP_REM_TIME}}</strong> 小时 | 清醒 <strong id="sleepAwakeCount">{{SLEEP_AWAKE_COUNT}}</strong> 次
        </div>
      </div>
      <!-- READINESS -->
      <div class="kpi-card">
        <div class="kpi-header">
          <div class="kpi-label">READINESS</div>
          <span class="kpi-score-tag" id="readyTag">{{READY_TAG}}</span>
        </div>
        <div class="kpi-value" id="readyValue">{{READY_VALUE}}</div>
        <div class="kpi-unit">/ 100</div>
        <div class="kpi-delta" id="readyDelta">{{READY_DELTA}}</div>
        <div class="kpi-formula" id="readyFormula">{{READY_FORMULA}}</div>
        <div class="kpi-detail" id="readyDetail">{{READY_DETAIL}}</div>
      </div>
      <!-- STRESS -->
      <div class="kpi-card">
        <div class="kpi-header">
          <div class="kpi-label">STRESS</div>
          <span class="kpi-score-tag" id="stressTag">{{STRESS_TAG}}</span>
        </div>
        <div class="kpi-value" id="stressValue">{{STRESS_VALUE}}</div>
        <div class="kpi-unit">压力水平</div>
        <div class="kpi-delta" id="stressDelta">{{STRESS_DELTA}}</div>
        <div class="kpi-formula" id="stressFormula">{{STRESS_FORMULA}}</div>
        <div class="kpi-detail" id="stressDetail">{{STRESS_DETAIL}}</div>
      </div>
    </div>
  </section>

  <!-- ===== 04 趋势总览 ===== -->
  <section class="slide" id="slide-4">
    <div class="slide-chrome">
      <span class="section-number">04</span>
      <span class="section-label">趋势总览</span>
    </div>
    <div class="ribbon-bar">7日数据趋势</div>
    <div class="charts-stack">
      <div class="chart-box">
        <div class="chart-box-title">恢复趋势</div>
        <div class="chart-box-sub" id="trendSub">{{TREND_SUB}}</div>
        <canvas id="trendChart" width="800" height="180"></canvas>
      </div>
      <div class="chart-box">
        <div class="chart-box-title">心率变异性 / 静息心率</div>
        <div class="chart-box-sub">双轴对比</div>
        <canvas id="dualChart" width="800" height="160"></canvas>
      </div>
      <div class="chart-box">
        <div class="chart-box-title">睡眠趋势</div>
        <div class="chart-box-sub">深睡 / REM / 清醒</div>
        <canvas id="sleepChart" width="800" height="160"></canvas>
      </div>
      <div class="chart-box">
        <div class="chart-box-title">准备度趋势</div>
        <div class="chart-box-sub" id="readySub">{{READY_SUB}}</div>
        <canvas id="readyChart" width="800" height="150"></canvas>
      </div>
    </div>
  </section>

  <!-- ===== 05 深度分析 ===== -->
  <section class="slide" id="slide-5">
    <div class="slide-chrome">
      <span class="section-number">05</span>
      <span class="section-label">深度分析</span>
    </div>
    <div class="ribbon-bar">心率指标深度解读</div>
    <div class="analysis-grid">
      <div class="analysis-card">
        <h3>心率变异性</h3>
        <div class="formula-box" id="hrvFormulaBox">{{HRV_FORMULA_BOX}}</div>
        <p class="analysis-text" id="hrvAnalysisText">{{HRV_ANALYSIS_TEXT}}</p>
        <div class="analysis-score">
          <span class="score-chip" id="hrvScoreChip">{{HRV_SCORE_CHIP}}</span>
          <span class="score-chip" id="hrvBaseChip">{{HRV_BASE_CHIP}}</span>
          <span class="score-chip" id="hrvDevChip">{{HRV_DEV_CHIP}}</span>
        </div>
      </div>
      <div class="analysis-card">
        <h3>静息心率</h3>
        <div class="formula-box" id="rhrFormulaBox">{{RHR_FORMULA_BOX}}</div>
        <p class="analysis-text" id="rhrAnalysisText">{{RHR_ANALYSIS_TEXT}}</p>
        <div class="analysis-score">
          <span class="score-chip" id="rhrScoreChip">{{RHR_SCORE_CHIP}}</span>
          <span class="score-chip" id="rhrBaseChip">{{RHR_BASE_CHIP}}</span>
          <span class="score-chip" id="rhrDevChip">{{RHR_DEV_CHIP}}</span>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== 06 睡眠与洞察 ===== -->
  <section class="slide" id="slide-6">
    <div class="slide-chrome">
      <span class="section-number">06</span>
      <span class="section-label">睡眠与洞察</span>
    </div>
    <div class="ribbon-bar">睡眠质量与模式匹配</div>
    <div class="insight-grid">
      <div class="insight-card">
        <h3>睡眠构成</h3>
        <div class="sleep-mini-bar">
          <div class="sleep-mini-seg sleep-mini-deep" id="detailDeepPct">{{DETAIL_DEEP_PCT}}</div>
          <div class="sleep-mini-seg sleep-mini-rem" id="detailRemPct">{{DETAIL_REM_PCT}}</div>
          <div class="sleep-mini-seg sleep-mini-awake" id="detailAwake">{{DETAIL_AWAKE}}</div>
        </div>
        <div class="kpi-detail" style="margin-top:10px;">
          总睡眠 <strong id="detailTotal">{{DETAIL_TOTAL}}</strong> 小时 |
          深睡 <strong id="detailDeepTime">{{DETAIL_DEEP_TIME}}</strong> 小时 |
          REM <strong id="detailRemTime">{{DETAIL_REM_TIME}}</strong> 小时 |
          清醒 <strong id="detailAwakeCount">{{DETAIL_AWAKE_COUNT}}</strong> 次
        </div>
        <div style="margin-top:10px;">
          <span class="stamp-mark green" id="detailSleepTag">{{DETAIL_SLEEP_TAG}}</span>
        </div>
      </div>
      <div class="insight-card">
        <h3>模式匹配</h3>
        <div id="patternList">
          {{PATTERN_LIST}}
        </div>
      </div>
      <div class="insight-card" style="grid-column: 1 / -1;">
        <h3>今日建议</h3>
        <ul class="advice-list" id="adviceList">
          {{ADVICE_LIST}}
        </ul>
      </div>
    </div>
  </section>

  <!-- ===== 07 收尾 ===== -->
  <section class="slide" id="slide-7">
    <div class="closing-block">
      <div class="closing-quote">保持<br>好奇，<br>保持<br>坚韧</div>
      <div class="closing-text">每日健康伴侣，为明天做好准备。</div>
      <div class="closing-sig">每日健康手账</div>
      <div class="closing-stamp">
        <span class="stamp-mark green">Retro Zine v1.0</span>
      </div>
    </div>
  </section>

  <div class="scroll-hint" id="scrollHint">向下滚动浏览</div>

  <script>
    /* ============================================
       STATIC_DATA — 由 build_zine.py 注入完整 kpi_today.json
       · file://（离线 / Hermes）：直接作为本源渲染，不做 fetch。
       · http(s)://（实时）：fetch 实时数据，失败一律走 showFailure，绝不回退内嵌旧数据。
       ============================================ */
    const STATIC_DATA = {{STATIC_DATA_JS}};

    /* ============================================
       DATA LOADING — 双模式（对齐标准版 deep_diagnosis_latest）
       ============================================ */
    function getDataUrl() {
      return '../kpi_today.json';
    }

    function showFailure(reason, hint) {
      document.body.innerHTML =
        '<div style="max-width:680px;margin:12vh auto;padding:32px 28px;'
        + 'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'
        + 'background:#fff;border:1px solid #e3d9c6;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.08);">'
        + '<div style="width:46px;height:46px;border-radius:50%;background:#b3402e;color:#fff;'
        + 'display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;margin-bottom:18px;">!</div>'
        + '<h1 style="margin:0 0 12px;font-size:22px;color:#1c1a17;">数据加载失败</h1>'
        + '<p style="margin:0 0 8px;color:#4a443c;line-height:1.6;">本页面需要有效的诊断数据才能展示，当前未加载到任何数据。</p>'
        + (hint ? '<p style="margin:0 0 8px;color:#4a443c;line-height:1.6;">' + hint + '</p>' : '')
        + '<p style="margin:14px 0 0;color:#8a7f6e;font-size:13px;">失败原因：<span>' + (reason || '未知错误') + '</span></p>'
        + '</div>';
    }

    async function loadData() {
      const fileProto = window.location.protocol === 'file:';
      if (fileProto) {
        try {
          const data = STATIC_DATA;
          if (!data || typeof data !== 'object') throw new Error('内嵌静态数据缺失');
          if (!data.history) throw new Error('内嵌静态数据缺少 history 字段');
          return normalizeData(data);
        } catch (err) {
          console.error('[zine] static load failed:', err);
          showFailure(err.message, '内嵌静态快照异常：请重新运行数据生成与本构建步骤后重试。');
          return null;
        }
      }
      try {
        const resp = await fetch(getDataUrl(), { cache: 'no-store' });
        if (!resp.ok) throw new Error('HTTP ' + resp.status + ' ' + (resp.statusText || ''));
        const json = await resp.json();
        if (!json || typeof json !== 'object') throw new Error('返回数据为空或非对象');
        if (!json.history) throw new Error('数据缺少 history 字段（不是标准 kpi_today.json）');
        return normalizeData(json);
      } catch (err) {
        console.error('[zine] loadData failed:', err);
        showFailure(err.message, '实时数据获取失败。请确认：① rebuild_kpi_today.py 已生成 kpi_today.json；② 通过本地 HTTP 服务访问本页。');
        return null;
      }
    }

    function normalizeData(raw) {
      const ri = raw.raw_inputs || {};
      const hist = raw.history || {};
      const bs = raw.baselines || {};
      const ds = raw.dimension_scores || {};
      const comp = raw.composite || {};
      const dms = raw.derived_metrics_summary || {};

      // --- HRV ---
      const hrvRaw = ri.hrv || {};
      const hrvDs = ds.hrv || {};
      const hrvBase = bs.hrv_baseline_7d || hrvRaw.weekly_avg || 0;
      const hrvLast = hrvRaw.last_night || hrvDs.last_night_ms || 0;
      const hrvPct = hrvDs.pct_change_pct != null ? hrvDs.pct_change_pct : 0;
      const hrvScore = hrvDs.score > 0 ? hrvDs.score :
        (hrvPct >= 5 ? 85 : hrvPct >= 0 ? 75 : hrvPct >= -5 ? 60 : 40);
      const hrvFormula = (bs.formulas && bs.formulas.hrv_baseline) ||
        'HRV = 过去7晚心率变异性的滚动平均值 (RMSSD)';
      const hrvAnalysis = `心率变异性 ${hrvLast}ms，基准 ${hrvBase}ms。变化 ${hrvPct >= 0 ? '+' : ''}${hrvPct.toFixed(2)}%。` +
        (hrvPct > 0 ? '副交感神经张力良好，恢复能力提升。' : hrvPct >= -5 ? '恢复能力稳定。' : '注意恢复，避免过度训练。');

      // --- RHR ---
      const rhrRaw = ri.rhr || {};
      const rhrDs = ds.rhr || {};
      const rhrBase = rhrDs.baseline_bpm || bs.rhr_baseline_28d || 0;
      const rhrCurrent = rhrRaw.current_bpm || rhrDs.current_bpm || 0;
      const rhrDev = rhrDs.deviation != null ? rhrDs.deviation :
        (rhrCurrent - rhrBase);
      const rhrScore = rhrDs.score != null ? rhrDs.score :
        (rhrDev <= -3 ? 95 : rhrDev <= 0 ? 85 : rhrDev <= 3 ? 75 : 60);
      const rhrFormula = (bs.formulas && bs.formulas.rhr_baseline) ||
        'RHR = 28日滚动静息心率基准。Bosquet 2003 [R12]';
      const rhrAnalysis = `静息心率 ${rhrCurrent} 次/分，基准 ${rhrBase} 次/分（偏差 ${rhrDev >= 0 ? '+' : ''}${rhrDev} 次/分）。` +
        (rhrDev < 0 ? '心血管效率优秀，恢复状态佳。' : '恢复状态良好。');

      // --- SLEEP ---
      const sleepRaw = ri.sleep || {};
      const sleepDs = ds.sleep || {};
      const sleepTotalSec = sleepRaw.total_seconds || 0;
      const sleepTotalH = sleepTotalSec / 3600;
      const deepSec = sleepRaw.deep_seconds || 0;
      const remSec = sleepRaw.rem_seconds || 0;
      const deepPct = sleepTotalSec > 0 ? (deepSec / sleepTotalSec * 100) : 0;
      const remPct = sleepTotalSec > 0 ? (remSec / sleepTotalSec * 100) : 0;
      const awakeCount = sleepRaw.awake_count || 0;
      const sleepScore = sleepRaw.garmin_sleep_score || sleepDs.score || 0;
      const sleepDeepH = deepSec / 3600;
      const sleepRemH = remSec / 3600;
      const sleepFormula = (bs.formulas && bs.formulas.sleep_baseline) ||
        '睡眠分数 = Garmin 综合评分。理想：7-9小时，深睡15-20%，REM 20-25%。';

      // --- READINESS ---
      const readyScore = ds.readiness ? ds.readiness.score :
        (ri.readiness ? ri.readiness.score : 0);
      const readyLevel = ds.readiness ? ds.readiness.zone :
        (ri.readiness ? ri.readiness.level : '--');
      const readyFormula = comp.formula ||
        '准备度综合 HRV、睡眠、RHR 和训练负荷加权计算';
      const readyDetail = comp.calculation_steps ?
        comp.calculation_steps.join('；') + '。总分：' + (comp.recovery_score || 0) :
        '准备度分数 ' + readyScore;

      // --- STRESS ---
      const stressDs = ds.stress || {};
      const stressRaw = ri.stress_raw || {};
      const stressLevel = stressDs.stress_level != null ? stressDs.stress_level :
        (stressRaw.avg_stress_level != null ? stressRaw.avg_stress_level : 0);
      const stressScore = stressDs.score != null ? stressDs.score :
        (stressLevel <= 25 ? 85 : stressLevel <= 50 ? 60 : stressLevel <= 75 ? 35 : 15);
      const stressZone = stressDs.zone || '--';
      const stressAnalysis = `平均压力水平 ${stressLevel}，处于${stressZone}区间。` +
        (stressLevel <= 25 ? '压力管理良好，恢复状态佳。' :
         stressLevel <= 50 ? '压力可控，注意保持作息规律。' :
         '压力偏高，建议优先保证睡眠和放松活动。');

      // --- COMPOSITE ---
      const score = comp.recovery_score || readyScore || 0;
      const grade = comp.grade || '--';

      // --- STATEMENT ---
      const gradeMap = { 'A': '优秀', 'B': '良好', 'C': '需要注意', 'D': '需要关注', 'F': '需要休息' };
      const gradeText = gradeMap[grade] || '评估中';
      const statement = `恢复分数 ${score}（${gradeText}）。` +
        (score >= 80 ? '身体状态优秀，继续保持良好习惯。' :
         score >= 60 ? '恢复状态尚可，注意保持睡眠和休息。' :
         '恢复状态需要关注，建议优先保证睡眠。');
      const statement_attr = raw.date ? `每日健康报告，${raw.date}` : '每日健康报告';

      // --- TREND DATA (最近 7 天；history 数组为降序「最新在前」，故按日期升序排序后取末尾 7 条) ---
      const recentN = (arr, n = 7) => {
        if (!Array.isArray(arr)) return [];
        return [...arr].sort((a, b) => new Date(a.date) - new Date(b.date)).slice(-n);
      };
      const recent7 = (arr, pick) => recentN(arr).map(pick);
      const recentDates = (arr) => recentN(arr).map(e => e.date || '');
      const fmtDate = (d) => {
        if (!d) return '';
        const dt = new Date(d);
        const m = dt.getMonth() + 1, day = dt.getDate();
        return m + '/' + day;
      };
      const trend = recent7(hist.hrv_14d, e => e.value != null ? e.value : 0);
      const rhrTrend = recent7(hist.rhr_28d, e => e.value != null ? e.value : 0);
      const sleepCal = (hist.sleep_cal_28d || []).filter(e => e.value && e.value.garmin_score != null);
      const sleepHist = recentN(sleepCal);
      const sleepScoreTrend = sleepHist.map(e => e.value.garmin_score);
      const sleepDeepTrend = sleepHist.map(e => {
        const v = e.value;
        return (v.deep_sec && v.total_sec) ? +(v.deep_sec / v.total_sec * 100).toFixed(1) : 0;
      });
      const readyTrend = recent7(hist.readiness_28d, e => e.score != null ? e.score : 0);
      const trendLabels = recentDates(hist.hrv_14d).map(fmtDate);

      // --- PATTERNS ---
      const patterns = [];
      if (hrvPct > 0) patterns.push({ tag: '良好', text: '心率变异性呈上升趋势，恢复状态良好' });
      else if (hrvPct >= -5) patterns.push({ tag: '稳定', text: '心率变异性稳定，恢复能力维持' });
      else patterns.push({ tag: '注意', text: '心率变异性下降，建议关注恢复' });

      if (rhrDev < 0) patterns.push({ tag: '良好', text: `静息心率低于基准 ${Math.abs(rhrDev)} 次/分，心肺功能改善` });
      else if (rhrDev === 0) patterns.push({ tag: '稳定', text: '静息心率与基准持平' });

      if (sleepScore >= 80) patterns.push({ tag: '良好', text: `睡眠分数 ${sleepScore}，睡眠质量优秀` });
      else if (sleepScore >= 60) patterns.push({ tag: '注意', text: `睡眠分数 ${sleepScore}，睡眠质量尚可但可改善` });
      else patterns.push({ tag: '注意', text: `睡眠分数 ${sleepScore}，建议优先改善睡眠` });

      if (readyScore >= 80) patterns.push({ tag: '良好', text: '准备度分数高，可承受训练压力' });

      // --- ADVICE ---
      const advice = [];
      if (sleepTotalH < 7.5) advice.push('睡眠时长不足，建议今晚提前入睡，目标7-9小时');
      else advice.push('睡眠时长达标，继续保持规律作息');
      if (hrvPct < 0) advice.push('心率变异性偏低，建议进行轻量恢复活动');
      if (rhrDev < -2) advice.push('静息心率表现优秀，可安排中高强度训练');
      else if (rhrDev > 2) advice.push('静息心率偏高，注意休息和恢复');
      if (awakeCount > 2) advice.push('夜间清醒次数较多，睡前减少屏幕时间');
      if (advice.length < 3) advice.push('保持规律作息，适度运动，持续关注健康数据');

      return {
        date: raw.date || '--',
        grade, score,
        hrv: hrvLast, hrv_base: hrvBase, hrv_dev_pct: hrvPct, hrv_score: hrvScore,
        hrv_weekly: hrvRaw.weekly_avg || 0, hrv_status: hrvRaw.status || '--',
        hrv_formula: hrvFormula, hrv_analysis: hrvAnalysis,
        rhr: rhrCurrent, rhr_base: rhrBase, rhr_dev: rhrDev, rhr_score: rhrScore,
        rhr_formula: rhrFormula, rhr_analysis: rhrAnalysis,
        sleep_total: sleepTotalH, deep_pct: deepPct, rem_pct: remPct,
        deep_time: sleepDeepH, rem_time: sleepRemH, awake_count: awakeCount,
        sleep_score: sleepScore, sleep_formula: sleepFormula,
        ready_score: readyScore, ready_level: readyLevel,
        ready_formula: readyFormula, ready_detail: readyDetail,
        stress_score: stressScore, stress_level: stressLevel,
        stress_zone: stressZone, stress_analysis: stressAnalysis,
        statement, statement_attr,
        _data_source: raw._data_source || (raw === STATIC_DATA ? 'static' : 'kpi_today.json'),
        trend, trend_labels: trendLabels,
        rhr_trend: rhrTrend,
        sleep_trend: sleepScoreTrend,
        sleep_deep_trend: sleepDeepTrend,
        ready_trend: readyTrend,
        patterns: patterns.slice(0, 4),
        advice: advice.slice(0, 3)
      };
    }

    /* ============================================
       RENDER
       ============================================ */
    function renderAll(d) {
      renderSlide1(d);
      renderSlide2(d);
      renderSlide3(d);
      renderSlide4(d);
      renderSlide5(d);
      drawAllCharts(d);
      renderSlide6(d);
    }

    function renderSlide1(d) {
      document.getElementById('heroGrade').textContent = d.grade;
      document.getElementById('heroScore').textContent = d.score;
      const dt = new Date(d.date);
      document.getElementById('heroDate').textContent =
        dt.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
      const badge = document.getElementById('dataSourceBadge');
      if (badge) {
        if (d._data_source === 'demo') {
          badge.style.display = 'block';
        } else {
          badge.style.display = 'none';
        }
      }
    }

    function renderSlide2(d) {
      document.getElementById('dailyMessage').innerHTML =
        `今日健康分数为 <strong>${d.score}</strong>。您的身体正在良好恢复。保持节奏。`;
      const stamp = document.getElementById('scoreStamp');
      stamp.classList.remove('green');
      if (d.score >= 80)      { stamp.textContent = '状态良好'; stamp.classList.add('green'); }
      else if (d.score >= 60) { stamp.textContent = '注意'; }
      else                    { stamp.textContent = '需要休息'; }

      document.getElementById('statementQuote').textContent = d.statement;
      document.getElementById('statementAttr').textContent = d.statement_attr;
    }

    function renderSlide3(d) {
      // HRV
      setKpi('hrv', d.hrv, d.hrv_dev_pct, d.hrv_score,
        d.hrv_formula, d.hrv_analysis, d.hrv_base, d.hrv_dev_pct, true);
      // RHR
      setKpi('rhr', d.rhr, d.hrv_dev, d.rhr_score,
        d.rhr_formula, d.rhr_analysis, d.rhr_base, d.rhr_dev, false);
      // SLEEP
      document.getElementById('sleepValue').textContent = d.sleep_total.toFixed(2);
      document.getElementById('sleepTag').textContent = '睡眠分数：' + d.sleep_score;
      const sTag = document.getElementById('sleepTag');
      d.sleep_score >= 80 ? sTag.classList.add('good') : d.sleep_score >= 60 ? sTag.classList.add('warn') : 0;
      document.getElementById('sleepDeepPct').textContent = Math.round(d.deep_pct) + '%';
      document.getElementById('sleepRemPct').textContent = Math.round(d.rem_pct) + '%';
      document.getElementById('sleepAwake').textContent = d.awake_count + '次';
      document.getElementById('sleepDeepTime').textContent = d.deep_time.toFixed(2);
      document.getElementById('sleepRemTime').textContent = d.rem_time.toFixed(2);
      document.getElementById('sleepAwakeCount').textContent = d.awake_count;
      document.getElementById('sleepDelta').textContent = '分数：' + d.sleep_score + '/100';
      const sf = document.getElementById('sleepFormula');
      if (sf) sf.textContent = d.sleep_formula.substring(0, 100) + '...';
      // READINESS
      document.getElementById('readyValue').textContent = d.ready_score;
      document.getElementById('readyTag').textContent = '准备度：' + d.ready_score;
      const rTag = document.getElementById('readyTag');
      d.ready_score >= 80 ? rTag.classList.add('good') : d.ready_score >= 60 ? rTag.classList.add('warn') : 0;
      document.getElementById('readyDelta').textContent =
        d.ready_score >= 80 ? '准备度高' : d.ready_score >= 60 ? '准备度中等' : '准备度低';
      const rf = document.getElementById('readyFormula');
      if (rf) rf.textContent = d.ready_formula.substring(0, 100) + '...';
      const rd = document.getElementById('readyDetail');
      if (rd) rd.textContent = d.ready_detail;
      // STRESS
      document.getElementById('stressValue').textContent = d.stress_level;
      document.getElementById('stressTag').textContent = '分数：' + d.stress_score;
      const stTag = document.getElementById('stressTag');
      d.stress_score >= 80 ? stTag.classList.add('good') : d.stress_score >= 60 ? stTag.classList.add('warn') : 0;
      document.getElementById('stressDelta').textContent =
        d.stress_score >= 80 ? '压力低' : d.stress_score >= 60 ? '压力中等' : '压力高';
      const sfm = document.getElementById('stressFormula');
      if (sfm) sfm.textContent = 'Stress = Garmin 全天平均压力指数 (0-100)。0-25 为低压力，25-50 为中等，>50 为高压力。';
      const sdt = document.getElementById('stressDetail');
      if (sdt) sdt.textContent = d.stress_analysis;
    }

    function renderSlide4(d) {
      document.getElementById('trendSub').textContent = '7日恢复趋势 — ' + (d.date || '');
    }

    function setKpi(id, val, dev, score, formula, analysis, base, deviation, isPct) {
      document.getElementById(id + 'Value').textContent = val;
      const tag = document.getElementById(id + 'Tag');
      if (score != null && tag) {
        tag.textContent = '分数：' + score;
        score >= 80 ? tag.classList.add('good') : score >= 60 ? tag.classList.add('warn') : 0;
      }
      const delta = document.getElementById(id + 'Delta');
      if (dev != null && delta) {
        const sign = dev >= 0 ? '+' : '';
        if (isPct) {
          delta.textContent = sign + dev.toFixed(2) + '%（较基准）';
        } else {
          delta.textContent = sign + dev + '（较基准）';
        }
        dev < 0 ? delta.classList.add('negative') : delta.classList.remove('negative');
      }
      const fEl = document.getElementById(id + 'Formula');
      if (fEl && formula) fEl.textContent = formula.substring(0, 100) + '...';
      const dEl = document.getElementById(id + 'Detail');
      if (dEl && analysis) dEl.textContent = analysis;
      if (id === 'hrv') {
        document.getElementById('hrvBaseChip').textContent = '基准：' + base + 'ms';
        document.getElementById('hrvDevChip').textContent = '偏差：' + (deviation >= 0 ? '+' : '') + deviation.toFixed(2) + '%';
        document.getElementById('hrvScoreChip').textContent = '分数：' + score;
        score >= 80 ? document.getElementById('hrvScoreChip').classList.add('good') : 0;
      }
      if (id === 'rhr') {
        document.getElementById('rhrBaseChip').textContent = '基准：' + base + '次/分';
        document.getElementById('rhrDevChip').textContent = '偏差：' + (deviation >= 0 ? '+' : '') + deviation + '次/分';
        document.getElementById('rhrScoreChip').textContent = '分数：' + score;
        score >= 80 ? document.getElementById('rhrScoreChip').classList.add('good') : 0;
      }
    }

    /* ============================================
       CHARTS
       ============================================ */
    function drawAllCharts(d) {
      drawScoreRing(d);
      drawTrendChart(d);
      drawDualChart(d);
      drawSleepChart(d);
      drawReadyChart(d);
    }

    function drawScoreRing(d) {
      const canvas = document.getElementById('scoreRing');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const cx = canvas.width / 2, cy = canvas.height / 2;
      const r = Math.max(10, Math.min(cx, cy) - 40);
      const lw = 18;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = '#1A1A1A'; ctx.lineWidth = lw; ctx.stroke();

      const score = Math.max(0, Math.min(100, d.score));
      const sa = -Math.PI / 2;
      const ea = sa + Math.PI * 2 * score / 100;
      ctx.beginPath(); ctx.arc(cx, cy, r, sa, ea);
      ctx.strokeStyle = '#008F4D'; ctx.lineWidth = lw; ctx.stroke();

      ctx.fillStyle = '#1A1A1A';
      ctx.font = 'bold 48px "Bebas Neue", sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(score, cx, cy - 10);
      ctx.fillStyle = '#008F4D';
      ctx.font = 'bold 22px "Space Grotesk", sans-serif';
      ctx.fillText('/ 100', cx, cy + 25);

      ctx.beginPath(); ctx.arc(cx, cy, r - 25, 0, Math.PI * 2);
      ctx.strokeStyle = '#C8B99A'; ctx.lineWidth = 2; ctx.stroke();
    }

    function baseChart(ctx, w, h, pad) {
      ctx.clearRect(0, 0, w, h);
      const cw = w - pad.left - pad.right;
      const ch = h - pad.top - pad.bottom;
      return { cw, ch };
    }

    function drawGrid(ctx, w, h, pad, min, max) {
      ctx.strokeStyle = '#E8E0D0'; ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + (h - pad.top - pad.bottom) * i / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        ctx.fillStyle = '#1A1A1A';
        ctx.font = '11px "Space Grotesk", sans-serif';
        ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(max - (max - min) * i / 4), pad.left - 6, y);
      }
    }

    function drawXLabels(ctx, labels, pad, w, h) {
      const cw = w - pad.left - pad.right;
      const step = cw / Math.max(1, labels.length - 1);
      labels.forEach((lb, i) => {
        const x = pad.left + step * i;
        ctx.fillStyle = '#1A1A1A';
        ctx.font = '11px "Space Grotesk", sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'top';
        ctx.fillText(lb, x, h - pad.bottom + 8);
      });
    }

    function drawLineData(ctx, data, labels, pad, w, h, color, fillBelow) {
      if (!data || data.length < 2) return;
      const cw = w - pad.left - pad.right;
      const ch = h - pad.top - pad.bottom;
      const min = Math.min(...data) - 5;
      const max = Math.max(...data) + 5;
      const step = cw / (data.length - 1);

      drawGrid(ctx, w, h, pad, min, max);
      const useLabels = labels && labels.length >= data.length ? labels : data.map((_, i) => '');
      drawXLabels(ctx, useLabels, pad, w, h);

      // fill
      if (fillBelow) {
        ctx.beginPath();
        data.forEach((v, i) => {
          const x = pad.left + step * i;
          const y = pad.top + ch * (1 - (v - min) / (max - min));
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.lineTo(pad.left + step * (data.length - 1), h - pad.bottom);
        ctx.lineTo(pad.left, h - pad.bottom);
        ctx.closePath();
        ctx.fillStyle = color + '18';
        ctx.fill();
      }

      // line
      ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 3;
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      data.forEach((v, i) => {
        const x = pad.left + step * i;
        const y = pad.top + ch * (1 - (v - min) / (max - min));
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();

      // dots
      data.forEach((v, i) => {
        const x = pad.left + step * i;
        const y = pad.top + ch * (1 - (v - min) / (max - min));
        ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#F4EFE6'; ctx.fill();
        ctx.strokeStyle = '#1A1A1A'; ctx.lineWidth = 2; ctx.stroke();
      });

      ctx.fillStyle = '#1A1A1A';
      ctx.font = 'bold 12px "Bebas Neue", sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(fillBelow ? 'RECOVERY' : 'SLEEP SCORE', pad.left, pad.top - 8);
    }

    function drawTrendChart(d) {
      const canvas = document.getElementById('trendChart');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const pad = { top: 22, right: 36, bottom: 36, left: 44 };
      drawLineData(ctx, d.trend, d.trend_labels, pad, canvas.width, canvas.height, '#008F4D', true);
      document.getElementById('trendSub').textContent = '7日恢复趋势 — ' + (d.date || '');
    }

    function drawDualChart(d) {
      const canvas = document.getElementById('dualChart');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width, h = canvas.height;
      const pad = { top: 22, right: 50, bottom: 36, left: 44 };
      ctx.clearRect(0, 0, w, h);

      const hrvData = d.trend || [];
      const rhrData = d.rhr_trend || [];
      const labels = d.trend_labels || [];
      const cw = w - pad.left - pad.right;
      const ch = h - pad.top - pad.bottom;
      const step = cw / Math.max(1, hrvData.length - 1);

      // HRV line (left axis, green)
      const hrvMin = Math.max(0, Math.min(...hrvData) - 5);
      const hrvMax = Math.max(...hrvData) + 5;
      ctx.strokeStyle = '#E8E0D0'; ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + ch * i / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        ctx.fillStyle = '#1A1A1A'; ctx.font = '10px "Space Grotesk", sans-serif';
        ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(hrvMax - (hrvMax - hrvMin) * i / 4), pad.left - 6, y);
      }
      ctx.fillStyle = '#008F4D'; ctx.font = 'bold 10px "Bebas Neue", sans-serif';
      ctx.textAlign = 'left'; ctx.fillText('HRV (ms)', pad.left, pad.top - 8);

      ctx.beginPath(); ctx.strokeStyle = '#008F4D'; ctx.lineWidth = 3;
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      hrvData.forEach((v, i) => {
        const x = pad.left + step * i;
        const y = pad.top + ch * (1 - (v - hrvMin) / (hrvMax - hrvMin));
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();

      // RHR line (right axis, red)
      const rhrMin = Math.max(0, Math.min(...rhrData) - 3);
      const rhrMax = Math.max(...rhrData) + 3;
      ctx.strokeStyle = '#E8E0D0'; ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + ch * i / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        ctx.fillStyle = '#1A1A1A'; ctx.font = '10px "Space Grotesk", sans-serif';
        ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(rhrMax - (rhrMax - rhrMin) * i / 4), w - pad.right + 6, y);
      }
      ctx.fillStyle = '#b91c1c'; ctx.font = 'bold 10px "Bebas Neue", sans-serif';
      ctx.textAlign = 'right'; ctx.fillText('RHR (bpm)', w - pad.right, pad.top - 8);

      ctx.beginPath(); ctx.strokeStyle = '#b91c1c'; ctx.lineWidth = 3;
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      rhrData.forEach((v, i) => {
        const x = pad.left + step * i;
        const y = pad.top + ch * (1 - (v - rhrMin) / (rhrMax - rhrMin));
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();

      // x labels
      labels.forEach((lb, i) => {
        const x = pad.left + step * i;
        ctx.fillStyle = '#1A1A1A'; ctx.font = '11px "Space Grotesk", sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'top';
        ctx.fillText(lb, x, h - pad.bottom + 8);
      });
    }

    function drawSleepChart(d) {
      const canvas = document.getElementById('sleepChart');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width, h = canvas.height;
      const pad = { top: 22, right: 50, bottom: 36, left: 44 };

      const deepPctData = d.sleep_deep_trend || [];
      const sleepScoreData = d.sleep_trend || [];

      // always show sleep score on left axis (0-100)
      const labels = d.trend_labels || [];
      const mainData = sleepScoreData.length >= 2 ? sleepScoreData : deepPctData;
      if (mainData.length < 2) return;

      ctx.clearRect(0, 0, w, h);
      const cw = w - pad.left - pad.right;
      const ch = h - pad.top - pad.bottom;
      const step = cw / (mainData.length - 1);

      // left axis: sleep score (0-100)
      const scoreMin = 0, scoreMax = 100;
      ctx.strokeStyle = '#E8E0D0'; ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + ch * i / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        ctx.fillStyle = '#1A1A1A'; ctx.font = '10px "Space Grotesk", sans-serif';
        ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(scoreMax - (scoreMax - scoreMin) * i / 4), pad.left - 6, y);
      }
      ctx.fillStyle = '#008F4D'; ctx.font = 'bold 10px "Bebas Neue", sans-serif';
      ctx.textAlign = 'left'; ctx.fillText('SLEEP SCORE', pad.left, pad.top - 8);

      // sleep score line (green)
      ctx.beginPath(); ctx.strokeStyle = '#008F4D'; ctx.lineWidth = 3;
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      mainData.forEach((v, i) => {
        const x = pad.left + step * i;
        const y = pad.top + ch * (1 - (Math.min(v, 100) - scoreMin) / (scoreMax - scoreMin));
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke();

      // right axis: deep% (auto-scale, min 0)
      const dpMin = 0;
      const dpMax = deepPctData.length >= 2
        ? Math.max(40, Math.ceil(Math.max(...deepPctData) / 5) * 5 + 5)
        : 40;
      ctx.strokeStyle = '#E8E0D0'; ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + ch * i / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        ctx.fillStyle = '#1A1A1A'; ctx.font = '10px "Space Grotesk", sans-serif';
        ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
        ctx.fillText(Math.round(dpMax - (dpMax - dpMin) * i / 4), w - pad.right + 6, y);
      }
      ctx.fillStyle = '#00A85D'; ctx.font = 'bold 10px "Bebas Neue", sans-serif';
      ctx.textAlign = 'right'; ctx.fillText('DEEP%', w - pad.right, pad.top - 8);

      // deep% overlay (dashed, right axis)
      if (deepPctData.length >= 2) {
        const dpStep = cw / (deepPctData.length - 1);
        ctx.beginPath(); ctx.strokeStyle = '#00A85D'; ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        deepPctData.forEach((v, i) => {
          const x = pad.left + dpStep * i;
          const y = pad.top + ch * (1 - (Math.min(v, dpMax) - dpMin) / (dpMax - dpMin));
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // x labels
      labels.slice(-mainData.length).forEach((lb, i) => {
        const x = pad.left + step * i;
        ctx.fillStyle = '#1A1A1A'; ctx.font = '11px "Space Grotesk", sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'top';
        ctx.fillText(lb, x, h - pad.bottom + 8);
      });

      // legend
      const legendY = h - 6;
      ctx.fillStyle = '#008F4D'; ctx.fillRect(pad.left, legendY - 8, 18, 3);
      ctx.fillStyle = '#1A1A1A'; ctx.font = '10px "Space Grotesk", sans-serif'; ctx.textAlign = 'left';
      ctx.fillText('睡眠分数', pad.left + 22, legendY);
      if (deepPctData.length >= 2) {
        ctx.setLineDash([3, 3]); ctx.strokeStyle = '#00A85D'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(pad.left + 80, legendY - 4); ctx.lineTo(pad.left + 98, legendY - 4); ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillText('深睡%', pad.left + 102, legendY);
      }
    }

    function drawReadyChart(d) {
      const canvas = document.getElementById('readyChart');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const pad = { top: 20, right: 36, bottom: 34, left: 44 };
      drawLineData(ctx, d.ready_trend, d.trend_labels, pad, canvas.width, canvas.height, '#008F4D', true);
      document.getElementById('readySub').textContent = '准备度7日趋势 — ' + (d.date || '');

      // legend
      ctx.fillStyle = '#008F4D';
      ctx.fillRect(pad.left, canvas.height - 8, 18, 3);
      ctx.fillStyle = '#1A1A1A'; ctx.font = '10px "Space Grotesk", sans-serif'; ctx.textAlign = 'left';
      ctx.fillText('准备度分数', pad.left + 22, canvas.height - 4);
    }

    /* ============================================
       SLIDE 5 — 深度分析
       ============================================ */
    function renderSlide5(d) {
      // HRV
      document.getElementById('hrvFormulaBox').textContent = d.hrv_formula;
      document.getElementById('hrvAnalysisText').innerHTML = d.hrv_analysis;
      document.getElementById('hrvScoreChip').textContent = '分数：' + d.hrv_score;
      if (d.hrv_score >= 80) document.getElementById('hrvScoreChip').classList.add('good');
      document.getElementById('hrvBaseChip').textContent = '基准：' + d.hrv_base + 'ms';
      document.getElementById('hrvDevChip').textContent = '偏差：' + (d.hrv_dev_pct >= 0 ? '+' : '') + d.hrv_dev_pct.toFixed(2) + '%';

      // RHR
      document.getElementById('rhrFormulaBox').textContent = d.rhr_formula;
      document.getElementById('rhrAnalysisText').innerHTML = d.rhr_analysis;
      document.getElementById('rhrScoreChip').textContent = '分数：' + d.rhr_score;
      if (d.rhr_score >= 80) document.getElementById('rhrScoreChip').classList.add('good');
      document.getElementById('rhrBaseChip').textContent = '基准：' + d.rhr_base + '次/分';
      document.getElementById('rhrDevChip').textContent = '偏差：' + (d.rhr_dev >= 0 ? '+' : '') + d.rhr_dev + '次/分';
    }

    /* ============================================
       SLIDE 6 — 睡眠与洞察
       ============================================ */
    function renderSlide6(d) {
      // sleep breakdown
      document.getElementById('detailDeepPct').textContent = Math.round(d.deep_pct) + '%';
      document.getElementById('detailRemPct').textContent = Math.round(d.rem_pct) + '%';
      document.getElementById('detailAwake').textContent = d.awake_count + '次';
      document.getElementById('detailTotal').textContent = d.sleep_total.toFixed(1);
      document.getElementById('detailDeepTime').textContent = d.deep_time.toFixed(2);
      document.getElementById('detailRemTime').textContent = d.rem_time.toFixed(2);
      document.getElementById('detailAwakeCount').textContent = d.awake_count;
      document.getElementById('detailSleepTag').textContent = '睡眠分数：' + d.sleep_score;

      // patterns
      const pl = document.getElementById('patternList');
      const patterns = (d.patterns || []).slice(0, 4);
      pl.innerHTML = patterns.map(p => {
        const cls = p.tag === '良好' ? 'good' : p.tag === '注意' ? 'warn' : '';
        return `<div class="insight-item">
          <span class="insight-tag ${cls}">${p.tag}</span>
          <span class="insight-text">${p.text}</span>
        </div>`;
      }).join('');

      // advice
      const al = document.getElementById('adviceList');
      al.innerHTML = (d.advice || []).slice(0, 3).map(a =>
        `<li>${a}</li>`).join('');
    }

    /* ============================================
       SCROLL HINT
       ============================================ */
    function setupScrollHint() {
      const hint = document.getElementById('scrollHint');
      let hidden = false;
      const hide = () => {
        if (!hidden) { hidden = true; hint.classList.add('hidden'); setTimeout(() => hint.remove(), 600); }
      };
      window.addEventListener('scroll', hide, { once: true, passive: true });
      setTimeout(() => { if (!hidden) hide(); }, 4000);
    }

    /* ============================================
       INIT
       ============================================ */
    async function init() {
      setupScrollHint();
      const data = await loadData();
      if (data) renderAll(data);
    }
    init();
  </script>
</body>
</html>'''


# ── Helper: Python dict → JS object string ──────────────────────────────────

def to_js(obj, indent=2):
    """Convert Python dict/list to JS object literal string."""
    if isinstance(obj, dict):
        lines = ["{"]
        for k, v in obj.items():
            key = f"'{k}'" if isinstance(k, str) else str(k)
            val = to_js(v, indent + 2)
            lines.append(f"{' ' * indent}{key}: {val},")
        lines.append(f"{' ' * (indent - 2)}" + "}")
        return "\n".join(lines)
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        items = [to_js(item, indent + 2) for item in obj]
        return "[\n" + ",\n".join(" " * indent + item for item in items) + "\n" + " " * (indent - 2) + "]"
    elif isinstance(obj, str):
        # Escape special chars for JS
        escaped = obj.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        return f"'{escaped}'"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif obj is None:
        return "null"
    else:
        return str(obj)


# ── Helper: date → 中文格式 ──────────────────────────────────────────────────

def fmt_date_zh(date_str):
    """'2026-07-16' → '2026年7月16日'"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.year}年{dt.month}月{dt.day}日"
    except Exception:
        return date_str


# ── Helper: 构建 FALLBACK 数据 ──────────────────────────────────────────────

def build_fallback_data(kpi: dict) -> dict:
    """从 kpi_today.json 提取 FALLBACK 需要的精简字段。"""
    composite = kpi["composite"]
    dims = kpi["dimension_scores"]
    raw = kpi["raw_inputs"]
    history = kpi["history"]
    baselines = kpi["baselines"]
    derived = kpi["derived_metrics_summary"]

    hrv_dim = dims["hrv"]
    rhr_dim = dims["rhr"]
    sleep_dim = dims["sleep"]
    rd_dim = dims["readiness"]
    stress_dim = dims["stress"]

    sleep_score = sleep_dim["score"]
    sleep_total_sec = raw["sleep"]["total_seconds"]
    sleep_total_h = sleep_total_sec / 3600
    deep_sec = raw["sleep"]["deep_seconds"]
    rem_sec = raw["sleep"]["rem_seconds"]
    deep_pct = (deep_sec / sleep_total_sec * 100) if sleep_total_sec > 0 else 0
    rem_pct = (rem_sec / sleep_total_sec * 100) if sleep_total_sec > 0 else 0
    awake_count = raw["sleep"]["awake_count"]

    # 7 日趋势
    hrv_trend = [e["value"] for e in (history.get("hrv_14d") or [])[-7:]]
    rhr_trend = [e["value"] for e in (history.get("rhr_28d") or [])[-7:]]

    sleep_hist = history.get("sleep_28d") or []
    sleep_score_trend = []
    sleep_deep_trend = []
    for e in sleep_hist[-7:]:
        gs = e.get("garmin_score")
        if gs is not None:
            sleep_score_trend.append(gs)
        elif e.get("total_sec"):
            sleep_score_trend.append(min(100, round(e["total_sec"] / 3600 / 9 * 100)))
        else:
            sleep_score_trend.append(0)
        ts = e.get("total_sec", 0)
        ds = e.get("deep_sec", 0)
        sleep_deep_trend.append(round(ds / ts * 100, 1) if ts > 0 else 0)

    rd_trend = []
    for e in (history.get("readiness_28d") or [])[-7:]:
        rd_trend.append(e.get("score", 0))

    # 趋势标签
    hrv_dates = [e.get("date", "") for e in (history.get("hrv_14d") or [])[-7:]]
    trend_labels = []
    for d_str in hrv_dates:
        if d_str:
            dt = datetime.strptime(d_str, "%Y-%m-%d")
            trend_labels.append(f"{dt.month}/{dt.day}")
        else:
            trend_labels.append("")

    return {
        "date": kpi["date"],
        "grade": composite["grade"],
        "score": composite["recovery_score"],
        "hrv": hrv_dim.get("last_night_ms", raw["hrv"]["last_night"]),
        "hrv_base": baselines["hrv_baseline_7d"],
        "hrv_dev_pct": hrv_dim.get("pct_change_pct", 0),
        "hrv_score": hrv_dim["score"],
        "hrv_weekly": raw["hrv"]["weekly_avg"],
        "hrv_status": raw["hrv"].get("status", "--"),
        "hrv_formula": baselines.get("formulas", {}).get("hrv_baseline",
            "HRV = 过去7晚心率变异性的滚动平均值 (RMSSD)。Plews 2014 [R7]"),
        "rhr": rhr_dim["current_bpm"],
        "rhr_base": rhr_dim["baseline_bpm"],
        "rhr_dev": rhr_dim["deviation"],
        "rhr_score": rhr_dim["score"],
        "rhr_formula": baselines.get("formulas", {}).get("rhr_baseline",
            "RHR = 28日滚动静息心率基准。Bosquet 2003 [R12]"),
        "sleep_total": round(sleep_total_h, 2),
        "deep_pct": round(deep_pct, 2),
        "rem_pct": round(rem_pct, 2),
        "deep_time": round(deep_sec / 3600, 2),
        "rem_time": round(rem_sec / 3600, 2),
        "awake_count": awake_count,
        "sleep_score": sleep_score,
        "sleep_formula": baselines.get("formulas", {}).get("sleep_baseline",
            "睡眠分数 = Garmin 综合评分。理想值：7-9小时，深睡15-20%，REM 20-25%。"),
        "ready_score": rd_dim["score"],
        "ready_level": rd_dim.get("zone", "--"),
        "ready_formula": composite.get("formula",
            "准备度综合 HRV、睡眠、RHR 和训练负荷加权计算"),
        "stress_level": stress_dim["stress_level"],
        "stress_score": stress_dim["score"],
        "stress_zone": stress_dim.get("zone", "--"),
        "trend": hrv_trend if hrv_trend else [73, 70, 75, 66, 80, 77, 73],
        "trend_labels": trend_labels if any(trend_labels) else ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
        "rhr_trend": rhr_trend if rhr_trend else [46, 45, 44, 46, 43, 42, 43],
        "sleep_trend": sleep_score_trend if sleep_score_trend else [94, 92, 97, 75, 88, 91, 97],
        "sleep_deep_trend": sleep_deep_trend if sleep_deep_trend else [18, 17, 19, 15, 16, 18, 18],
        "ready_trend": rd_trend if rd_trend else [78, 80, 85, 70, 82, 88, 91],
    }


# ── Helper: 构建 HTML 的 {{PLACEHOLDER}} 替换 ──────────────────────────────

def build_render_data(kpi: dict, fallback: dict) -> dict:
    """构建模板占位符 → 实际值的映射。"""
    composite = kpi["composite"]
    dims = kpi["dimension_scores"]
    raw = kpi["raw_inputs"]
    baselines = kpi["baselines"]
    derived = kpi["derived_metrics_summary"]

    hrv_dim = dims["hrv"]
    rhr_dim = dims["rhr"]
    sleep_dim = dims["sleep"]
    rd_dim = dims["readiness"]
    stress_dim = dims["stress"]

    sleep_total_sec = raw["sleep"]["total_seconds"]
    sleep_total_h = sleep_total_sec / 3600
    deep_sec = raw["sleep"]["deep_seconds"]
    rem_sec = raw["sleep"]["rem_seconds"]
    deep_pct = (deep_sec / sleep_total_sec * 100) if sleep_total_sec > 0 else 0
    rem_pct = (rem_sec / sleep_total_sec * 100) if sleep_total_sec > 0 else 0
    awake_count = raw["sleep"]["awake_count"]

    # 陈述
    grade = composite["grade"]
    score = composite["recovery_score"]
    grade_map = {'A': '优秀', 'B': '良好', 'C': '需要注意', 'D': '需要关注', 'F': '需要休息'}
    grade_text = grade_map.get(grade, '评估中')
    statement = (
        f"恢复分数 {score}（{grade_text}）。"
        + ("身体状态优秀，继续保持良好习惯。" if score >= 80
           else "恢复状态尚可，注意保持睡眠和休息。" if score >= 60
           else "恢复状态需要关注，建议优先保证睡眠。")
    )
    statement_attr = f"每日健康报告，{kpi['date']}"

    # 模式匹配
    hrv_pct = hrv_dim.get("pct_change_pct", 0)
    rhr_dev = rhr_dim["deviation"]
    patterns = []
    if hrv_pct > 0:
        patterns.append("<div class='insight-item'><span class='insight-tag good'>良好</span><span class='insight-text'>心率变异性呈上升趋势，恢复状态良好</span></div>")
    elif hrv_pct >= -5:
        patterns.append("<div class='insight-item'><span class='insight-tag'>稳定</span><span class='insight-text'>心率变异性稳定，恢复能力维持</span></div>")
    else:
        patterns.append("<div class='insight-item'><span class='insight-tag warn'>注意</span><span class='insight-text'>心率变异性下降，建议关注恢复</span></div>")

    if rhr_dev < 0:
        patterns.append(f"<div class='insight-item'><span class='insight-tag good'>良好</span><span class='insight-text'>静息心率低于基准 {abs(rhr_dev)} 次/分，心肺功能改善</span></div>")
    elif rhr_dev == 0:
        patterns.append("<div class='insight-item'><span class='insight-tag'>稳定</span><span class='insight-text'>静息心率与基准持平</span></div>")

    sleep_score_val = sleep_dim["score"]
    if sleep_score_val >= 80:
        patterns.append(f"<div class='insight-item'><span class='insight-tag good'>良好</span><span class='insight-text'>睡眠分数 {sleep_score_val}，睡眠质量优秀</span></div>")
    elif sleep_score_val >= 60:
        patterns.append(f"<div class='insight-item'><span class='insight-tag warn'>注意</span><span class='insight-text'>睡眠分数 {sleep_score_val}，睡眠质量尚可但可改善</span></div>")
    else:
        patterns.append(f"<div class='insight-item'><span class='insight-tag warn'>注意</span><span class='insight-text'>睡眠分数 {sleep_score_val}，建议优先改善睡眠</span></div>")

    if rd_dim["score"] >= 80:
        patterns.append("<div class='insight-item'><span class='insight-tag good'>良好</span><span class='insight-text'>准备度分数高，可承受训练压力</span></div>")

    # 建议
    advice = []
    if sleep_total_h < 7.5:
        advice.append("睡眠时长不足，建议今晚提前入睡，目标7-9小时")
    else:
        advice.append("睡眠时长达标，继续保持规律作息")
    if hrv_pct < 0:
        advice.append("心率变异性偏低，建议进行轻量恢复活动")
    if rhr_dev < -2:
        advice.append("静息心率表现优秀，可安排中高强度训练")
    elif rhr_dev > 2:
        advice.append("静息心率偏高，注意休息和恢复")
    if awake_count > 2:
        advice.append("夜间清醒次数较多，睡前减少屏幕时间")
    if len(advice) < 3:
        advice.append("保持规律作息，适度运动，持续关注健康数据")

    # 准备度
    ready_score = rd_dim["score"]
    ready_detail = (
        "; ".join(composite.get("calculation_steps", []))
        + "。总分：" + str(composite.get("recovery_score", 0))
        if composite.get("calculation_steps")
        else f"准备度分数 {ready_score}"
    )

    # 压力分析
    stress_level = stress_dim["stress_level"]
    stress_zone = stress_dim.get("zone", "--")
    stress_analysis = (
        f"平均压力水平 {stress_level}，处于{stress_zone}区间。"
        + ("压力管理良好，恢复状态佳。" if stress_level <= 25
           else "压力可控，注意保持作息规律。" if stress_level <= 50
           else "压力偏高，建议优先保证睡眠和放松活动。")
    )

    # 评分标签样式
    def tag_class(val, thresholds):
        for th, cls in thresholds:
            if val >= th:
                return cls
        return ""

    return {
        "GRADE": grade,
        "SCORE": score,
        "DATE_ZH": fmt_date_zh(kpi["date"]),
        "DAILY_MSG": f"今日健康分数为 <strong>{score}</strong>。您的身体正在良好恢复。保持节奏。",
        "SCORE_STAMP": "状态良好" if score >= 80 else ("注意" if score >= 60 else "需要休息"),
        "STATEMENT_QUOTE": statement,
        "STATEMENT_ATTR": statement_attr,
        # HRV
        "HRV_TAG": f"分数：{hrv_dim['score']}",
        "HRV_VALUE": hrv_dim.get("last_night_ms", raw["hrv"]["last_night"]),
        "HRV_DELTA": f"{hrv_dim.get('pct_change_pct', 0):+.2f}%（较基准）",
        "HRV_FORMULA": (baselines.get("formulas", {}).get("hrv_baseline", ""))[:100] + "...",
        "HRV_DETAIL": (
            f"心率变异性 {hrv_dim.get('last_night_ms', 0)}ms，"
            f"基准 {baselines['hrv_baseline_7d']}ms。"
            f"变化 {hrv_dim.get('pct_change_pct', 0):+.2f}%。"
            + ("副交感神经张力良好，恢复能力提升。" if hrv_dim.get("pct_change_pct", 0) > 0
               else "恢复能力稳定。" if hrv_dim.get("pct_change_pct", 0) >= -5
               else "注意恢复，避免过度训练。")
        ),
        # RHR
        "RHR_TAG": f"分数：{rhr_dim['score']}",
        "RHR_VALUE": rhr_dim["current_bpm"],
        "RHR_DELTA": f"{rhr_dim['deviation']:+d}（较基准）",
        "RHR_FORMULA": (baselines.get("formulas", {}).get("rhr_baseline", ""))[:100] + "...",
        "RHR_DETAIL": (
            f"静息心率 {rhr_dim['current_bpm']} 次/分，"
            f"基准 {rhr_dim['baseline_bpm']} 次/分（偏差 {rhr_dim['deviation']:+d} 次/分）。"
            + ("心血管效率优秀，恢复状态佳。" if rhr_dim["deviation"] < 0 else "恢复状态良好。")
        ),
        # SLEEP
        "SLEEP_TAG": f"睡眠分数：{sleep_score_val}",
        "SLEEP_VALUE": f"{sleep_total_h:.2f}",
        "SLEEP_DELTA": f"分数：{sleep_score_val}/100",
        "SLEEP_FORMULA": (baselines.get("formulas", {}).get("sleep_baseline", ""))[:100] + "...",
        "SLEEP_DEEP_PCT": f"{round(deep_pct)}%",
        "SLEEP_REM_PCT": f"{round(rem_pct)}%",
        "SLEEP_AWAKE": f"{awake_count}次",
        "SLEEP_DEEP_TIME": f"{deep_sec / 3600:.2f}",
        "SLEEP_REM_TIME": f"{rem_sec / 3600:.2f}",
        "SLEEP_AWAKE_COUNT": str(awake_count),
        # READINESS
        "READY_TAG": f"准备度：{ready_score}",
        "READY_VALUE": ready_score,
        "READY_DELTA": "准备度高" if ready_score >= 80 else ("准备度中等" if ready_score >= 60 else "准备度低"),
        "READY_FORMULA": composite.get("formula", "")[:100] + "...",
        "READY_DETAIL": ready_detail[:200],
        # STRESS
        "STRESS_TAG": f"分数：{stress_dim['score']}",
        "STRESS_VALUE": stress_level,
        "STRESS_DELTA": "压力低" if stress_dim["score"] >= 80 else ("压力中等" if stress_dim["score"] >= 60 else "压力高"),
        "STRESS_FORMULA": "Stress = Garmin 全天平均压力指数 (0-100)。0-25 为低压力，25-50 为中等，>50 为高压力。",
        "STRESS_DETAIL": stress_analysis,
        # Slide 4
        "TREND_SUB": f"7日恢复趋势 — {kpi['date']}",
        "READY_SUB": f"准备度7日趋势 — {kpi['date']}",
        # Slide 5
        "HRV_FORMULA_BOX": baselines.get("formulas", {}).get("hrv_baseline", ""),
        "HRV_ANALYSIS_TEXT": (
            f"心率变异性 {hrv_dim.get('last_night_ms', 0)}ms，"
            f"基准 {baselines['hrv_baseline_7d']}ms。"
            f"变化 {hrv_dim.get('pct_change_pct', 0):+.2f}%。"
            + ("副交感神经张力良好，恢复能力提升。" if hrv_dim.get("pct_change_pct", 0) > 0
               else "恢复能力稳定。" if hrv_dim.get("pct_change_pct", 0) >= -5
               else "注意恢复，避免过度训练。")
        ),
        "HRV_SCORE_CHIP": f"分数：{hrv_dim['score']}",
        "HRV_BASE_CHIP": f"基准：{baselines['hrv_baseline_7d']}ms",
        "HRV_DEV_CHIP": f"偏差：{hrv_dim.get('pct_change_pct', 0):+.2f}%",
        "RHR_FORMULA_BOX": baselines.get("formulas", {}).get("rhr_baseline", ""),
        "RHR_ANALYSIS_TEXT": (
            f"静息心率 {rhr_dim['current_bpm']} 次/分，"
            f"基准 {rhr_dim['baseline_bpm']} 次/分（偏差 {rhr_dim['deviation']:+d} 次/分）。"
            + ("心血管效率优秀，恢复状态佳。" if rhr_dim["deviation"] < 0 else "恢复状态良好。")
        ),
        "RHR_SCORE_CHIP": f"分数：{rhr_dim['score']}",
        "RHR_BASE_CHIP": f"基准：{rhr_dim['baseline_bpm']}次/分",
        "RHR_DEV_CHIP": f"偏差：{rhr_dim['deviation']:+d}次/分",
        # Slide 6
        "DETAIL_DEEP_PCT": f"{round(deep_pct)}%",
        "DETAIL_REM_PCT": f"{round(rem_pct)}%",
        "DETAIL_AWAKE": f"{awake_count}次",
        "DETAIL_TOTAL": f"{sleep_total_h:.1f}",
        "DETAIL_DEEP_TIME": f"{deep_sec / 3600:.2f}",
        "DETAIL_REM_TIME": f"{rem_sec / 3600:.2f}",
        "DETAIL_AWAKE_COUNT": str(awake_count),
        "DETAIL_SLEEP_TAG": f"睡眠分数：{sleep_score_val}",
        "PATTERN_LIST": "\n          ".join(patterns),
        "ADVICE_LIST": "\n          ".join(f"<li>{a}</li>" for a in advice[:3]),
    }


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="从 kpi_today.json 生成 wellness_zine.html")
    parser.add_argument("--output", "-o", default=None,
                        help="输出路径（默认: output/html/wellness_zine.html）")
    parser.add_argument("--kpi", default=None,
                        help="kpi_today.json 路径（默认: output/kpi_today.json）")
    args = parser.parse_args()

    kpi_path = Path(args.kpi) if args.kpi else PROJECT_ROOT / "output" / "kpi_today.json"
    output_path = Path(args.output) if args.output else PROJECT_ROOT / "output" / "html" / "wellness_zine.html"

    print("=" * 60)
    print(f"build_zine.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. Load kpi_today.json
    if not kpi_path.exists():
        print(f"ERROR: {kpi_path} not found")
        print("请先运行: python scripts/rebuild_kpi_today.py")
        return 1

    with open(kpi_path, encoding="utf-8") as f:
        kpi = json.load(f)

    print(f"\n[1] Loaded kpi_today.json")
    print(f"    date: {kpi['date']}")
    print(f"    recovery_score: {kpi['composite']['recovery_score']} ({kpi['composite']['grade']})")
    print(f"    data_source: {kpi.get('data_source', 'unknown')}")

    # 2. Build render data (template placeholders) from full kpi
    #    STATIC_DATA 注入完整 kpi_today.json（嵌套结构），供 file:// 双模式渲染
    render_data = build_render_data(kpi, kpi)

    # 4. Render template
    html = ZINE_TEMPLATE
    for key, value in render_data.items():
        html = html.replace("{{" + key + "}}", str(value))

    html = html.replace("{{STATIC_DATA_JS}}", to_js(kpi))

    # 5. Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Backup if exists
    if output_path.exists():
        backup_path = output_path.with_suffix(".html.bak")
        backup_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\n[2] Backed up existing file to: {backup_path}")

    output_path.write_text(html, encoding="utf-8")

    print(f"\n[3] Generated: {output_path}")
    print(f"    File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"    STATIC_DATA fields: {len(kpi)}")
    print(f"    Template placeholders replaced: {len(render_data)}")

    # 6. Verify key values
    print(f"\n[4] Verification:")
    print(f"    Grade: {kpi['composite']['grade']} | Score: {kpi['composite']['recovery_score']}")
    print(f"    HRV: {dims_hrv(kpi)} ms (score {dims_hrv_score(kpi)})")
    print(f"    RHR: {dims_rhr(kpi)} bpm (score {dims_rhr_score(kpi)})")
    print(f"    Sleep: {dims_sleep_score(kpi)} | Total: {dims_sleep_total(kpi):.2f}h")
    print(f"    Readiness: {dims_ready(kpi)} | Stress: {dims_stress(kpi)}")

    print(f"\nDone! Open {output_path} to verify.")
    return 0


def dims_hrv(kpi): return kpi["dimension_scores"]["hrv"].get("last_night_ms", kpi["raw_inputs"]["hrv"]["last_night"])
def dims_hrv_score(kpi): return kpi["dimension_scores"]["hrv"]["score"]
def dims_rhr(kpi): return kpi["dimension_scores"]["rhr"]["current_bpm"]
def dims_rhr_score(kpi): return kpi["dimension_scores"]["rhr"]["score"]
def dims_sleep_score(kpi): return kpi["dimension_scores"]["sleep"]["score"]
def dims_sleep_total(kpi): return kpi["raw_inputs"]["sleep"]["total_seconds"] / 3600
def dims_ready(kpi): return kpi["dimension_scores"]["readiness"]["score"]
def dims_stress(kpi): return kpi["dimension_scores"]["stress"]["score"]


if __name__ == "__main__":
    exit(main())
