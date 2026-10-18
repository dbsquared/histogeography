#!/usr/bin/env node
/*
 * 时间轴 v2 升级补丁：给两个地图页 + 两份地标数据做一次性升级
 *   1) 数据：sites 文件新增「大事记 event」类（汉末 13 条 / 楚汉 8 条）
 *   2) 图层：第五类 event 全链路支持（glyph / meta / 面板开关 / 合并角标 / 优先级 / 计数）
 *   3) 时间轴：胶水整块升级 v2 —— TL_BC 值域修复（楚汉 bc 正负号）、
 *      battle+event 双类引用收集与过滤、时间窗语义、onEngage 首交互勾选
 * 默认 dry-run 只报告匹配；--apply 才写入。
 * 用法：
 *   NODE="C:/Users/dbsqu/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"
 *   "$NODE" tools/patch_maptimebar_v2.js          # dry-run
 *   "$NODE" tools/patch_maptimebar_v2.js --apply  # 写入
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APPLY = process.argv.includes('--apply');

/* ═══════════ 事件数据（大事记） ═══════════ */

const TK_EVENT = `  ],
  // ── 五、大事记（政治与时局大事；供地图时间轴按年过滤，2026-10-13 增）──
  event: [
    {name:'黄巾起义', year:'184', lon:115.02, lat:37.07, place:'巨鹿（河北平乡西南）', result:'张角兄弟以「苍天已死，黄天当立」号令起事，八州并起，天下遂乱', nudge:[12,-10]},
    {name:'董卓入洛阳·废少帝', year:'189', lon:112.45, lat:34.62, place:'洛阳', result:'董卓率西凉军入京，废少帝、立献帝，专断朝政', nudge:[13,-11]},
    {name:'关东联军讨董·火烧洛阳', year:'190', lon:112.45, lat:34.62, place:'洛阳', result:'关东州郡起兵讨董，董卓焚洛阳宫室、挟献帝西迁长安', nudge:[-13,-11]},
    {name:'曹操迎帝都许', year:'196', lon:113.85, lat:34.04, place:'许县（河南许昌）', result:'曹操奉迎献帝迁都许县，行「挟天子以令诸侯」之策', nudge:[11,10]},
    {name:'袁术僭号仲氏', year:'197', lon:117.02, lat:32.57, place:'寿春', result:'袁术于寿春称帝，国号仲氏，诸侯共讨，众叛亲离', nudge:[12,-9]},
    {name:'三顾茅庐·隆中对', year:'207', lon:112.03, lat:31.98, place:'隆中（湖北襄阳西）', result:'刘备三顾草庐，诸葛亮纵论天下三分'},
    {name:'刘备入蜀', year:'211', lon:104.68, lat:31.47, place:'涪城（四川绵阳东）', result:'刘备应刘璋之邀入蜀御张鲁，进据涪城，图取益州'},
    {name:'曹操进爵魏公·魏王', year:'213-216', lon:114.62, lat:36.07, place:'邺城', result:'曹操受封魏公（213）、进爵魏王（216），魏国社稷立于邺', nudge:[11,9]},
    {name:'曹丕受禅·汉祚终', year:'220', lon:113.94, lat:33.86, place:'繁阳亭（河南临颍）', result:'汉献帝禅位于曹丕，曹魏建立，四百余年汉祚告终'},
    {name:'刘备称帝', year:'221', lon:104.07, lat:30.66, place:'成都', result:'刘备于成都即帝位，国号汉，史称蜀汉', nudge:[10,12]},
    {name:'孙权称帝', year:'229', lon:114.89, lat:30.40, place:'武昌（湖北鄂州）', result:'孙权于武昌称帝，国号吴，旋还都建业'},
    {name:'高平陵之变', year:'249', lon:112.45, lat:34.62, place:'洛阳', result:'司马懿趁曹爽兄弟随帝出城谒陵发动政变，魏权尽归司马氏', nudge:[13,12]},
    {name:'司马炎代魏', year:'265', lon:112.45, lat:34.62, place:'洛阳', result:'司马炎受禅代魏，晋朝建立', nudge:[-13,12]}
  ]
`;

