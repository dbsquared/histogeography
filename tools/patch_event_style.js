#!/usr/bin/env node
/*
 * 大事记（event）样式整改补丁：
 *   1) 事件名精简（汉末 7 条 / 楚汉 5 条）——地图标签只留短名，详情在弹窗 result 里
 *   2) 标签补专属颜色（浅紫）——此前无 color 规则，浅色字被 9px 黑描边糊成一团
 *   3) 图标图形：旗帜 → 简牍/文书（方框 + 三行字）；圈色：金 → 白（与关隘/津渡一致）
 *   4) sites 数据版本戳升档（2026101801）
 *   5) 冒烟测试里的事件名同步
 * 默认 dry-run；--apply 写入。
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APPLY = process.argv.includes('--apply');

const OLD_GLYPH = `    return '<g transform="translate(0,-1)"><path d="M -2.2 -17 L -2.2 16" stroke="#FFFFFF" stroke-width="2.6" stroke-linecap="round"/><path d="M -0.4 -17 L 15 -11.6 L -0.4 -6.2 Z" fill="#FFFFFF"/><circle cx="-2.2" cy="16" r="2.4" fill="#FFFFFF"/></g>';`;
const NEW_GLYPH = `    return '<g transform="translate(0,-0.5)"><rect x="-15" y="-15" width="30" height="30" rx="3.5" fill="none" stroke="#FFFFFF" stroke-width="3.2"/><path d="M -8 -8 H 8 M -8 -1.5 H 8 M -8 5 H 2.5" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round"/></g>';`;

const RULES = {
  '汉末三国/three_kingdoms_sites.js': [
    { name: '改名：董卓入洛阳·废少帝 → 董卓废帝', old: `name:'董卓入洛阳·废少帝'`, neu: `name:'董卓废帝'` },
    { name: '改名：关东联军讨董·火烧洛阳 → 火烧洛阳', old: `name:'关东联军讨董·火烧洛阳'`, neu: `name:'火烧洛阳'` },
    { name: '改名：曹操迎帝都许 → 迎帝都许', old: `name:'曹操迎帝都许'`, neu: `name:'迎帝都许'` },
    { name: '改名：袁术僭号仲氏 → 袁术称帝', old: `name:'袁术僭号仲氏'`, neu: `name:'袁术称帝'` },
    { name: '改名：三顾茅庐·隆中对 → 三顾茅庐', old: `name:'三顾茅庐·隆中对'`, neu: `name:'三顾茅庐'` },
    { name: '改名：曹操进爵魏公·魏王 → 曹操进魏王', old: `name:'曹操进爵魏公·魏王'`, neu: `name:'曹操进魏王'` },
    { name: '改名：曹丕受禅·汉祚终 → 曹丕称帝', old: `name:'曹丕受禅·汉祚终'`, neu: `name:'曹丕称帝'` }
  ],
  '楚汉争霸/chu_han_sites.js': [
    { name: '改名：陈胜称王·张楚 → 陈胜称王', old: `name:'陈胜称王·张楚'`, neu: `name:'陈胜称王'` },
    { name: '改名：刘邦起兵·为沛公 → 刘邦起兵', old: `name:'刘邦起兵·为沛公'`, neu: `name:'刘邦起兵'` },
    { name: '改名：项羽分封十八王 → 分封十八王', old: `name:'项羽分封十八王'`, neu: `name:'分封十八王'` },
    { name: '改名：韩信拜将·登坛 → 韩信拜将', old: `name:'韩信拜将·登坛'`, neu: `name:'韩信拜将'` },
    { name: '改名：刘邦称帝·汉室肇建 → 刘邦称帝', old: `name:'刘邦称帝·汉室肇建'`, neu: `name:'刘邦称帝'` }
  ],
  '汉末三国/index.html': [
    { name: '标签补 event 色（浅紫）', old: `.tk-label.battle{color:#ffd24d;}`, neu: `.tk-label.battle{color:#ffd24d;}.tk-label.event{color:#e1bee7;}` },
    { name: '图标：旗帜改简牍', old: OLD_GLYPH, neu: NEW_GLYPH },
    { name: '单点图标圈改白', old: `  const ring = category==='battle' ? '#FFC107' : (category==='event' ? '#FFD479' : '#FFFFFF');`, neu: `  const ring = category==='battle' ? '#FFC107' : '#FFFFFF';` },
    { name: '融合图标圈改白', old: `  const ring = mainCat==='battle' ? '#FFC107' : (mainCat==='event' ? '#FFD479' : '#FFFFFF');`, neu: `  const ring = mainCat==='battle' ? '#FFC107' : '#FFFFFF';` },
    { name: 'sites 版本戳升档', old: `three_kingdoms_sites.js?v=2026101301`, neu: `three_kingdoms_sites.js?v=2026101801` }
  ],
  '楚汉争霸/index.html': [
    { name: '标签补 event 色（浅紫）', old: `.ch-label.battle{color:#ffd24d;}`, neu: `.ch-label.battle{color:#ffd24d;}.ch-label.event{color:#e1bee7;}` },
    { name: '图标：旗帜改简牍', old: OLD_GLYPH, neu: NEW_GLYPH },
    { name: '单点图标圈改白', old: `  const ring = category==='battle' ? '#FFC107' : (category==='event' ? '#FFD479' : '#FFFFFF');`, neu: `  const ring = category==='battle' ? '#FFC107' : '#FFFFFF';` },
    { name: '融合图标圈改白', old: `  const ring = mainCat==='battle' ? '#FFC107' : (mainCat==='event' ? '#FFD479' : '#FFFFFF');`, neu: `  const ring = mainCat==='battle' ? '#FFC107' : '#FFFFFF';` },
    { name: 'sites 版本戳升档', old: `chu_han_sites.js?v=2026101301`, neu: `chu_han_sites.js?v=2026101801` }
  ],
  'tools/smoke_maptimebar.js': [
    { name: '冒烟：三顾茅庐改名同步', old: `'三顾茅庐·隆中对'`, neu: `'三顾茅庐'` },
    { name: '冒烟：曹丕称帝改名同步', old: `'曹丕受禅·汉祚终'`, neu: `'曹丕称帝'` },
    { name: '冒烟：韩信拜将改名同步', old: `'韩信拜将·登坛'`, neu: `'韩信拜将'` },
    { name: '冒烟：刘邦称帝改名同步', old: `'刘邦称帝·汉室肇建'`, neu: `'刘邦称帝'` }
  ]
};

function patchFile(file, rules) {
  const abs = path.join(ROOT, file);
  let text = fs.readFileSync(abs, 'utf8');
  const eol = /\r\n/.test(text.slice(0, 4096)) ? '\r\n' : '\n';
  const co = (s) => s.split('\n').join(eol);
  let ok = true;
  const report = ['  · 换行 ' + JSON.stringify(eol)];

  rules.forEach(function (r) {
    const cnt = text.split(co(r.old)).length - 1;
    if (cnt !== 1) { ok = false; report.push('  ✗ [' + r.name + '] 匹配 ' + cnt + ' 次（期望 1）'); return; }
    text = text.split(co(r.old)).join(co(r.neu));
    report.push('  ✓ ' + r.name);
  });

  console.log('\n═══ ' + file + ' ═══');
  report.forEach(function (l) { console.log(l); });
  if (!ok) { console.log('  ⚠ 有规则未命中 → 未写入'); return false; }
  if (APPLY) { fs.writeFileSync(abs, text, 'utf8'); console.log('  → 已写入'); }
  else { console.log('  → dry-run（全部命中，未写入）'); }
  return true;
}

let all = true;
Object.keys(RULES).forEach(function (f) { if (!patchFile(f, RULES[f])) all = false; });
process.exit(all ? 0 : 1);
