/* water_info.js —— 河流 / 湖泊 点击信息面板
 * 内容三段：基本信息 · 数据 · 重要历史事件
 * 用法：时期页构建水域图层后调用
 *   WaterInfo.attach({riverLayer, lakeLayer}, showInfo)
 * 未收录的河湖自动回退为「基础信息」+「暂无收录」，保证任何一条都能点出内容。
 * 数值为通行说法（约数），仅供历史地理参考；坐标与几何来自 Natural Earth 10m / 手工补绘。
 */
(function(){
  'use strict';

  var WATER_INFO = {
    /* ══════════════════════ 主要河流 ══════════════════════ */
    '长江': {
      water:'长江水系 → 东海', origin:'青海省唐古拉山各拉丹冬雪山（正源沱沱河）',
      flows:'青海、西藏、四川、云南、重庆、湖北、湖南、江西、安徽、江苏、上海', mouth:'上海市崇明岛附近注入东海',
      length:'约 6300 km（中国第一大河）', area:'流域约 180 万 km²',
      events:[
        {y:'前278', t:'秦将白起拔郢，楚东迁；江汉流域归秦'},
        {y:'208', t:'赤壁之战：孙刘联军于赤壁大破曹操水军，奠定三国鼎立'},
        {y:'222', t:'夷陵之战：陆逊火烧连营，大破刘备于猇亭'},
        {y:'280', t:'西晋王濬楼船自益州顺江东下，灭吴'},
        {y:'三国', t:'魏、蜀、吴隔江对峙，长江成为南北政权分界'}
      ]
    },
    '黄河': {
      water:'黄河水系 → 渤海', origin:'青海省巴颜喀拉山北麓约古宗列曲',
      flows:'青海、四川、甘肃、宁夏、内蒙古、陕西、山西、河南、山东', mouth:'山东省东营市垦利区注入渤海',
      length:'约 5464 km（中国第二大河）', area:'流域约 75 万 km²',
      events:[
        {y:'前225', t:'秦将王贲引黄河水灌魏都大梁，魏亡'},
        {y:'西汉', t:'瓠子决口，汉武帝亲临堵口；东汉王景治河，河患稍息'},
        {y:'200', t:'官渡之战：曹操于黄河沿岸白马、延津一带破袁绍前锋'},
        {y:'204', t:'曹操破邺城，据河北；黄河以北为曹魏根基'},
        {y:'220', t:'曹丕于洛阳受禅称帝，国号魏'}
      ]
    },
    '汉江': {
      water:'长江最大支流', origin:'陕西省宁强县秦岭南麓（蟠冢山）',
      flows:'陕西（汉中、安康）、湖北（十堰、襄阳、荆门、天门、孝感）', mouth:'武汉市汉口注入长江',
      length:'约 1577 km（长江最长支流）', area:'流域约 15.9 万 km²',
      events:[
        {y:'前206', t:'项羽封刘邦为汉王，"王巴、蜀、汉中，都南郑"；刘邦自汉中"还定三秦"'},
        {y:'西汉', t:'汉朝国号"汉"即源于汉水、汉中'},
        {y:'219', t:'关羽利用汉水暴涨"水淹七军"，擒于禁、斩庞德，威震华夏'},
        {y:'三国', t:'汉中—襄阳沿汉水对峙，为魏蜀交锋主轴'}
      ]
    },
    '洛水': {
      water:'黄河支流（南洛河）', origin:'陕西省洛南县（秦岭南麓）',
      flows:'陕西洛南，河南卢氏、洛宁、宜阳、洛阳', mouth:'巩义市东北洛口注入黄河',
      length:'约 447 km', area:'流域约 1.89 万 km²',
      events:[
        {y:'上古', t:'"河图洛书"传说，洛水出书，为华夏文明重要意象'},
        {y:'25', t:'东汉光武帝定都洛阳，洛阳因"水北为阳"得名'},
        {y:'190', t:'董卓焚洛阳、挟献帝西迁长安，宫室焚毁殆尽'},
        {y:'220', t:'曹丕于洛阳繁阳亭受禅称帝'},
        {y:'约222', t:'曹植作《洛神赋》，咏洛水之神宓妃'}
      ]
    },
    '淮河': {
      water:'淮河水系（今大部经洪泽湖入长江）', origin:'河南省桐柏县桐柏山太白顶',
      flows:'河南、安徽、江苏', mouth:'原独流入海，1128 年黄河夺淮后主流经洪泽湖入长江',
      length:'约 1000 km', area:'流域约 27 万 km²',
      events:[
        {y:'前203', t:'楚汉以鸿沟为界，鸿沟南通淮河、北连黄河'},
        {y:'383', t:'淝水之战（淮河支流淝水）：东晋以少胜多大破前秦'},
        {y:'三国', t:'淮南为魏吴争夺焦点，合肥、寿春反复易手'}
      ]
    },
    '湘江': {
      water:'长江支流 → 洞庭湖', origin:'广西灵川县海洋山',
      flows:'湖南永州、衡阳、株洲、湘潭、长沙', mouth:'注入洞庭湖，经城陵矶入长江',
      length:'约 856 km', area:'流域约 9.46 万 km²',
      events:[
        {y:'前219', t:'秦始皇凿灵渠，沟通湘江与漓江，通岭南'},
        {y:'215', t:'孙刘"湘水之盟"，以湘水为界中分荆州'},
        {y:'三国', t:'湘江流域为荆南四郡腹地，孙刘反复争夺'}
      ]
    },
    '珠江': {
      water:'珠江水系 → 南海', origin:'云南省曲靖市马雄山（西江源）',
      flows:'云南、贵州、广西、广东', mouth:'珠江口注入南海',
      length:'约 2320 km（以西江为主）', area:'流域约 45 万 km²',
      events:[
        {y:'前214', t:'秦定岭南，置桂林、南海、象郡'},
        {y:'秦末', t:'赵佗建南越国，都番禺'},
        {y:'前111', t:'汉武帝灭南越，置九郡'}
      ]
    },
    '黑龙江': {
      water:'黑龙江水系 → 鄂霍次克海', origin:'蒙古肯特山（鄂嫩河）／中国境内以海拉尔河—额尔古纳河为源',
      flows:'中俄界河，经漠河、黑河、同江', mouth:'俄罗斯尼古拉耶夫斯克附近注入鄂霍次克海',
      length:'约 4444 km', area:'流域约 185 万 km²',
      events:[
        {y:'唐', t:'黑水靺鞨居黑龙江流域，唐置黑水都督府'},
        {y:'金', t:'女真兴起于"白山黑水"'},
        {y:'1685-1686', t:'雅克萨之战；1689 年《尼布楚条约》划定中俄东段边界'}
      ]
    },
    '松花江': {
      water:'黑龙江最大支流', origin:'长白山天池（二道白河）',
      flows:'吉林、黑龙江（吉林、哈尔滨、佳木斯）', mouth:'同江市注入黑龙江',
      length:'约 1927 km', area:'流域约 55.7 万 km²',
      events:[
        {y:'1115', t:'金太祖完颜阿骨打建金，上京会宁府（今哈尔滨阿城）临近松花江支流阿什河'},
        {y:'明', t:'设奴儿干都司，经松花江、黑龙江下航至奴儿干'}
      ]
    },
    '辽河': {
      water:'辽河水系 → 渤海', origin:'河北平泉（西辽河源）／吉林哈达岭（东辽河源）',
      flows:'河北、内蒙古、辽宁', mouth:'盘锦市注入渤海',
      length:'约 1345 km', area:'流域约 21.9 万 km²',
      events:[
        {y:'前222', t:'秦破燕，取辽东'},
        {y:'唐', t:'唐太宗、高宗征高句丽，辽东为前线'},
        {y:'辽', t:'契丹以辽河流域为腹地，国号"辽"即源于辽河'}
      ]
    },
    '海河': {
      water:'海河水系 → 渤海', origin:'太行山、燕山诸支流（永定河、滹沱河、漳河等）',
      flows:'北京、天津、河北', mouth:'天津大沽口注入渤海',
      length:'干流约 73 km（各支流合计逾千公里）', area:'流域约 31.8 万 km²',
      events:[
        {y:'前204', t:'韩信破赵于井陉，背水一战于滹沱河（海河支流）'},
        {y:'三国', t:'曹魏据河北，以邺城为治所，海河平原为粮赋重地'}
      ]
    },
    '嘉陵江': {
      water:'长江支流', origin:'陕西省凤县秦岭南麓',
      flows:'陕西、甘肃、四川、重庆', mouth:'重庆市注入长江',
      length:'约 1120 km', area:'流域约 16 万 km²',
      events:[
        {y:'三国', t:'诸葛亮北伐多以嘉陵江流域为侧翼，蜀汉据剑阁之险'},
        {y:'1258', t:'蒙古攻钓鱼城（嘉陵江、渠江、涪江交汇），久攻不下'}
      ]
    },
    '岷江': {
      water:'长江支流', origin:'四川省松潘县岷山',
      flows:'四川（成都、乐山、宜宾）', mouth:'宜宾市注入长江',
      length:'约 735 km', area:'流域约 13.6 万 km²',
      events:[
        {y:'前256', t:'秦蜀郡守李冰修都江堰，引岷江水灌溉成都平原，"天府之国"由此而成'},
        {y:'三国', t:'蜀汉以成都为都，岷江流域为其经济命脉'}
      ]
    },
    '雅砻江': {
      water:'金沙江最大支流', origin:'青海省巴颜喀拉山南麓',
      flows:'青海、四川（甘孜、凉山、攀枝花）', mouth:'攀枝花市注入金沙江',
      length:'约 1571 km', area:'流域约 12.8 万 km²',
      events:[{y:'三国', t:'蜀汉南中、越嶲诸郡沿雅砻江分布，为诸葛亮南征所经之域'}]
    },
    '金沙江': {
      water:'长江上游', origin:'青海省唐古拉山（通天河以下称金沙江）',
      flows:'青海、西藏、四川、云南', mouth:'宜宾市与岷江汇合后始称长江',
      length:'约 2308 km', area:'流域约 47 万 km²',
      events:[
        {y:'225', t:'诸葛亮南征，"五月渡泸"（泸水，多指金沙江）'},
        {y:'1253', t:'忽必烈"革囊渡江"，自金沙江入大理'}
      ]
    },
    '通天河': {
      water:'长江上游（沱沱河以下）', origin:'青海省唐古拉山各拉丹冬雪山',
      flows:'青海玉树', mouth:'玉树巴塘河口以下称金沙江',
      length:'约 828 km', area:'流域约 14.5 万 km²',
      events:[{y:'唐', t:'唐蕃古道渡通天河，文成公主入藏经此一带'}]
    },
    '沱沱河': {
      water:'长江正源', origin:'各拉丹冬雪山姜根迪如冰川',
      flows:'青海格尔木市唐古拉山镇', mouth:'与当曲、楚玛尔河汇合后为通天河',
      length:'约 358 km', area:'流域约 1.76 万 km²',
      events:[{y:'1976-1978', t:'长江源头考察确认沱沱河为长江正源'}]
    },
    '怒江': {
      water:'萨尔温江水系 → 安达曼海', origin:'西藏唐古拉山南麓',
      flows:'西藏、云南（怒江州、保山）', mouth:'入缅甸称萨尔温江，注入安达曼海',
      length:'中国境内约 2013 km（全河约 3240 km）', area:'中国境内流域约 13.6 万 km²',
      events:[{y:'三国', t:'怒江以西为永昌郡徼外，蜀汉南中西南边陲'}]
    },
    '澜沧江': {
      water:'湄公河水系 → 南海', origin:'青海省唐古拉山北麓扎曲',
      flows:'青海、西藏、云南（迪庆、大理、西双版纳）', mouth:'出境后称湄公河，注入南海',
      length:'中国境内约 2130 km（全河约 4880 km）', area:'中国境内流域约 16.4 万 km²',
      events:[
        {y:'唐', t:'南诏依澜沧江而立；茶马古道沿江而下'},
        {y:'元', t:'设云南行省，澜沧江流域纳入版图'}
      ]
    },
    '湄公河': {
      water:'澜沧江下游（中南半岛）', origin:'中国青海唐古拉山（上游即澜沧江）',
      flows:'缅甸、老挝、泰国、柬埔寨、越南', mouth:'越南南部注入南海',
      length:'约 4880 km', area:'流域约 81 万 km²',
      events:[{y:'汉', t:'"永昌道"出澜沧江—湄公河，为西南丝路要冲'}]
    },
    '雅鲁藏布江': {
      water:'布拉马普特拉河水系 → 孟加拉湾', origin:'西藏喜马拉雅山北麓杰马央宗冰川',
      flows:'西藏日喀则、拉萨、山南、林芝', mouth:'出境后称布拉马普特拉河，注入孟加拉湾',
      length:'中国境内约 2057 km', area:'中国境内流域约 24 万 km²',
      events:[
        {y:'唐', t:'吐蕃兴起于雅隆河谷（雅鲁藏布江支流），松赞干布统一青藏'},
        {y:'元', t:'设乌思藏宣慰司，雅鲁藏布江流域纳入中央管辖'}
      ]
    },
    '伊洛瓦底江': {
      water:'伊洛瓦底江水系 → 安达曼海', origin:'缅甸北部克钦邦',
      flows:'缅甸全境', mouth:'伊洛瓦底江三角洲注入安达曼海',
      length:'约 2170 km', area:'流域约 41 万 km²',
      events:[{y:'汉', t:'汉使自永昌通掸国（今缅甸），伊洛瓦底江为西南对外通道'}]
    },
    '塔里木河': {
      water:'塔里木河（内流河）', origin:'天山、昆仑山（叶尔羌河、阿克苏河、和田河汇合）',
      flows:'新疆塔里木盆地', mouth:'尾闾台特玛湖',
      length:'约 2179 km（中国最长内流河）', area:'流域约 102 万 km²',
      events:[
        {y:'汉', t:'西域三十六国沿塔里木河绿洲分布；张骞通西域'},
        {y:'汉', t:'设西域都护府，丝绸之路南北二道绕盆地而行'},
        {y:'前77', t:'傅介子刺楼兰王，楼兰改名鄯善'}
      ]
    },
    '伊犁河': {
      water:'伊犁河（内流河）', origin:'新疆天山北麓特克斯河',
      flows:'新疆伊犁河谷', mouth:'注入哈萨克斯坦巴尔喀什湖',
      length:'约 1439 km（中国境内约 442 km）', area:'流域约 15.1 万 km²',
      events:[
        {y:'汉', t:'乌孙居伊犁河流域，汉与乌孙和亲共击匈奴'},
        {y:'清', t:'设伊犁将军，统辖天山南北'}
      ]
    },
    '额尔齐斯河': {
      water:'鄂毕河水系 → 北冰洋', origin:'新疆阿尔泰山南麓',
      flows:'新疆阿勒泰，入哈萨克斯坦、俄罗斯', mouth:'汇入鄂毕河，注入北冰洋',
      length:'中国境内约 546 km（全河约 4248 km）', area:'中国境内流域约 5 万 km²',
      events:[{y:'清', t:'中俄《勘分西北界约记》后成为界河相关水系'}]
    },
    '乌苏里江': {
      water:'黑龙江支流', origin:'吉林长白山／俄罗斯锡霍特山',
      flows:'中俄界河', mouth:'哈巴罗夫斯克附近注入黑龙江',
      length:'约 909 km', area:'流域约 18.7 万 km²',
      events:[{y:'1860', t:'《中俄北京条约》割乌苏里江以东至海之地'}]
    },
    '元江': {
      water:'红河水系 → 南海', origin:'云南省大理州巍山县',
      flows:'云南大理、楚雄、玉溪、红河', mouth:'入越南称红河，注入北部湾',
      length:'中国境内约 695 km（全河约 1280 km）', area:'中国境内流域约 7.9 万 km²',
      events:[
        {y:'唐', t:'南诏、大理依元江（红河）经营滇南'},
        {y:'元', t:'元军三征安南，红河水道为进军路线'}
      ]
    },
    '闽江': {
      water:'闽江水系 → 东海', origin:'福建建宁、三明',
      flows:'福建南平、福州', mouth:'福州市注入东海',
      length:'约 577 km', area:'流域约 6.1 万 km²',
      events:[
        {y:'前110', t:'汉武帝灭闽越，迁其民于江淮'},
        {y:'三国', t:'闽江流域属吴，置建安郡'}
      ]
    },
    '乌江': {
      water:'长江支流', origin:'贵州省威宁县乌蒙山',
      flows:'贵州、重庆', mouth:'重庆市涪陵区注入长江',
      length:'约 1037 km', area:'流域约 8.79 万 km²',
      events:[
        {y:'三国', t:'蜀汉南中诸郡沿乌江上游分布'},
        {y:'明', t:'奢香夫人开龙场九驿，连通乌江流域'}
      ]
    },
    '色楞格河': {
      water:'贝加尔湖水系', origin:'蒙古杭爱山北麓',
      flows:'蒙古、俄罗斯', mouth:'注入贝加尔湖',
      length:'约 1024 km', area:'流域约 44.7 万 km²',
      events:[{y:'汉', t:'匈奴、鲜卑活动于漠北，色楞格河流域为其核心牧场之一'}]
    },
    '勒拿河': {
      water:'勒拿河水系 → 北冰洋', origin:'俄罗斯贝加尔山西麓',
      flows:'俄罗斯西伯利亚', mouth:'注入拉普捷夫海',
      length:'约 4400 km', area:'流域约 249 万 km²',
      events:[{y:'—', t:'中国境外大河，与中原历史地理关联较弱'}]
    },
    '扎曲': {
      water:'澜沧江正源', origin:'青海省杂多县唐古拉山北麓',
      flows:'青海杂多、西藏昌都', mouth:'与昂曲汇合后称澜沧江',
      length:'约 500 km（正源段）', area:'—',
      events:[{y:'唐', t:'吐蕃东扩，澜沧江上源为唐蕃争夺之域'}]
    },
    '玛曲': {
      water:'黄河上游河段（藏语"孔雀河"）', origin:'青海省巴颜喀拉山',
      flows:'青海果洛、甘肃玛曲', mouth:'玛曲以下仍称黄河',
      length:'—', area:'—',
      events:[{y:'唐', t:'唐蕃以黄河源一带为界，文成公主入藏经河源'}]
    },
    '伊德尔河': {
      water:'蒙古国河流', origin:'蒙古杭爱山', flows:'蒙古国', mouth:'—',
      length:'—', area:'—',
      events:[{y:'—', t:'中国境外河流，与中原历史地理关联较弱'}]
    },

    '大渡河': {
      water:'岷江最大支流（长江水系）', origin:'青海省班玛县巴颜喀拉山南麓',
      flows:'青海、四川（阿坝、甘孜、雅安、乐山）', mouth:'乐山市注入岷江',
      length:'约 1062 km', area:'流域约 7.74 万 km²',
      events:[
        {y:'唐', t:'吐蕃、南诏与唐在此反复争战，为川西边防要冲'},
        {y:'1863', t:'太平天国石达开部兵败安顺场，全军覆没'},
        {y:'1935', t:'红军强渡大渡河、飞夺泸定桥'}
      ]
    },
    '赣江': {
      water:'长江支流 → 鄱阳湖', origin:'江西省赣州（章水、贡水汇合）',
      flows:'江西赣州、吉安、南昌', mouth:'注入鄱阳湖，经湖口入长江',
      length:'约 766 km（江西最大河）', area:'流域约 8.35 万 km²',
      events:[
        {y:'汉', t:'设豫章郡，赣江流域纳入版图'},
        {y:'唐', t:'王勃作《滕王阁序》，"落霞与孤鹜齐飞"咏赣江之滨'},
        {y:'三国', t:'属吴，为扬州南部腹地'}
      ]
    },
    '南盘江': {
      water:'珠江上游（西江源）', origin:'云南省曲靖市马雄山',
      flows:'云南曲靖、玉溪、红河', mouth:'与北盘江汇合后称红水河',
      length:'约 914 km', area:'流域约 5.6 万 km²',
      events:[{y:'汉', t:'属益州郡，为"西南夷"通道'}]
    },
    '红水河': {
      water:'珠江上游（广西）', origin:'南盘江与北盘江汇合处',
      flows:'广西百色、河池、来宾', mouth:'与柳江汇合后称黔江',
      length:'约 659 km', area:'流域约 13.8 万 km²',
      events:[
        {y:'明', t:'大藤峡瑶民起义，持续数十年'},
        {y:'汉', t:'属郁林郡，为岭南西道'}
      ]
    },
    '富春江': {
      water:'钱塘江中游（浙江）', origin:'浙江桐庐、富阳一带',
      flows:'浙江桐庐、富阳', mouth:'经钱塘江注入东海',
      length:'约 110 km', area:'—',
      events:[
        {y:'东汉', t:'严子陵隐居富春江垂钓，拒光武帝征召'},
        {y:'元', t:'黄公望绘《富春山居图》，为中国山水画巅峰之作'}
      ]
    },
    '桑干河': {
      water:'永定河上游（海河水系）', origin:'山西省宁武县管涔山',
      flows:'山西、河北', mouth:'入官厅水库，以下称永定河',
      length:'约 506 km', area:'流域约 2.4 万 km²',
      events:[
        {y:'汉', t:'流域设代郡、雁门郡，为汉匈交界'},
        {y:'现代', t:'丁玲小说《太阳照在桑干河上》以此为背景'}
      ]
    },
    '瓯江': {
      water:'浙江第二大河', origin:'浙江省龙泉市',
      flows:'浙江丽水、温州', mouth:'温州市注入东海',
      length:'约 388 km', area:'流域约 1.8 万 km²',
      events:[
        {y:'汉', t:'东瓯国故地，汉武帝时内迁江淮'},
        {y:'三国', t:'属吴临海郡，为东南海疆'}
      ]
    },
    '东江': {
      water:'珠江支流（广东）', origin:'江西省寻乌县',
      flows:'广东河源、惠州、东莞', mouth:'汇入珠江口',
      length:'约 562 km', area:'流域约 3.5 万 km²',
      events:[
        {y:'秦', t:'赵佗任龙川县令，经营东江流域'},
        {y:'宋', t:'苏轼贬惠州，咏东江风物'}
      ]
    },
    '北江': {
      water:'珠江北支（广东）', origin:'江西信丰／湖南临武',
      flows:'广东韶关、清远、佛山', mouth:'汇入珠江三角洲',
      length:'约 573 km', area:'流域约 4.67 万 km²',
      events:[
        {y:'秦', t:'设横浦关，北江为入岭南通道'},
        {y:'唐', t:'张九龄开凿大庾岭新路，北江航运大兴'}
      ]
    },
    '邕江': {
      water:'郁江上游（广西南宁段）', origin:'广西南宁',
      flows:'广西南宁', mouth:'与左江汇合后称郁江',
      length:'约 133 km', area:'—',
      events:[{y:'唐', t:'置邕州，为桂南重镇'}, {y:'宋', t:'侬智高起兵据邕州'}]
    },
    '郁江': {
      water:'西江支流（广西）', origin:'广西南宁（邕江以下）',
      flows:'广西南宁、贵港', mouth:'桂平汇入浔江',
      length:'约 1152 km（含上游）', area:'流域约 8.7 万 km²',
      events:[{y:'汉', t:'设郁林郡，为岭南九郡之一'}]
    },
    '寻江': {
      water:'浔江（西江中游，广西）', origin:'广西桂平（黔江、郁江汇合）',
      flows:'广西桂平、平南、梧州', mouth:'梧州以下称西江',
      length:'约 172 km', area:'—',
      events:[
        {y:'汉', t:'设苍梧郡，为岭南要冲'},
        {y:'明', t:'大藤峡之役，王守仁平定瑶乱'}
      ]
    },
    '酉水': {
      water:'沅江支流（湘、鄂、渝界）', origin:'湖北宣恩／湖南龙山',
      flows:'湖北、湖南、重庆', mouth:'注入沅江，入洞庭湖',
      length:'约 477 km', area:'流域约 1.85 万 km²',
      events:[{y:'2002', t:'里耶古城出土秦简三万六千余枚，震惊学界'}]
    },
    '永定河': {
      water:'海河支流（京津冀）', origin:'山西宁武（桑干河）／内蒙古（洋河）',
      flows:'山西、河北、北京、天津', mouth:'入海河注入渤海',
      length:'约 747 km', area:'流域约 4.7 万 km²',
      events:[
        {y:'1192', t:'金代建成卢沟桥，为永定河上著名石桥'},
        {y:'1937', t:'卢沟桥事变，抗日战争全面爆发'}
      ]
    },
    '海拉尔河': {
      water:'黑龙江上游（额尔古纳河源）', origin:'内蒙古牙克石大兴安岭',
      flows:'内蒙古呼伦贝尔', mouth:'汇入额尔古纳河',
      length:'约 708 km', area:'流域约 5.4 万 km²',
      events:[{y:'汉', t:'匈奴左地；后为鲜卑、室韦牧地'}]
    },
    '额尔古纳河': {
      water:'中俄界河（黑龙江上游）', origin:'内蒙古呼伦贝尔（海拉尔河汇合处）',
      flows:'中俄边界', mouth:'与石勒喀河汇合后称黑龙江',
      length:'约 970 km', area:'流域约 15 万 km²',
      events:[{y:'1689', t:'《尼布楚条约》以额尔古纳河为中俄东段界河'}]
    },
    '叶尔羌河': {
      water:'塔里木河源（新疆）', origin:'喀喇昆仑山北麓',
      flows:'新疆喀什、和田、阿克苏', mouth:'与阿克苏河、和田河汇合为塔里木河',
      length:'约 1079 km', area:'流域约 9.4 万 km²',
      events:[
        {y:'汉', t:'莎车国临河而居，属西域都护'},
        {y:'清', t:'大小和卓之乱，清军平定金川'}
      ]
    },
    '孔雀河': {
      water:'新疆内流河', origin:'博斯腾湖',
      flows:'新疆巴州库尔勒、尉犁', mouth:'尾闾罗布泊（历史变迁）',
      length:'约 785 km', area:'—',
      events:[
        {y:'汉', t:'孔雀河下游为楼兰古城，丝绸之路咽喉'},
        {y:'前77', t:'傅介子刺楼兰王，汉改鄯善'}
      ]
    },
    '西辽河': {
      water:'辽河上游（内蒙、吉林）', origin:'西拉木伦河与老哈河汇合',
      flows:'内蒙古、吉林、辽宁', mouth:'与东辽河汇合为辽河',
      length:'约 449 km', area:'流域约 13.6 万 km²',
      events:[{y:'辽', t:'契丹以潢水（西拉木伦河）流域为发祥地'}]
    },
    '西拉木伦河': {
      water:'西辽河源（内蒙古）', origin:'内蒙古克什克腾旗',
      flows:'内蒙古赤峰', mouth:'汇入西辽河',
      length:'约 380 km', area:'—',
      events:[{y:'辽', t:'古称"潢水"，契丹始祖传说与辽代肇兴之地'}]
    },
    '克孜勒河': {
      water:'喀什噶尔河上游（新疆）', origin:'帕米尔高原',
      flows:'新疆克州、喀什', mouth:'汇入喀什噶尔河',
      length:'约 700 km', area:'—',
      events:[{y:'汉', t:'疏勒国临河而居，为西域三十六国之一'}]
    },
    '萨尔温江': {
      water:'怒江下游（缅甸）', origin:'中国西藏唐古拉山（上游为怒江）',
      flows:'缅甸掸邦、克伦邦', mouth:'莫塔马湾注入安达曼海',
      length:'全河约 3240 km', area:'流域约 32 万 km²',
      events:[{y:'汉', t:'与怒江同源，为西南丝路南向通道'}]
    },
    '汉江（韩国）': {
      water:'韩国汉江水系', origin:'韩国太白山脉',
      flows:'韩国首尔、京畿道', mouth:'注入黄海',
      length:'约 514 km', area:'流域约 2.6 万 km²',
      events:[
        {y:'朝鲜', t:'李氏朝鲜定都汉阳（今首尔），汉江为京畿命脉'},
        {y:'现代', t:'20 世纪后期"汉江奇迹"指韩国经济腾飞'}
      ]
    },
    '印度河': {
      water:'印度河水系 → 阿拉伯海', origin:'中国西藏冈底斯山',
      flows:'中国、印度、巴基斯坦', mouth:'巴基斯坦卡拉奇附近注入阿拉伯海',
      length:'约 3180 km', area:'流域约 96 万 km²',
      events:[
        {y:'上古', t:'印度河流域文明（哈拉帕）发祥地'},
        {y:'汉', t:'上游经罽宾（今克什米尔）入西域南道'},
        {y:'唐', t:'玄奘西行曾涉印度河流域'}
      ]
    },
    '恒河': {
      water:'恒河水系 → 孟加拉湾', origin:'喜马拉雅山南麓',
      flows:'印度、孟加拉国', mouth:'恒河三角洲注入孟加拉湾',
      length:'约 2525 km', area:'流域约 90 万 km²',
      events:[
        {y:'前6世纪', t:'佛教兴起于恒河流域，摩揭陀国为佛教中心'},
        {y:'唐', t:'玄奘游学那烂陀寺，戒日王统摄恒河平原'}
      ]
    },
    '恩梅开江': {
      water:'伊洛瓦底江源（云南、缅甸）', origin:'西藏察隅／云南贡山',
      flows:'云南怒江州、缅甸克钦邦', mouth:'与迈立开江汇合为伊洛瓦底江',
      length:'—', area:'—',
      events:[{y:'汉', t:'"蜀身毒道"经此南下，为西南丝路'}]
    },

    /* ══════════════════════ 主要湖泊 ══════════════════════ */
    '青海湖': {
      water:'内流咸水湖', origin:'青海省海南、海北州',
      area:'约 4625 km²（中国最大湖泊）', elev:'湖面海拔约 3196 m',
      events:[
        {y:'汉', t:'古称"西海""鲜水海"；王莽于公元 4 年置西海郡'},
        {y:'唐', t:'吐蕃据青海，唐蕃在此反复争战'},
        {y:'清', t:'设青海办事大臣，青海湖周边为蒙古和硕特部牧地'}
      ]
    },
    '鄱阳湖': {
      water:'长江中游吞吐湖（江西）', origin:'江西省北部',
      area:'高水位约 4000 km²，低水位约 1000 km²（中国最大淡水湖）', elev:'湖口海拔约 12-22 m',
      events:[
        {y:'上古', t:'古称"彭蠡泽"，为《禹贡》所载名泽'},
        {y:'208', t:'赤壁战后，东吴据鄱阳湖训练水军'},
        {y:'1363', t:'鄱阳湖之战：朱元璋大破陈友谅，奠定明朝基业'}
      ]
    },
    '鄱湖': {
      water:'即鄱阳湖（异名）', origin:'江西省北部',
      area:'中国最大淡水湖', elev:'—',
      events:[{y:'1363', t:'鄱阳湖之战：朱元璋破陈友谅'}]
    },
    '洞庭湖': {
      water:'长江中游吞吐湖（湖南）', origin:'湖南省北部',
      area:'约 2579 km²（中国第二大淡水湖）', elev:'城陵矶约 33 m',
      events:[
        {y:'上古', t:'古称"云梦泽"，先秦为楚地大泽'},
        {y:'前278', t:'屈原自沉于汨罗江（入洞庭）'},
        {y:'三国', t:'赤壁战后刘备取荆南四郡，洞庭湖为荆州腹心'},
        {y:'宋', t:'范仲淹作《岳阳楼记》，"先天下之忧而忧"'}
      ]
    },
    '太湖': {
      water:'长江三角洲吞吐湖（江苏、浙江）', origin:'江苏省南部、浙江省北部',
      area:'约 2338 km²', elev:'湖面海拔约 3 m',
      events:[
        {y:'上古', t:'古称"震泽""具区"，为《禹贡》名泽'},
        {y:'春秋', t:'吴越争霸，太湖为两国水战之地'},
        {y:'三国', t:'太湖流域属吴，为其财赋重地'}
      ]
    },
    '洪泽湖': {
      water:'淮河下游吞吐湖（江苏）', origin:'江苏省淮安、宿迁',
      area:'约 2069 km²', elev:'湖面海拔约 13 m',
      events:[
        {y:'1128', t:'黄河夺淮，洪泽湖逐渐扩大'},
        {y:'明清', t:'"蓄清刷黄"治河方略，洪泽湖成为黄淮治理枢纽'}
      ]
    },
    '巢湖': {
      water:'长江下游吞吐湖（安徽）', origin:'安徽省合肥、巢湖市',
      area:'约 780 km²', elev:'湖面海拔约 8 m',
      events:[
        {y:'三国', t:'濡须口（巢湖入江处）为魏吴对峙要冲，孙权多次筑坞'},
        {y:'上古', t:'古称"焦湖"，相传为巢父、许由隐居之地'}
      ]
    },
    '呼倫湖': {
      water:'内流淡水湖（内蒙古）', origin:'内蒙古呼伦贝尔市',
      area:'约 2339 km²（内蒙古第一大湖）', elev:'湖面海拔约 545 m',
      events:[
        {y:'汉', t:'匈奴、鲜卑活动于呼伦贝尔草原'},
        {y:'蒙古', t:'成吉思汗统一蒙古诸部，呼伦贝尔为发祥地之一'}
      ]
    },
    '贝尔湖': {
      water:'中蒙界湖', origin:'内蒙古呼伦贝尔／蒙古国东方省',
      area:'约 609 km²', elev:'湖面海拔约 583 m',
      events:[{y:'1962', t:'中蒙边界条约确定贝尔湖为界湖'}]
    },
    '兴凯湖': {
      water:'中俄界湖', origin:'黑龙江省鸡西／俄罗斯滨海边疆区',
      area:'约 4380 km²', elev:'湖面海拔约 69 m',
      events:[{y:'1860', t:'《中俄北京条约》后兴凯湖成为界湖，南部划归俄国'}]
    },
    '纳木错': {
      water:'内流咸水湖（西藏）', origin:'西藏拉萨市当雄县',
      area:'约 1920 km²', elev:'湖面海拔约 4718 m',
      events:[
        {y:'唐', t:'吐蕃以纳木错为圣湖，藏传佛教重要圣地'},
        {y:'清', t:'驻藏大臣辖区，纳木错为蒙古语"腾格里淖尔"'}
      ]
    },
    '色林错': {
      water:'内流咸水湖（西藏）', origin:'西藏那曲市',
      area:'约 2391 km²（今西藏第一大湖）', elev:'湖面海拔约 4530 m',
      events:[{y:'唐', t:'吐蕃"大湖"之一，藏北羌塘核心湖区'}]
    },
    '羊卓雍错': {
      water:'内流咸水湖（西藏）', origin:'西藏山南市浪卡子县',
      area:'约 638 km²', elev:'湖面海拔约 4441 m',
      events:[{y:'唐', t:'藏传佛教三大圣湖之一，吐蕃王室祭祀之地'}]
    },
    '滇池': {
      water:'长江上游吞吐湖（云南）', origin:'云南省昆明市',
      area:'约 330 km²', elev:'湖面海拔约 1886 m',
      events:[
        {y:'战国-汉', t:'古滇国环滇池而居；汉武帝置益州郡，赐"滇王印"'},
        {y:'唐-宋', t:'南诏、大理国以滇池为东都（善阐府）'}
      ]
    },
    '洱海': {
      water:'澜沧江水系（云南）', origin:'云南省大理州',
      area:'约 252 km²', elev:'湖面海拔约 1972 m',
      events:[
        {y:'唐', t:'南诏统一洱海地区，建都太和城'},
        {y:'宋', t:'大理国以洱海为中心，佛教盛极一时'}
      ]
    },
    '抚仙湖': {
      water:'珠江/长江分水岭深水湖（云南）', origin:'云南省玉溪市澄江、江川',
      area:'约 212 km²', elev:'最深约 155 m（中国第二深湖）',
      events:[{y:'汉', t:'属益州郡俞元县，湖底有古城遗址传说'}]
    },
    '泸沽湖': {
      water:'长江水系（云南、四川界湖）', origin:'云南省宁蒗／四川省盐源',
      area:'约 50 km²', elev:'湖面海拔约 2690 m',
      events:[{y:'—', t:'摩梭人"母系大家庭"与走婚文化核心区'}]
    },
    '程海': {
      water:'内流咸水湖（云南）', origin:'云南省永胜县', area:'约 77 km²', elev:'湖面海拔约 1503 m',
      events:[{y:'—', t:'云南高原断陷湖，周边为程海断裂带'}]
    },
    '星云湖': {
      water:'珠江水系（云南）', origin:'云南省玉溪市江川区', area:'约 34 km²', elev:'湖面海拔约 1722 m',
      events:[{y:'—', t:'与抚仙湖隔河相邻，为云南九大高原湖泊之一'}]
    },
    '阳宗海': {
      water:'珠江水系（云南）', origin:'云南省昆明市宜良、澄江', area:'约 31 km²', elev:'湖面海拔约 1770 m',
      events:[{y:'—', t:'云南高原断陷湖'}]
    },
    '异龙湖': {
      water:'珠江水系（云南）', origin:'云南省石屏县', area:'约 31 km²', elev:'湖面海拔约 1414 m',
      events:[{y:'—', t:'云南九大高原湖泊中最南端者'}]
    },
    '博斯腾湖': {
      water:'开都河注入、孔雀河源（新疆）', origin:'新疆巴音郭楞州博湖县',
      area:'约 988 km²（中国最大内陆淡水湖）', elev:'湖面海拔约 1048 m',
      events:[
        {y:'汉', t:'古称"西海"，焉耆国临湖而居，属西域都护'},
        {y:'唐', t:'安西四镇之焉耆镇，扼丝路中道'}
      ]
    },
    '艾比湖': {
      water:'内流咸水湖（新疆）', origin:'新疆博尔塔拉州精河县',
      area:'约 500-1000 km²（随补给波动）', elev:'湖面海拔约 189 m',
      events:[{y:'清', t:'为伊犁—塔尔巴哈台通道要冲'}]
    },
    '密云水库': {
      water:'海河水系（北京）', origin:'北京市密云区',
      area:'约 188 km²', elev:'1958-1960 年建成',
      events:[{y:'1958-1960', t:'建成蓄水，为北京主要水源地'}]
    },
    '千岛湖': {
      water:'钱塘江水系（浙江）', origin:'浙江省杭州市淳安县',
      area:'约 573 km²', elev:'即新安江水库，1959 年蓄水',
      events:[{y:'1959', t:'新安江水电站建成，形成千岛湖'}]
    },
    '洪湖': {
      water:'长江中游吞吐湖（湖北）', origin:'湖北省荆州洪湖市',
      area:'约 348 km²', elev:'湖面海拔约 25 m',
      events:[{y:'三国', t:'邻近赤壁、乌林古战场，为江汉水网要地'}]
    },
    '南四湖': {
      water:'淮河水系（山东）', origin:'山东省济宁微山等县',
      area:'约 1266 km²', elev:'由微山、昭阳、独山、南阳四湖组成',
      events:[{y:'明清', t:'京杭大运河穿湖而过，为漕运枢纽'}]
    },
    '微山湖': {
      water:'淮河水系（山东、江苏界）', origin:'山东省微山县',
      area:'约 660 km²', elev:'南四湖中最大者',
      events:[
        {y:'明清', t:'京杭大运河重要水柜，漕运咽喉'},
        {y:'抗战', t:'铁道游击队活动于微山湖一带'}
      ]
    },
    '白洋淀': {
      water:'海河水系（河北）', origin:'河北省雄安新区安新等县',
      area:'约 366 km²', elev:'华北最大淡水湖',
      events:[
        {y:'宋', t:'北宋"塘泺"防线，白洋淀为拒马河防辽水网'},
        {y:'抗战', t:'雁翎队活动于白洋淀'}
      ]
    },
    '日月潭': {
      water:'台湾最大天然湖', origin:'台湾南投县鱼池乡',
      area:'约 7.9 km²', elev:'湖面海拔约 748 m',
      events:[
        {y:'清', t:'康熙年间文献已有记载，为邵族祖居地'},
        {y:'1934', t:'日月潭水电站建成，水位抬升'}
      ]
    },
    '茶卡盐湖': {
      water:'盐湖（青海）', origin:'青海省海西州乌兰县',
      area:'约 105 km²', elev:'湖面海拔约 3059 m',
      events:[{y:'汉', t:'"茶卡"藏语意为盐池，自古为青盐产地'}]
    },
    '察尔汗盐湖': {
      water:'盐湖（青海）', origin:'青海省海西州格尔木市',
      area:'约 5856 km²（中国最大盐湖）', elev:'湖面海拔约 2670 m',
      events:[{y:'现代', t:'中国最大钾肥生产基地，盐盖可筑"万丈盐桥"'}]
    },
    '扎龙湖': {
      water:'湿地湖泊（黑龙江）', origin:'黑龙江省齐齐哈尔市',
      area:'湿地约 2100 km²', elev:'—',
      events:[{y:'现代', t:'丹顶鹤之乡，国家级自然保护区'}]
    },
    '镜泊湖': {
      water:'火山堰塞湖（黑龙江）', origin:'黑龙江省牡丹江市宁安',
      area:'约 91.5 km²', elev:'湖面海拔约 350 m',
      events:[
        {y:'唐', t:'渤海国上京龙泉府邻近镜泊湖'},
        {y:'—', t:'中国最大火山堰塞湖'}
      ]
    },
    '五大连池': {
      water:'火山堰塞湖群（黑龙江）', origin:'黑龙江省黑河市五大连池市',
      area:'五个串珠状湖泊', elev:'—',
      events:[{y:'1719-1721', t:'老黑山、火烧山喷发，熔岩堰塞白河形成五池'}]
    },
    '松花湖': {
      water:'松花江水系（吉林）', origin:'吉林省吉林市',
      area:'约 550 km²', elev:'即丰满水库，1937-1943 年建成',
      events:[{y:'1937-1943', t:'丰满水电站建成，形成松花湖'}]
    },
    '班公错': {
      water:'中印边界湖（西藏）', origin:'西藏阿里日土县',
      area:'约 604 km²', elev:'湖面海拔约 4241 m',
      events:[{y:'清', t:'属阿里地区，为传统牧场与边界湖泊'}]
    },
    '玛旁雍错': {
      water:'内流淡水湖（西藏）', origin:'西藏阿里普兰县',
      area:'约 412 km²', elev:'湖面海拔约 4588 m',
      events:[{y:'唐', t:'藏传佛教、印度教共尊的"圣湖"，与冈仁波齐并称神山圣湖'}]
    },
    '拉昂错': {
      water:'内流咸水湖（西藏）', origin:'西藏阿里普兰县',
      area:'约 269 km²', elev:'湖面海拔约 4574 m',
      events:[{y:'—', t:'紧邻玛旁雍错，俗称"鬼湖"'}]
    },
    '当惹雍错': {
      water:'内流咸水湖（西藏）', origin:'西藏那曲尼玛县', area:'约 836 km²', elev:'湖面海拔约 4528 m',
      events:[{y:'苯教', t:'苯教重要圣湖，象雄文明核心区'}]
    },
    '昂拉仁错': {
      water:'内流咸水湖（西藏）', origin:'西藏日喀则仲巴县', area:'约 560 km²', elev:'湖面海拔约 4689 m',
      events:[{y:'—', t:'藏北—阿里内流湖区'}]
    },
    '普莫雍错': {
      water:'内流淡水湖（西藏）', origin:'西藏山南浪卡子县', area:'约 290 km²', elev:'湖面海拔约 5010 m',
      events:[{y:'—', t:'世界海拔最高的大型淡水湖之一'}]
    },
    '扎陵湖': {
      water:'黄河源湖泊（青海）', origin:'青海省果洛州玛多县', area:'约 526 km²', elev:'湖面海拔约 4293 m',
      events:[
        {y:'汉', t:'古称"柏海"，《禹贡》"导河积石"上游湖区'},
        {y:'唐', t:'唐蕃"柏海之盟"，文成公主与松赞干布在此相会'}
      ]
    },
    '鄂陵湖': {
      water:'黄河源湖泊（青海）', origin:'青海省果洛州玛多县', area:'约 610 km²', elev:'湖面海拔约 4268 m',
      events:[{y:'唐', t:'与扎陵湖并称"柏海"，为黄河上游双子湖'}]
    },
    '可可西里湖': {
      water:'内流咸水湖（青海）', origin:'青海省玉树州治多县', area:'约 300 km²', elev:'湖面海拔约 4878 m',
      events:[{y:'现代', t:'可可西里无人区核心湖，藏羚羊保护区'}]
    },
    '梁子湖': {
      water:'长江中游吞吐湖（湖北）', origin:'湖北省鄂州市', area:'约 271 km²', elev:'—',
      events:[{y:'三国', t:'属武昌郡，邻近孙权所建武昌（今鄂州）'}]
    },
    '大官湖': {
      water:'长江下游湖泊（安徽）', origin:'安徽省宿松县', area:'约 200 km²', elev:'—',
      events:[{y:'—', t:'龙感湖群之一，与长江相通'}]
    },
    '龙感湖': {
      water:'长江下游湖泊（湖北、安徽界）', origin:'湖北省黄梅／安徽省宿松', area:'约 220 km²', elev:'—',
      events:[{y:'—', t:'古称"雷池"，"不敢越雷池一步"典故所指'}]
    },
    '黄塘湖': {
      water:'长江下游湖泊（安徽）', origin:'安徽省', area:'—', elev:'—',
      events:[{y:'—', t:'长江中下游中小型湖泊'}]
    },
    '石臼湖': {
      water:'长江下游湖泊（江苏、安徽界）', origin:'江苏省南京／安徽省马鞍山', area:'约 208 km²', elev:'—',
      events:[{y:'—', t:'古称"丹阳湖"之一部'}]
    },
    '高邮湖': {
      water:'淮河入江水道湖泊（江苏）', origin:'江苏省高邮、宝应', area:'约 760 km²', elev:'—',
      events:[{y:'明清', t:'京杭大运河穿湖，为漕运与防洪要地'}]
    },
    '钱尼湖': {
      water:'—', origin:'—', area:'—', elev:'—',
      events:[{y:'—', t:'数据来源标注不详，欢迎补充'}]
    },
    '斋桑泊': {
      water:'额尔齐斯河水系（哈萨克斯坦）', origin:'哈萨克斯坦东哈萨克斯坦州', area:'约 5500 km²', elev:'—',
      events:[{y:'清', t:'原属中国，1864 年《勘分西北界约记》后划归俄'}]
    },
    '阿拉湖': {
      water:'内流咸水湖（哈萨克斯坦）', origin:'哈萨克斯坦阿拉木图州', area:'约 2650 km²', elev:'—',
      events:[{y:'清', t:'原属中国，19 世纪中后期划归俄'}]
    },
    '库苏古尔湖': {
      water:'贝加尔湖水系（蒙古）', origin:'蒙古库苏古尔省', area:'约 2760 km²', elev:'湖面海拔约 1645 m',
      events:[{y:'汉', t:'匈奴、丁零活动于漠北湖区'}]
    },
    '烏布蘇湖': {
      water:'内流咸水湖（蒙古）', origin:'蒙古乌布苏省', area:'约 3350 km²', elev:'—',
      events:[{y:'—', t:'蒙古最大湖泊，中亚内流湖'}]
    },
    '烏雷格湖': {
      water:'内流湖（蒙古）', origin:'蒙古乌布苏省', area:'约 239 km²', elev:'—',
      events:[{y:'—', t:'蒙古西部内流湖'}]
    },
    '吉爾吉斯湖': {
      water:'内流湖（蒙古）', origin:'蒙古扎布汗省', area:'约 140 km²', elev:'—',
      events:[{y:'—', t:'蒙古西部内流湖'}]
    },
    '庫倫達湖': {
      water:'内流湖（俄罗斯）', origin:'俄罗斯阿尔泰边疆区', area:'约 728 km²', elev:'—',
      events:[{y:'—', t:'西西伯利亚内流湖'}]
    },
    '布拉茨克水庫': {
      water:'安加拉河水库（俄罗斯）', origin:'俄罗斯伊尔库茨克州', area:'约 5470 km²', elev:'1961-1967 年建成',
      events:[{y:'1961-1967', t:'布拉茨克水电站建成，形成世界最大水库之一'}]
    },
    '托克托古尔水库': {
      water:'纳伦河水库（吉尔吉斯斯坦）', origin:'吉尔吉斯斯坦贾拉拉巴德州', area:'约 284 km²', elev:'—',
      events:[{y:'1970s', t:'托克托古尔水电站建成'}]
    },
    '谢列特田吉兹湖': {
      water:'内流湖（哈萨克斯坦）', origin:'哈萨克斯坦阿克莫拉州', area:'约 750 km²', elev:'—',
      events:[{y:'—', t:'哈萨克斯坦北部内流湖'}]
    },
    '哈尔乌苏湖': {
      water:'内流湖（蒙古）', origin:'蒙古科布多省', area:'约 1400 km²', elev:'—',
      events:[{y:'—', t:'蒙古西部内流湖'}]
    },
    '贝加尔湖': {
      water:'裂谷湖（俄罗斯）', origin:'俄罗斯东西伯利亚',
      area:'约 3.15 万 km²（世界最深湖）', elev:'最深约 1637 m',
      events:[
        {y:'汉', t:'古称"北海"，苏武牧羊于此十九年'},
        {y:'前100', t:'苏武持节不屈，为后世气节典范'},
        {y:'清', t:'1689 年《尼布楚条约》划定中俄东段边界，贝加尔湖归俄'}
      ]
    },
    '巴尔喀什湖': {
      water:'内流湖（哈萨克斯坦）', origin:'哈萨克斯坦东南部',
      area:'约 1.82 万 km²', elev:'西部淡水、东部咸水，一半咸一半淡',
      events:[{y:'清', t:'原为中国西北边外大湖，1864 年后划归俄'}]
    },
    '伊塞克湖': {
      water:'内流咸水湖（吉尔吉斯斯坦）', origin:'吉尔吉斯斯坦伊塞克湖州',
      area:'约 6236 km²', elev:'湖面海拔约 1607 m',
      events:[
        {y:'唐', t:'玄奘《大唐西域记》称"大清池"（亦作热海）'},
        {y:'唐', t:'安西四镇之碎叶城位于湖西，为丝路要冲'}
      ]
    },
    '琵琶湖': {
      water:'日本最大湖泊', origin:'日本滋贺县', area:'约 670 km²', elev:'湖面海拔约 85 m',
      events:[{y:'—', t:'日本近畿地区水源，与中原历史地理无关，仅作参照'}]
    },
    '塔什幹日本滯留者墓地': {
      water:'—', origin:'乌兹别克斯坦塔什干', area:'—', elev:'—',
      events:[{y:'—', t:'此要素疑为 Natural Earth 湖泊数据的误标（一处墓地被当作湖泊），仅作提示'}]
    }
  };

  /* ── 样式（只作用于 #info 详情面板） ── */
  var CSS = ''
    + '#info .wi-h{font-weight:bold;color:#ffd479;margin:12px 0 5px;font-size:1.03em;'
    + 'border-left:3px solid #ffd479;padding-left:7px;letter-spacing:.3px}'
    + '#info .wi-h:first-child{margin-top:0}'
    + '#info .wi-t{width:100%;border-collapse:collapse}'
    + '#info .wi-t td{padding:2px 0;vertical-align:top}'
    + '#info .wi-t td.k{color:#9fb3c8;white-space:nowrap;padding-right:9px}'
    + '#info .wi-t td.v{color:#e8eef5}'
    + '#info .wi-ev{margin:2px 0 0;padding-left:18px}'
    + '#info .wi-ev li{margin:4px 0}'
    + '#info .wi-ev b{color:#ffd479;font-weight:bold}'
    + '#info .wi-none{color:#8da2b8}'
    + '#info .wi-src{margin-top:10px;padding-top:6px;border-top:1px dashed #34507a;color:#8da2b8;font-size:.9em}'
    + '#info .wi-tag{display:inline-block;background:rgba(122,180,255,.16);color:#cfe3ff;'
    + 'border:1px solid #3f5f8a;border-radius:3px;padding:0 5px;font-size:.88em;margin-left:5px;vertical-align:1px}'
  function injectCSS(){
    if(document.getElementById('wi-style')) return;
    var s=document.createElement('style'); s.id='wi-style'; s.textContent=CSS;
    document.head.appendChild(s);
  }

  function esc(s){
    return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
  function row(k,v){
    if(v==null||v===''||v==='—') return '';
    return '<tr><td class="k">'+esc(k)+'</td><td class="v">'+esc(v)+'</td></tr>';
  }

  function buildHtml(name, kind, props){
    props = props || {};
    var info = WATER_INFO[name] || null;
    var isRiver = (kind === 'river');
    var kindCN = isRiver ? '河流' : '湖泊';
    var title = name || (isRiver ? '未名河流' : '未名湖泊');

    var h = '';
    /* 基本信息 */
    h += '<div class="wi-h">基本信息</div><table class="wi-t">';
    h += row('名称', name || '（图层未命名）');
    var tags = '';
    if(typeof props.major === 'boolean'){
      tags += props.major ? '<span class="wi-tag">主要</span>' : '<span class="wi-tag">一般</span>';
    }
    if(isRiver && props.scalerank!=null){ tags += '<span class="wi-tag">等级 ' + esc(props.scalerank) + '</span>'; }
    h += '<tr><td class="k">类型</td><td class="v">' + kindCN + tags + '</td></tr>';
    if(info){
      h += row('所属水系', info.water);
      h += row('发源', info.origin);
      h += row('流经', info.flows);
      h += row('汇入', info.mouth);
    }
    h += '</table>';

    /* 数据 */
    h += '<div class="wi-h">数据</div><table class="wi-t">';
    if(info){
      h += row('长度', info.length);
      h += row('流域面积 / 面积', info.area);
      h += row('海拔 / 其他', info.elev);
    }
    h += '</table>';
    if(!info || (!info.length && !info.area && !info.elev)){
      h += '<div class="wi-none">该' + kindCN + '暂无收录的定量数据。</div>';
    }

    /* 重要历史事件 */
    h += '<div class="wi-h">重要历史事件</div>';
    if(info && info.events && info.events.length){
      h += '<ul class="wi-ev">';
      for(var i=0;i<info.events.length;i++){
        var ev = info.events[i];
        h += '<li>' + (ev.y && ev.y!=='—' ? '<b>' + esc(ev.y) + '</b> ' : '') + esc(ev.t) + '</li>';
      }
      h += '</ul>';
    } else {
      h += '<div class="wi-none">暂无收录（该水体与重大历史事件的关联尚未整理）。</div>';
    }

    h += '<div class="wi-src">数据来源：' + (props.source === 'hand-drawn' ? '手工补绘' : 'Natural Earth 10m（公有领域）')
       + '　几何仅供历史地理参考</div>';
    return {title: title, html: h};
  }

  function open(name, kind, props, showInfo){
    var r = buildHtml(name, kind, props);
    if(typeof showInfo === 'function') showInfo(r.title, r.html);
    else if(window.showInfo) window.showInfo(r.title, r.html);
  }

  var WaterInfo = {
    info: WATER_INFO,
    html: buildHtml,
    attach: function(opts, showInfo){
      opts = opts || {};
      injectCSS();
      if(this._done) return this;
      this._done = true;
      var self = this;

      function bind(layer, kind, name, props){
        if(!layer || !layer.on) return;
        layer.on('click', function(ev){
          if(ev && ev.originalEvent && window.L && L.DomEvent) { try{ L.DomEvent.stopPropagation(ev.originalEvent); }catch(e){} }
          open(name, kind, props, showInfo);
        });
      }

      /* 河流：细线不易点中 → 追加一条透明加宽"命中线"，随图层一起显隐 */
      var riverLayer = opts.riverLayer;
      /* 名称 → 要素属性 索引：让"点标签"与"点本体"拿到完全相同的属性，信息逐字一致 */
      var propsByKey = {};

      if(riverLayer && riverLayer.eachLayer){
        var hits = [];
        riverLayer.eachLayer(function(l){
          if(!l || !l.feature){ return; }
          var p = l.feature.properties || {};
          if(p.kind !== 'river') return;
          if(p.name) propsByKey['river|' + p.name] = p;
          bind(l, 'river', p.name || '', p);
          if(l.getLatLngs){
            try{
              var hit = L.polyline(l.getLatLngs(), {weight:14, opacity:0, fill:false, interactive:true});
              bind(hit, 'river', p.name || '', p);
              hits.push(hit);
            }catch(e){}
          }
        });
        for(var i=0;i<hits.length;i++){ riverLayer.addLayer(hits[i]); }
      }

      /* 湖泊：多边形有填充，本身即可点中 */
      var lakeLayer = opts.lakeLayer;
      if(lakeLayer && lakeLayer.eachLayer){
        lakeLayer.eachLayer(function(l){
          if(!l || !l.feature){ return; }
          var p = l.feature.properties || {};
          if(p.kind !== 'lake') return;
          if(p.name) propsByKey['lake|' + p.name] = p;
          bind(l, 'lake', p.name || '', p);
        });
      }

      /* 名称标签：点文字也弹出同一份信息（标签本身是 Leaflet marker，天然可点） */
      function bindLabels(group, kind){
        if(!group || !group.eachLayer) return;
        group.eachLayer(function(m){
          if(!m || !m.options || !m.options.icon){ return; }
          var io = m.options.icon.options || {};
          var hm = String(io.html || '').match(/>([^<]*)</);
          var nm = hm ? hm[1] : '';
          if(!nm) return;
          if(m.setZIndexOffset) { try{ m.setZIndexOffset(600); }catch(e){} }  /* 标签置于水系之上，便于点中 */
          m.on('click', function(ev){
            if(ev && ev.originalEvent && window.L && L.DomEvent){ try{ L.DomEvent.stopPropagation(ev.originalEvent); }catch(e){} }
            open(nm, kind, propsByKey[kind + '|' + nm] || {}, showInfo);
          });
        });
      }
      bindLabels(opts.riverLabelLayer, 'river');
      bindLabels(opts.lakeLabelLayer, 'lake');
      return self;
    }
  };

  window.WATER_INFO = WATER_INFO;
  window.WaterInfo = WaterInfo;
})();
