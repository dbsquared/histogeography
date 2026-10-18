// 地图时间轴控件 v2 · 纯逻辑测试（Node，无需浏览器）
// 覆盖：年份解析 / 事件构建（真实数据兼容）/ 时间窗计算 / 二分区间 / 两行布局 / 格式化
'use strict';

const assert = require('assert');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const T = require(path.join(ROOT, 'timeline', 'map_timeline.js'));
const U = T.Util;

/* 真实地图数据（页面脚本是 window.X = {...}，Node 里补 window 后加载） */
global.window = {};
require(path.join(ROOT, '楚汉争霸', 'chu_han_sites.js'));
require(path.join(ROOT, '汉末三国', 'three_kingdoms_sites.js'));
const CH = global.window.CHU_HAN_SITES;
const TK = global.window.THREE_KINGDOM_SITES;

let passed = 0;
const failures = [];
function ok(name, fn) {
  try { fn(); passed++; console.log('  \u2713 ' + name); }
  catch (e) { failures.push(name); console.error('  \u2717 ' + name + '\n      ' + e.message); }
}
function approx(a, b, eps) { eps = eps || 1e-9; assert.ok(Math.abs(a - b) < eps, a + ' vs ' + b); }

console.log('\n== 年份解析 ==');
ok("parseYearNum('208') = 208", () => assert.strictEqual(U.parseYearNum('208'), 208));
ok("parseYearNum('208-209') = 208（取起始年）", () => assert.strictEqual(U.parseYearNum('208-209'), 208));
ok("parseYearNum('206-205') = 206", () => assert.strictEqual(U.parseYearNum('206-205'), 206));
ok('parseYearNum(null/空) = null', () => {
  assert.strictEqual(U.parseYearNum(null), null);
  assert.strictEqual(U.parseYearNum(''), null);
});

console.log('\n== 格式化 ==');
ok("fmtYear(-209) = '前209 年'", () => assert.strictEqual(U.fmtYear(-209), '前209 年'));
ok("fmtYear(208) = '208 年'", () => assert.strictEqual(U.fmtYear(208), '208 年'));

console.log('\n== 事件构建（真实数据兼容） ==');
ok('汉末三国战役 34 条解析，范围 [190, 280]', () => {
  const evs = U.buildEvents(TK.battle, false);
  assert.strictEqual(evs.length, 34);
  assert.strictEqual(evs[0].year, 190);
  assert.strictEqual(evs[evs.length - 1].year, 280);
});
ok('楚汉 26 条解析，bc 模式范围 [-209, -202]', () => {
  const evs = U.buildEvents(CH.battle, true);
  assert.strictEqual(evs.length, 26);
  assert.strictEqual(evs[0].year, -209);
  assert.strictEqual(evs[evs.length - 1].year, -202);
});
ok('缺 year 的条目被跳过', () => {
  const evs = U.buildEvents([{ name: '无年份' }, { name: '有', year: '200' }], false);
  assert.strictEqual(evs.length, 1);
});

console.log('\n== 时间窗半宽（自适应） ==');
ok('汉末（span 90 / n 48）≈ 5.625 年', () => approx(U.computeHalfWin(90, 48), 5.625));
ok('楚汉（span 7 / n 34）≈ 0.6176 年', () => approx(U.computeHalfWin(7, 34), 7 / 34 * 3));
ok('稀疏数据触发上界 clamp（span*0.34）', () => approx(U.computeHalfWin(100, 1), 34));
ok('密集数据触发下界 clamp（span*0.02）', () => approx(U.computeHalfWin(100, 1000), 2));
ok('span=0 兜底 = 1', () => assert.strictEqual(U.computeHalfWin(0, 5), 1));

console.log('\n== 时间窗区间计数（二分） ==');
const sg = U.buildEvents(TK.battle, false);
const chev = U.buildEvents(CH.battle, true);
ok('windowCount(汉末, 200, 210) = 6（200×2/202/208×3）', () => {
  assert.strictEqual(U.windowCount(sg, 200, 210), 6);
});
ok('windowCount(汉末, 250, 260) = 2（洮西/寿春）', () => {
  assert.strictEqual(U.windowCount(sg, 250, 260), 2);
});
ok('windowCount(楚汉, -210, -205) = 14', () => {
  assert.strictEqual(U.windowCount(chev, -210, -205), 14);
});
ok('windowCount 空区间 = 0', () => {
  assert.strictEqual(U.windowCount(sg, 181, 184), 0);
});
ok('lowerBound/upperBound 边界正确（含端点）', () => {
  assert.strictEqual(U.lowerBound(sg, 208), 8);          // 190..202 共 8 条 < 208
  assert.strictEqual(U.upperBound(sg, 208), 11);         // 含 208 的三条
});
ok('窗口覆盖全轴时计数 = 全部', () => {
  assert.strictEqual(U.windowCount(sg, 0, 999), sg.length);
});

console.log('\n== 事件点布局 ==');
ok('汉末 34 点：t∈[0,1]，row∈{0,1}，同年散开', () => {
  const dots = U.layoutDots(sg, 190, 280);
  assert.strictEqual(dots.length, 34);
  dots.forEach((d) => {
    assert.ok(d.t >= 0 && d.t <= 1);
    assert.ok(d.row === 0 || d.row === 1);
  });
  let same = 0;
  for (let i = 1; i < sg.length; i++) {
    if (sg[i].year === sg[i - 1].year) {
      same++;
      assert.notStrictEqual(dots[i].t, dots[i - 1].t);
    }
  }
  assert.ok(same >= 2);
});

console.log('\n────────────────────────────');
if (failures.length) {
  console.error(`✗ 失败 ${failures.length} 项 / 共 ${passed + failures.length} 项`);
  process.exit(1);
} else {
  console.log(`✓ 全部通过：${passed} 项`);
}
