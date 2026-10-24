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
      ['/* ── 魏晋南北朝战争路线 ── */', '/* ── 南北朝战争路线 ── */'],
      ['据《中国历史地图集》秦楚之际通行方案示意性重建（非精确数字化）',
       '据《中国历史地图集》南北朝后期（546 年 东魏·西魏·梁）通行方案示意性重建（非精确数字化）'],
      ['魏晋南北朝战争路线', '南北朝战争路线'],
      ['// ── 2d) 魏晋南北朝十八国（示意性重建：十八王 + 西楚）──',
       '// ── 2d) 魏晋南北朝疆域（546 年：东魏 · 西魏 · 梁，附吐谷浑 · 柔然）──'],
      ['魏晋南北朝十八国: ', '魏晋南北朝政权: '],
      ['<br/>魏晋南北朝之际诸侯国', '<br/>魏晋南北朝时期政权（546 年）'],
      [' 国已叠加', ' 个政权已叠加'],
      ['// ── 2g) 南北朝战争路线（六条路线）',
       '// ── 2g) 南北朝战争路线（七条路线）'],
      ['// ── 2f) 魏晋南北朝关键地点', '// ── 2f) 魏晋南北朝关键地点']
    ],
    // ── 3. 面板计数（必须与数据文件实际长度一致）──
    counts: [['城池', 33], ['关隘', 10], ['津渡', 6], ['战役', 26], ['大事记', 15]],
    // ── 4. 路线开关（id 后缀 + 面板文案）──
    routes: [
      [1, '①魏灭蜀 263'],
      [2, '②晋灭吴 279-280'],
      [3, '③淝水之战 383'],
      [4, '④刘裕北伐 409-417'],
      [5, '⑤陈庆之入洛 529'],
      [6, '⑥侯景之乱 547-552'],
      [7, '⑦隋灭陈 588-589']
    ],
    // ── 5. 时间轴：公元纪年（bc=false）+ 固定时期跨度 ──
    timeline: { bc: false, minYear: 220, maxYear: 589 },
    // ── 6. 外链版本戳 ──
    stamps: {
      'wei_jin_states.js': '2026102401',
      'wei_jin_sites.js': '2026102401',
      'wei_jin_routes.js': '2026102401'
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
// 4) routes：整块替换
{
  const re = /<label><input type="checkbox" id="cb-wjr-1">[\s\S]*?id="cb-wjr-6">[^<]*<\/label>/;
  must(re.test(html), 'route label block');
  const block = P.routes.map(([i, t]) =>
    '          <label><input type="checkbox" id="cb-wjr-' + i + '"> ' + t + '</label>').join('\n');
  html = html.replace(re, block);
  // subs 数组
  must(html.includes("const subs = ['cb-wjr-1','cb-wjr-2','cb-wjr-3','cb-wjr-4','cb-wjr-5','cb-wjr-6'];"), 'subs array');
  html = html.replace(
    "const subs = ['cb-wjr-1','cb-wjr-2','cb-wjr-3','cb-wjr-4','cb-wjr-5','cb-wjr-6'];",
    'const subs = [' + P.routes.map(([i]) => "'cb-wjr-" + i + "'").join(',') + '];');
  console.log('  路线开关：6 → ' + P.routes.length + ' 条');
}
// 5) timeline
{
  must(html.includes('const TL_BC = true;'), 'TL_BC');
  html = html.replace('const TL_BC = true;', 'const TL_BC = ' + P.timeline.bc + ';');
  must(html.includes('    bc: true,\n'), 'timeline bc opt');
  html = html.replace('    bc: true,\n',
    '    bc: ' + P.timeline.bc + ',\n    minYear: ' + P.timeline.minYear + ',\n    maxYear: ' + P.timeline.maxYear + ',\n');
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
