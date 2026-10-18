#!/usr/bin/env node
/*
 * 给两个地图页接入「战役时间轴」（../timeline/map_timeline.js）
 * - 一次性集成脚本：head 引用 / #timebar 容器与定位 / 截图模式隐藏 /
 *   地标重建处收集 battle 引用 / tkFusedIcon 战役图形加类 / 全部开关联动 / 页尾胶水
 * - 默认 dry-run 只报告匹配情况；--apply 才写入
 * 用法：
 *   NODE="C:/Users/dbsqu/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"
 *   "$NODE" tools/patch_maptimebar.js          # dry-run
 *   "$NODE" tools/patch_maptimebar.js --apply  # 写入
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APPLY = process.argv.includes('--apply');

/* ─────────── 公共块 ─────────── */

const CSS_HEAD = `  #legend { position:absolute; bottom:18px; left:12px; z-index:1000; width:min(82vw,260px);
            backdrop-filter:none; -webkit-backdrop-filter:none; }`;

const CSS_TIMEBAR = `  /* 战役时间轴（../timeline/map_timeline.js）：桌面贴底右侧，避开左下角图例；窄屏置于图例上方 */
  #timebar { position:absolute; right:12px; bottom:18px; z-index:1000; width:min(660px, calc(100vw - 320px)); }
  @media (max-width: 700px) {
    #timebar { left:10px; right:10px; width:auto; bottom: calc(18px + 100px); }
  }`;

const SHOT_OLD = `  .screenshot-mode #menu-toggle,
  .screenshot-mode #info-toggle,
  .screenshot-mode #info { display:none !important; }`;
const SHOT_NEW = `  .screenshot-mode #menu-toggle,
  .screenshot-mode #info-toggle,
  .screenshot-mode #info,
  .screenshot-mode #timebar { display:none !important; }`;

const LEGEND_TAIL = `</div>


<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"`;

/* ─────────── 页尾胶水（参数化：tk/ch 两族变量） ─────────── */
function glue(o) {
  return `// 7) 战役时间轴：拖动/播放按年份在地图上显示隐藏战役事件（../timeline/map_timeline.js）
function parseTimelineYear(v){
  const m = String(v == null ? '' : v).match(/\\d+/);
  return m ? parseInt(m[0],10) : null;
}
let _btVer = -1, _btSorted = [], _btK = 0;
function refreshBattleTimeFilter(){
  applyBattleTimeFilter(battleTimeCurYear);
}
/* 显示条件：游标年份 ≥ 事件起始年（累积式）——refs 按起始年排序 + 二分 + 差分更新 */
function applyBattleTimeFilter(year){
  battleTimeCurYear = year;
  if(battleTimeRefs.version !== _btVer){
    _btVer = battleTimeRefs.version;
    _btSorted = battleTimeRefs.slice().sort((a,b)=>a.ymin-b.ymin);
    _btK = -1;
  }
  const n = _btSorted.length;
  let lo=0, hi=n;
  while(lo<hi){ const mid=(lo+hi)>>1; if(_btSorted[mid].ymin<=year) lo=mid+1; else hi=mid; }
  const k = lo;
  if(_btK < 0 || k !== _btK){
    const from = _btK < 0 ? 0 : Math.min(k, _btK);
    const to   = _btK < 0 ? n : Math.max(k, _btK);
    for(let i=from;i<to;i++){
      const r = _btSorted[i], show = i < k;
      const el = r.marker.getElement();
      if(el) el.style.display = show ? '' : 'none';
      if(r.label){ const le = r.label.getElement(); if(le) le.style.display = show ? '' : 'none'; }
      if(r.fuse && el){ const g = el.querySelector('.tkf-battle'); if(g) g.style.display = show ? '' : 'none'; }
    }
    _btK = k;
  }
}
(function initBattleTimebar(){
  const host = document.getElementById('timebar');
  if(!host || !window.MapTimeline || !${o.dataVar} || !${o.dataVar}.battle) return;
  const tl = new MapTimeline(host, {
    events: ${o.dataVar}.battle,
    bc: ${o.bc},
    onChange: function(v){
      battleTimeCurYear = v;
      const cb = document.getElementById('${o.cbPrefix}battle');
      if(cb && !cb.checked && v < tl.maxY){ cb.checked = true; if(typeof cb.onchange==='function') cb.onchange({target:cb}); }
      applyBattleTimeFilter(v);
    },
    onSettle: function(){ scheduleCollision(); }
  });
  window.__battleTimebar = tl;
  applyBattleTimeFilter(tl.value);
})();`;
}

