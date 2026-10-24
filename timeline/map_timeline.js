/* ══════════════════════════════════════════════════════════════
   华夏历史地图 · 地图时间轴 v2（战役 + 大事记 的时间窗过滤条）
   ─────────────────────────────────────────────────────────────
   嵌在地图页底部：拖动游标，按「时间窗」显示 / 隐藏地图上的历史事件--
   窗口以游标年份为中心、半宽自适应（让窗口内平均可见 ~6 件），
   窗口内的事件显示，窗口外的（含更早的）全部隐藏。
   两种状态：
     · all    —— 全部显示（初始态 / 点「全部」按钮返回；与地图既有默认一致）
     · filter —— 时间窗过滤（拖动 / 键盘任意操作后进入）
   用法（地图页内）：
     const tl = new MapTimeline(document.getElementById('timebar'), {
       events: battle.concat(event),        // 带 year 的原始数据（两类事件）
       bc: true,                            // true=公元前模式（年份值取负，如楚汉）
       onChange: st => applyTimeFilter(st), // st: {all, year, lo, hi, k, n, pos}
       onEngage: () => ensureEventLayers(), // 用户按下/键盘时（每轮交互首帧；页面自行幂等）
       onSettle: () => scheduleCollision()  // 值稳定后（松手/键盘）：重排标签
     });
   零依赖 · UMD 双导出 · 样式见 map_timeline.css（.mtl- 命名空间）
   ══════════════════════════════════════════════════════════════ */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') {
    window.MapTimeline = api.MapTimeline;
    window.MapTimelineUtil = api.Util;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  /* ────────────────────────── 纯函数区 ────────────────────────── */

  var JITTER = 0.011;   // 同年多事件横向散开量（轴比例），避免叠成一坨
  var GAP = 0.014;      // 同一行相邻事件点的最小间距（轴比例）

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* 年份显示：-209 → '前209 年'；208 → '208 年' */
  function fmtYear(y) {
    y = Math.round(y);
    return (y < 0 ? '前' + (-y) : String(y)) + ' 年';
  }

  /* 从数据里的年份字段取数值：'208' / '208-209' / '206-205' → 208 / 208 / 206 */
  function parseYearNum(raw) {
    var m = String(raw == null ? '' : raw).match(/-?\d+/);
    return m ? parseInt(m[0], 10) : null;
  }

  /* 构建事件表（按起始年升序；bc=true 时把公元前年份记为负数） */
  function buildEvents(list, bc) {
    var out = [];
    (list || []).forEach(function (f) {
      var n = parseYearNum(f && f.year);
      if (n == null) return;
      out.push({ f: f, year: bc ? -Math.abs(n) : n, name: (f && f.name) || '' });
    });
    out.sort(function (a, b) { return a.year - b.year; });
    return out;
  }

  /* 时间窗半宽：让窗口内平均可见约 6 件（span/n*3），并夹在 [2%, 34%] 跨度内 */
  function computeHalfWin(span, n) {
    if (!(span > 0)) return 1;
    if (n <= 0) return span / 20;
    return clamp(span / n * 3.0, span * 0.02, span * 0.34);
  }

  function lowerBound(events, y) {
    var lo = 0, hi = events.length;
    while (lo < hi) { var m = (lo + hi) >> 1; if (events[m].year < y) lo = m + 1; else hi = m; }
    return lo;
  }
  function upperBound(events, y) {
    var lo = 0, hi = events.length;
    while (lo < hi) { var m = (lo + hi) >> 1; if (events[m].year <= y) lo = m + 1; else hi = m; }
    return lo;
  }

  /* 时间窗 [lo, hi] 内的事件数 */
  function windowCount(events, lo, hi) {
    return upperBound(events, hi) - lowerBound(events, lo);
  }

  /* 事件点在轴上的两行错落布局：返回与 events 同序的 [{t,row}] */
  function layoutDots(events, minY, maxY) {
    var span = (maxY - minY) || 1;
    var last = [-9, -9];
    var out = [];
    var i = 0;
    while (i < events.length) {
      var j = i;
      while (j < events.length && events[j].year === events[i].year) j++;
      var cnt = j - i;
      for (var k = i; k < j; k++) {
        var t0 = clamp((events[k].year - minY) / span, 0, 1);
        var t = clamp(t0 + (cnt > 1 ? (k - i - (cnt - 1) / 2) * JITTER : 0), 0, 1);
        var row;
        if (t - last[0] >= GAP) row = 0;
        else if (t - last[1] >= GAP) row = 1;
        else row = (last[0] <= last[1]) ? 0 : 1;
        last[row] = t;
        out.push({ t: t, row: row });
      }
      i = j;
    }
    return out;
  }

  /* ────────────────────────── 组件实现 ────────────────────────── */

  function MapTimeline(el, opts) {
    opts = opts || {};
    this.root = typeof el === 'string' ? document.querySelector(el) : el;
    if (!this.root) throw new Error('MapTimeline: 未找到挂载容器');

    this.onChange = typeof opts.onChange === 'function' ? opts.onChange : null;
    this.onSettle = typeof opts.onSettle === 'function' ? opts.onSettle : null;
    this.onEngage = typeof opts.onEngage === 'function' ? opts.onEngage : null;

    this.events = buildEvents(opts.events, !!opts.bc);
    // 纪元标记（可选）：例如疆域断面的年份；画在轴下方，可点击跳转
    this.marks = Array.isArray(opts.marks) ? opts.marks.slice().sort(function (a, b) { return a.year - b.year; }) : [];
    var ys = this.events.map(function (e) { return e.year; });
    this.minY = opts.minYear != null ? opts.minYear : (ys.length ? ys[0] : 0);
    this.maxY = opts.maxYear != null ? opts.maxYear : (ys.length ? ys[ys.length - 1] : 100);
    this.halfWin = opts.windowHalf != null ? opts.windowHalf : computeHalfWin(this.maxY - this.minY, this.events.length);

    this.mode = 'all';          // 'all' | 'filter'
    this.year = this.maxY;      // filter 态游标年份
    this.pos = 1;               // 游标位置（连续）
    this._lastK = -1;           // 窗口计数缓存
    this._settleTimer = null;
    this._glideTimer = null;

    this._build();
    this._bind();
    this._moveKnob(1, false);
    this._render();
  }

  MapTimeline.prototype._build = function () {
    var dots = layoutDots(this.events, this.minY, this.maxY);
    var dotsHtml = dots.map(function (d) {
      return '<i class="mtl-pt" style="left:' + (d.t * 100).toFixed(3) + '%;top:' + (d.row * 9) + 'px"></i>';
    }).join('');

    /* 纪元标记：轴上的一列年份刻度（有标记时轴加高 14px，无标记的页面外观不变） */
    var span = (this.maxY - this.minY) || 1;
    var self = this;
    var marksHtml = '';
    if (this.marks.length) {
      marksHtml = '<div class="mtl-marks">' + this.marks.map(function (m, i) {
        var pct = (Math.min(Math.max((m.year - self.minY) / span, 0), 1) * 100).toFixed(3);
        return '<i class="mtl-mark" data-i="' + i + '" style="left:' + pct + '%" title="' +
          esc((m.name || '') + ' ' + fmtYear(m.year)) + '"><span>' + esc(m.short || m.year) + '</span></i>';
      }).join('') + '</div>';
    }

    this.root.classList.add('mtl');
    if (this.marks.length) this.root.classList.add('has-marks');
    this.root.innerHTML =
      '<div class="mtl-side">' +
        '<button class="mtl-btn mtl-all" type="button" title="全部显示（复位，恢复初始视图）">⏭</button>' +
      '</div>' +
      '<div class="mtl-mid">' +
        '<div class="mtl-axis" tabindex="0" role="slider" aria-label="历史事件时间轴"' +
          ' aria-valuemin="' + this.minY + '" aria-valuemax="' + this.maxY + '" aria-valuenow="' + this.maxY + '">' +
          '<div class="mtl-dots">' + dotsHtml + '</div>' +
          '<div class="mtl-track"><div class="mtl-fill"></div></div>' +
          '<div class="mtl-knob"><div class="mtl-knob-head"></div></div>' +
          '<div class="mtl-ends"><span>' + esc(fmtYear(this.minY)) + '</span><span>' + esc(fmtYear(this.maxY)) + '</span></div>' +
          marksHtml +
          '<div class="mtl-hit"></div>' +
        '</div>' +
      '</div>' +
      '<div class="mtl-read"><b class="mtl-year"></b><span class="mtl-count"></span><span class="mtl-era"></span></div>';

    this.elAxis = this.root.querySelector('.mtl-axis');
    this.elHit = this.root.querySelector('.mtl-hit');
    this.elKnob = this.root.querySelector('.mtl-knob');
    this.elFill = this.root.querySelector('.mtl-fill');
    this.elYear = this.root.querySelector('.mtl-year');
    this.elCount = this.root.querySelector('.mtl-count');
    this.elEra = this.root.querySelector('.mtl-era');
    this.elAll = this.root.querySelector('.mtl-all');
    this.elMarks = Array.prototype.slice.call(this.root.querySelectorAll('.mtl-mark'));
    this.dots = Array.prototype.slice.call(this.root.querySelectorAll('.mtl-pt'));
  };

  MapTimeline.prototype._bind = function () {
    var self = this;
    var axis = this.elAxis;
    var hit = this.elHit;
    var dragging = false;
    var rafId = 0;
    var lastX = 0;

    function engage() { if (self.onEngage) self.onEngage(); }
    function flush() {
      rafId = 0;
      var rect = axis.getBoundingClientRect();
      if (!rect.width) return;
      self._fromPos((lastX - rect.left) / rect.width);
    }
    hit.addEventListener('pointerdown', function (e) {
      dragging = true;
      self._stopGlide();
      try { hit.setPointerCapture(e.pointerId); } catch (_) { /* 桩环境无此 API */ }
      axis.classList.add('dragging');
      self.root.classList.add('dragging');
      engage();
      e.preventDefault();
      lastX = e.clientX;
      if (!rafId) rafId = requestAnimationFrame(flush);
    });
    hit.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      lastX = e.clientX;
      if (!rafId) rafId = requestAnimationFrame(flush);
    });
    function endDrag() {
      if (!dragging) return;
      dragging = false;
      axis.classList.remove('dragging');
      self.root.classList.remove('dragging');
      self._settle();
    }
    hit.addEventListener('pointerup', endDrag);
    hit.addEventListener('pointercancel', endDrag);

    axis.addEventListener('keydown', function (e) {
      var step = e.shiftKey ? 5 : 1;
      var handled = true;
      switch (e.key) {
        case 'ArrowLeft': case 'ArrowDown': self.setYear(Math.max(self.year - step, self.minY), true); break;
        case 'ArrowRight': case 'ArrowUp': self.setYear(self.year + step, true); break;
        case 'PageDown': self.setYear(Math.max(self.year - 10, self.minY), true); break;
        case 'PageUp': self.setYear(self.year + 10, true); break;
        case 'Home': self.setYear(self.minY, true); break;
        case 'End': self.setYear(self.maxY, true); break;
        default: handled = false;
      }
      if (handled) { engage(); self._settle(); e.preventDefault(); }
    });

    this.elAll.addEventListener('click', function () {
      engage();
      self.showAll(true);
      self._settle();
    });

    /* 纪元标记：点年份刻度直接跳到该断面（等同拖到该年） */
    this.elMarks.forEach(function (el) {
      el.addEventListener('click', function (e) {
        e.stopPropagation();
        var m = self.marks[Number(el.getAttribute('data-i'))];
        if (!m) return;
        engage();
        self.setYear(m.year, true);
        self._settle();
      });
    });
  };

  MapTimeline.prototype._stopGlide = function () {
    clearTimeout(this._glideTimer);
    this.elKnob.classList.remove('glide');
    this.elFill.classList.remove('glide');
  };

  /* 拖动路径：pos 为连续轴位置（游标跟手），year 取整 */
  MapTimeline.prototype._fromPos = function (pos) {
    pos = clamp(pos, 0, 1);
    var span = (this.maxY - this.minY) || 1;
    this._toFilter(Math.round(this.minY + pos * span), pos, false);
  };

  /* 程序路径（键盘/外部 API）：由整数年份反推位置 */
  MapTimeline.prototype.setYear = function (y, glide) {
    y = Math.round(clamp(y, this.minY, this.maxY));
    var span = (this.maxY - this.minY) || 1;
    var pos = clamp((y - this.minY) / span, 0, 1);
    this._toFilter(y, pos, !!glide);
  };

  /* 进入 / 更新「时间窗过滤」态 */
  MapTimeline.prototype._toFilter = function (y, pos, glide) {
    var changed = (this.mode !== 'filter') || (y !== this.year);
    this.mode = 'filter';
    this.year = y;
    this.pos = pos;
    this._moveKnob(pos, glide);
    this._render();
    if (changed) this._emit();
  };

  /* 回到「全部显示」态（复位到初始视图） */
  MapTimeline.prototype.showAll = function (glide) {
    var changed = (this.mode !== 'all');
    this.mode = 'all';
    this.year = this.maxY;
    this.pos = 1;
    this._moveKnob(1, !!glide);
    this._render();
    if (changed) this._emit();
  };

  MapTimeline.prototype._moveKnob = function (pos, glide) {
    if (glide) {
      var self = this;
      this.elKnob.classList.add('glide');
      this.elFill.classList.add('glide');
      clearTimeout(this._glideTimer);
      this._glideTimer = setTimeout(function () {
        self.elKnob.classList.remove('glide');
        self.elFill.classList.remove('glide');
      }, 420);
    }
    this.elKnob.style.left = (pos * 100).toFixed(3) + '%';
  };

  /* 当前状态（供页面初始 apply 与外部读取） */
  MapTimeline.prototype.getState = function () {
    var lo = this.year - this.halfWin;
    var hi = this.year + this.halfWin;
    var k = this.mode === 'all' ? this.events.length : windowCount(this.events, lo, hi);
    return { all: this.mode === 'all', year: this.year, lo: lo, hi: hi, k: k, n: this.events.length, pos: this.pos, halfWin: this.halfWin };
  };

  MapTimeline.prototype._emit = function () {
    if (this.onChange) this.onChange(this.getState());
  };

  MapTimeline.prototype._render = function () {
    var all = this.mode === 'all';
    var span = (this.maxY - this.minY) || 1;
    var st = this.getState();

    /* 右侧读数 */
    this.elYear.textContent = all ? '全部' : fmtYear(this.year);
    this.elCount.textContent = st.k + ' / ' + st.n + ' 件';
    this.elAll.classList.toggle('on', all);

    /* 纪元标记：高亮「当前年份所属」的断面，并在右侧显示其名称（全部态不高亮） */
    if (this.marks.length) {
      var act = -1;
      if (!all) {
        for (var mi = 0; mi < this.marks.length; mi++) { if (this.marks[mi].year <= this.year + 0.5) act = mi; }
      }
      for (var mj = 0; mj < this.elMarks.length; mj++) this.elMarks[mj].classList.toggle('on', mj === act);
      if (this.elEra) this.elEra.textContent = act >= 0 ? (this.marks[act].name || '') : '';
    }

    /* 轴面高亮：all=整条；filter=时间窗区间 */
    if (all) {
      this.elFill.style.left = '0%';
      this.elFill.style.width = '100%';
    } else {
      var loPct = clamp((st.lo - this.minY) / span, 0, 1) * 100;
      var hiPct = clamp((st.hi - this.minY) / span, 0, 1) * 100;
      this.elFill.style.left = loPct.toFixed(3) + '%';
      this.elFill.style.width = (hiPct - loPct).toFixed(3) + '%';
    }

    /* 事件点：窗口内亮、窗口外暗 */
    if (st.k !== this._lastK || all) {
      var a = all ? 0 : lowerBound(this.events, st.lo);
      var b = all ? this.dots.length : upperBound(this.events, st.hi);
      for (var i = 0; i < this.dots.length; i++) {
        this.dots[i].classList.toggle('past', i >= a && i < b);
      }
      this._lastK = st.k;
    }

    /* aria */
    this.elAxis.setAttribute('aria-valuenow', String(all ? this.maxY : clamp(this.year, this.minY, this.maxY)));
    this.elAxis.setAttribute('aria-valuetext',
      all ? ('全部显示，共 ' + st.n + ' 件')
          : (fmtYear(this.year) + '，显示 ' + fmtYear(st.lo).replace(' 年', '') + '至' + fmtYear(st.hi).replace(' 年', '') + ' 共 ' + st.k + ' 件'));
  };

  /* 值稳定后（松手 / 键盘）通知宿主重排（防抖） */
  MapTimeline.prototype._settle = function () {
    var self = this;
    if (!this.onSettle) return;
    clearTimeout(this._settleTimer);
    this._settleTimer = setTimeout(function () { self.onSettle(); }, 120);
  };

  MapTimeline.prototype.destroy = function () {
    clearTimeout(this._settleTimer);
    this._stopGlide();
    this.root.innerHTML = '';
    this.root.classList.remove('mtl', 'dragging');
  };

  return {
    MapTimeline: MapTimeline,
    Util: {
      clamp: clamp,
      esc: esc,
      fmtYear: fmtYear,
      parseYearNum: parseYearNum,
      buildEvents: buildEvents,
      computeHalfWin: computeHalfWin,
      lowerBound: lowerBound,
      upperBound: upperBound,
      windowCount: windowCount,
      layoutDots: layoutDots
    }
  };
});
