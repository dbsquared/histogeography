// 时间轴组件 DOM 集成测试（linkedom 模拟浏览器环境）
// 覆盖：组件完整构建 / 初始状态 / 拖动（pointer 事件全链路）/ 键盘 / 时期切换 / 事件显隐 / 销毁
'use strict';

const assert = require('assert');
const path = require('path');

const WS = 'C:/Users/dbsqu/.workbuddy/binaries/node/workspace/node_modules';
const { parseHTML } = require(WS + '/linkedom');

const ROOT = path.join(__dirname, '..');
const T = require(path.join(ROOT, 'timeline', 'timeline.js'));
const DATA = require(path.join(ROOT, 'timeline', 'timeline_data.js')).HISTORY_TIMELINE_DATA;

/* ── 浏览器 API 桩 ── */
global.requestAnimationFrame = function (fn) { return setTimeout(fn, 0); };
global.cancelAnimationFrame = function (id) { clearTimeout(id); };

const { document, window } = parseHTML('<!DOCTYPE html><html><body><div id="tl"></div></body></html>');
const Ev = (window && window.Event) || globalThis.Event;

let passed = 0;
const failures = [];
function ok(name, fn) {
  try { fn(); passed++; console.log('  \u2713 ' + name); }
  catch (e) { failures.push(name); console.error('  \u2717 ' + name + '\n      ' + e.message); }
}
function approx(a, b, eps) { eps = eps || 1e-6; assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}`); }
function tick(ms) { return new Promise((r) => setTimeout(r, ms == null ? 12 : ms)); }

(async function main() {

  /* ── 构建组件 ── */
  const el = document.getElementById('tl');
  let changeCount = 0;
  let lastState = null;

  const tl = new T.HistoryTimeline(el, {
    eras: DATA.eras,
    initialEra: 'han-san-guo',
    initialYear: 208,
    onChange: function (st) { changeCount++; lastState = st; }
  });

  console.log('\n== 组件构建 ==');
  ok('根容器挂载 .htl 且结构完整', () => {
    assert.ok(el.classList.contains('htl'));
    assert.ok(el.querySelector('.htl-status'), '缺状态条');
    assert.ok(el.querySelector('.htl-axis'), '缺轴');
    assert.ok(el.querySelector('.htl-knob'), '缺游标');
    assert.ok(el.querySelector('.htl-hit'), '缺热区');
    assert.ok(el.querySelector('.htl-events'), '缺事件区');
  });
  ok('5 个时期列 + 4 个断裂标记', () => {
    assert.strictEqual(el.querySelectorAll('.htl-col').length, 5);
    assert.strictEqual(el.querySelectorAll('.htl-gap').length, 4);
  });
  ok('事件点与卡片总数 = 87（26+34+11+8+8）', () => {
    assert.strictEqual(el.querySelectorAll('.htl-pt').length, 87);
    assert.strictEqual(el.querySelectorAll('.htl-ev').length, 87);
  });
  ok('轴具备无障碍属性 role=slider', () => {
    const axis = el.querySelector('.htl-axis');
    assert.strictEqual(axis.getAttribute('role'), 'slider');
    assert.strictEqual(axis.getAttribute('aria-valuemin'), '0');
    assert.strictEqual(axis.getAttribute('aria-valuemax'), '1000');
  });

  console.log('\n== 初始状态（汉末三国 · 208 年） ==');
  ok('状态条：时期 / 年份 / 计数 / 徽标', () => {
    assert.strictEqual(el.querySelector('.htl-status-era').textContent, '汉末三国');
    assert.strictEqual(el.querySelector('.htl-status-year').textContent, '公元 208 年');
    assert.strictEqual(el.querySelector('.htl-status-count').textContent, '34 件大事');
    assert.strictEqual(el.querySelector('.htl-status-tag').textContent, '已上线');
  });
  ok('仅汉末三国的事件卡片显示（34 张），其余隐藏', () => {
    const on = el.querySelectorAll('.htl-ev.on');
    assert.strictEqual(on.length, 34);
    on.forEach((c) => assert.strictEqual(c.getAttribute('data-era'), '2'));
  });
  ok('仅第 3 个时期列高亮', () => {
    const cols = el.querySelectorAll('.htl-col');
    assert.strictEqual(cols[2].classList.contains('active'), true);
    assert.strictEqual(cols[0].classList.contains('active'), false);
  });
  ok('游标位于 45%（208 年段内位置）', () => {
    const left = parseFloat(el.querySelector('.htl-knob').style.left);
    approx(left, 45);
  });
  ok('已发生 / 未至状态：11 个 past，其余 future', () => {
    const col3 = el.querySelectorAll('.htl-col')[2];
    assert.strictEqual(col3.querySelectorAll('.htl-pt.past').length, 11);
    assert.strictEqual(col3.querySelectorAll('.htl-pt.future').length, 23);
    assert.strictEqual(el.querySelectorAll('.htl-ev.future').length, 23);
  });
  ok('地图入口链接指向汉末三国', () => {
    const link = el.querySelector('.htl-era-link');
    assert.strictEqual(link.getAttribute('href'), '../汉末三国/');
    assert.strictEqual(link.classList.contains('disabled'), false);
    assert.ok(link.textContent.indexOf('汉末三国地图') >= 0);
  });
  ok('onChange 已回调且携带状态', () => {
    assert.ok(changeCount >= 1);
    assert.strictEqual(lastState.era.id, 'han-san-guo');
    assert.strictEqual(lastState.year, 208);
  });

  console.log('\n== 拖动交互（pointer 全链路） ==');
  const axis = el.querySelector('.htl-axis');
  const hit = el.querySelector('.htl-hit');
  axis.getBoundingClientRect = function () {
    return { left: 0, top: 0, width: 960, height: 114, right: 960, bottom: 114 };
  };

  const down = new Ev('pointerdown'); down.clientX = 200; down.pointerId = 1;
  hit.dispatchEvent(down);
  await tick();
  ok('pointerdown(200px) → 进入楚汉段（前209 年附近）', () => {
    assert.strictEqual(el.querySelector('.htl-status-era').textContent, '楚汉争霸');
    assert.ok(el.querySelector('.htl-status-year').textContent.indexOf('公元前') === 0);
    assert.strictEqual(el.querySelectorAll('.htl-ev.on').length, 26);
  });

  const move = new Ev('pointermove'); move.clientX = 480; move.pointerId = 1;
  hit.dispatchEvent(move);
  await tick();
  ok('pointermove(480px) → 实时切至汉末三国中点（232 年）', () => {
    assert.strictEqual(el.querySelector('.htl-status-era').textContent, '汉末三国');
    assert.strictEqual(el.querySelector('.htl-status-year').textContent, '公元 232 年');
    const left = parseFloat(el.querySelector('.htl-knob').style.left);
    approx(left, 50, 0.02);
  });
  ok('拖动过程中根节点带 dragging 类（禁入场动画）', () => {
    assert.strictEqual(el.classList.contains('dragging'), true);
  });

  const up = new Ev('pointerup'); up.pointerId = 1;
  hit.dispatchEvent(up);
  await tick();
  ok('pointerup → dragging 类移除', () => {
    assert.strictEqual(el.classList.contains('dragging'), false);
  });

  console.log('\n== 键盘操作 ==');
  axis.getBoundingClientRect = axis.getBoundingClientRect; // 已桩
  const k1 = new Ev('keydown'); k1.key = 'ArrowRight';
  const beforeYear = el.querySelector('.htl-status-year').textContent;
  axis.dispatchEvent(k1);
  ok('ArrowRight 微调后年份前进（232 → 233）', () => {
    const after = el.querySelector('.htl-status-year').textContent;
    assert.notStrictEqual(after, beforeYear);
  });
  const k2 = new Ev('keydown'); k2.key = 'Home';
  axis.dispatchEvent(k2);
  await tick(450);
  ok('Home → 跳至先秦段开端', () => {
    assert.strictEqual(el.querySelector('.htl-status-era').textContent, '先秦');
    const left = parseFloat(el.querySelector('.htl-knob').style.left);
    approx(left, 0, 0.001);
  });

  console.log('\n== 筹备时期（先秦）状态 ==');
  ok('筹备时期：入口禁用、徽标为筹备中', () => {
    assert.strictEqual(el.querySelector('.htl-status-tag').textContent, '筹备中');
    const link = el.querySelector('.htl-era-link');
    assert.strictEqual(link.classList.contains('disabled'), true);
    assert.strictEqual(link.getAttribute('href'), null);
    assert.strictEqual(link.textContent, '地图筹备中');
  });
  ok('先秦 11 张卡片显示', () => {
    assert.strictEqual(el.querySelectorAll('.htl-ev.on').length, 11);
    el.querySelectorAll('.htl-ev.on').forEach((c) => assert.strictEqual(c.getAttribute('data-era'), '0'));
  });

  console.log('\n== 程序化定位与销毁 ==');
  tl.setYear(200, 'han-san-guo');
  await tick(450);
  ok('setYear(200) → 汉末三国 · 公元 200 年，7 个 past', () => {
    assert.strictEqual(el.querySelector('.htl-status-year').textContent, '公元 200 年');
    const col3 = el.querySelectorAll('.htl-col')[2];
    assert.strictEqual(col3.querySelectorAll('.htl-pt.past').length, 7);
  });

  ok('切换回先秦再回三国：进度状态正确重算（无残留）', () => {
    tl.setFrac(0);
    assert.strictEqual(el.querySelectorAll('.htl-ev.on').length, 11);
    tl.setFrac(0.45);
    assert.strictEqual(el.querySelectorAll('.htl-ev.on').length, 34);
    const col3 = el.querySelectorAll('.htl-col')[2];
    assert.strictEqual(col3.querySelectorAll('.htl-pt.past').length, 11);
    assert.strictEqual(col3.querySelectorAll('.htl-pt.future').length, 23);
  });

  ok('destroy() 清空根容器', () => {
    tl.destroy();
    assert.strictEqual(el.innerHTML, '');
    assert.strictEqual(el.classList.contains('htl'), false);
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
