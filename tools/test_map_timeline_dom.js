// 地图时间轴控件 v2 · DOM 集成测试（linkedom 模拟浏览器）
// 覆盖：构建 / all 初始态 / pointer 拖动时间窗 / 键盘 / 全部复位 / onEngage / 钳制 / 销毁
'use strict';

const assert = require('assert');
const path = require('path');

const WS = 'C:/Users/dbsqu/.workbuddy/binaries/node/workspace/node_modules';
const { parseHTML } = require(WS + '/linkedom');

const ROOT = path.join(__dirname, '..');
const T = require(path.join(ROOT, 'timeline', 'map_timeline.js'));

global.requestAnimationFrame = function (fn) { return setTimeout(fn, 0); };

const { document, window } = parseHTML('<!DOCTYPE html><html><body><div id="bar"></div></body></html>');
const Ev = (window && window.Event) || globalThis.Event;

/* 精简事件集（控制断言可手算）：span 44 / n 5 → 半窗 clamp 到 44*0.34 = 14.96 */
const MINI = [
  { name: '虎牢关之战', year: '190' },
  { name: '官渡之战', year: '200' },
  { name: '赤壁之战', year: '208' },
  { name: '夷陵之战', year: '222' },
  { name: '五丈原之战', year: '234' }
];

let passed = 0;
const failures = [];
function ok(name, fn) {
  try { fn(); passed++; console.log('  \u2713 ' + name); }
  catch (e) { failures.push(name); console.error('  \u2717 ' + name + '\n      ' + e.message); }
}
function tick(ms) { return new Promise((r) => setTimeout(r, ms == null ? 12 : ms)); }
function approx(a, b, eps) { eps = eps || 1e-6; assert.ok(Math.abs(a - b) < eps, a + ' vs ' + b); }

