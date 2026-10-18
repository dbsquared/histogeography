// 地图时间轴 · 跨层冒烟测试（真代码整跑）
// 方法：从两个地图页提取「时间轴胶水代码」原文，在 linkedom 桩环境里用真实数据执行，
//       再用真控件真交互驱动，断言地图引用元素（marker/label）的显示与隐藏。
// 专测跨层一致性：控件值域（bc 正负号）↔ 页面引用表值域 ↔ 过滤语义（时间窗）。
// 背景：楚汉页曾因「parseTimelineYear 未做公元前转换」导致全量误隐藏（2026-10-13）。
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const WS = 'C:/Users/dbsqu/.workbuddy/binaries/node/workspace/node_modules';
const { parseHTML } = require(WS + '/linkedom');

const ROOT = path.join(__dirname, '..');
const T = require(path.join(ROOT, 'timeline', 'map_timeline.js'));

/* 真实数据（页面脚本是 window.X = {...}，Node 里补 window 后加载） */
global.window = {};
require(path.join(ROOT, '汉末三国', 'three_kingdoms_sites.js'));
const TK = global.window.THREE_KINGDOM_SITES;
global.window = {};
require(path.join(ROOT, '楚汉争霸', 'chu_han_sites.js'));
const CH = global.window.CHU_HAN_SITES;

let passed = 0;
const failures = [];
function ok(name, fn) {
  try { fn(); passed++; console.log('  \u2713 ' + name); }
  catch (e) { failures.push(name); console.error('  \u2717 ' + name + '\n      ' + e.message); }
}

const CB_STUBS = '<input type="checkbox" id="cb-tk-battle"><input type="checkbox" id="cb-tk-event">' +
                 '<input type="checkbox" id="cb-ch-battle"><input type="checkbox" id="cb-ch-event">';

function runPage(spec) {
  console.log('\n═══ ' + spec.lbl + ' ═══');
  const html = fs.readFileSync(path.join(ROOT, spec.file), 'utf8');

  /* ── 1) 提取胶水代码 ── */
  const i = html.indexOf('// 7) ');
  const j = html.lastIndexOf('scheduleCollision();');
  ok('提取到时间轴胶水代码', () => {
    assert.ok(i >= 0, '找不到胶水起始锚点「// 7) 」');
    assert.ok(j > i, '找不到胶水结束锚点');
  });
  const glue = html.slice(i, j);

  /* ── 2) 静态断言（跨层一致性） ── */
  ok('胶水定义 TL_BC 且与控件 bc 参数一致', () => {
    const m1 = glue.match(/const TL_BC\s*=\s*(true|false)/);
    const m2 = glue.match(/bc:\s*(true|false)/);
    assert.ok(m1, '缺少 TL_BC 常量（公元前值域转换）');
    assert.ok(m2, '找不到控件 bc 参数');
    assert.strictEqual(m1[1], m2[1], 'TL_BC=' + m1[1] + ' 与 bc:' + m2[1] + ' 不一致');
    assert.strictEqual(m1[1], String(spec.expectBC), '本页应 ' + (spec.expectBC ? '为' : '不为') + '公元前模式');
  });
  ok('refs 收集涵盖 battle 与 event（3 分支）', () => {
    const c1 = (html.match(/cat==='battle'\|\|cat==='event'/g) || []).length;
    const c2 = (html.match(/s\.cat==='battle'\|\|s\.cat==='event'/g) || []).length;
    const c3 = (html.match(/const _evg = g\.filter\(x=>x\.cat==='event'\)/g) || []).length;
    assert.strictEqual(c1, 1, '非合并分支未涵盖 event');
    assert.strictEqual(c2, 1, '孤立站点分支未涵盖 event');
    assert.strictEqual(c3, 1, '融合组分支缺 event 独立收集');
  });
  ok('融合组 event 有独立图形类（tkf-event）', () => {
    assert.ok((html.match(/tkf-event/g) || []).length >= 2);
  });

  /* ── 3) 桩环境执行真胶水 ── */
  const { document, window } = parseHTML('<!DOCTYPE html><html><body><div id="timebar"></div>' + CB_STUBS + '</body></html>');
  window.MapTimeline = T.MapTimeline;

  const refs = [];
  refs.version = 0;
  const byName = {};

  const ret = new Function(
    'document', 'window', 'Event', '_tkD', '_chD', 'battleTimeRefs', 'scheduleCollision', 'MapTimeline',
    glue +
    '\nreturn {' +
    ' tl: window.__eventTimebar || window.__battleTimebar || null,' +
    ' parse: (typeof parseTimelineYear === "function" ? parseTimelineYear : null)' +
    '};'
  )(document, window, window.Event, spec.data, spec.data, refs, function () {}, T.MapTimeline);

  ok('胶水初始化未抛异常且控件已创建', () => assert.ok(ret.tl, 'initEventTimebar 未成功初始化'));
  ok('页面 parse 的符号语义正确（bc 转换生效）', () => {
    assert.ok(ret.parse, '缺少 parseTimelineYear');
    const v = ret.parse('209');
    if (spec.expectBC) assert.ok(v < 0, "'209' 应转负，实际 " + v);
    else assert.ok(v > 0, "'209' 应保持正，实际 " + v);
  });

  /* ── 4) 用真 parse 填引用表（模拟 rebuild 收集） ── */
  const events = (spec.data.battle || []).concat(spec.data.event || []);
  events.forEach((f) => {
    const y = ret.parse(f.year);
    if (y == null) return;
    const mEl = document.createElement('div');
    const lEl = document.createElement('div');
    refs.push({ ymin: y, marker: { getElement: () => mEl }, label: { getElement: () => lEl } });
    byName[f.name] = { mEl: mEl, lEl: lEl };
  });
  refs.version = 1;

  function vis(name) {
    const r = byName[name];
    return r ? r.mEl.style.display !== 'none' : null;
  }
  function setY(y) {
    if (ret.tl.setYear) ret.tl.setYear(y);      /* v2 */
    else ret.tl.setValue(y);                     /* v1 兼容 */
  }

  /* ── 5) 场景断言 ── */
  spec.scenes.forEach((sc) => {
    setY(sc.year);
    ok('[场景] ' + sc.lbl, () => {
      sc.visible.forEach((n) => assert.strictEqual(vis(n), true, '「' + n + '」应可见'));
      sc.hidden.forEach((n) => assert.strictEqual(vis(n), false, '「' + n + '」应隐藏'));
    });
  });

  /* ── 6) 全部复位（v2 专有） ── */
  if (ret.tl.showAll) {
    ret.tl.showAll();
    ok('[复位] 全部显示恢复所有事件', () => {
      const sample = spec.scenes[0];
      sample.hidden.forEach((n) => assert.strictEqual(vis(n), true, '复位后「' + n + '」应可见'));
    });
  } else {
    console.log('  \u2013 [复位] v1 无全部态，跳过');
  }

  return ret;
}

