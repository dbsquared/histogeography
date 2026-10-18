// 时间轴组件核心逻辑测试（Node 环境，无需浏览器）
// 覆盖：年份格式化 / 轴位置映射 / 事件进度二分 / 点布局 / 数据完整性 / 静态交叉检查
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const T = require(path.join(ROOT, 'timeline', 'timeline.js'));
const DATA = require(path.join(ROOT, 'timeline', 'timeline_data.js')).HISTORY_TIMELINE_DATA;
const U = T.Util;

let passed = 0;
const failures = [];
function ok(name, fn) {
  try { fn(); passed++; console.log('  \u2713 ' + name); }
  catch (e) { failures.push(name); console.error('  \u2717 ' + name + '\n      ' + e.message); }
}
function approx(a, b, eps) { eps = eps || 1e-9; assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}`); }

const eras = DATA.eras;

console.log('\n== 年份格式化 ==');
ok('fmtYear(-209) = 前209', () => assert.strictEqual(U.fmtYear(-209), '前209'));
ok('fmtYear(208) = 208', () => assert.strictEqual(U.fmtYear(208), '208'));
ok('fmtYearFull(-209) = 公元前 209 年', () => assert.strictEqual(U.fmtYearFull(-209), '公元前 209 年'));
ok('fmtYearFull(208) = 公元 208 年', () => assert.strictEqual(U.fmtYearFull(208), '公元 208 年'));
ok('fmtSpan(-206,-205) = 前206–205', () => assert.strictEqual(U.fmtSpan(-206, -205), '前206–205'));
ok('fmtSpan(184,280) = 184–280', () => assert.strictEqual(U.fmtSpan(184, 280), '184–280'));
ok('fmtSpan(-209,-209) 去重 = 前209', () => assert.strictEqual(U.fmtSpan(-209, -209), '前209'));
ok('hexToRgba 六位', () => assert.strictEqual(U.hexToRgba('#ffd479', 0.16), 'rgba(255,212,121,0.16)'));
ok('hexToRgba 三位', () => assert.strictEqual(U.hexToRgba('#f00', 1), 'rgba(255,0,0,1)'));

console.log('\n== 轴位置映射（5 段等宽，段内线性） ==');
ok('resolve(0) → 首段起点', () => {
  const s = U.resolve(0, eras);
  assert.strictEqual(s.i, 0);
  assert.strictEqual(s.year, eras[0].from); // -1046
});
ok('resolve(1) → 末段终点', () => {
  const s = U.resolve(1, eras);
  assert.strictEqual(s.i, eras.length - 1);
  assert.strictEqual(s.year, eras[eras.length - 1].to); // 1644
});
ok('resolve(0.2) → 楚汉段起点（前209）', () => {
  const s = U.resolve(0.2, eras);
  assert.strictEqual(s.i, 1);
  assert.strictEqual(s.year, -209);
});
ok('resolve(0.4) → 汉末三国段起点（184）', () => {
  const s = U.resolve(0.4, eras);
  assert.strictEqual(s.i, 2);
  assert.strictEqual(s.year, 184);
});
ok('resolve(0.5) → 汉末三国段中点（232）', () => {
  const s = U.resolve(0.5, eras);
  assert.strictEqual(s.i, 2);
  assert.strictEqual(s.year, 232);
});
ok('越界：resolve(-1) 夹到 0；resolve(2) 夹到 1', () => {
  assert.strictEqual(U.resolve(-1, eras).frac, 0);
  assert.strictEqual(U.resolve(2, eras).frac, 1);
});
ok('fracOf/resolve 往返：208 年落于汉末三国段 0.25 处', () => {
  const f = U.fracOf(208, 2, eras);
  approx(f, 0.45);
  const s = U.resolve(f, eras);
  assert.strictEqual(s.i, 2);
  assert.strictEqual(s.year, 208);
});
ok('段端点不越界：fracOf(三国的 to=280) 仍落在三国段内', () => {
  const f = U.fracOf(280, 2, eras);
  const s = U.resolve(f, eras);
  assert.strictEqual(s.i, 2);
  assert.strictEqual(s.year, 280);
});

console.log('\n== 事件进度（二分） ==');
const sg = U.parseEvents(DATA.eras[2].events);
ok('事件已按年份升序', () => {
  for (let i = 1; i < sg.length; i++) assert.ok(sg[i].year >= sg[i - 1].year);
});
ok('pastCount(208) = 11（含赤壁/长坂/江陵）', () => {
  assert.strictEqual(U.pastCount(sg, 208), 11);
});
ok('pastCount(280) = 全部 = 34', () => assert.strictEqual(U.pastCount(sg, 280), sg.length));
ok('pastCount(183) = 0', () => assert.strictEqual(U.pastCount(sg, 183), 0));
ok('pastCount 在事件边界逐点递增', () => {
  const k1 = U.pastCount(sg, 228);
  const k2 = U.pastCount(sg, 227);
  assert.ok(k1 > k2, `228: ${k1} 应大于 227: ${k2}`);
});

console.log('\n== 事件点错落布局 ==');
ok('每段点数与事件数一致，t∈[0,1]，row∈{0,1,2}', () => {
  eras.forEach((era) => {
    const layout = U.layoutPoints(U.parseEvents(era.events), era);
    assert.strictEqual(layout.length, era.events.length, era.name + ' 点数不符');
    layout.forEach((p) => {
      assert.ok(p.t >= 0 && p.t <= 1, era.name + ' t 越界 ' + p.t);
      assert.ok(p.row >= 0 && p.row < 3, era.name + ' row 越界 ' + p.row);
    });
  });
});

console.log('\n== 数据完整性 ==');
ok('时期按时间先后排列（首尾相接的断裂轴）', () => {
  for (let i = 1; i < eras.length; i++) {
    assert.ok(eras[i].from >= eras[i - 1].to, `${eras[i - 1].name} → ${eras[i].name} 顺序错误`);
  }
});
ok('每个事件年份落在所属时期区间内', () => {
  eras.forEach((era) => {
    const lo = Math.min(era.from, era.to);
    const hi = Math.max(era.from, era.to);
    era.events.forEach((ev) => {
      assert.ok(ev.year >= lo && ev.year <= hi, `${era.name} · ${ev.name} year=${ev.year} 超出 [${lo},${hi}]`);
      const e = ev.endYear == null ? ev.year : ev.endYear;
      assert.ok(e >= lo && e <= hi, `${era.name} · ${ev.name} endYear=${e} 超出区间`);
      assert.ok(e >= ev.year, `${era.name} · ${ev.name} endYear 早于 year`);
    });
  });
});
ok('时期字段齐全（id/name/color/from/to/events）', () => {
  eras.forEach((era) => {
    assert.ok(era.id && era.name && era.color, '缺字段: ' + era.name);
    assert.ok(typeof era.from === 'number' && typeof era.to === 'number');
    assert.ok(Array.isArray(era.events) && era.events.length > 0);
  });
});
ok('事件规模：楚汉 26 条、汉末三国 34 条', () => {
  assert.strictEqual(eras[1].events.length, 26);
  assert.strictEqual(eras[2].events.length, 34);
});

console.log('\n== 静态交叉检查（HTML / CSS / JS 引用链） ==');
const html = fs.readFileSync(path.join(ROOT, 'timeline', 'index.html'), 'utf8');
const css = fs.readFileSync(path.join(ROOT, 'timeline', 'timeline.css'), 'utf8');
const js = fs.readFileSync(path.join(ROOT, 'timeline', 'timeline.js'), 'utf8');
ok('index.html 含挂载点 #timeline 且三个资源引用齐全', () => {
  assert.ok(html.includes('id="timeline"'));
  assert.ok(html.includes('timeline.css'));
  assert.ok(html.includes('timeline.js'));
  assert.ok(html.includes('timeline_data.js'));
  assert.ok(html.includes('new HistoryTimeline'));
});
ok('JS 中 querySelector 的类名均在 CSS 中有定义', () => {
  const sel = [...js.matchAll(/querySelector(?:All)?\(\s*'\.([a-z0-9-]+)/g)].map((m) => m[1]);
  const missing = sel.filter((c) => !css.includes('.' + c));
  assert.deepStrictEqual(missing, [], 'CSS 缺少：' + missing.join(', '));
});
ok('JS 动态注入的关键类名均在 CSS 中有定义', () => {
  const injected = ['htl-status-dot', 'htl-status-era', 'htl-status-year', 'htl-status-tag', 'htl-col-name',
    'htl-col-lanes', 'htl-col-track', 'htl-col-seg', 'htl-gap', 'htl-col-range', 'htl-pt',
    'htl-knob-line', 'htl-knob-head', 'htl-knob-bubble', 'htl-hit', 'htl-events-title',
    'htl-era-link', 'htl-ev-in', 'htl-ev-year', 'htl-ev-name', 'htl-ev-meta', 'htl-ev-result'];
  const missing = injected.filter((c) => !css.includes('.' + c));
  assert.deepStrictEqual(missing, [], 'CSS 缺少：' + missing.join(', '));
});
ok('UMD 双导出（浏览器挂载 window / Node 可 require）', () => {
  assert.ok(typeof T.HistoryTimeline === 'function');
  assert.ok(js.includes('window.HistoryTimeline'));
});

console.log('\n────────────────────────────');
if (failures.length) {
  console.error(`✗ 失败 ${failures.length} 项 / 共 ${passed + failures.length} 项`);
  process.exit(1);
} else {
  console.log(`✓ 全部通过：${passed} 项`);
}