/* ─────────── 汉末三国页规则 ─────────── */
const TK_RULES = [
  { name: 'H1 head 引入时间轴样式', old: `</style>\n</head>\n<body>`, neu: `</style>\n<link rel="stylesheet" href="../timeline/map_timeline.css">\n</head>\n<body>` },
  { name: 'H2 #timebar 定位 CSS（插到 #legend 规则后）', old: CSS_HEAD, neu: CSS_HEAD + '\n' + CSS_TIMEBAR },
  { name: 'H3 截图模式隐藏 #timebar', old: SHOT_OLD, neu: SHOT_NEW },
  { name: 'H4 legend 后插入 #timebar 容器', old: LEGEND_TAIL, neu: `</div>\n\n<div id="timebar"></div>\n\n<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"` },
  { name: 'H5 引入 map_timeline.js', old: `    <script src="zhuge_routes.js?v=2026101102"></script>`, neu: `    <script src="zhuge_routes.js?v=2026101102"></script>\n    <script src="../timeline/map_timeline.js?v=2026101301"></script>` },
  { name: 'H6 引用表声明（_tkD 后）', old: `const _tkD = window.THREE_KINGDOM_SITES;`, neu: `const _tkD = window.THREE_KINGDOM_SITES;\n\n// 时间轴过滤（map_timeline.js）：引用表随 rebuildTK 重建；curYear=Infinity 表示全部显示\nconst battleTimeRefs = [];\nbattleTimeRefs.version = 0;\nlet battleTimeCurYear = Infinity;` },
  { name: 'H7 tkFusedIcon 战役图形加类', old: `      inner += '<g transform="translate(0,-10) scale(1.0)">'+tkGlyph('battle',buid)+'</g>';`, neu: `      inner += '<g class="tkf-battle" transform="translate(0,-10) scale(1.0)">'+tkGlyph('battle',buid)+'</g>';` },
  { name: 'H8 rebuildTK 顶部清空引用表', old: `function rebuildTK(){\n  ['city','pass','ford','battle'].forEach(cat=>{`, neu: `function rebuildTK(){\n  battleTimeRefs.length = 0;\n  battleTimeRefs.version++;\n  ['city','pass','ford','battle'].forEach(cat=>{` },
  { name: 'H9 非合并模式：battle 引用收集', old:
`        tkLabelLayer[cat].addLayer(L.marker(ll,{
          icon:L.divIcon({ className:'', html:'<div class="tk-label '+cat+'" data-tkid="'+tid+'">'+f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
          interactive:false, keyboard:false
        }));`, neu:
`        const _lm=L.marker(ll,{
          icon:L.divIcon({ className:'', html:'<div class="tk-label '+cat+'" data-tkid="'+tid+'">'+f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
          interactive:false, keyboard:false
        });
        tkLabelLayer[cat].addLayer(_lm);
        if(cat==='battle'){ const _y=parseTimelineYear(f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }` },
  { name: 'H10 合并模式：融合组 battle 引用收集', old:
`    marker.on('click', () => showInfo(_grpTitle, '<div class="tk-popup-body">'+html+'</div>'));
    tkMergeLayer.addLayer(marker);`, neu:
`    marker.on('click', () => showInfo(_grpTitle, '<div class="tk-popup-body">'+html+'</div>'));
    const _btg = g.filter(x=>x.cat==='battle');
    if(_btg.length){
      const _btys = _btg.map(x=>parseTimelineYear(x.f.year)).filter(y=>y!=null);
      if(_btys.length) battleTimeRefs.push({ymin:Math.min.apply(null,_btys), marker, fuse:true});
    }
    tkMergeLayer.addLayer(marker);` },
  { name: 'H11 合并模式：孤立 battle 引用收集', old:
`    marker.on('click', () => showInfo(s.f.name + ' · ' + tkMeta[s.cat].label, tkTip(s.cat,s.f)));
    tkMergeLayer.addLayer(marker);
    tkMergeLabelLayer.addLayer(L.marker(ll,{
      icon:L.divIcon({ className:'', html:'<div class="tk-label '+s.cat+'" data-tkid="'+tid+'">'+s.f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
      interactive:false, keyboard:false
    }));`, neu:
`    marker.on('click', () => showInfo(s.f.name + ' · ' + tkMeta[s.cat].label, tkTip(s.cat,s.f)));
    tkMergeLayer.addLayer(marker);
    const _lm=L.marker(ll,{
      icon:L.divIcon({ className:'', html:'<div class="tk-label '+s.cat+'" data-tkid="'+tid+'">'+s.f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
      interactive:false, keyboard:false
    });
    tkMergeLabelLayer.addLayer(_lm);
    if(s.cat==='battle'){ const _y=parseTimelineYear(s.f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }` },
  { name: 'H12 地标开关联动（重建后重放过滤）', old:
`['city','pass','ford','battle','merge'].forEach(suf=>{
  const cb=document.getElementById('cb-tk-'+suf);
  if(cb) cb.onchange=()=>rebuildTK();
});
rebuildTK();`, neu:
`['city','pass','ford','battle','merge'].forEach(suf=>{
  const cb=document.getElementById('cb-tk-'+suf);
  if(cb) cb.onchange=()=>{ rebuildTK(); refreshBattleTimeFilter(); };
});
rebuildTK();` },
  { name: 'H13 合并尺度滑块联动', old: `    if(document.getElementById('cb-tk-merge').checked) rebuildTK();`, neu: `    if(document.getElementById('cb-tk-merge').checked){ rebuildTK(); refreshBattleTimeFilter(); }` },
  { name: 'H14 页尾胶水（scheduleCollision 之前）', old: `});\nscheduleCollision();\n</script>`, neu: `});\n` + glue({ dataVar: '_tkD', bc: 'false', cbPrefix: 'cb-tk-' }) + `\nscheduleCollision();\n</script>` }
];

