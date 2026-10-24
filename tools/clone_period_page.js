#!/usr/bin/env node
/*
 * 时期页克隆：从一个已上线时期页生成另一个时期的 index.html
 * ------------------------------------------------------------------
 * 页面骨架（图层/碰撞/时间轴/面板联动）在所有时期完全一致，只有「前缀家族」和
 * 「数据文件 / 文案 / 计数 / 路线开关 / 时间轴参数」不同。手工改 1600+ 行极易漏，
 * 故用脚本做确定性替换，每条规则不命中就报错退出（避免静默半成品）。
 *
 * 用法：node tools/clone_period_page.js [periodKey]   # 默认 weijin
 * 说明：源页必须与目标时期「五类地标 + 事件时间轴」结构一致（楚汉页是当前模板）。
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');

const PERIODS = {
  weijin: {
    src: '楚汉争霸/index.html',
    dst: '魏晋南北朝/index.html',
    // ── 1. 标识符重命名（顺序敏感：长的在前，避免前缀互相吃掉）──
    tokens: [
      ['CHU_HAN_STATES', 'WEI_JIN_STATES'],
      ['CHU_HAN_SITES', 'WEI_JIN_SITES'],
      ['CHU_HAN_ROUTES', 'WEI_JIN_ROUTES'],
      ['chu_han_states.js', 'wei_jin_states.js'],
      ['chu_han_sites.js', 'wei_jin_sites.js'],
      ['chu_han_routes.js', 'wei_jin_routes.js'],
      ['cb-chr-', 'cb-wjr-'],
      ['cb-ch-', 'cb-wj-'],
      ['__syncChMaster', '__syncWjMaster'],
      ['chMergeLabelLayer', 'wjMergeLabelLayer'],
      ['chMergeLayer', 'wjMergeLayer'],
      ['chLabelLayer', 'wjLabelLayer'],
      ['chSeatLabelLayer', 'wjSeatLabelLayer'],
      ['chStateLabelLayer', 'wjStateLabelLayer'],
      ['chBoundaryLayer', 'wjBoundaryLayer'],
      ['chCapitalLayer', 'wjCapitalLayer'],
      ['chSeatLayer', 'wjSeatLayer'],
      ['chLayer', 'wjLayer'],
      ['chTypeOrder', 'wjTypeOrder'],
      ['chIconSVG', 'wjIconSVG'],
      ['chFusedIcon', 'wjFusedIcon'],
      ['chGlyph', 'wjGlyph'],
      ['chMeta', 'wjMeta'],
      ['chTip', 'wjTip'],
      ['rebuildCH', 'rebuildWj'],
      ['showChBnd', 'showWjBnd'],
      ['hideChBnd', 'hideWjBnd'],
      ['showChSeat', 'showWjSeat'],
      ['hideChSeat', 'hideWjSeat'],
      ['CH_FUSE_DEG', 'WJ_FUSE_DEG'],
      ['_chD', '_wjD'],
      ['chrLineLayer', 'wjrLineLayer'],
      ['chrChipLayer', 'wjrChipLayer'],
      ['chstate-label', 'wjstate-label'],
      ['chseat-label', 'wjseat-label'],
      ['ch-label', 'wj-label'],
      ['chr-chip', 'wjr-chip'],
      ['chr-badge', 'wjr-badge'],
      ['chr-label', 'wjr-label'],
      ['chr-nodedot', 'wjr-nodedot'],
      ['chr-node', 'wjr-node'],
      ["className:'chpt'", "className:'wjpt'"],
      ['data-chid', 'data-wjid'],
      ['chAll', 'wjAll'],
      ['chSubs', 'wjSubs']
    ],
    // ── 2. 文案：先整体换朝代名，再逐条修细节 ──
    text: [
      ['楚汉', '魏晋南北朝'],
      ['<title>中国历史地形图</title>', '<title>中国历史地形图 · 魏晋南北朝</title>'],
      ['魏晋南北朝十八国图层标签', '魏晋南北朝疆域标签'],
      ['/* ── 魏晋南北朝战争路线 ── */',
       '/* ── 南北朝战争路线 ── */\n.rgroup { font-size:10px; color:#8fa7c0; letter-spacing:.04em; margin:6px 0 1px; }\n.eratable { font-size:10px; line-height:1.7; color:#bcd; }\n.erabar { display:flex; align-items:center; gap:6px; margin:2px 0 1px; }\n.erabar input[type=range] { flex:1; min-width:56px; }\n.erabtn { background:rgba(30,44,64,.9); color:#cfe0f0; border:1px solid #34507a; border-radius:4px; padding:0 5px; font-size:11px; line-height:16px; cursor:pointer; }\n.erabtn:hover { border-color:#ffd479; color:#ffd479; }\n.eraread { font-size:10px; color:#ffd479; margin-bottom:3px; }'],
      // 疆域下方：断面纪年滑条（◀ ▶ + 滑条 + 读数）
      ['      <label><input type="checkbox" id="cb-wj-bnd"> 疆域</label>',
       '      <label><input type="checkbox" id="cb-wj-bnd"> 疆域</label>\n' +
       '      <div class="erabar">\n' +
       '        <button id="era-prev" type="button" class="erabtn" title="上一个断面">◀</button>\n' +
       '        <input type="range" id="era-range" min="0" max="6" step="1" value="4" aria-label="疆域纪年">\n' +
       '        <button id="era-next" type="button" class="erabtn" title="下一个断面">▶</button>\n' +
       '      </div>\n' +
       '      <div id="era-readout" class="eraread">546 年 · 东魏｜西魏｜梁</div>\n' +
       '      <div class="eraread" style="opacity:.55;margin-top:-2px">↕ 亦可拖动或点击底部时间轴的年份刻度</div>'],
      // 底部时间轴：拖动时顺带把疆域切到对应年份（「全部」态不动）
      ['    onChange: function(st){\n      if(!st.all) ensureTimelineLayers();\n      applyBattleTimeFilter(st);\n    },',
       '    onChange: function(st){\n      if(!st.all) ensureTimelineLayers();\n      if(!st.all && window.__setEraYear) window.__setEraYear(st.year);\n      applyBattleTimeFilter(st);\n    },'],
      ['据《中国历史地图集》秦楚之际通行方案示意性重建（非精确数字化）',
       '据《中国历史地图集》南北朝后期（546 年 东魏·西魏·梁）通行方案示意性重建（非精确数字化）'],
      ['魏晋南北朝战争路线', '南北朝战争路线'],
      ['魏晋南北朝争霸', '魏晋南北朝'],
      ['// ── 2g) 南北朝战争路线（六条路线）',
       '// ── 2g) 南北朝战争路线（十八条，按政权与年代分组）'],
      ['// ── 2f) 魏晋南北朝关键地点', '// ── 2f) 魏晋南北朝关键地点'],
      // 面板底部：政权年表（静态说明，让「各朝均有覆盖」可核对）
      ['  <div class="btnbar">\n    <button id="btn-all-on"',
        '  <div class="citysep">\n' +
        '    <div style="font-weight:bold;margin-bottom:2px;">政权年表（220–589）</div>\n' +
        '    <div class="eratable">\n' +
        '      三国 · 魏 220–266 ／ 蜀 221–263 ／ 吴 222–280<br>\n' +
        '      西晋 266–316 · 东晋 317–420 · 十六国 304–439<br>\n' +
        '      南朝 · 宋 420–479 ／ 齐 479–502 ／ 梁 502–557 ／ 陈 557–589<br>\n' +
        '      北朝 · 北魏 386–534 ／ 东魏 534–550 ／ 西魏 535–557 ／ 北齐 550–577 ／ 北周 557–581<br>\n' +
        '      吐谷浑 · 柔然（见疆域层） · 隋 581–589\n' +
        '    </div>\n' +
        '  </div>\n' +
        '  <div class="btnbar">\n    <button id="btn-all-on"']
    ],
    // ── 2b. 整块替换：疆域 2d 段换成「多断面渲染器」（模板见 tools/templates/）
    blocks: [
      { start: '// ── 2d)', end: '// ── 2e)', file: 'tools/templates/wj_era_block.js' }
    ],
    // ── 3. 面板计数（必须与数据文件实际长度一致）──
    counts: [['城池', 34], ['关隘', 10], ['津渡', 6], ['战役', 26], ['大事记', 20]],
    // ── 4. 路线开关：分组 + 编号 + 面板文案（组按年代先后排列）──
    routes: {
      title: '南北朝战争路线',
      groups: [
        ['三国 · 西晋（220–316）', [
          [1, '①魏灭蜀 263'],
          [2, '②晋灭吴 279-280'],
          [3, '③永嘉之乱 304-316']
        ]],
        ['十六国 · 东晋（304–420）', [
          [4, '④石勒灭前赵 328-329'],
          [5, '⑤桓温灭成汉 347'],
          [6, '⑥桓温北伐 354-369'],
          [7, '⑦淝水之战 383'],
          [8, '⑧参合陂·北魏开国 395-439'],
          [9, '⑨刘裕北伐 409-417']
        ]],
        ['南朝 · 北魏（420–534）', [
          [10, '⑩元嘉北伐 430-451'],
          [11, '⑪萧衍代齐 501-502'],
          [12, '⑫钟离之战 507'],
          [13, '⑬陈庆之入洛 529']
        ]],
        ['东西魏 · 周齐 · 梁陈（534–581）', [
          [14, '⑭沙苑·玉壁 537-546'],
          [15, '⑮侯景之乱 547-552'],
          [16, '⑯西魏取蜀 553-554'],
          [17, '⑰北周灭北齐 575-577']
        ]],
        ['隋（581–589）', [
          [18, '⑱隋灭陈 588-589']
        ]]
      ]
    },
    // ── 5. 时间轴：公元纪年（bc=false）+ 固定时期跨度 ──
    timeline: { bc: false, minYear: 220, maxYear: 589 },
    // ── 6. 外链版本戳 ──
    stamps: {
      'wei_jin_states.js': '2026102501',
      'wei_jin_sites.js': '2026102501',
      'wei_jin_routes.js': '2026102501'
    }
  }
};

