// 主要城市图层 (省会/直辖市 · 古都 · 古战场重镇)
// 坐标为城市中心点经纬度，仅在地图上标注点位与名称，不绘制行政区划
// type 优先级: ancient_capital(古都) > capital(省会/直辖市) > battle(古战场/重镇)
// 同一城市有多重身份时，主 type 取最高优先级，所有身份在 tooltip 中显示
window.MAJOR_CITIES = {
  meta: {
    title: '中国主要城市 · 省会/直辖市/古都/古战场',
    types: {
      capital:          { label: '省会/直辖市',   color: '#7ad1e8', shape: 'circle',  radius: 4.5 },
      ancient_capital:  { label: '古都',           color: '#ffd24d', shape: 'star',    radius: 6.0 },
      battle:           { label: '古战场/重镇',    color: '#ff6b6b', shape: 'triangle',radius: 5.5 }
    }
  },
  features: [
    // ───────── 省会/直辖市（含特别行政区/台湾省治所）─────────
    { name:'北京', lon:116.41, lat:39.90, type:'capital', note:'中华人民共和国首都' },
    { name:'上海', lon:121.47, lat:31.23, type:'capital', note:'直辖市' },
    { name:'天津', lon:117.20, lat:39.13, type:'capital', note:'直辖市' },
    { name:'哈尔滨', lon:126.64, lat:45.75, type:'capital', note:'黑龙江省会' },
    { name:'长春', lon:125.32, lat:43.90, type:'capital', note:'吉林省会' },
    { name:'沈阳', lon:123.43, lat:41.80, type:'capital', note:'辽宁省会（清盛京）' },
    { name:'呼和浩特', lon:111.75, lat:40.84, type:'capital', note:'内蒙古自治区首府（归化/绥远）' },
    { name:'石家庄', lon:114.51, lat:38.04, type:'capital', note:'河北省会' },
    { name:'太原', lon:112.55, lat:37.87, type:'capital', note:'山西省会（晋阳）' },
    { name:'济南', lon:117.00, lat:36.65, type:'capital', note:'山东省会' },
    { name:'郑州', lon:113.62, lat:34.75, type:'capital', note:'河南省会（早商都城/管城）' },
    { name:'兰州', lon:103.84, lat:36.06, type:'capital', note:'甘肃省会（金城）' },
    { name:'西宁', lon:101.78, lat:36.62, type:'capital', note:'青海省会（鄯州）' },
    { name:'乌鲁木齐', lon:87.62, lat:43.83, type:'capital', note:'新疆维吾尔自治区首府（迪化）' },
    { name:'南京', lon:118.78, lat:32.06, type:'capital', note:'江苏省会' },
    { name:'合肥', lon:117.28, lat:31.86, type:'capital', note:'安徽省会（逍遥津之战地）' },
    { name:'杭州', lon:120.16, lat:30.27, type:'capital', note:'浙江省会' },
    { name:'福州', lon:119.30, lat:26.08, type:'capital', note:'福建省会（冶城/福州）' },
    { name:'南昌', lon:115.89, lat:28.68, type:'capital', note:'江西省会（豫章/洪州）' },
    { name:'武汉', lon:114.30, lat:30.59, type:'capital', note:'湖北省会（夏口/江夏）' },
    { name:'长沙', lon:112.94, lat:28.23, type:'capital', note:'湖南省会' },
    { name:'广州', lon:113.27, lat:23.13, type:'capital', note:'广东省会' },
    { name:'海口', lon:110.32, lat:20.04, type:'capital', note:'海南省会' },
    { name:'南宁', lon:108.37, lat:22.82, type:'capital', note:'广西壮族自治区首府（邕州）' },
    { name:'贵阳', lon:106.71, lat:26.60, type:'capital', note:'贵州省会（贵州/顺元）' },
    { name:'昆明', lon:102.72, lat:25.04, type:'capital', note:'云南省会（拓东/善阐）' },
    { name:'香港', lon:114.17, lat:22.32, type:'capital', note:'特别行政区' },
    { name:'澳门', lon:113.55, lat:22.20, type:'capital', note:'特别行政区（濠镜）' },
    { name:'台北', lon:121.50, lat:25.04, type:'capital', note:'台湾省治所' },

    // ───────── 古都（八大古都 + 其他重要古都）─────────
    { name:'西安', lon:108.94, lat:34.34, type:'ancient_capital', note:'古长安·西周/秦/西汉/隋/唐等十三朝古都' },
    { name:'洛阳', lon:112.45, lat:34.62, type:'ancient_capital', note:'古洛邑·东周/东汉/曹魏/西晋/北魏/武周/五代后唐等九朝古都' },
    { name:'开封', lon:114.31, lat:34.79, type:'ancient_capital', note:'古汴梁·战国魏/五代/北宋/金等七朝古都' },
    { name:'安阳', lon:114.40, lat:36.10, type:'ancient_capital', note:'古殷墟/邺城·商/曹魏/后赵/东魏/北齐都' },
    { name:'咸阳', lon:108.71, lat:34.34, type:'ancient_capital', note:'秦都（与长安隔渭水相望）' },
    { name:'大同', lon:113.30, lat:40.08, type:'ancient_capital', note:'古平城·北魏前期都城/辽金陪都' },
    { name:'成都', lon:104.07, lat:30.67, type:'ancient_capital', note:'古蜀·蜀汉/成汉/前蜀/后蜀等割据都城' },
    { name:'银川', lon:106.23, lat:38.49, type:'ancient_capital', note:'古兴庆府·西夏都城' },
    { name:'拉萨', lon:91.13, lat:29.65, type:'ancient_capital', note:'古逻些·吐蕃都城' },
    { name:'江陵', lon:112.24, lat:30.33, type:'ancient_capital', note:'古郢都·楚国都城/南朝萧梁都/五代荆南都' },
    { name:'许昌', lon:113.85, lat:34.04, type:'ancient_capital', note:'古许县·东汉末献帝都/曹魏五都之一' },
    { name:'邺城', lon:114.61, lat:36.32, type:'ancient_capital', note:'古邺·曹魏/后赵/冉魏/前燕/东魏/北齐都' },
    { name:'武威', lon:102.64, lat:37.93, type:'ancient_capital', note:'古姑臧·前凉/后凉/南凉/北凉都' },
    { name:'吐鲁番', lon:89.19, lat:42.95, type:'ancient_capital', note:'古高昌·高昌国都城' },

    // ───────── 古战场/重镇（按朝代）─────────
    // 先秦
    { name:'涿鹿', lon:115.42, lat:40.36, type:'battle', note:'涿鹿之战·黄帝与蚩尤决战' },
    { name:'牧野', lon:113.93, lat:35.37, type:'battle', note:'牧野之战·武王伐纣灭商（前1046）' },
    { name:'长平', lon:112.92, lat:35.80, type:'battle', note:'长平之战·秦坑赵卒四十万（前260）' },
    // 秦汉
    { name:'巨鹿', lon:114.93, lat:37.10, type:'battle', note:'巨鹿之战·项羽破釜沉舟破秦（前207）' },
    { name:'井陉', lon:114.14, lat:38.13, type:'battle', note:'井陉之战·韩信背水阵破赵（前204）' },
    { name:'垓下', lon:117.40, lat:33.50, type:'battle', note:'垓下之战·楚汉决战，项羽乌江自刎（前202）' },
    { name:'玉门关', lon:93.87, lat:40.30, type:'battle', note:'汉开西域门户·汉匈争夺要塞' },
    // 三国
    { name:'官渡', lon:114.07, lat:34.74, type:'battle', note:'官渡之战·曹操以少胜多破袁绍（200）' },
    { name:'赤壁', lon:113.90, lat:29.72, type:'battle', note:'赤壁之战·孙刘联军火烧曹军（208）' },
    { name:'夷陵', lon:111.29, lat:30.70, type:'battle', note:'夷陵之战·陆逊火烧连营破刘备（222）' },
    { name:'樊城', lon:112.18, lat:32.12, type:'battle', note:'襄樊之战·关羽水淹七军围樊城（219）' },
    { name:'麦城', lon:111.79, lat:30.82, type:'battle', note:'关羽败走麦城被擒（219）' },
    { name:'虎牢关', lon:113.39, lat:34.78, type:'battle', note:'虎牢关之战·三英战吕布传说地' },
    { name:'汉中', lon:107.03, lat:33.07, type:'battle', note:'汉中之战·刘备取汉中称王（219）' },
    { name:'定军山', lon:106.86, lat:33.13, type:'battle', note:'定军山之战·黄忠斩夏侯渊（219）' },
    { name:'街亭', lon:105.93, lat:35.10, type:'battle', note:'街亭之战·马谡失守，诸葛亮一出祁山受挫（228）' },
    { name:'五丈原', lon:107.51, lat:34.20, type:'battle', note:'五丈原之战·诸葛亮病逝于此（234）' },
    { name:'白帝城', lon:109.55, lat:31.04, type:'battle', note:'夷陵兵败后·刘备托孤于诸葛亮（223）' },
    { name:'柴桑', lon:115.97, lat:29.71, type:'battle', note:'赤壁战前孙权驻节决策地' },
    { name:'寿春', lon:116.78, lat:32.55, type:'battle', note:'淮南三叛·曹魏反司马氏主战场（251-258）；淝水之战·东晋以少胜多破前秦（383）' },
    { name:'徐州', lon:117.28, lat:34.21, type:'battle', note:'古彭城·楚汉相争与三国争夺要地' },
    // 隋唐宋
    { name:'襄阳', lon:112.14, lat:32.04, type:'battle', note:'襄阳之战·宋元对峙六年城破（1267-1273）' },
    { name:'钓鱼城', lon:106.27, lat:29.99, type:'battle', note:'钓鱼城之战·宋抗蒙36年，蒙哥汗殁于此（1243-1279）' },
    { name:'崖山', lon:113.04, lat:22.50, type:'battle', note:'崖山海战·南宋亡国（1279）' },
    { name:'鄱阳湖', lon:116.30, lat:29.10, type:'battle', note:'鄱阳湖之战·朱元璋灭陈友谅（1363）' },
    // 明清
    { name:'山海关', lon:119.74, lat:40.00, type:'battle', note:'山海关之战·吴三桂引清军入关（1644）' },
    { name:'宁远', lon:120.80, lat:40.83, type:'battle', note:'宁远之战·袁崇焕炮击努尔哈赤（1626）' },
    { name:'雅克萨', lon:122.27, lat:50.35, type:'battle', note:'雅克萨之战·清抗击沙俄（1685-1686）' }
  ]
};
