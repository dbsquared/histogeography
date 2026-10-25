// ── 2d) 魏晋南北朝疆域（七个断面：262 / 300 / 382 / 500 / 546 / 576 / 589）──
// 数据: window.WEI_JIN_STATES = {meta, snapshots:[{year, name, states:[{name,color,rings,seats}]}]}
// 两级图层: 疆域 (cb-wj-bnd) + 都邑 (cb-wj-seat)；断面由「疆域纪年」滑条与底部时间轴共同驱动
const wjBoundaryLayer = L.layerGroup();
const wjSeatLayer     = L.layerGroup();
const wjSeatLabelLayer= L.layerGroup();
const wjStateLabelLayer=L.layerGroup();
const wjCapitalLayer  =L.layerGroup();  // 疆域模式下随疆域一起显示的都城（仅治所名）

// 计算国名标签位置：优先面积加权质心（若落在疆域内则用之，最贴合"几何中心"）；
// 若质心落在境外（如渤海海上），改用"最内点"算法（pole of inaccessibility 近似），
// 即在境内网格采样取离边界最远的点，保证标签始终落在疆域内。
function pointInPolygon(x,y,poly){
  let inside=false;
  for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const xi=poly[i][0],yi=poly[i][1],xj=poly[j][0],yj=poly[j][1];
    if(((yi>y)!=(yj>y)) && (x < (xj-xi)*(y-yi)/(yj-yi)+xi)) inside=!inside;
  }
  return inside;
}
function distToSeg(px,py,x1,y1,x2,y2){
  const dx=x2-x1,dy=y2-y1,l2=dx*dx+dy*dy;
  if(l2===0) return Math.hypot(px-x1,py-y1);
  let t=((px-x1)*dx+(py-y1)*dy)/l2; t=Math.max(0,Math.min(1,t));
  return Math.hypot(px-(x1+t*dx), py-(y1+t*dy));
}
function computeLabelPoint(ring){
  const pts = ring.map(p=>[p[1],p[0]]);  // [[lat,lon]] → [[lon,lat]]
  const n = pts.length;
  let A=0,Cx=0,Cy=0;
  for(let i=0;i<n-1;i++){
    const x0=pts[i][0],y0=pts[i][1],x1=pts[i+1][0],y1=pts[i+1][1];
    const cr=x0*y1-x1*y0; A+=cr; Cx+=(x0+x1)*cr; Cy+=(y0+y1)*cr;
  }
  A*=0.5;
  if(!A) return [pts[0][1], pts[0][0]];
  const clon=Cx/(6*A), clat=Cy/(6*A);
  if(pointInPolygon(clon,clat,pts)) return [clat,clon];
  let lons=pts.map(p=>p[0]), lats=pts.map(p=>p[1]);
  const minLon=Math.min(...lons),maxLon=Math.max(...lons),minLat=Math.min(...lats),maxLat=Math.max(...lats);
  const step=0.12;
  let best=null,bestDist=-1;
  for(let lat=minLat;lat<=maxLat;lat+=step){
    for(let lon=minLon;lon<=maxLon;lon+=step){
      if(!pointInPolygon(lon,lat,pts)) continue;
      let dmin=Infinity;
      for(let i=0;i<n-1;i++){
        const d=distToSeg(lat,lon,pts[i][1],pts[i][0],pts[i+1][1],pts[i+1][0]);
        if(d<dmin)dmin=d;
      }
      if(dmin>bestDist){bestDist=dmin;best=[lat,lon];}
    }
  }
  return best || [clat,clon];
}

