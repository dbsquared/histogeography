// 华夏历史地图 · 时间轴事件数据
// ─────────────────────────────────────────────────────────────
// 楚汉争霸 / 汉末三国：事件转录自项目既有数据（楚汉争霸/chu_han_sites.js、
//   汉末三国/three_kingdoms_sites.js 的 battle 数组），与地图页保持同源。
// 先秦 / 唐 / 明：平台筹备时期，仅收录通行史观下的标志性事件（年份取通说）。
//
// 数据约定：
//   year / endYear —— 数值年份，负数表示公元前（如 -209 = 公元前 209 年）；
//     endYear 缺省表示瞬时事件（当年发生）。
//   from / to       —— 时期在时间轴上的映射区间（years）。
//   status          —— 'live' 已上线（可进入地图）| 'planned' 筹备中。
//   color           —— 该时期在组件中的识别色。
//   link            —— 已上线时期的地图入口（相对当前页面）。
// ─────────────────────────────────────────────────────────────
(function (root, factory) {
  var data = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = { HISTORY_TIMELINE_DATA: data };
  if (typeof window !== 'undefined') window.HISTORY_TIMELINE_DATA = data;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  return {
    eras: [
      // ── 一、先秦：西周至战国 ──
      {
        id: 'pre-qin',
        name: '先秦',
        period: '西周至战国',
        status: 'planned',
        color: '#c9a227',
        from: -1046,
        to: -221,
        note: '诸侯会盟与列国疆域',
        link: null,
        events: [
          { name: '牧野之战·西周建立', year: -1046, place: '牧野（河南淇县南）', sides: '周武王 vs 商纣王', result: '武王伐纣，商亡周兴，封建诸侯，礼乐肇基' },
          { name: '国人暴动·共和行政', year: -841, place: '镐京（陕西西安）', sides: '国人 vs 周厉王', result: '厉王暴虐被逐，周召共和执政，中国确切纪年始此' },
          { name: '犬戎破镐京·平王东迁', year: -771, place: '镐京（陕西西安）', sides: '犬戎 vs 周室', result: '西周覆亡，周室东迁洛邑，春秋时代开始' },
          { name: '齐桓公称霸', year: -651, place: '葵丘（河南兰考）', sides: '齐 vs 诸侯', result: '葵丘会盟，"尊王攘夷"，春秋首霸' },
          { name: '城濮之战·践土之盟', year: -632, place: '城濮（山东鄄城）', sides: '晋 vs 楚', result: '晋文公退避三舍败楚，会盟称霸中原' },
          { name: '勾践灭吴', year: -473, place: '姑苏（江苏苏州）', sides: '越 vs 吴', result: '卧薪尝胆二十年，越灭吴，北上会盟称霸' },
          { name: '三家分晋', year: -403, place: '晋（山西一带）', sides: '韩、赵、魏 vs 晋室', result: '三家列为诸侯，战国时代开始' },
          { name: '商鞅变法', year: -356, place: '咸阳（陕西咸阳）', sides: '秦孝公、商鞅', result: '废井田、开阡陌、行军功，秦强之基' },
          { name: '桂陵之战', year: -353, place: '桂陵（河南长垣）', sides: '齐（孙膑） vs 魏（庞涓）', result: '围魏救赵，魏军大败' },
          { name: '长平之战', year: -260, place: '长平（山西高平）', sides: '秦（白起） vs 赵', result: '赵军尽丧，六国再无力抗秦' },
          { name: '秦灭六国', year: -230, endYear: -221, place: '咸阳（陕西咸阳）', sides: '秦王政 vs 六国', result: '自灭韩至灭齐，十年并天下，秦朝建立' }
        ]
      },

      // ── 二、楚汉争霸：秦亡至汉兴（事件同源于 chu_han_sites.js）──
      {
        id: 'chu-han',
        name: '楚汉争霸',
        period: '秦亡至汉兴',
        status: 'live',
        color: '#ffd479',
        from: -209,
        to: -202,
        note: '十八诸侯国疆域与都邑',
        link: '../楚汉争霸/',
        events: [
          { name: '大泽乡起义', year: -209, place: '大泽乡（安徽宿州东南）', sides: '陈胜、吴广 vs 秦', result: '中国历史上第一次大规模农民起义，反秦序幕由此拉开' },
          { name: '定陶之战', year: -208, place: '定陶（山东定陶）', sides: '章邯 vs 项梁', result: '项梁兵败战死，反秦军一时受挫' },
          { name: '巨鹿之战', year: -207, place: '巨鹿（河北平乡西南）', sides: '项羽 vs 秦（章邯、王离）', result: '破釜沉舟，秦军主力尽丧，诸侯皆属项羽' },
          { name: '蓝田之战', year: -207, place: '蓝田（陕西蓝田）', sides: '刘邦 vs 秦', result: '破秦军最后屏障，刘邦直抵霸上' },
          { name: '霸上受降', year: -207, place: '霸上（陕西西安东南·白鹿原）', sides: '秦王子婴 vs 刘邦', result: '子婴素车白马出降，秦朝灭亡' },
          { name: '鸿门宴', year: -206, place: '鸿门（陕西临潼东）', sides: '刘邦 vs 项羽（范增）', result: '项庄舞剑、樊哙护主；刘邦脱险归霸上，楚汉裂痕始此' },
          { name: '陈仓之战', year: -206, place: '陈仓（陕西宝鸡东）', sides: '韩信、刘邦 vs 章邯', result: '“明修栈道，暗度陈仓”，还定三秦之始' },
          { name: '好畤之战', year: -206, place: '好畤（陕西乾县东）', sides: '刘邦 vs 章邯', result: '章邯连败，退守废丘孤城' },
          { name: '田荣并三齐', year: -206, endYear: -205, place: '临淄（齐地）', sides: '田荣 vs 田都、田市、田安', result: '击杀三齐王，并地自立；项羽北上伐齐，刘邦得以东出' },
          { name: '废丘之围', year: -205, place: '废丘（陕西兴平东南）', sides: '刘邦（韩信） vs 章邯', result: '围城近一年，城破章邯自杀，雍亡' },
          { name: '彭城之战', year: -205, place: '彭城、睢水（江苏徐州南）', sides: '项羽 vs 刘邦（诸侯联军）', result: '项羽三万精骑大破汉军五十六万，睢水为之不流' },
          { name: '京索之战', year: -205, place: '京索（河南荥阳东南）', sides: '刘邦（韩信、曹参等） vs 楚', result: '汉军止住溃势，荥阳—成皋防线得以建立' },
          { name: '安邑之战', year: -205, place: '安邑（山西夏县西北）', sides: '韩信 vs 魏豹', result: '木罂缻渡河奇袭，魏豹被俘，魏亡' },
          { name: '阏与之战', year: -205, place: '阏与（山西和顺）', sides: '韩信 vs 代（夏说）', result: '破代军，擒代相夏说' },
          { name: '井陉之战', year: -204, place: '井陉（河北井陉北）', sides: '韩信 vs 赵（陈余）', result: '背水一战，大破赵军二十万' },
          { name: '泜水之战', year: -204, place: '泜水（河北高邑南）', sides: '韩信 vs 赵', result: '追斩成安君陈余于泜水，赵地遂定' },
          { name: '历下之战', year: -204, place: '历下（山东济南）', sides: '韩信（袭齐） vs 齐', result: '齐历下军溃散，韩信乘虚直入临淄' },
          { name: '荥阳之围', year: -204, place: '荥阳（河南荥阳）', sides: '项羽 vs 刘邦', result: '纪信诈降代死，刘邦得以脱走成皋' },
          { name: '成皋之战', year: -204, place: '成皋（河南荥阳汜水镇）', sides: '刘邦 vs 曹咎（楚）', result: '曹咎渡汜水半渡被击，楚军覆没，成皋归汉' },
          { name: '广武对峙·鸿沟之约', year: -203, place: '广武、鸿沟（河南荥阳北）', sides: '刘邦 vs 项羽', result: '相持经年，约中分天下：鸿沟以西属汉、以东属楚' },
          { name: '潍水之战', year: -203, place: '潍水（山东高密一带）', sides: '韩信 vs 楚（龙且）', result: '壅水断流、半渡而击，龙且败死，齐地底定' },
          { name: '固陵之战', year: -202, place: '固陵（河南太康南）', sides: '项羽（反击） vs 刘邦', result: '汉军追击败绩，张良献策裂土封韩信、彭越' },
          { name: '陈下之战', year: -202, place: '陈下（河南淮阳）', sides: '刘邦、灌婴等 vs 项羽', result: '楚军再败，项羽退保垓下' },
          { name: '垓下之战', year: -202, place: '垓下（安徽固镇濠城·一说灵璧）', sides: '刘邦（韩信为主将） vs 项羽', result: '十面埋伏、四面楚歌，楚军崩溃，项羽夜遁' },
          { name: '乌江自刎', year: -202, place: '乌江（安徽和县东北·长江北岸）', sides: '项羽 vs 汉军追兵', result: '项羽愧见江东父老，自刎乌江，楚汉战争终以汉胜' },
          { name: '灭临江之战', year: -202, place: '江陵（湖北荆州）', sides: '汉（刘贾、卢绾） vs 共尉（临江）', result: '江陵城破，共尉被擒，临江亡' }
        ]
      },

      // ── 三、汉末三国：东汉末年至三国（事件同源于 three_kingdoms_sites.js）──
      {
        id: 'han-san-guo',
        name: '汉末三国',
        period: '东汉末年至三国',
        status: 'live',
        color: '#e06666',
        from: 184,
        to: 280,
        note: '十三州州界与郡治',
        link: '../汉末三国/',
        events: [
          { name: '虎牢关之战', year: 190, place: '虎牢关', sides: '关东联军 vs 董卓', result: '联军无功，董卓迁都长安' },
          { name: '界桥之战', year: 191, place: '界桥（河北威县）', sides: '袁绍 vs 公孙瓒', result: '袁绍确立河北优势' },
          { name: '宛城之战', year: 197, place: '宛城', sides: '曹操 vs 张绣', result: '曹操失典韦、曹昂' },
          { name: '易京之战', year: 198, place: '易京（河北雄县）', sides: '袁绍 vs 公孙瓒', result: '公孙瓒亡，袁绍并幽冀' },
          { name: '下邳之战', year: 198, place: '下邳', sides: '曹操 vs 吕布', result: '吕布被擒斩' },
          { name: '官渡之战', year: 200, place: '官渡', sides: '曹操 vs 袁绍', result: '曹操以少胜多，统一北方关键' },
          { name: '白马/延津之战', year: 200, place: '白马津、延津', sides: '曹操 vs 袁绍', result: '关羽斩颜良，解白马围' },
          { name: '博望坡之战', year: 202, place: '博望（河南方城）', sides: '刘备 vs 曹仁', result: '刘备用火败曹军（演义）' },
          { name: '赤壁之战', year: 208, place: '赤壁/乌林', sides: '孙刘联军 vs 曹操', result: '三国鼎立奠基' },
          { name: '长坂坡之战', year: 208, place: '当阳', sides: '曹操 vs 刘备', result: '赵云救阿斗，张飞断桥' },
          { name: '江陵之争', year: 208, endYear: 209, place: '江陵', sides: '周瑜 vs 曹仁', result: '孙权取南郡' },
          { name: '逍遥津之战', year: 215, place: '合肥', sides: '张辽 vs 孙权', result: '张辽以少破吴' },
          { name: '濡须口之战', year: 217, place: '濡须口', sides: '曹操 vs 孙权', result: '互有胜负，划江而治' },
          { name: '汉中之战', year: 217, endYear: 219, place: '汉中/定军山', sides: '刘备 vs 曹操', result: '刘备取汉中，称汉中王' },
          { name: '定军山之战', year: 219, place: '定军山', sides: '黄忠 vs 夏侯渊', result: '斩夏侯渊' },
          { name: '樊城之战（水淹七军）', year: 219, place: '樊城/襄阳', sides: '关羽 vs 曹仁/于禁', result: '关羽威震华夏，后吕蒙袭荆州' },
          { name: '麦城之围', year: 219, place: '麦城（湖北当阳）', sides: '孙权 vs 关羽', result: '关羽败亡' },
          { name: '夷陵/猇亭之战', year: 222, place: '猇亭（湖北宜昌）', sides: '陆逊 vs 刘备', result: '蜀汉元气大伤' },
          { name: '南中（七擒孟获）', year: 225, place: '南中（今云南、贵州及四川西南部）', sides: '蜀汉 vs 南中诸部（孟获等）', result: '七擒孟获，南中平定，蜀汉后方得固' },
          { name: '街亭之战', year: 228, place: '街亭', sides: '马谡 vs 张郃', result: '诸葛亮首发失利' },
          { name: '石亭之战', year: 228, place: '石亭（安徽潜山）', sides: '陆逊 vs 曹休', result: '东吴破魏' },
          { name: '祁山之战（多次）', year: 228, endYear: 234, place: '祁山', sides: '诸葛亮 vs 曹真/司马懿', result: '北伐主线' },
          { name: '陈仓之战', year: 229, place: '陈仓（宝鸡）', sides: '诸葛亮 vs 郝昭', result: '蜀攻魏不克' },
          { name: '武都阴平之战', year: 229, place: '武都、阴平（今陇南一带）', sides: '蜀汉（陈式、诸葛亮） vs 曹魏（郭淮）', result: '蜀取武都、阴平二郡，北伐唯一实质扩地' },
          { name: '卤城之战', year: 231, place: '卤城（甘肃礼县东北）', sides: '诸葛亮 vs 司马懿', result: '蜀军大胜，获甲首三千' },
          { name: '木门道之战', year: 231, place: '木门道（甘肃天水西南）', sides: '蜀军伏击 vs 张郃', result: '张郃中伏中箭而亡' },
          { name: '合肥新城之战', year: 233, place: '合肥', sides: '孙权 vs 满宠', result: '吴攻魏不克' },
          { name: '五丈原之战', year: 234, place: '五丈原（陕西岐山·渭水南岸）', sides: '诸葛亮 vs 司马懿', result: '诸葛亮病逝' },
          { name: '洮西/狄道之战', year: 255, place: '狄道（甘肃临洮）', sides: '姜维 vs 王经', result: '蜀胜魏' },
          { name: '寿春之战', year: 257, place: '寿春', sides: '司马昭 vs 诸葛诞', result: '平定淮南三叛最后一叛' },
          { name: '阴平偷渡', year: 263, place: '阴平道', sides: '邓艾 vs 蜀', result: '奇袭成都，蜀汉亡' },
          { name: '绵竹之战', year: 263, place: '绵竹', sides: '诸葛瞻 vs 邓艾', result: '蜀军败，刘禅出降' },
          { name: '西陵之战', year: 272, place: '西陵（湖北宜昌）', sides: '陆抗 vs 步阐', result: '吴平内乱' },
          { name: '晋灭吴', year: 280, place: '建业/长江沿线', sides: '晋 vs 吴', result: '三国归晋' }
        ]
      },

      // ── 四、唐（筹备中）──
      {
        id: 'tang',
        name: '唐',
        period: '隋末至唐末',
        status: 'planned',
        color: '#7fb2d9',
        from: 618,
        to: 907,
        note: '道州县体系与丝路通道',
        link: null,
        events: [
          { name: '唐朝建立', year: 618, place: '长安（陕西西安）', sides: '李渊', result: '李渊称帝建唐，定都长安' },
          { name: '玄武门之变·贞观之治', year: 626, place: '长安（陕西西安）', sides: '李世民 vs 李建成', result: '李世民即位，纳谏图治，四夷宾服' },
          { name: '唐灭东突厥', year: 630, place: '阴山（内蒙古）', sides: '李靖 vs 东突厥', result: '夜袭阴山，颉利可汗被擒，太宗被尊"天可汗"' },
          { name: '文成公主入藏', year: 641, place: '吐蕃（西藏）', sides: '唐蕃和亲', result: '松赞干布迎娶文成公主，汉藏交流一时之盛' },
          { name: '安史之乱', year: 755, endYear: 763, place: '范阳（北京）→洛阳·长安', sides: '安禄山、史思明 vs 唐', result: '八年战乱，唐由盛转衰' },
          { name: '推行两税法', year: 780, place: '长安（陕西西安）', sides: '杨炎', result: '以资产为宗、夏秋两征，赋税制度大变' },
          { name: '黄巢起义', year: 875, endYear: 884, place: '曹州（山东菏泽）→长安', sides: '黄巢 vs 唐', result: '席卷大半个中国，唐廷濒临崩溃' },
          { name: '朱温篡唐·唐亡', year: 907, place: '汴州（河南开封）', sides: '朱温 vs 唐哀帝', result: '唐亡，五代十国开始' }
        ]
      },

      // ── 五、明（筹备中）──
      {
        id: 'ming',
        name: '明',
        period: '元末至明末',
        status: 'planned',
        color: '#b08de0',
        from: 1368,
        to: 1644,
        note: '两京十三布政使司',
        link: null,
        events: [
          { name: '明朝建立', year: 1368, place: '应天（江苏南京）', sides: '朱元璋', result: '称帝建明，北伐逐元' },
          { name: '郑和下西洋', year: 1405, endYear: 1433, place: '刘家港（江苏太仓）', sides: '郑和', result: '七下西洋，远航规模空前' },
          { name: '迁都北京', year: 1421, place: '北京', sides: '明成祖', result: '迁都北京，营建紫禁城' },
          { name: '土木堡之变', year: 1449, place: '土木堡（河北怀来）', sides: '瓦剌 vs 明', result: '英宗被俘，于谦守京师' },
          { name: '戚继光抗倭', year: 1555, endYear: 1565, place: '东南沿海', sides: '戚继光 vs 倭寇', result: '练兵平倭，东南海疆渐靖' },
          { name: '张居正改革', year: 1572, endYear: 1582, place: '北京', sides: '张居正', result: '考成法、一条鞭法，号称中兴' },
          { name: '萨尔浒之战', year: 1619, place: '萨尔浒（辽宁抚顺）', sides: '后金 vs 明', result: '明军四路败绩，后金入主辽东之势成' },
          { name: '明朝灭亡', year: 1644, place: '北京', sides: '李自成 vs 明', result: '大顺军入京，崇祯帝自缢，明亡' }
        ]
      }
    ]
  };
});