const CH_EVENT = `  ],
  // ── 五、大事记（政治与时局大事；供地图时间轴按年过滤，2026-10-13 增）──
  event: [
    {name:'陈胜称王·张楚', year:'209', lon:114.87, lat:33.73, place:'陈县（河南淮阳）', result:'陈胜据陈称王，号「张楚」——中国历史上第一个农民政权', nudge:[12,-9]},
    {name:'刘邦起兵·为沛公', year:'209', lon:116.94, lat:34.73, place:'沛县（江苏沛县）', result:'刘邦杀沛令起事，众推为沛公', nudge:[10,10]},
    {name:'项梁立楚怀王', year:'208', lon:117.26, lat:34.79, place:'薛（山东枣庄薛城）', result:'项梁召诸将会薛，立熊心为楚怀王，复楚室以号召天下', nudge:[0,-12]},
    {name:'怀王之约', year:'208', lon:117.18, lat:34.27, place:'彭城（江苏徐州）', result:'怀王与诸将约「先入定关中者王之」，刘邦西进、项羽救赵皆循此约', nudge:[12,10]},
    {name:'项羽分封十八王', year:'206', lon:109.40, lat:34.45, place:'戏（陕西临潼东北）', result:'项羽以联军统帅分封十八路诸侯，自王西楚九郡', nudge:[-10,-10]},
    {name:'义帝遇弑', year:'206', lon:113.03, lat:25.80, place:'郴县（湖南郴州）', result:'项羽阴令英布弑义帝于江南，诸侯由是离心', nudge:[0,10]},
    {name:'韩信拜将·登坛', year:'206', lon:107.02, lat:33.07, place:'南郑（陕西汉中）', result:'萧何追韩信而还，刘邦设坛具礼拜为大将', nudge:[11,-9]},
    {name:'刘邦称帝·汉室肇建', year:'202', lon:115.57, lat:35.07, place:'定陶（氾水之阳）', result:'刘邦即皇帝位于氾水之阳，国号汉，汉室肇建', nudge:[-11,10]}
  ]
`;

/* ═══════════ 时间轴 v2 胶水（整块替换） ═══════════ */

function glueV2(o) {
  return `// 7) 事件时间轴：拖动游标按时间窗显示/隐藏地图上的战役与大事（../timeline/map_timeline.js）
const TL_BC = ${o.bc};                         // 本页数据是否按「公元前」计年（必须与下方控件 bc 参数一致！）
function parseTimelineYear(v){
  const m = String(v == null ? '' : v).match(/\\d+/);
  if(!m) return null;
  const n = parseInt(m[0],10);
  return TL_BC ? -Math.abs(n) : n;
}
let battleTimeState = { all: true, year: 0, lo: 0, hi: 0 };
let _btVer = -1, _btSorted = [], _btWasAll = null;
function refreshBattleTimeFilter(){
  applyBattleTimeFilter(battleTimeState);
}
/* 用户首交互（按下 / 键盘 / 点复位）：确保「战役 / 大事记」图层已勾选（幂等） */
function ensureTimelineLayers(){
  ['battle','event'].forEach(k=>{
    const cb = document.getElementById('${o.cbPrefix}'+k);
    if(cb && !cb.checked){ cb.checked = true; cb.dispatchEvent(new Event('change')); }
  });
}
/* 显隐：all=全部显示（初始视图）；filter=仅显示 [lo,hi] 时间窗内的事件——窗口外的（含更早的）一律隐藏 */
function applyBattleTimeFilter(st){
  battleTimeState = st;
  if(battleTimeRefs.version !== _btVer){
    _btVer = battleTimeRefs.version;
    _btSorted = battleTimeRefs.slice().sort((a,b)=>a.ymin-b.ymin);
    _btWasAll = null;
  }
  const n = _btSorted.length;
  let showFrom = 0, showTo = n;
  if(!st.all){
    let a=0,b=n;
    while(a<b){ const m=(a+b)>>1; if(_btSorted[m].ymin < st.lo) a=m+1; else b=m; }
    let p=a,q=n;
    while(p<q){ const m=(p+q)>>1; if(_btSorted[m].ymin <= st.hi) p=m+1; else q=m; }
    showFrom = a; showTo = p;
  } else if(_btWasAll === true){
    return;   // 已在「全部显示」态，无需重复
  }
  for(let i=0;i<n;i++){
    const r = _btSorted[i];
    const show = (i >= showFrom && i < showTo);
    const el = r.marker.getElement();
    if(el) el.style.display = show ? '' : 'none';
    if(r.label){ const le = r.label.getElement(); if(le) le.style.display = show ? '' : 'none'; }
    if(r.fuse && el && r.gcls){ const g = el.querySelector(r.gcls); if(g) g.style.display = show ? '' : 'none'; }
  }
  _btWasAll = !!st.all;
}
(function initEventTimebar(){
  const host = document.getElementById('timebar');
  if(!host || !window.MapTimeline || !${o.dataVar}) return;
  const evs = [].concat(${o.dataVar}.battle||[], ${o.dataVar}.event||[]);
  if(!evs.length) return;
  const tl = new MapTimeline(host, {
    events: evs,
    bc: ${o.bc},
    onChange: function(st){
      if(!st.all) ensureTimelineLayers();
      applyBattleTimeFilter(st);
    },
    onEngage: ensureTimelineLayers,
    onSettle: function(){ scheduleCollision(); }
  });
  window.__eventTimebar = tl;
  applyBattleTimeFilter(tl.getState());
})();
`;
}