const key = process.argv[2] || 'weijin';
const P = PERIODS[key];
if (!P) { console.error('未知 periodKey: ' + key); process.exit(2); }

const srcPath = path.join(ROOT, P.src);
const dstPath = path.join(ROOT, P.dst);
let html = fs.readFileSync(srcPath, 'utf8');

const must = (cond, msg) => { if (!cond) { console.error('✗ 规则未命中：' + msg); process.exit(1); } };

// 1) tokens
P.tokens.forEach(([a, b]) => {
  const n = html.split(a).length - 1;
  must(n > 0, 'token ' + a);
  html = html.split(a).join(b);
});
// 1b) blocks：按起止标记整块替换（内容来自模板文件）
(P.blocks || []).forEach(b => {
  const i = html.indexOf(b.start), j = html.indexOf(b.end, i + 1);
  must(i >= 0 && j > i, 'block ' + b.start + ' … ' + b.end);
  const tpl = fs.readFileSync(path.join(ROOT, b.file), 'utf8');
  html = html.slice(0, i) + tpl + html.slice(j);
  console.log('  整块替换 ' + b.start + ' … ' + b.end + '（' + tpl.split('\n').length + ' 行模板）');
});
// 2) text
P.text.forEach(([a, b]) => {
  const n = html.split(a).length - 1;
  must(n > 0, 'text ' + a.slice(0, 40));
  html = html.split(a).join(b);
});
// 3) counts
P.counts.forEach(([label, n]) => {
  const rx = new RegExp('(' + label + '（)(\\d+)(）)');
  must(rx.test(html), 'count ' + label);
  html = html.replace(rx, (m, p1, old, p3) => {
    console.log('  计数 ' + label + '：' + old + ' → ' + n);
    return p1 + n + p3;
  });
});
// 4) routes：整块替换（分组 + 编号）
{
  const re = /[ \t]*<label><input type="checkbox" id="cb-wjr-1">[\s\S]*?id="cb-wjr-6">[^<]*<\/label>/;
  must(re.test(html), 'route label block');
  const lines = [];
  P.routes.groups.forEach(([title, items]) => {
    lines.push('          <div class="rgroup">' + title + '</div>');
    items.forEach(([i, t]) =>
      lines.push('          <label><input type="checkbox" id="cb-wjr-' + i + '"> ' + t + '</label>'));
  });
  html = html.replace(re, lines.join('\n'));
  const ids = [].concat.apply([], P.routes.groups.map(g => g[1].map(x => x[0])));
  const oldSubs = "const subs = ['cb-wjr-1','cb-wjr-2','cb-wjr-3','cb-wjr-4','cb-wjr-5','cb-wjr-6'];";
  must(html.includes(oldSubs), 'subs array');
  html = html.replace(oldSubs, 'const subs = [' + ids.map(i => "'cb-wjr-" + i + "'").join(',') + '];');
  console.log('  路线开关：6 → ' + ids.length + ' 条（' + P.routes.groups.length + ' 组）');
}
// 5) timeline
{
  must(html.includes('const TL_BC = true;'), 'TL_BC');
  html = html.replace('const TL_BC = true;', 'const TL_BC = ' + P.timeline.bc + ';');
  must(html.includes('    bc: true,\n'), 'timeline bc opt');
  html = html.replace('    bc: true,\n',
    '    bc: ' + P.timeline.bc + ',\n    minYear: ' + P.timeline.minYear + ',\n    maxYear: ' + P.timeline.maxYear + ',\n' +
    '    marks: (window.WEI_JIN_STATES && window.WEI_JIN_STATES.snapshots || []).map(function(x){ return { year: x.year, name: x.name, short: String(x.year) }; }),\n');
  console.log('  时间轴：bc=' + P.timeline.bc + '，跨度 ' + P.timeline.minYear + '–' + P.timeline.maxYear);
}
// 6) script stamps
Object.keys(P.stamps).forEach(f => {
  const re = new RegExp('src="' + f.replace('.', '\\.') + '\\?v=\\d+"');
  must(re.test(html), 'script tag ' + f);
  html = html.replace(re, 'src="' + f + '?v=' + P.stamps[f] + '"');
});

fs.mkdirSync(path.dirname(dstPath), { recursive: true });
fs.writeFileSync(dstPath, html, 'utf8');
console.log('✓ 生成 ' + P.dst + '（' + html.split('\n').length + ' 行，' + Buffer.byteLength(html) + ' 字节）');

// 7) 残留自检
const leftovers = ['cb-ch', 'cb-chr', 'CHU_HAN', 'chMeta', 'chLayer', 'rebuildCH', '楚汉', 'data-chid']
  .filter(t => html.includes(t));
if (leftovers.length) { console.error('✗ 残留旧标识：' + leftovers.join(', ')); process.exit(1); }
console.log('✓ 无旧标识残留');