/* ════ 汉末三国 ════ */
runPage({
  lbl: '汉末三国页',
  file: path.join('汉末三国', 'index.html'),
  data: TK,
  expectBC: false,
  scenes: [
    {
      lbl: '拖到 208 年：赤壁/三顾茅庐可见，190 虎牢关/220 曹丕/234 五丈原隐藏（时间窗）',
      year: 208,
      visible: ['赤壁之战', '三顾茅庐·隆中对'],
      hidden: ['虎牢关之战', '五丈原之战', '曹丕受禅·汉祚终']
    },
    {
      lbl: '拖到 255 年：洮西/寿春可见，190 隐藏',
      year: 255,
      visible: ['洮西/狄道之战', '寿春之战'],
      hidden: ['虎牢关之战']
    }
  ]
});

/* ════ 楚汉争霸 ════ */
runPage({
  lbl: '楚汉争霸页',
  file: path.join('楚汉争霸', 'index.html'),
  data: CH,
  expectBC: true,
  scenes: [
    {
      lbl: '拖到前205 年：彭城之战可见，前209 大泽乡/前202 乌江隐藏',
      year: -205,
      visible: ['彭城之战'],
      hidden: ['大泽乡起义', '乌江自刎']
    },
    {
      lbl: '拖到前206 年：鸿门宴/韩信拜将可见，前209 大泽乡/前202 刘邦称帝隐藏（时间窗）',
      year: -206,
      visible: ['鸿门宴', '韩信拜将·登坛'],
      hidden: ['大泽乡起义', '刘邦称帝·汉室肇建']
    }
  ]
});

console.log('\n────────────────────────────');
if (failures.length) {
  console.error('✗ 失败 ' + failures.length + ' 项 / 共 ' + (passed + failures.length) + ' 项');
  process.exit(1);
} else {
  console.log('✓ 全部通过：' + passed + ' 项');
}