// ── 断面切换 ──
let WJ_SNAP = -1;                       // 当前断面序号
function wjSnapList(){ const D = window.WEI_JIN_STATES; return (D && D.snapshots) || []; }
function wjPickIndex(year){
  const S = wjSnapList();
  if(!S.length) return -1;
  let k = 0;                              // 早于第一个断面时，取第一个（262 三国）
  for(let i=0;i<S.length;i++){ if(S[i].year <= year + 0.5){ k = i; } else break; }
  return k;
}
// 政权简介（wei_jin_regimes.js）；缺条目时退回只显示年份与都邑
function wjRegimeInfo(name){
  const R = window.WEI_JIN_REGIMES || {};
  return R[name] || null;
}
function wjEraTip(st, snap){
  const r = wjRegimeInfo(st.name);
  const seats = (st.seats||[]).map(s=>s.name.replace('/', ' · ')).join('、');
  let h = '<b>' + ((r && r.full) ? r.full : st.name) + '</b>';
  h += '　<span style="color:#9fb3c8">' + snap.year + ' 年 · ' + snap.name + '</span>';
  const meta = [];
  if(r && r.span)    meta.push('立国 ' + r.span);
  if(r && r.capital) meta.push('都 ' + r.capital);
  if(r && r.founder) meta.push(r.founder);
  if(meta.length) h += '<div style="color:#ffd479;margin:3px 0 2px">' + meta.join('　·　') + '</div>';
  if(r && r.desc) h += '<div style="color:#cfe0f0;font-size:11px;line-height:1.7;margin:5px 0 4px">' + r.desc + '</div>';
  h += '<div style="margin-top:4px">都邑：' + (seats || '—') + '</div>';
  return h;
}
function buildWjEra(idx){
  const S = wjSnapList();
  if(!S.length){ console.warn('魏晋南北朝疆域数据未加载'); return; }
  idx = Math.max(0, Math.min(S.length-1, idx));
  if(idx === WJ_SNAP) return;            // 同一断面不重建（时间轴拖动时每帧都会调用）
  WJ_SNAP = idx;
  const snap = S[idx];
  [wjBoundaryLayer, wjSeatLayer, wjSeatLabelLayer, wjStateLabelLayer, wjCapitalLayer].forEach(l=>{
    map.removeLayer(l); l.clearLayers();
  });
  snap.states.forEach(st=>{
    // 1) 疆域（可能由多环组成，逐环绘制）
    (st.rings || []).forEach(ring0=>{
      const ring = ring0.map(p=>[p[1],p[0]]);          // [lon,lat] → [lat,lon]
      const baseStyle = { color:st.color, weight:2.6, opacity:0.92, fillColor:st.color, fillOpacity:0.15 };
      const poly = L.polygon(ring, baseStyle);
      poly.on('mouseover', function(){
        this.setStyle({ weight:3.4, opacity:1, fillOpacity:0.22 });
        this.bringToFront();
      });
      poly.on('mouseout', function(){ this.setStyle(baseStyle); });
      poly.on('click', () => {
        const r = wjRegimeInfo(st.name);
        showInfo(((r && r.full) ? r.full : st.name) + '（' + snap.year + ' 年）', wjEraTip(st, snap));
      });
      wjBoundaryLayer.addLayer(poly);
    });

    // 2) 国名标签（落在最大一环的内部）
    const rings = (st.rings || []).slice().sort((a,b)=>b.length-a.length);
    if(rings.length){
      const labelLL = computeLabelPoint(rings[0].map(p=>[p[1],p[0]]));
      wjStateLabelLayer.addLayer(L.marker(labelLL,{
        icon:L.divIcon({className:'', html:'<div class="wjstate-label">'+st.name+'</div>',
          iconSize:[0,0], iconAnchor:[0,0]}),
        interactive:false, keyboard:false
      }));
    }

    // 3) 都邑点 + 标签
    const splitSeat = n => { const i=n.indexOf('/'); return i<0 ? [n,''] : [n.slice(0,i), n.slice(i+1)]; };
    (st.seats||[]).forEach(seat=>{
      const isCap = seat.role==='capital';
      const [jun, zhi] = splitSeat(seat.name);
      const dotColor = isCap ? '#ffd24d' : '#ffb870';
      const dot = L.circleMarker([seat.lat, seat.lon],{
        radius: isCap?3:2,
        color:'#fff', weight:1, opacity:0.95,
        fillColor:dotColor, fillOpacity:0.92,
      });
      const sub = st.name + ' · ' + (isCap?'都城':'郡治') + '（' + snap.year + ' 年）';
      dot.bindTooltip(`<b>${seat.name}</b><br/>${sub}`, {direction:'top', offset:[0,-6], opacity:0.95});
      dot.on('click', () => showInfo(seat.name + ' · ' + st.name, `<b>${seat.name}</b><br/>${sub}`));
      wjSeatLayer.addLayer(dot);
      const labelCls = isCap ? 'wjseat-label capital' : 'wjseat-label';
      const labelHtml = zhi ? `${jun}<br><span class="zhi">${zhi}</span>` : jun;
      wjSeatLabelLayer.addLayer(L.marker([seat.lat, seat.lon],{
        icon:L.divIcon({className:'', html:`<div class="${labelCls}">${labelHtml}</div>`,
          iconSize:[0,0], iconAnchor:[0,0]}),
        interactive:false, keyboard:false
      }));
      if(isCap){
        wjCapitalLayer.addLayer(L.circleMarker([seat.lat, seat.lon],{
          radius:3, color:'#fff', weight:1, opacity:0.95,
          fillColor:'#ffd24d', fillOpacity:0.92,
        }));
      }
    });
  });

  // 4) 读数与滑条同步
  const ro = document.getElementById('era-readout');
  if(ro) ro.textContent = snap.year + ' 年 · ' + snap.states.map(s=>s.name).join('｜');
  const rg = document.getElementById('era-range');
  if(rg && Number(rg.value) !== idx) rg.value = String(idx);
  const tt = document.getElementById('era-range');
  if(tt) tt.setAttribute('aria-valuetext', snap.year + ' 年 ' + snap.name);

  if(document.getElementById('cb-wj-bnd').checked) showWjBnd();
  if(document.getElementById('cb-wj-seat').checked) showWjSeat();
  scheduleCollision();
}
function showWjBnd(){ wjBoundaryLayer.addTo(map); wjStateLabelLayer.addTo(map); }   // 疆域不再显示都城（用户要求）
function hideWjBnd(){ map.removeLayer(wjBoundaryLayer); map.removeLayer(wjStateLabelLayer); }
function showWjSeat(){ wjSeatLayer.addTo(map); wjSeatLabelLayer.addTo(map); }
function hideWjSeat(){ map.removeLayer(wjSeatLayer); map.removeLayer(wjSeatLabelLayer); }
document.getElementById('cb-wj-bnd').onchange = e => e.target.checked ? showWjBnd() : hideWjBnd();
document.getElementById('cb-wj-seat').onchange = e => e.target.checked ? showWjSeat() : hideWjSeat();