(async function main() {

  const el = document.getElementById('bar');
  const seen = [];
  let engageCount = 0;
  const tl = new T.MapTimeline(el, {
    events: MINI,
    onChange: (st) => seen.push(st),
    onEngage: () => { engageCount++; }
  });

  console.log('\n== 构建与初始态（全部显示） ==');
  ok('结构完整且不含播放按钮', () => {
    assert.ok(el.classList.contains('mtl'));
    assert.ok(el.querySelector('.mtl-axis'));
    assert.ok(el.querySelector('.mtl-hit'));
    assert.ok(el.querySelector('.mtl-all'), '缺复位钮');
    assert.strictEqual(el.querySelector('.mtl-play'), null, 'v2 不应再有播放按钮');
  });
  ok('5 个事件点；轴 aria 范围 [190, 234]', () => {
    assert.strictEqual(el.querySelectorAll('.mtl-pt').length, 5);
    const axis = el.querySelector('.mtl-axis');
    assert.strictEqual(axis.getAttribute('aria-valuemin'), '190');
    assert.strictEqual(axis.getAttribute('aria-valuemax'), '234');
  });
  ok('初始 = all 态：读数「全部 / 5 / 5 件」，按钮高亮，游标 100%', () => {
    const st = tl.getState();
    assert.strictEqual(st.all, true);
    assert.strictEqual(el.querySelector('.mtl-year').textContent, '全部');
    assert.strictEqual(el.querySelector('.mtl-count').textContent, '5 / 5 件');
    assert.strictEqual(el.querySelector('.mtl-all').classList.contains('on'), true);
    approx(parseFloat(el.querySelector('.mtl-knob').style.left), 100, 0.01);
    assert.strictEqual(el.querySelectorAll('.mtl-pt.past').length, 5);
  });
  ok('半窗自适应 = 14.96（clamp 上界）', () => approx(tl.getState().halfWin, 14.96, 1e-6));

  console.log('\n== 拖动进入时间窗过滤 ==');
  const axis = el.querySelector('.mtl-axis');
  const hit = el.querySelector('.mtl-hit');
  axis.getBoundingClientRect = () => ({ left: 0, top: 0, width: 960, height: 44, right: 960, bottom: 44 });

  const down = new Ev('pointerdown'); down.clientX = 480; down.pointerId = 1;
  hit.dispatchEvent(down);
  await tick();
  ok('pointerdown → 212 年，窗口 [197,227] 内 3 件（200/208/222）', () => {
    const st = tl.getState();
    assert.strictEqual(st.all, false);
    assert.strictEqual(st.year, 212);
    assert.strictEqual(st.k, 3);
    assert.strictEqual(el.querySelector('.mtl-year').textContent, '212 年');
    assert.strictEqual(el.querySelector('.mtl-count').textContent, '3 / 5 件');
    assert.strictEqual(el.querySelector('.mtl-all').classList.contains('on'), false);
  });
  ok('onEngage 已触发（按下即通知宿主）', () => assert.strictEqual(engageCount, 1));
  ok('拖动中根节点带 dragging 类', () => assert.strictEqual(el.classList.contains('dragging'), true));

  const move = new Ev('pointermove'); move.clientX = 240; move.pointerId = 1;
  hit.dispatchEvent(move);
  await tick();
  ok('pointermove → 201 年（190/200/208 在窗外→窗内 3 件）', () => {
    assert.strictEqual(tl.getState().year, 201);
    assert.strictEqual(el.querySelector('.mtl-count').textContent, '3 / 5 件');
  });

  const up = new Ev('pointerup'); up.pointerId = 1;
  hit.dispatchEvent(up);
  await tick();
  ok('pointerup → dragging 移除', () => assert.strictEqual(el.classList.contains('dragging'), false));

  console.log('\n== 键盘 ==');
  const k1 = new Ev('keydown'); k1.key = 'ArrowLeft';
  axis.dispatchEvent(k1);
  ok('ArrowLeft → 200 年', () => assert.strictEqual(tl.getState().year, 200));

  const k2 = new Ev('keydown'); k2.key = 'End';
  axis.dispatchEvent(k2);
  ok('End → 234 年，仅 222/234 可见（2 件）', () => {
    assert.strictEqual(tl.getState().year, 234);
    assert.strictEqual(el.querySelector('.mtl-count').textContent, '2 / 5 件');
  });

  const k3 = new Ev('keydown'); k3.key = 'Home';
  axis.dispatchEvent(k3);
  ok('Home → 190 年，190/200 可见（2 件）', () => {
    assert.strictEqual(tl.getState().year, 190);
    assert.strictEqual(el.querySelector('.mtl-count').textContent, '2 / 5 件');
  });

  const k4 = new Ev('keydown'); k4.key = 'ArrowLeft';
  axis.dispatchEvent(k4);
  ok('最左端继续 ArrowLeft → 钳制在 190', () => assert.strictEqual(tl.getState().year, 190));
  ok('键盘也触发 onEngage', () => assert.ok(engageCount >= 2));

  console.log('\n== 步进按钮（下一个事件） ==');
  el.querySelector('.mtl-all').dispatchEvent(new Ev('click'));      /* 先回 all 态 */
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('all 态点步进 → 第一个事件（190）', () => {
    assert.strictEqual(tl.getState().all, false);
    assert.strictEqual(tl.getState().year, 190);
  });
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('再点 → 200', () => assert.strictEqual(tl.getState().year, 200));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('连续步进 → 末事件 234', () => assert.strictEqual(tl.getState().year, 234));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('末事件再点 → 回全部显示', () => assert.strictEqual(tl.getState().all, true));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('全部态再点 → 回到第一个事件（循环）', () => assert.strictEqual(tl.getState().year, 190));

  console.log('\n== 全部复位 ==');
  el.querySelector('.mtl-all').dispatchEvent(new Ev('click'));
  ok('⏭ → 回到 all 态（全部 / 5 / 5 件）', () => {
    const st = tl.getState();
    assert.strictEqual(st.all, true);
    assert.strictEqual(el.querySelector('.mtl-year').textContent, '全部');
    assert.strictEqual(el.querySelector('.mtl-count').textContent, '5 / 5 件');
    assert.strictEqual(el.querySelectorAll('.mtl-pt.past').length, 5);
  });

  console.log('\n== 边界与销毁 ==');
  const down2 = new Ev('pointerdown'); down2.clientX = -50; down2.pointerId = 2;
  hit.dispatchEvent(down2);
  await tick();
  ok('拖出左边界 → 钳到 190（2 件）', () => {
    assert.strictEqual(tl.getState().year, 190);
    assert.strictEqual(el.querySelector('.mtl-count').textContent, '2 / 5 件');
  });
  const up2 = new Ev('pointerup'); up2.pointerId = 2;
  hit.dispatchEvent(up2);

  ok('onChange 回调序列的末项为 filter 态且携带 lo/hi', () => {
    const last = seen[seen.length - 1];
    assert.strictEqual(last.all, false);
    approx(last.lo, 190 - 14.96, 1e-6);
    approx(last.hi, 190 + 14.96, 1e-6);
  });

  ok('destroy() 清空容器', () => {
    tl.destroy();
    assert.strictEqual(el.innerHTML, '');
    assert.strictEqual(el.classList.contains('mtl'), false);
  });

  console.log('\n────────────────────────────');
  if (failures.length) {
    console.error(`✗ 失败 ${failures.length} 项 / 共 ${passed + failures.length} 项`);
    process.exit(1);
  } else {
    console.log(`✓ 全部通过：${passed} 项`);
  }
})().catch((e) => {
  console.error('测试脚本异常：', e);
  process.exit(1);
});