/* ═══════════ 规则集 ═══════════ */

/* —— 汉末三国：数据文件 —— */
const TK_DATA_RULES = [
  {
    name: 'D1 新增大事记 event 数组（13 条）',
    old: `    {name:'木门道之战', year:'231', lon:105.52, lat:34.36, place:'木门道（甘肃天水西南）', sides:'蜀军伏击 vs 张郃', result:'张郃中伏中箭而亡'}
  ]
};`,
    neu: `    {name:'木门道之战', year:'231', lon:105.52, lat:34.36, place:'木门道（甘肃天水西南）', sides:'蜀军伏击 vs 张郃', result:'张郃中伏中箭而亡'}
` + TK_EVENT + `};`
  }
];

/* —— 楚汉争霸：数据文件 —— */
const CH_DATA_RULES = [
  {
    name: 'D2 新增大事记 event 数组（8 条）',
    old: `    {name:'灭临江之战', year:'202', lon:112.19, lat:30.35, place:'江陵（湖北荆州）', sides:'汉（刘贾、卢绾） vs 共尉（临江）', result:'江陵城破，共尉被擒，临江亡', nudge:[-16,-10]}
  ]
};`,
    neu: `    {name:'灭临江之战', year:'202', lon:112.19, lat:30.35, place:'江陵（湖北荆州）', sides:'汉（刘贾、卢绾） vs 共尉（临江）', result:'江陵城破，共尉被擒，临江亡', nudge:[-16,-10]}
` + CH_EVENT + `};`
  }
];

