// 地图时间轴 · 纪元标记（marks）DOM 测试
// 覆盖：刻度数量与位置 / has-marks 类 / 点击刻度跳转 / 高亮当前断面 / 右侧纪元名 / 无 marks 时不改动外观
'use strict';
const assert = require('assert');
const path = require('path');

const WS = 'C:/Users/dbsqu/.workbuddy/binaries/node/workspace/node_modules';
const { parseHTML } = require(WS + '/linkedom');
const ROOT = path.join(__dirname, '..');
const T = require(path.join(ROOT, 'timeline', 'map_timeline.js'));

global.requestAnimationFrame = function (fn) { return setTimeout(fn, 0); };
const { document, window } = parseHTML('<!DOCTYPE html><html><body><div id="bar"></div><div id="bar2"></div></body></html>');
const Ev = (window && window.Event) || globalThis.Event;

let passed = 0, failed = 0;
function ok(name, fn) {
  try { fn(); passed++; console.log('  ✓ ' + name); }
  catch (e) { failed++; console.error('  ✗ ' + name + '\n      ' + e.message); }
}
const tick = ms => new Promise(r => setTimeout(r, ms == null ? 12 : ms));

const EVENTS = [
  { name: '甲', year: '262' }, { name: '乙', year: '383' },
  { name: '丙', year: '546' }, { name: '丁', year: '589' }
];
const MARKS = [
  { year: 262, name: '三国鼎立', short: '262' },
  { year: 383, name: '前秦·东晋', short: '383' },
  { year: 546, name: '东魏·西魏·梁', short: '546' },
  { year: 589, name: '隋', short: '589' }
];

(async function main() {
  console.log('═══ 时间轴 · 纪元标记 ═══');

  const seen = [];
  const tl = new T.MapTimeline(document.getElementById('bar'), {
    events: EVENTS, bc: false, minYear: 262, maxYear: 589,
    marks: MARKS,
    onChange: st => seen.push(st)
  });

  const host = document.getElementById('bar');
  const ticks = host.querySelectorAll('.mtl-mark');

  ok('刻度数量与 marks 一致', () => assert.strictEqual(ticks.length, 4));
  ok('轴上加了 has-marks 类', () => assert.ok(host.classList.contains('has-marks')));
  ok('刻度年份文字正确', () => {
    const txt = Array.from(ticks).map(t => t.textContent.trim()).join(',');
    assert.strictEqual(txt, '262,383,546,589');
  });
  ok('刻度位置按年份比例落点', () => {
    const lefts = Array.from(ticks).map(t => parseFloat(t.style.left));
    assert.ok(Math.abs(lefts[0] - 0) < 0.01, '首刻度应在 0%：' + lefts[0]);
    assert.ok(Math.abs(lefts[3] - 100) < 0.01, '末刻度应在 100%：' + lefts[3]);
    // 383 在 262–589 的 (383-262)/327 = 37.0%
    assert.ok(Math.abs(lefts[1] - 37.0) < 0.5, '383 应在 37% 附近：' + lefts[1]);
  });
  ok('右侧纪元名预留空位（all 态不显示）', () => {
    const era = host.querySelector('.mtl-era');
    assert.ok(era, '缺少 .mtl-era');
    assert.strictEqual(era.textContent, '');
  });

  // 点击第三个刻度（546）→ 应跳到该年并进入 filter 态
  Array.from(ticks)[2].dispatchEvent(new Ev('click'));
  await tick(20);

  ok('点击刻度后年份跳到该断面', () => {
    assert.ok(seen.length > 0, 'onChange 未被调用');
    const st = seen[seen.length - 1];
    assert.strictEqual(st.all, false);
    assert.strictEqual(st.year, 546);
  });
  ok('对应刻度高亮（.on）', () => {
    const on = Array.from(host.querySelectorAll('.mtl-mark')).filter(t => t.classList.contains('on'));
    assert.strictEqual(on.length, 1);
    assert.strictEqual(on[0].textContent.trim(), '546');
  });
  ok('右侧显示该断面名称', () => {
    assert.strictEqual(host.querySelector('.mtl-era').textContent, '东魏·西魏·梁');
  });

  // 点最左侧刻度 → 回到 262
  Array.from(host.querySelectorAll('.mtl-mark'))[0].dispatchEvent(new Ev('click'));
  await tick(20);
  ok('点首刻度回到 262，高亮随之左移', () => {
    const on = Array.from(host.querySelectorAll('.mtl-mark')).filter(t => t.classList.contains('on'));
    assert.strictEqual(on.length, 1);
    assert.strictEqual(on[0].textContent.trim(), '262');
    assert.strictEqual(host.querySelector('.mtl-era').textContent, '三国鼎立');
  });

  // 复位：全部态不高亮、纪元名清空
  host.querySelector('.mtl-all').dispatchEvent(new Ev('click'));
  await tick(20);
  ok('复位后取消高亮与纪元名', () => {
    assert.strictEqual(host.querySelectorAll('.mtl-mark.on').length, 0);
    assert.strictEqual(host.querySelector('.mtl-era').textContent, '');
  });

  // 不传 marks 的页面：外观与旧版一致
  new T.MapTimeline(document.getElementById('bar2'), { events: EVENTS, bc: false });
  const h2 = document.getElementById('bar2');
  ok('无 marks 时不加 has-marks、不渲染刻度', () => {
    assert.ok(!h2.classList.contains('has-marks'));
    assert.strictEqual(h2.querySelectorAll('.mtl-mark').length, 0);
  });

  console.log('\n────────────────────────────');
  if (failed) { console.error('✗ 失败 ' + failed + ' 项 / 共 ' + (passed + failed) + ' 项'); process.exit(1); }
  console.log('✓ 全部通过：' + passed + ' 项');
})();
