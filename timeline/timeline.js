/* ══════════════════════════════════════════════════════════════
   华夏历史地图 · 可交互时间轴组件
   ─────────────────────────────────────────────────────────────
   功能：
     · 分节时间轴：各历史时期等宽分段，段内按真实年份线性映射
     · 拖动游标（指针 / 触屏 / 键盘）实时切换「当前时期」
     · 当前时期的事件显示，其余时期的事件隐藏（列表 + 轴上标记点）
     · 游标年份之后的事件呈「未至」态，拖过即点亮（实时更新）
     · 响应式适配常见屏幕尺寸；零依赖、命名空间 .htl- 隔离
   用法：
     new HistoryTimeline(container, {
       eras: HISTORY_TIMELINE_DATA.eras,   // 时期与事件数据
       initialEra: 'han-san-guo', initialYear: 208,
       onChange: function (state) { ... }  // 可选回调
     });
   ══════════════════════════════════════════════════════════════ */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') {
    window.HistoryTimeline = api.HistoryTimeline;
    window.HistoryTimelineUtil = api.Util;
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  /* ────────────────────────── 纯函数区 ────────────────────────── */

  var ROWS = 3;        // 事件点在轴上错落 3 行
  var MIN_GAP = 0.012; // 同一行相邻事件点的最小间隔（段内比例）

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function hexToRgba(hex, a) {
    var h = String(hex || '#ffd479').replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  /* 年份显示：-209 → '前209'；208 → '208' */
  function fmtYear(y) {
    y = Math.round(y);
    return y < 0 ? '前' + (-y) : String(y);
  }

  /* 完整年份显示：-209 → '公元前 209 年'；208 → '公元 208 年' */
  function fmtYearFull(y) {
    y = Math.round(y);
    return y < 0 ? '公元前 ' + (-y) + ' 年' : '公元 ' + y + ' 年';
  }

  /* 年份跨度显示：(-206,-205) → '前206–205'；(184,280) → '184–280' */
  function fmtSpan(a, b) {
    a = Math.round(a); b = Math.round(b);
    if (a === b) return fmtYear(a);
    if (a < 0 && b < 0) return '前' + (-a) + '–' + (-b);
    if (a >= 0 && b >= 0) return a + '–' + b;
    return fmtYear(a) + '–' + fmtYear(b);
  }

  /* 事件标准化 + 按年份升序排列 */
  function parseEvents(list) {
    return (list || []).map(function (ev) {
      var s = Number(ev.year);
      var e = (ev.endYear == null ? s : Number(ev.endYear));
      return {
        name: ev.name || '',
        year: Math.min(s, e),
        endYear: Math.max(s, e),
        place: ev.place || '',
        sides: ev.sides || '',
        result: ev.result || ''
      };
    }).sort(function (A, B) { return (A.year - B.year) || (A.endYear - B.endYear); });
  }

  /* 全局轴位置 frac∈[0,1] → { 段序号 i, 段内比例 t, 年份 year } */
  function resolve(frac, eras) {
    var n = eras.length;
    var f = clamp(frac, 0, 1);
    var idx, t;
    if (f >= 1) { idx = n - 1; t = 1; }
    else { idx = Math.min(n - 1, Math.floor(f * n)); t = f * n - idx; }
    var era = eras[idx];
    var lo = Math.min(era.from, era.to);
    var hi = Math.max(era.from, era.to);
    var year = clamp(Math.round(era.from + (era.to - era.from) * t), lo, hi);
    return { i: idx, era: era, t: t, year: year, frac: f };
  }

  /* 年份 → 全局轴位置（用于初始定位、跳转） */
  function fracOf(year, eraIndex, eras) {
    var era = eras[eraIndex];
    var span = era.to - era.from;
    var t = span === 0 ? 0 : (year - era.from) / span;
    t = clamp(t, 0, 0.999999);
    return clamp((eraIndex + t) / eras.length, 0, 1);
  }

  /* 事件点错落布局：返回与 events 同序的 [{t, row}] */
  function layoutPoints(events, era) {
    var lastT = [];
    var r;
    for (r = 0; r < ROWS; r++) lastT.push(-Infinity);
    var span = era.to - era.from;
    return events.map(function (ev) {
      var t = span === 0 ? 0 : (ev.year - era.from) / span;
      t = clamp(t, 0.008, 0.985);
      var row = 0;
      while (row < ROWS && t - lastT[row] < MIN_GAP) row++;
      if (row === ROWS) {
        row = 0;
        for (r = 1; r < ROWS; r++) if (lastT[r] < lastT[row]) row = r;
      }
      lastT[row] = t;
      return { t: t, row: row };
    });
  }

  /* 截至 year（含）已发生的事件数（events 需按 year 升序） */
  function pastCount(events, year) {
    var lo = 0, hi = events.length;
    while (lo < hi) {
      var mid = (lo + hi) >> 1;
      if (events[mid].year <= year) lo = mid + 1; else hi = mid;
    }
    return lo;
  }

  /* ────────────────────────── 组件实现 ────────────────────────── */

  function HistoryTimeline(root, opts) {
    opts = opts || {};
    this.root = typeof root === 'string' ? document.querySelector(root) : root;
    if (!this.root) throw new Error('HistoryTimeline: 未找到挂载容器');
    if (!opts.eras || !opts.eras.length) throw new Error('HistoryTimeline: eras 不能为空');

    this.eras = opts.eras.map(function (e, i) {
      var era = {};
      for (var k in e) if (Object.prototype.hasOwnProperty.call(e, k)) era[k] = e[k];
      era.index = i;
      era.events = parseEvents(e.events);
      return era;
    });

    this.onChange = typeof opts.onChange === 'function' ? opts.onChange : null;
    this.frac = 0;
    this.state = null;
    this._progI = -1;    // 进度状态缓存：段
    this._progK = -1;    // 进度状态缓存：已发生数
    this._peekTimer = null;
    this._glideTimer = null;

    this._build();
    this._bindAxis();

    /* 初始位置：initialFrac 优先，其次 initialYear（配合 initialEra） */
    var initFrac = 0;
    if (opts.initialFrac != null) {
      initFrac = clamp(opts.initialFrac, 0, 1);
    } else if (opts.initialYear != null) {
      var i = -1;
      if (opts.initialEra != null) {
        i = this._eraIndexById(opts.initialEra);
      }
      if (i < 0) {
        i = this.eras.findIndex(function (e) {
          var lo = Math.min(e.from, e.to), hi = Math.max(e.from, e.to);
          return opts.initialYear >= lo && opts.initialYear <= hi;
        });
      }
      if (i < 0) i = 0;
      initFrac = fracOf(opts.initialYear, i, this.eras);
    }
    this.setFrac(initFrac);
  }

  HistoryTimeline.prototype._eraIndexById = function (id) {
    for (var i = 0; i < this.eras.length; i++) if (this.eras[i].id === id) return i;
    return -1;
  };

  /* ── 构建 DOM ── */
  HistoryTimeline.prototype._build = function () {
    var self = this;
    var n = this.eras.length;
    var colW = 100 / n;
    var colsHtml = '';
    var cardsHtml = '';

    this.eras.forEach(function (era, i) {
      var planned = era.status !== 'live';
      var layout = layoutPoints(era.events, era);
      var ptsHtml = layout.map(function (p) {
        return '<i class="htl-pt" style="left:' + (p.t * 100).toFixed(3) + '%;top:' + (p.row * 10) + 'px"></i>';
      }).join('');

      colsHtml +=
        '<div class="htl-col' + (planned ? ' planned' : '') + '" style="left:' + (i * colW) + '%;width:' + colW + '%;--era:' + era.color + ';--era-soft:' + hexToRgba(era.color, 0.16) + '">' +
          '<button class="htl-col-name" type="button" title="' + esc(era.name + '（' + (planned ? '筹备中' : '已上线') + '）· 点击直达') + '">' +
            '<i class="htl-dot"></i><span>' + esc(era.name) + '</span>' +
          '</button>' +
          '<div class="htl-col-lanes">' + ptsHtml + '</div>' +
          '<div class="htl-col-track"><div class="htl-col-seg"></div></div>' +
          (i < n - 1 ? '<i class="htl-gap"></i>' : '') +
          '<div class="htl-col-range">' + esc(fmtSpan(era.from, era.to)) + '</div>' +
        '</div>';

      era.events.forEach(function (ev) {
        var yb = fmtSpan(ev.year, ev.endYear);
        var meta = [ev.place, ev.sides].filter(Boolean).join(' · ');
        cardsHtml +=
          '<article class="htl-ev" data-era="' + i + '">' +
            '<div class="htl-ev-in">' +
              '<span class="htl-ev-year">' + esc(yb) + '</span>' +
              '<h4 class="htl-ev-name">' + esc(ev.name) + '</h4>' +
              (meta ? '<div class="htl-ev-meta">' + esc(meta) + '</div>' : '') +
              (ev.result ? '<p class="htl-ev-result">' + esc(ev.result) + '</p>' : '') +
            '</div>' +
          '</article>';
      });
    });

    this.root.classList.add('htl');
    this.root.innerHTML =
      '<div class="htl-status" aria-hidden="true">' +
        '<span class="htl-status-dot"></span>' +
        '<span class="htl-status-era"></span>' +
        '<span class="htl-status-year"></span>' +
        '<span class="htl-status-count"></span>' +
        '<span class="htl-status-tag"></span>' +
      '</div>' +
      '<div class="htl-axis" tabindex="0" role="slider" aria-label="历史时间轴"' +
        ' aria-valuemin="0" aria-valuemax="1000" aria-valuenow="0" aria-valuetext="">' +
        colsHtml +
        '<div class="htl-knob">' +
          '<div class="htl-knob-line"></div>' +
          '<div class="htl-knob-head"></div>' +
          '<div class="htl-knob-bubble"></div>' +
        '</div>' +
        '<div class="htl-hit"></div>' +
      '</div>' +
      '<div class="htl-events-wrap">' +
        '<div class="htl-events-head">' +
          '<div class="htl-events-title"></div>' +
          '<a class="htl-era-link disabled" href="#"></a>' +
        '</div>' +
        '<div class="htl-events">' + cardsHtml + '</div>' +
      '</div>';

    /* 缓存引用 */
    this.elStatusEra = this.root.querySelector('.htl-status-era');
    this.elStatusYear = this.root.querySelector('.htl-status-year');
    this.elStatusCount = this.root.querySelector('.htl-status-count');
    this.elStatusTag = this.root.querySelector('.htl-status-tag');
    this.elAxis = this.root.querySelector('.htl-axis');
    this.elKnob = this.root.querySelector('.htl-knob');
    this.elKnobBubble = this.root.querySelector('.htl-knob-bubble');
    this.elHit = this.root.querySelector('.htl-hit');
    this.elTitle = this.root.querySelector('.htl-events-title');
    this.elLink = this.root.querySelector('.htl-era-link');

    this.cols = Array.prototype.slice.call(this.root.querySelectorAll('.htl-col'));
    this.ptsByEra = this.cols.map(function (col) {
      return Array.prototype.slice.call(col.querySelectorAll('.htl-pt'));
    });
    this.cardsByEra = this.eras.map(function (era, i) {
      return Array.prototype.slice.call(self.root.querySelectorAll('.htl-ev[data-era="' + i + '"]'));
    });
  };

  /* ── 交互绑定 ── */
  HistoryTimeline.prototype._bindAxis = function () {
    var self = this;
    var axis = this.elAxis;
    var hit = this.elHit;
    var dragging = false;
    var rafId = 0;
    var lastX = 0;

    function flush() {
      rafId = 0;
      var rect = axis.getBoundingClientRect();
      if (!rect.width) return;
      self.setFrac((lastX - rect.left) / rect.width);
    }
    function push(clientX) {
      lastX = clientX;
      if (!rafId) rafId = requestAnimationFrame(flush);
    }

    hit.addEventListener('pointerdown', function (e) {
      dragging = true;
      self.elKnob.classList.remove('glide');
      try { hit.setPointerCapture(e.pointerId); } catch (_) { /* 忽略 */ }
      axis.classList.add('dragging');
      self.root.classList.add('dragging');
      self.root.classList.add('peeking');
      e.preventDefault();
      push(e.clientX);
    });
    hit.addEventListener('pointermove', function (e) {
      if (dragging) push(e.clientX);
    });
    function endDrag() {
      if (!dragging) return;
      dragging = false;
      axis.classList.remove('dragging');
      self.root.classList.remove('dragging');
      clearTimeout(self._peekTimer);
      self._peekTimer = setTimeout(function () {
        self.root.classList.remove('peeking');
      }, 900);
    }
    hit.addEventListener('pointerup', endDrag);
    hit.addEventListener('pointercancel', endDrag);

    /* 点击时期名 → 平滑滑动至该时期中央 */
    this.cols.forEach(function (col, i) {
      col.querySelector('.htl-col-name').addEventListener('click', function () {
        self._glideTo((i + 0.5) / self.eras.length);
      });
    });

    /* 键盘操作 */
    axis.addEventListener('keydown', function (e) {
      var small = e.shiftKey ? 0.05 : 0.008;
      var handled = true;
      switch (e.key) {
        case 'ArrowLeft': case 'ArrowDown': self._step(-small); break;
        case 'ArrowRight': case 'ArrowUp': self._step(small); break;
        case 'PageDown': self._step(-0.05); break;
        case 'PageUp': self._step(0.05); break;
        case 'Home': self._glideTo(0); break;
        case 'End': self._glideTo(1); break;
        default: handled = false;
      }
      if (handled) e.preventDefault();
    });
  };

  HistoryTimeline.prototype._peek = function () {
    var self = this;
    this.root.classList.add('peeking');
    clearTimeout(this._peekTimer);
    this._peekTimer = setTimeout(function () {
      self.root.classList.remove('peeking');
    }, 1200);
  };

  HistoryTimeline.prototype._step = function (d) {
    this._peek();
    this.setFrac(this.frac + d);
  };

  HistoryTimeline.prototype._glideTo = function (frac) {
    var self = this;
    this.elKnob.classList.add('glide');
    this._peek();
    this.setFrac(frac);
    clearTimeout(this._glideTimer);
    this._glideTimer = setTimeout(function () {
      self.elKnob.classList.remove('glide');
    }, 420);
  };

  /* ── 核心：设置游标位置（拖动 / 键盘 / 程序调用统一入口） ── */
  HistoryTimeline.prototype.setFrac = function (frac) {
    var st = resolve(frac, this.eras);
    var prev = this.state;
    this.frac = st.frac;
    this.state = st;

    this.elKnob.style.left = (this.frac * 100).toFixed(4) + '%';
    this.elKnobBubble.textContent = fmtYear(st.year) + ' 年';
    /* 靠近两端时气泡改为贴边对齐，避免溢出容器 */
    this.elKnobBubble.classList.toggle('edge-left', this.frac < 0.06);
    this.elKnobBubble.classList.toggle('edge-right', this.frac > 0.94);

    var eraChanged = !prev || prev.i !== st.i;
    var yearChanged = !prev || prev.year !== st.year;

    if (eraChanged) this._activateEra(st.i);

    if (eraChanged || yearChanged) {
      this.elStatusYear.textContent = fmtYearFull(st.year);
      this._syncProgress(st.i, st.year);
      this.elAxis.setAttribute('aria-valuenow', String(Math.round(this.frac * 1000)));
      this.elAxis.setAttribute('aria-valuetext', st.era.name + '，' + fmtYearFull(st.year));
      if (this.onChange) {
        this.onChange({ era: st.era, eraIndex: st.i, year: st.year, t: st.t, frac: this.frac });
      }
    }
  };

  /* 设置年份（优先在指定 id 的时期内查找；找不到时按年份落入的时期） */
  HistoryTimeline.prototype.setYear = function (year, eraId) {
    var i = eraId != null ? this._eraIndexById(eraId) : -1;
    if (i < 0) {
      for (var k = 0; k < this.eras.length; k++) {
        var e = this.eras[k];
        var lo = Math.min(e.from, e.to), hi = Math.max(e.from, e.to);
        if (year >= lo && year <= hi) { i = k; break; }
      }
    }
    if (i < 0) i = 0;
    this._glideTo(fracOf(year, i, this.eras));
  };

  /* ── 时期切换：高亮、事件列表显隐、状态文案 ── */
  HistoryTimeline.prototype._activateEra = function (i) {
    var self = this;
    var era = this.eras[i];

    this.root.style.setProperty('--era', era.color);
    this.root.style.setProperty('--era-soft', hexToRgba(era.color, 0.16));

    this.cols.forEach(function (col, k) {
      col.classList.toggle('active', k === i);
    });

    /* 当前时期事件卡片显示（带错峰入场动画），其余全部隐藏 */
    this.eras.forEach(function (e, k) {
      var on = (k === i);
      self.cardsByEra[k].forEach(function (el, j) {
        el.classList.toggle('on', on);
        if (on) el.style.setProperty('--d', Math.min(j * 14, 240) + 'ms');
      });
    });

    var planned = era.status !== 'live';
    this.elTitle.innerHTML = '<b>' + esc(era.name) + '</b>' +
      '<span class="htl-events-count">共 ' + era.events.length + ' 件大事' +
      (era.period ? ' · ' + esc(era.period) : '') + '</span>';

    if (era.link) {
      this.elLink.setAttribute('href', era.link);
      this.elLink.classList.remove('disabled');
      this.elLink.textContent = '进入' + era.name + '地图 →';
    } else {
      this.elLink.removeAttribute('href');
      this.elLink.classList.add('disabled');
      this.elLink.textContent = '地图筹备中';
    }

    this.elStatusEra.textContent = era.name;
    this.elStatusCount.textContent = era.events.length + ' 件大事';
    this.elStatusTag.textContent = planned ? '筹备中' : '已上线';
    this.elStatusTag.classList.toggle('planned', planned);

    /* 强制进度状态全量刷新（避免跨段后残留旧状态） */
    this._progI = -1;
    this._progK = -1;
  };

  /* ── 进度同步：轴上事件点与卡片的「已发生 / 未至」状态 ── */
  HistoryTimeline.prototype._syncProgress = function (i, year) {
    var pts = this.ptsByEra[i];
    var cards = this.cardsByEra[i];
    var k = pastCount(this.eras[i].events, year);
    var j;

    if (this._progI !== i) {
      for (j = 0; j < pts.length; j++) {
        pts[j].classList.toggle('past', j < k);
        pts[j].classList.toggle('future', j >= k);
      }
      for (j = 0; j < cards.length; j++) {
        cards[j].classList.toggle('future', j >= k);
      }
    } else if (this._progK !== k) {
      var lo = Math.min(this._progK, k);
      var hi = Math.max(this._progK, k);
      for (j = lo; j < hi; j++) {
        var past = j < k;
        pts[j].classList.toggle('past', past);
        pts[j].classList.toggle('future', !past);
        cards[j].classList.toggle('future', !past);
      }
    }
    this._progI = i;
    this._progK = k;
  };

  HistoryTimeline.prototype.destroy = function () {
    this.root.innerHTML = '';
    this.root.classList.remove('htl', 'peeking');
    this.root.style.removeProperty('--era');
    this.root.style.removeProperty('--era-soft');
  };

  /* ────────────────────────── 导出 ────────────────────────── */

  return {
    HistoryTimeline: HistoryTimeline,
    Util: {
      clamp: clamp,
      esc: esc,
      hexToRgba: hexToRgba,
      fmtYear: fmtYear,
      fmtYearFull: fmtYearFull,
      fmtSpan: fmtSpan,
      parseEvents: parseEvents,
      resolve: resolve,
      fracOf: fracOf,
      layoutPoints: layoutPoints,
      pastCount: pastCount
    }
  };
});