/* —— 页面规则生成器（tk=汉末 / ch=楚汉） —— */
function pageRules(k) {
  const isTK = k === 'tk';
  return {
    precise: [
      {
        name: 'P1 面板新增「大事记」开关',
        old: `      <label><input type="checkbox" id="cb-${isTK ? 'tk' : 'ch'}-battle"> 战役（${isTK ? 34 : 26}）</label>`,
        neu: `      <label><input type="checkbox" id="cb-${isTK ? 'tk' : 'ch'}-battle"> 战役（${isTK ? 34 : 26}）</label>\n      <label><input type="checkbox" id="cb-${isTK ? 'tk' : 'ch'}-event"> 大事记（${isTK ? 13 : 8}）</label>`
      },
      {
        name: 'P2 meta 新增 event 类型',
        old: `  battle: { color:'#1B1B1B', label:'战役' }\n};`,
        neu: `  battle: { color:'#1B1B1B', label:'战役' },\n  event:  { color:'#7B1FA2', label:'大事记' }\n};`
      },
      {
        name: 'P3 glyph 新增 event 分支（旗帜）',
        old: `  } else { // battle`,
        neu: `  } else if(category==='event'){\n    return '<g transform="translate(0,-1)"><path d="M -2.2 -17 L -2.2 16" stroke="#FFFFFF" stroke-width="2.6" stroke-linecap="round"/><path d="M -0.4 -17 L 15 -11.6 L -0.4 -6.2 Z" fill="#FFFFFF"/><circle cx="-2.2" cy="16" r="2.4" fill="#FFFFFF"/></g>';\n  } else { // battle`
      },
      {
        name: 'P4 单点图标 ring 色（event 金圈）',
        old: `  const ring = category==='battle' ? '#FFC107' : '#FFFFFF';`,
        neu: `  const ring = category==='battle' ? '#FFC107' : (category==='event' ? '#FFD479' : '#FFFFFF');`
      },
      {
        name: 'P5 融合图标 ring 色',
        old: `  const ring = mainCat==='battle' ? '#FFC107' : '#FFFFFF';`,
        neu: `  const ring = mainCat==='battle' ? '#FFC107' : (mainCat==='event' ? '#FFD479' : '#FFFFFF');`
      },
      {
        name: 'P6 融合角标 event 加类（tkf-event）',
        old: `    inner += '<g transform="translate('+bx+','+by+') scale(0.34)"><circle r="14" fill="rgba(18,18,26,0.82)" stroke="'+${k}Meta[bc].color+'" stroke-width="2.6"/>'+${k}Glyph(bc,buid)+'</g>';`,
        neu: `    inner += '<g'+((bc==='event')?' class="tkf-event"':'')+' transform="translate('+bx+','+by+') scale(0.34)"><circle r="14" fill="rgba(18,18,26,0.82)" stroke="'+${k}Meta[bc].color+'" stroke-width="2.6"/>'+${k}Glyph(bc,buid)+'</g>';`
      },
      {
        name: 'P7 弹窗内容支持 event',
        old: `  if(cat==='battle'){\n    return '<div style="margin:3px 0"><b>'+f.name+'</b>（'+f.year+'）<br/>地点：'+f.place+'<br/>'+f.sides+'<br/><span style="color:#ffd479">'+f.result+'</span>'+(f.desc?('<br/><span style="color:#cfe0f0;font-size:11px;line-height:1.5">'+f.desc+'</span>'):'')+'</div>';\n  }`,
        neu: `  if(cat==='battle'){\n    return '<div style="margin:3px 0"><b>'+f.name+'</b>（'+f.year+'）<br/>地点：'+f.place+'<br/>'+f.sides+'<br/><span style="color:#ffd479">'+f.result+'</span>'+(f.desc?('<br/><span style="color:#cfe0f0;font-size:11px;line-height:1.5">'+f.desc+'</span>'):'')+'</div>';\n  }\n  if(cat==='event'){\n    return '<div style="margin:3px 0"><b>'+f.name+'</b>（'+f.year+'）<br/>地点：'+f.place+'<br/><span style="color:#ffd479">'+f.result+'</span>'+(f.desc?('<br/><span style="color:#cfe0f0;font-size:11px;line-height:1.5">'+f.desc+'</span>'):'')+'</div>';\n  }`
      },
      {
        name: 'P8 标签防重叠优先级（event=68）',
        old: `  if(c.indexOf('${isTK ? 'tk' : 'ch'}-label')>=0 && c.indexOf('battle')>=0) return 72;`,
        neu: `  if(c.indexOf('${isTK ? 'tk' : 'ch'}-label')>=0 && c.indexOf('battle')>=0) return 72;\n  if(c.indexOf('${isTK ? 'tk' : 'ch'}-label')>=0 && c.indexOf('event')>=0) return 68;`
      },
      {
        name: 'P9 四类数组全部扩为五类（5 处）',
        count: 5,
        old: `'city','pass','ford','battle'`,
        neu: `'city','pass','ford','battle','event'`
      },
      {
        name: 'P10 渲染顺序表加 event',
        old: `const ${k}TypeOrder = { city:0, pass:1, ford:2, battle:3 };`,
        neu: `const ${k}TypeOrder = { city:0, pass:1, ford:2, battle:3, event:4 };`
      },
      {
        name: 'P11 图标尺寸表加 event',
        old: `  const size = { city:22, pass:20, ford:20, battle:22 };`,
        neu: `  const size = { city:22, pass:20, ford:20, battle:22, event:20 };`
      },
      {
        name: 'P12 全选/一键列表加 event（3 处）',
        count: 3,
        old: `'cb-${isTK ? 'tk' : 'ch'}-battle','cb-${isTK ? 'tk' : 'ch'}-merge'`,
        neu: `'cb-${isTK ? 'tk' : 'ch'}-battle','cb-${isTK ? 'tk' : 'ch'}-event','cb-${isTK ? 'tk' : 'ch'}-merge'`
      },
      {
        name: 'P13 非合并分支：收集 battle+event',
        old: `        if(cat==='battle'){ const _y=parseTimelineYear(f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }`,
        neu: `        if(cat==='battle'||cat==='event'){ const _y=parseTimelineYear(f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }`
      },
      {
        name: 'P14 融合组分支：battle 记类 + event 独立收集',
        old: `    const _btg = g.filter(x=>x.cat==='battle');\n    if(_btg.length){\n      const _btys = _btg.map(x=>parseTimelineYear(x.f.year)).filter(y=>y!=null);\n      if(_btys.length) battleTimeRefs.push({ymin:Math.min.apply(null,_btys), marker, fuse:true});\n    }`,
        neu: `    const _btg = g.filter(x=>x.cat==='battle');\n    if(_btg.length){\n      const _btys = _btg.map(x=>parseTimelineYear(x.f.year)).filter(y=>y!=null);\n      if(_btys.length) battleTimeRefs.push({ymin:Math.min.apply(null,_btys), marker, fuse:true, gcls:'.tkf-battle'});\n    }\n    const _evg = g.filter(x=>x.cat==='event');\n    if(_evg.length){\n      const _evys = _evg.map(x=>parseTimelineYear(x.f.year)).filter(y=>y!=null);\n      if(_evys.length) battleTimeRefs.push({ymin:Math.min.apply(null,_evys), marker, fuse:true, gcls:'.tkf-event'});\n    }`
      },
      {
        name: 'P15 孤立站点分支：收集 battle+event',
        old: `    if(s.cat==='battle'){ const _y=parseTimelineYear(s.f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }`,
        neu: `    if(s.cat==='battle'||s.cat==='event'){ const _y=parseTimelineYear(s.f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }`
      }
    ],
    region: [
      {
        name: 'P16 胶水整块升级 v2（TL_BC 修复 / 时间窗 / 双类 / onEngage）',
        start: '// 7) ',
        end: 'scheduleCollision();',
        neu: glueV2(isTK
          ? { dataVar: '_tkD', bc: 'false', cbPrefix: 'cb-tk-' }
          : { dataVar: '_chD', bc: 'true', cbPrefix: 'cb-ch-' })
      }
    ]
  };
}