// 纪年滑条：◀ 上一期 / 下一期 ▶（滑条本身按下标走，读数显示年份）
// 同时把底部时间轴的游标一起移到该年——图上只有「一个时间游标」，两处操作等价
function eraJump(i){
  const S = wjSnapList(); if(!S.length) return;
  i = Math.max(0, Math.min(S.length-1, i));
  buildWjEra(i);
  const tl = window.__eventTimebar;
  if(tl && typeof tl.setYear === 'function') tl.setYear(S[i].year, true);
}
(function(){
  const rg = document.getElementById('era-range');
  const S = wjSnapList();
  if(rg){
    rg.max = String(Math.max(0, S.length - 1));
    rg.oninput = e => eraJump(Number(e.target.value));
  }
  const pv = document.getElementById('era-prev'), nx = document.getElementById('era-next');
  if(pv) pv.onclick = () => eraJump(WJ_SNAP - 1);
  if(nx) nx.onclick = () => eraJump(WJ_SNAP + 1);
})();

// 供底部时间轴调用：按年份切到对应断面（同一年份不重建）
window.__setEraYear = function(year){ buildWjEra(wjPickIndex(year)); };

// 初始断面：546 年（东魏 · 西魏 · 梁）
buildWjEra(wjPickIndex(546));
if(document.getElementById('cb-wj-bnd').checked) showWjBnd();
if(document.getElementById('cb-wj-seat').checked) showWjSeat();

