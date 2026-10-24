// 地标重建 · 冒烟测试（真代码整跑）
// 方法：从页面提取「地标数据结构 + rebuild 函数」连续代码段，在【严格 Leaflet 桩】里真跑：
//   - 桩 map.removeLayer 对 undefined/非图层 主动抛错（模拟 Leaflet 真实行为）
//   - 非合并 / 合并 两种模式各跑一遍 rebuild，断言不抛异常、refs 收集数量正确
// 背景：2026-10-13 五类扩展（battle+event）时 tkLayer/tkLabelLayer 漏加 event 键，
//       rebuildTK 首段清理即抛错，脚本中断 → 时间轴初始化未执行（页面时间轴"消失"）。
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

/* 真实数据 */
global.window = {};
require(path.join(ROOT, '汉末三国', 'three_kingdoms_sites.js'));
const TK = global.window.THREE_KINGDOM_SITES;
global.window = {};
require(path.join(ROOT, '楚汉争霸', 'chu_han_sites.js'));
const CH = global.window.CHU_HAN_SITES;
global.window = {};
require(path.join(ROOT, '魏晋南北朝', 'wei_jin_sites.js'));
const WJ = global.window.WEI_JIN_SITES;

let passed = 0;
const failures = [];
function ok(name, fn) {
  try { fn(); passed++; console.log('  \u2713 ' + name); }
  catch (e) { failures.push(name); console.error('  \u2717 ' + name + '\n      ' + e.message); }
}

/* 严格 Leaflet 桩：行为对齐 Leaflet —— 对非图层参数会抛（这正是本测试要抓的） */
function makeStrictL() {
  return {
    layerGroup: function () { return { addLayer: function () {}, clearLayers: function () {}, addTo: function () { return this; } }; },
    marker: function () { return { on: function () { return this; }, getElement: function () { return { style: {}, querySelector: function () { return null; } }; } }; },
    divIcon: function (o) { return o; }
  };
}
function makeStrictMap() {
  return {
    removeLayer: function (l) {
      if (!l || typeof l !== 'object' || typeof l.addLayer !== 'function') {
        throw new TypeError('map.removeLayer(非图层: ' + String(l) + ')：按类图层表可能缺键（如 event）');
      }
    }
  };
}

function runPage(spec) {
  console.log('\n═══ ' + spec.lbl + ' ═══');
  const html = fs.readFileSync(path.join(ROOT, spec.file), 'utf8');
  const i = html.indexOf(spec.startMark);
  const j = html.indexOf(spec.endMark, i);
  ok('提取「数据结构 + rebuild」代码段', () => {
    assert.ok(i >= 0, '起点未命中: ' + spec.startMark);
    assert.ok(j > i, '终点未命中: ' + spec.endMark);
  });
  const code = html.slice(i, j);

  const cbs = {};
  const doc = { getElementById: function (id) { if (!cbs[id]) cbs[id] = { checked: false }; return cbs[id]; } };
  const win = {};
  win[spec.dataName] = spec.data;

  const ret = new Function(
    'window', 'document', 'L', 'map', 'showInfo', 'scheduleCollision', 'parseTimelineYear',
    code + '\nreturn { rebuild: ' + spec.rebuildFn + ', refs: battleTimeRefs, layer: ' + spec.layerVar + ' };'
  )(win, doc, makeStrictL(), makeStrictMap(), function () {}, function () {}, function (v) {
    const m = String(v == null ? '' : v).match(/\d+/);
    return m ? parseInt(m[0], 10) : null;
  });

  ok('按类图层表含 event 键', () => {
    assert.ok(ret.layer, '未取到 ' + spec.layerVar);
    assert.ok(ret.layer.event, spec.layerVar + '.event 缺失 → rebuild 首段清理即抛错');
  });

  /* 场景 1：非合并模式，勾选 city + battle + event */
  Object.keys(cbs).forEach(function (k) { delete cbs[k]; });
  cbs[spec.cbPrefix + 'city'] = { checked: true };
  cbs[spec.cbPrefix + 'battle'] = { checked: true };
  cbs[spec.cbPrefix + 'event'] = { checked: true };
  cbs[spec.cbPrefix + 'merge'] = { checked: false };
  let err1 = null;
  try { ret.rebuild(); } catch (e) { err1 = e; }
  ok('rebuild（非合并模式）不抛异常', () => assert.strictEqual(err1, null, err1 && err1.message));
  ok('refs 收集 battle+event 共 ' + spec.expectCount + ' 条', () => {
    assert.strictEqual(ret.refs.length, spec.expectCount);
    assert.ok(ret.refs.version >= 1);
  });

  /* 场景 2：合并模式 */
  cbs[spec.cbPrefix + 'merge'].checked = true;
  let err2 = null;
  try { ret.rebuild(); } catch (e) { err2 = e; }
  ok('rebuild（合并模式）不抛异常且含融合组收集', () => {
    assert.strictEqual(err2, null, err2 && err2.message);
    assert.ok(ret.refs.length >= 1, 'refs 为空');
    assert.ok(ret.refs.some(function (r) { return r.fuse; }), '无 fuse 项');
  });

  /* 场景 3：全部取消勾选（重建为空）也不应抛 */
  Object.keys(cbs).forEach(function (k) { cbs[k].checked = false; });
  let err3 = null;
  try { ret.rebuild(); } catch (e) { err3 = e; }
  ok('rebuild（全未勾选）不抛异常且 refs 为空', () => {
    assert.strictEqual(err3, null, err3 && err3.message);
    assert.strictEqual(ret.refs.length, 0);
  });
}

runPage({
  lbl: '汉末三国页',
  file: path.join('汉末三国', 'index.html'),
  data: TK, dataName: 'THREE_KINGDOM_SITES',
  startMark: 'const tkMeta = {',
  endMark: "\n['city','pass','ford','battle','event','merge']",
  rebuildFn: 'rebuildTK', layerVar: 'tkLayer', cbPrefix: 'cb-tk-',
  expectCount: 34 + 13
});
runPage({
  lbl: '楚汉争霸页',
  file: path.join('楚汉争霸', 'index.html'),
  data: CH, dataName: 'CHU_HAN_SITES',
  startMark: 'const chMeta = {',
  endMark: "\n['city','pass','ford','battle','event','merge']",
  rebuildFn: 'rebuildCH', layerVar: 'chLayer', cbPrefix: 'cb-ch-',
  expectCount: 26 + 8
});
runPage({
  lbl: '魏晋南北朝页',
  file: path.join('魏晋南北朝', 'index.html'),
  data: WJ, dataName: 'WEI_JIN_SITES',
  startMark: 'const wjMeta = {',
  endMark: "\n['city','pass','ford','battle','event','merge']",
  rebuildFn: 'rebuildWj', layerVar: 'wjLayer', cbPrefix: 'cb-wj-',
  expectCount: 26 + 15
});

console.log('\n────────────────────────────');
if (failures.length) {
  console.error('✗ 失败 ' + failures.length + ' 项 / 共 ' + (passed + failures.length) + ' 项');
  process.exit(1);
} else {
  console.log('✓ 全部通过：' + passed + ' 项');
}
