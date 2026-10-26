#!/usr/bin/env node
/*
 * 时间轴「步进」按钮补丁：
 *   - 新增 » 按钮：每点一次跳到下一个事件年份（all 态 → 第一个事件；末尾再点 → 回全部显示；循环）
 *   - 新增 MapTimeline.prototype.nextEvent()
 *   - 两页 map_timeline.js 版本戳升 2026102601
 *   - DOM 测试补步进用例
 * 默认 dry-run；--apply 写入。
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APPLY = process.argv.includes('--apply');

const RULES = {
  'timeline/map_timeline.js': [
    {
      name: '按钮区：新增步进按钮 »',
      old: `        '<button class="mtl-btn mtl-all" type="button" title="全部显示（复位，恢复初始视图）">⏭</button>' +`,
      neu: `        '<button class="mtl-btn mtl-next" type="button" title="下一个事件（步进）">»</button>' +\n        '<button class="mtl-btn mtl-all" type="button" title="全部显示（复位，恢复初始视图）">⏭</button>' +`
    },
    {
      name: '引用：elNext',
      old: `    this.elAll = this.root.querySelector('.mtl-all');`,
      neu: `    this.elNext = this.root.querySelector('.mtl-next');\n    this.elAll = this.root.querySelector('.mtl-all');`
    },
    {
      name: '绑定：步进按钮 click',
      old: `    this.elAll.addEventListener('click', function () {\n      engage();\n      self.showAll(true);\n      self._settle();\n    });`,
      neu: `    this.elNext.addEventListener('click', function () {\n      engage();\n      self.nextEvent();\n      self._settle();\n    });\n\n    this.elAll.addEventListener('click', function () {\n      engage();\n      self.showAll(true);\n      self._settle();\n    });`
    },
    {
      name: '方法：nextEvent()',
      old: `  MapTimeline.prototype._moveKnob = function (pos, glide) {`,
      neu: `  /* 步进：跳到下一个事件年份；all 态 → 第一个事件；末尾再点 → 回全部显示（循环） */\n  MapTimeline.prototype.nextEvent = function () {\n    if (!this.events.length) return;\n    if (this.mode === 'all') { this.setYear(this.events[0].year, true); return; }\n    for (var i = 0; i < this.events.length; i++) {\n      if (this.events[i].year > this.year) { this.setYear(this.events[i].year, true); return; }\n    }\n    this.showAll(true);\n  };\n\n  MapTimeline.prototype._moveKnob = function (pos, glide) {`
    }
  ],

  '汉末三国/index.html': [
    { name: '版本戳升 2026102601', old: `map_timeline.js?v=2026102501`, neu: `map_timeline.js?v=2026102601` }
  ],
  '楚汉争霸/index.html': [
    { name: '版本戳升 2026102601', old: `map_timeline.js?v=2026102501`, neu: `map_timeline.js?v=2026102601` }
  ],

  'tools/test_map_timeline_dom.js': [
    {
      name: '补步进按钮测试用例',
      old: `  console.log('\\n== 全部复位 ==');`,
      neu: `  console.log('\\n== 步进按钮（下一个事件） ==');
  el.querySelector('.mtl-all').dispatchEvent(new Ev('click'));      /* 先回 all 态 */
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('all 态点步进 → 第一个事件（190）', () => {
    assert.strictEqual(tl.getState().all, false);
    assert.strictEqual(tl.getState().year, 190);
  });
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('再点 → 200', () => assert.strictEqual(tl.getState().year, 200));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('连续步进 → 末事件 234', () => assert.strictEqual(tl.getState().year, 234));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('末事件再点 → 回全部显示', () => assert.strictEqual(tl.getState().all, true));
  el.querySelector('.mtl-next').dispatchEvent(new Ev('click'));
  ok('全部态再点 → 回到第一个事件（循环）', () => assert.strictEqual(tl.getState().year, 190));

  console.log('\\n== 全部复位 ==');`
    }
  ]
};

function patchFile(file, rules) {
  const abs = path.join(ROOT, file);
  let text = fs.readFileSync(abs, 'utf8');
  const eol = /\r\n/.test(text.slice(0, 4096)) ? '\r\n' : '\n';
  const co = (s) => s.split('\n').join(eol);
  let ok = true;
  const report = ['  · 换行 ' + JSON.stringify(eol)];

  rules.forEach(function (r) {
    const cnt = text.split(co(r.old)).length - 1;
    if (cnt !== 1) { ok = false; report.push('  ✗ [' + r.name + '] 匹配 ' + cnt + ' 次（期望 1）'); return; }
    text = text.split(co(r.old)).join(co(r.neu));
    report.push('  ✓ ' + r.name);
  });

  console.log('\n═══ ' + file + ' ═══');
  report.forEach(function (l) { console.log(l); });
  if (!ok) { console.log('  ⚠ 有规则未命中 → 未写入'); return false; }
  if (APPLY) { fs.writeFileSync(abs, text, 'utf8'); console.log('  → 已写入'); }
  else { console.log('  → dry-run（全部命中，未写入）'); }
  return true;
}

let all = true;
Object.keys(RULES).forEach(function (f) { if (!patchFile(f, RULES[f])) all = false; });
process.exit(all ? 0 : 1);
