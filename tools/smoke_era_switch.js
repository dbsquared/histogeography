// 疆域断面切换 · 冒烟测试（真代码整跑）
// 从 魏晋南北朝/index.html 抽出 2d 区块，在 Leaflet 桩里把七个断面逐个 build 一遍：
//   - 断言不抛异常、政区多边形数 = 各断面 rings 总数、国名标签数 = 政权数、都邑点/标签数 = 治所数
//   - 断言按年份取断面的边界（250→262、546→546、600→589 等）
//   - 断言读数与滑条同步
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.join(__dirname, '..');
const PAGE = path.join(ROOT, '魏晋南北朝', 'index.html');
const html = fs.readFileSync(PAGE, 'utf8');

const A = html.indexOf('// ── 2d)');
const B = html.indexOf('// ── 2e)');
assert.ok(A > 0 && B > A, '未能定位 2d 区块');
const code = html.slice(A, B);

global.window = {};
require(path.join(ROOT, '魏晋南北朝', 'wei_jin_states.js'));
const DATA = global.window.WEI_JIN_STATES;

/* ── Leaflet / DOM 桩 ── */
const rec = { polygon: 0, marker: 0, dot: 0, groups: 0 };
function LG() { return { addLayer() {}, clearLayers() {}, addTo() { return this; } }; }
const L = {
  layerGroup() { rec.groups++; return LG(); },
  polygon(ring, style) {
    rec.polygon++;
    return { ring, style, on() { return this; }, setStyle() {}, bringToFront() {} };
  },
  marker(ll, opts) { rec.marker++; return { ll, opts, on() { return this; }, getElement() { return null; } }; },
  circleMarker(ll, opts) { rec.dot++; return { ll, opts, bindTooltip() { return this; }, on() { return this; } }; },
  divIcon(o) { return o; }
};
const els = {};
const document = {
  getElementById(id) {
    if (!els[id]) els[id] = { id, checked: false, value: '4', textContent: '', max: '6', setAttribute() {}, oninput: null, onclick: null };
    return els[id];
  }
};
const map = { removeLayer() {}, addLayer() {} };
let collisions = 0;
const scheduleCollision = () => { collisions++; };
const showInfo = () => {};

const api = new Function('L', 'map', 'document', 'window', 'showInfo', 'scheduleCollision', 'console',
  code + '\nreturn { build: buildWjEra, pick: wjPickIndex, S: wjSnapList, idx: () => WJ_SNAP };'
)(L, map, document, global.window, showInfo, scheduleCollision, console);

let pass = 0, fail = 0;
function ok(name, fn) {
  try { fn(); pass++; console.log('  ✓ ' + name); }
  catch (e) { fail++; console.error('  ✗ ' + name + '\n      ' + e.message); }
}

console.log('═══ 魏晋南北朝 · 疆域断面 ═══');
ok('数据含 7 个断面', () => assert.strictEqual(api.S().length, 7));
ok('初始断面为 546 年（序号 4）', () => assert.strictEqual(api.idx(), 4));

console.log('\n【逐年切换】');
let totalPoly = 0, totalSeats = 0;
api.S().forEach((snap, i) => {
  rec.polygon = rec.marker = rec.dot = 0;
  let err = null;
  try { api.build(i); } catch (e) { err = e; }
  const rings = snap.states.reduce((a, s) => a + (s.rings || []).length, 0);
  const seats = snap.states.reduce((a, s) => a + (s.seats || []).length, 0);
  totalPoly += rings; totalSeats += seats;
  ok(snap.year + ' ' + snap.name + '：' + snap.states.length + ' 政权 / ' + rings + ' 环 / ' + seats + ' 治所',
    () => {
      assert.strictEqual(err, null, err && err.message);
      assert.strictEqual(rec.polygon, rings, '多边形数不符');
      assert.strictEqual(rec.marker, snap.states.length + seats, '标记数 = 国名标签 + 都邑标签');
      const caps = snap.states.reduce((a,s)=>a+(s.seats||[]).filter(x=>x.role==='capital').length,0);
      assert.strictEqual(rec.dot, seats + caps, '都邑点数 = 治所 + 都城（capital 另画一层）');
      assert.strictEqual(api.idx(), i);
    });
});
console.log('  合计 ' + totalPoly + ' 个政区多边形 / ' + totalSeats + ' 个都邑');

console.log('\n【按年份取断面】');
[[220, 0], [262, 0], [300, 1], [350, 1], [382, 2], [480, 2], [546, 4], [560, 4], [576, 5], [589, 6], [600, 6]]
  .forEach(([y, want]) => ok('公元 ' + y + ' 年 → 第 ' + want + ' 断面', () => assert.strictEqual(api.pick(y), want)));

console.log('\n【读数与滑条】');
const ro = () => els['era-readout'].textContent;
api.build(6);
ok('589 年读数', () => assert.ok(/589 年 · 隋/.test(ro()), ro()));
ok('滑条同步到 6', () => assert.strictEqual(els['era-range'].value, '6'));
api.build(0);
ok('262 年读数含魏蜀吴', () => assert.ok(/262 年 · 魏｜蜀｜吴/.test(ro()), ro()));

console.log('\n【重复调用不重建】');
const before = rec.polygon;
api.build(0);
ok('同断面重复 build 直接返回', () => assert.strictEqual(rec.polygon, before));
ok('调度过碰撞重排', () => assert.ok(collisions > 0));

console.log('\n────────────────────────────');
if (fail) { console.error('✗ 失败 ' + fail + ' 项 / 共 ' + (pass + fail) + ' 项'); process.exit(1); }
console.log('✓ 全部通过：' + pass + ' 项');