/* ─────────── 楚汉争霸页规则 ─────────── */
const CH_RULES = [
  { name: 'C1 head 引入时间轴样式', old: `</style>\n</head>\n<body>`, neu: `</style>\n<link rel="stylesheet" href="../timeline/map_timeline.css">\n</head>\n<body>` },
  { name: 'C2 #timebar 定位 CSS（插到 #legend 规则后）', old: CSS_HEAD, neu: CSS_HEAD + '\n' + CSS_TIMEBAR },
  { name: 'C3 截图模式隐藏 #timebar', old: SHOT_OLD, neu: SHOT_NEW },
  { name: 'C4 legend 后插入 #timebar 容器', old: LEGEND_TAIL, neu: `</div>\n\n<div id="timebar"></div>\n\n<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"` },
  { name: 'C5 引入 map_timeline.js', old: `    <script src="chu_han_routes.js?v=2026101101"></script>`, neu: `    <script src="chu_han_routes.js?v=2026101101"></script>\n    <script src="../timeline/map_timeline.js?v=2026101301"></script>` },
  { name: 'C6 引用表声明（_chD 后）', old: `const _chD = window.CHU_HAN_SITES;`, neu: `const _chD = window.CHU_HAN_SITES;\n\n// 时间轴过滤（map_timeline.js）：引用表随 rebuildCH 重建；curYear=Infinity 表示全部显示\nconst battleTimeRefs = [];\nbattleTimeRefs.version = 0;\nlet battleTimeCurYear = Infinity;` },
  { name: 'C7 chFusedIcon 战役图形加类', old: `      inner += '<g transform="translate(0,-10) scale(1.0)">'+chGlyph('battle',buid)+'</g>';`, neu: `      inner += '<g class="tkf-battle" transform="translate(0,-10) scale(1.0)">'+chGlyph('battle',buid)+'</g>';` },
  { name: 'C8 rebuildCH 顶部清空引用表', old: `function rebuildCH(){\n  ['city','pass','ford','battle'].forEach(cat=>{`, neu: `function rebuildCH(){\n  battleTimeRefs.length = 0;\n  battleTimeRefs.version++;\n  ['city','pass','ford','battle'].forEach(cat=>{` },
  { name: 'C9 非合并模式：battle 引用收集', old:
`        chLabelLayer[cat].addLayer(L.marker(ll,{
          icon:L.divIcon({ className:'', html:'<div class="ch-label '+cat+'" data-chid="'+tid+'">'+f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
          interactive:false, keyboard:false
        }));`, neu:
`        const _lm=L.marker(ll,{
          icon:L.divIcon({ className:'', html:'<div class="ch-label '+cat+'" data-chid="'+tid+'">'+f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
          interactive:false, keyboard:false
        });
        chLabelLayer[cat].addLayer(_lm);
        if(cat==='battle'){ const _y=parseTimelineYear(f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }` },
  { name: 'C10 合并模式：融合组 battle 引用收集', old:
`    marker.on('click', () => showInfo(_grpTitle, '<div class="tk-popup-body">'+html+'</div>'));
    chMergeLayer.addLayer(marker);`, neu:
`    marker.on('click', () => showInfo(_grpTitle, '<div class="tk-popup-body">'+html+'</div>'));
    const _btg = g.filter(x=>x.cat==='battle');
    if(_btg.length){
      const _btys = _btg.map(x=>parseTimelineYear(x.f.year)).filter(y=>y!=null);
      if(_btys.length) battleTimeRefs.push({ymin:Math.min.apply(null,_btys), marker, fuse:true});
    }
    chMergeLayer.addLayer(marker);` },
  { name: 'C11 合并模式：孤立 battle 引用收集', old:
`    marker.on('click', () => showInfo(s.f.name + ' · ' + chMeta[s.cat].label, chTip(s.cat,s.f)));
    chMergeLayer.addLayer(marker);
    chMergeLabelLayer.addLayer(L.marker(ll,{
      icon:L.divIcon({ className:'', html:'<div class="ch-label '+s.cat+'" data-chid="'+tid+'">'+s.f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
      interactive:false, keyboard:false
    }));`, neu:
`    marker.on('click', () => showInfo(s.f.name + ' · ' + chMeta[s.cat].label, chTip(s.cat,s.f)));
    chMergeLayer.addLayer(marker);
    const _lm=L.marker(ll,{
      icon:L.divIcon({ className:'', html:'<div class="ch-label '+s.cat+'" data-chid="'+tid+'">'+s.f.name+'</div>', iconSize:[0,0], iconAnchor:[nudge[0],nudge[1]] }),
      interactive:false, keyboard:false
    });
    chMergeLabelLayer.addLayer(_lm);
    if(s.cat==='battle'){ const _y=parseTimelineYear(s.f.year); if(_y!=null) battleTimeRefs.push({ymin:_y, marker, label:_lm}); }` },
  { name: 'C12 地标开关联动（重建后重放过滤）', old:
`['city','pass','ford','battle','merge'].forEach(suf=>{
  const cb=document.getElementById('cb-ch-'+suf);
  if(cb) cb.onchange=()=>rebuildCH();
});
rebuildCH();`, neu:
`['city','pass','ford','battle','merge'].forEach(suf=>{
  const cb=document.getElementById('cb-ch-'+suf);
  if(cb) cb.onchange=()=>{ rebuildCH(); refreshBattleTimeFilter(); };
});
rebuildCH();` },
  { name: 'C13 合并尺度滑块联动', old: `    if(document.getElementById('cb-ch-merge').checked) rebuildCH();`, neu: `    if(document.getElementById('cb-ch-merge').checked){ rebuildCH(); refreshBattleTimeFilter(); }` },
  { name: 'C14 页尾胶水（scheduleCollision 之前）', old: `});\nscheduleCollision();\n</script>`, neu: `});\n` + glue({ dataVar: '_chD', bc: 'true', cbPrefix: 'cb-ch-' }) + `\nscheduleCollision();\n</script>` }
];