/* ═══════════ 执行 ═══════════ */

function patchFile(file, preciseRules, regionRules) {
  const abs = path.join(ROOT, file);
  let text = fs.readFileSync(abs, 'utf8');
  const eol = /\r\n/.test(text.slice(0, 4096)) ? '\r\n' : '\n';
  const co = (s) => s.split('\n').join(eol);
  let ok = true;
  const report = ['  · 换行风格 ' + JSON.stringify(eol)];

  (preciseRules || []).forEach(function (r) {
    const oldS = co(r.old);
    const cnt = text.split(oldS).length - 1;
    const want = r.count || 1;
    if (cnt !== want) { ok = false; report.push('  ✗ [' + r.name + '] 匹配 ' + cnt + ' 次（期望 ' + want + '）'); return; }
    text = text.split(oldS).join(co(r.neu));
    report.push('  ✓ ' + r.name + (want > 1 ? '（' + want + ' 处）' : ''));
  });

  (regionRules || []).forEach(function (r) {
    const i = text.indexOf(r.start);
    const j = text.lastIndexOf(r.end);
    if (i < 0 || j <= i) { ok = false; report.push('  ✗ [' + r.name + '] 区域锚点未命中 (i=' + i + ', j=' + j + ')'); return; }
    const newS = co(r.neu);
    text = text.slice(0, i) + newS + text.slice(j);
    report.push('  ✓ ' + r.name + '（区域 ' + (j - i) + ' → ' + newS.length + ' 字符）');
  });

  console.log('\n═══ ' + file + ' ═══');
  report.forEach(function (l) { console.log(l); });
  if (!ok) { console.log('  ⚠ 有规则未命中 → 未写入'); return false; }
  if (APPLY) { fs.writeFileSync(abs, text, 'utf8'); console.log('  → 已写入'); }
  else { console.log('  → dry-run（全部命中，未写入）'); }
  return true;
}

const r1 = patchFile(path.join('汉末三国', 'three_kingdoms_sites.js'), TK_DATA_RULES);
const r2 = patchFile(path.join('汉末三国', 'index.html'), pageRules('tk').precise, pageRules('tk').region);
const r3 = patchFile(path.join('楚汉争霸', 'chu_han_sites.js'), CH_DATA_RULES);
const r4 = patchFile(path.join('楚汉争霸', 'index.html'), pageRules('ch').precise, pageRules('ch').region);
process.exit((r1 && r2 && r3 && r4) ? 0 : 1);