function patch(file, rules) {
  const abs = path.join(ROOT, file);
  let text = fs.readFileSync(abs, 'utf8');
  /* 两个时期页的换行风格不同（汉末=CRLF / 楚汉=LF）：按各自文件的风格转换替换文本 */
  const eol = /\r\n/.test(text.slice(0, 4096)) ? '\r\n' : '\n';
  const co = (s) => s.split('\n').join(eol);
  let ok = true;
  const report = [];
  report.push('  · 换行风格 ' + JSON.stringify(eol) + '，共 ' + rules.length + ' 条规则');
  rules.forEach(function (r) {
    const oldS = co(r.old);
    const cnt = text.split(oldS).length - 1;
    if (cnt !== 1) { ok = false; report.push('  ✗ [' + r.name + '] 匹配 ' + cnt + ' 次（期望 1）'); return; }
    text = text.split(oldS).join(co(r.neu));
    report.push('  ✓ ' + r.name);
  });
  console.log('\n═══ ' + file + ' ═══');
  report.forEach(function (l) { console.log(l); });
  if (!ok) { console.log('  ⚠ 有规则未唯一匹配 → 未写入'); return false; }
  if (APPLY) { fs.writeFileSync(abs, text, 'utf8'); console.log('  → 已写入（' + rules.length + ' 处）'); }
  else { console.log('  → dry-run：全部 ' + rules.length + ' 处可唯一匹配，未写入'); }
  return true;
}

const ok1 = patch(path.join('汉末三国', 'index.html'), TK_RULES);
const ok2 = patch(path.join('楚汉争霸', 'index.html'), CH_RULES);
process.exit((ok1 && ok2) ? 0 : 1);
