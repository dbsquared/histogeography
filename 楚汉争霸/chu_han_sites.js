// 楚汉争霸关键地点（城池 / 关隘 / 津渡 / 战役）
// 时间范围：前209 陈胜起义 — 前202 垓下·乌江；坐标系与疆域底图一致（经度,纬度），经 L.CRS.Simple 直接叠加。
// 结构对齐 three_kingdoms_sites.js：city/pass/ford {name,lon,lat,modern,zhou,desc,tier?}；
// battle {name,year,lon,lat,place,sides,result,desc?,nudge?}。坐标为 WGS84 近似值，仅供上图定位参考。
window.CHU_HAN_SITES = {
  // ── 一、都城与重镇（城池）──
  city: [
    {name:'彭城', lon:117.18, lat:34.27, modern:'江苏徐州', zhou:'西楚', desc:'西楚都城。项羽定都于此，前205年楚汉彭城大战即在其郊', tier:'capital'},
    {name:'下相', lon:118.24, lat:33.92, modern:'江苏宿迁西南', zhou:'西楚', desc:'项羽出生地（下相县）', tier:'capital'},
    {name:'沛县', lon:116.94, lat:34.73, modern:'江苏沛县', zhou:'西楚', desc:'刘邦出生地，起兵之初称“沛公”'},
    {name:'丰邑', lon:116.60, lat:34.70, modern:'江苏丰县', zhou:'西楚', desc:'刘邦生长之地，起兵后曾以丰邑为根'},
    {name:'芒砀山', lon:116.55, lat:34.30, modern:'河南永城东北（芒砀山）', zhou:'西楚', desc:'刘邦亡匿芒砀山泽中，斩白蛇起事传说即在此'},
    {name:'薛', lon:117.26, lat:34.79, modern:'山东枣庄薛城', zhou:'西楚', desc:'薛县；项梁召诸将会薛计事，立楚怀王孙心为楚王'},
    {name:'会稽（吴县）', lon:120.59, lat:31.30, modern:'江苏苏州', zhou:'西楚', desc:'会稽郡治吴县；项梁、项羽起兵江东之地'},
    {name:'郴县', lon:113.03, lat:25.80, modern:'湖南郴州', zhou:'义帝', desc:'义帝熊心自彭城徙都郴县，次年遇弑'},
    {name:'陈县', lon:114.87, lat:33.73, modern:'河南淮阳', zhou:'西楚', desc:'陈胜建都称“张楚”之地；楚汉之际为陈郡治'},
    {name:'睢阳', lon:115.63, lat:34.41, modern:'河南商丘', zhou:'西楚', desc:'砀郡治；彭越以此为中心游击梁地，断楚粮道'},
    {name:'昌邑', lon:116.22, lat:34.93, modern:'山东金乡西北', zhou:'西楚', desc:'彭越起兵之地；刘邦西进至此与彭越合兵'},
    {name:'下邑', lon:116.36, lat:34.42, modern:'安徽砀山', zhou:'西楚', desc:'彭城大败后刘邦退守下邑，用张良“下邑之谋”画策'},
    {name:'荥阳', lon:113.39, lat:34.79, modern:'河南荥阳', zhou:'河南', desc:'荥阳、敖仓所在；楚汉两年拉锯的核心（敖仓粟仓）'},
    {name:'成皋', lon:113.19, lat:34.76, modern:'河南荥阳汜水镇', zhou:'河南', desc:'虎牢故地，成皋之战曹咎失守，楚东线崩解'},
    {name:'修武', lon:113.45, lat:35.23, modern:'河南获嘉（修武故城）', zhou:'殷', desc:'刘邦渡河入修武，夺韩信、张耳军，军势复振'},
    {name:'宛城', lon:112.53, lat:32.99, modern:'河南南阳', zhou:'西楚', desc:'南阳郡治；刘邦西进至宛受降，后属西楚'},
    {name:'洛阳', lon:112.45, lat:34.62, modern:'河南洛阳', zhou:'河南', desc:'河南王申阳都；刘邦至此为义帝发丧，号令诸侯', tier:'capital'},
    {name:'阳翟', lon:113.49, lat:34.14, modern:'河南禹州', zhou:'韩', desc:'韩王韩成都', tier:'capital'},
    {name:'朝歌', lon:114.20, lat:35.61, modern:'河南淇县', zhou:'殷', desc:'殷王司马卬都', tier:'capital'},
    {name:'平阳', lon:111.52, lat:36.08, modern:'山西临汾', zhou:'魏', desc:'西魏王魏豹都', tier:'capital'},
    {name:'襄国', lon:114.48, lat:37.05, modern:'河北邢台', zhou:'常山', desc:'常山王张耳都；赵王歇后亦都此，为韩信所擒', tier:'capital'},
    {name:'代县（代王城）', lon:114.65, lat:39.87, modern:'河北蔚县', zhou:'代', desc:'代王赵歇都', tier:'capital'},
    {name:'临淄', lon:118.33, lat:36.89, modern:'山东淄博临淄区', zhou:'齐', desc:'齐王田都都；楚汉之际齐地反覆，终为韩信所定', tier:'capital'},
    {name:'博阳', lon:117.15, lat:36.12, modern:'山东泰安东南', zhou:'济北', desc:'济北王田安都', tier:'capital'},
    {name:'即墨', lon:120.26, lat:36.68, modern:'山东平度东南（即墨故城）', zhou:'胶东', desc:'胶东王田市都；田荣追杀田市于即墨', tier:'capital'},
    {name:'蓟', lon:116.40, lat:39.91, modern:'北京（蓟城）', zhou:'燕', desc:'燕王臧荼都', tier:'capital'},
    {name:'无终', lon:117.41, lat:40.03, modern:'天津蓟州', zhou:'辽东', desc:'辽东王韩广都', tier:'capital'},
    {name:'六县', lon:116.50, lat:31.78, modern:'安徽六安（六县故城）', zhou:'九江', desc:'九江王英布都', tier:'capital'},
    {name:'邾县', lon:114.80, lat:30.82, modern:'湖北武汉新洲（邾城遗址）', zhou:'衡山', desc:'衡山王吴芮都', tier:'capital'},
    {name:'江陵', lon:112.19, lat:30.35, modern:'湖北荆州', zhou:'临江', desc:'临江王共敖都；前202年汉将刘贾、卢绾破江陵，临江亡', tier:'capital'},
    {name:'南郑', lon:107.02, lat:33.07, modern:'陕西汉中', zhou:'汉', desc:'汉王刘邦就国之地；韩信拜将坛所在', tier:'capital'},
    {name:'咸阳', lon:108.71, lat:34.34, modern:'陕西咸阳', zhou:'雍', desc:'秦都；项羽入关屠烧宫室，一炬焦土'},
    {name:'栎阳', lon:109.25, lat:34.57, modern:'陕西西安阎良（栎阳故城）', zhou:'塞', desc:'塞王司马欣都', tier:'capital'},
    {name:'废丘', lon:108.46, lat:34.28, modern:'陕西兴平东南', zhou:'雍', desc:'雍王章邯都，被围近一年而亡', tier:'capital'},
    {name:'高奴', lon:109.53, lat:36.60, modern:'陕西延安城东', zhou:'翟', desc:'翟王董翳都', tier:'capital'},
    {name:'番禺', lon:113.26, lat:23.13, modern:'广东广州', zhou:'南越', desc:'南海郡治；赵佗据此建南越国，未入十八国'}
  ],
  // ── 二、关隘 ──
  pass: [
    {name:'函谷关', lon:110.88, lat:34.60, modern:'河南灵宝北（秦函谷关）', zhou:'塞/河南界', desc:'关中东大门；刘邦入关、楚汉相持皆以此为界标'},
    {name:'武关', lon:110.83, lat:33.83, modern:'陕西商南西北', zhou:'塞', desc:'关中东南锁钥；刘邦由此破关入秦'},
    {name:'峣关', lon:109.42, lat:34.06, modern:'陕西蓝田东南（蓝田关）', zhou:'塞', desc:'刘邦用张良疑兵之计破此关，遂至霸上'},
    {name:'散关（大散关）', lon:107.13, lat:34.35, modern:'陕西宝鸡南', zhou:'雍', desc:'陈仓道北口；韩信“暗度陈仓”出此'},
    {name:'萧关', lon:106.25, lat:35.65, modern:'宁夏固原东南', zhou:'雍', desc:'陇北要隘，关中北面门户'},
    {name:'陇关', lon:106.62, lat:34.93, modern:'陕西陇县西北（陇山）', zhou:'雍', desc:'陇山（陇坂）要隘，关中西面屏障'},
    {name:'临晋关', lon:110.30, lat:34.85, modern:'陕西大荔东（蒲津渡口）', zhou:'塞/魏界', desc:'韩信陈船临晋为疑兵，潜师自夏阳渡河破魏'},
    {name:'井陉关', lon:114.30, lat:38.06, modern:'河北井陉北（井陉口）', zhou:'常山', desc:'太行八陉之一；韩信出此背水破赵'},
    {name:'壶关', lon:113.22, lat:36.18, modern:'山西长治东南', zhou:'魏', desc:'上党门户，太行之险'},
    {name:'天井关', lon:112.93, lat:35.55, modern:'山西晋城东南', zhou:'魏', desc:'太行南陉，上党通河内之道'},
    {name:"扞关（江关）", lon:109.68, lat:30.99, modern:'重庆奉节东', zhou:'临江', desc:'巴楚之界，楚置西塞以拒巴'}
  ],
  // ── 三、津渡 ──
  ford: [
    {name:'白马津', lon:114.55, lat:35.58, modern:'河南滑县西北（古黄河渡口）', zhou:'西楚（东郡）', desc:'前204年刘邦遣卢绾、刘贾渡白马津入楚地，与彭越焚楚积聚'},
    {name:'平阴津', lon:112.62, lat:34.88, modern:'河南孟津东北（古黄河渡口）', zhou:'河南', desc:'前205年刘邦自洛阳北渡处；渡河后至洛阳为义帝发丧'},
    {name:'夏阳渡', lon:110.32, lat:35.28, modern:'陕西韩城东南（夏阳）', zhou:'塞', desc:'韩信以木罂缻潜渡夏阳，袭安邑破魏豹'},
    {name:'鸿沟（广武涧）', lon:113.36, lat:34.86, modern:'河南荥阳北（广武山）', zhou:'河南/西楚界', nudge:[-16,-12], desc:'楚汉隔涧相持经年；“鸿沟之约”以此分天下'},
    {name:'乌江渡', lon:118.42, lat:31.83, modern:'安徽和县东北（长江北岸）', zhou:'九江', desc:'长江渡口；项羽自刎处，后世称乌江亭'}
  ],
  // ── 四、著名战役与事件 ──
  battle: [
    {name:'大泽乡起义', year:'209', lon:117.10, lat:33.55, place:'大泽乡（安徽宿州东南）', sides:'陈胜、吴广 vs 秦', result:'中国历史上第一次大规模农民起义，反秦序幕由此拉开'},
    {name:'定陶之战', year:'208', lon:115.57, lat:35.07, place:'定陶（山东定陶）', sides:'章邯 vs 项梁', result:'项梁兵败战死，反秦军一时受挫'},
    {name:'巨鹿之战', year:'207', lon:115.02, lat:37.07, place:'巨鹿（河北平乡西南）', sides:'项羽 vs 秦（章邯、王离）', result:'破釜沉舟，秦军主力尽丧，诸侯皆属项羽'},
    {name:'蓝田之战', year:'207', lon:109.32, lat:34.15, place:'蓝田（陕西蓝田）', sides:'刘邦 vs 秦', result:'破秦军最后屏障，刘邦直抵霸上', nudge:[-12,-10]},
    {name:'霸上受降', year:'207', lon:109.10, lat:34.22, place:'霸上（陕西西安东南·白鹿原）', sides:'秦王子婴 vs 刘邦', result:'子婴素车白马出降，秦朝灭亡'},
    {name:'鸿门宴', year:'206', lon:109.30, lat:34.42, place:'鸿门（陕西临潼东）', sides:'刘邦 vs 项羽（范增）', result:'项庄舞剑、樊哙护主；刘邦脱险归霸上，楚汉裂痕始此', nudge:[12,10]},
    {name:'陈仓之战', year:'206', lon:107.28, lat:34.37, place:'陈仓（陕西宝鸡东）', sides:'韩信、刘邦 vs 章邯', result:'“明修栈道，暗度陈仓”，还定三秦之始', nudge:[14,6]},
    {name:'好畤之战', year:'206', lon:108.24, lat:34.53, place:'好畤（陕西乾县东）', sides:'刘邦 vs 章邯', result:'章邯连败，退守废丘孤城'},
    {name:'废丘之围', year:'205', lon:108.46, lat:34.28, place:'废丘（陕西兴平东南）', sides:'刘邦（韩信） vs 章邯', result:'围城近一年，城破章邯自杀，雍亡', nudge:[14,8]},
    {name:'彭城之战', year:'205', lon:117.02, lat:34.08, place:'彭城、睢水（江苏徐州南）', sides:'项羽 vs 刘邦（诸侯联军）', result:'项羽三万精骑大破汉军五十六万，睢水为之不流'},
    {name:'京索之战', year:'205', lon:113.60, lat:34.62, place:'京索（河南荥阳东南）', sides:'刘邦（韩信、曹参等） vs 楚', result:'汉军止住溃势，荥阳—成皋防线得以建立'},
    {name:'安邑之战', year:'205', lon:111.25, lat:35.20, place:'安邑（山西夏县西北）', sides:'韩信 vs 魏豹', result:'木罂缻渡河奇袭，魏豹被俘，魏亡', nudge:[14,8]},
    {name:'阏与之战', year:'205', lon:113.57, lat:37.33, place:'阏与（山西和顺）', sides:'韩信 vs 代（夏说）', result:'破代军，擒代相夏说'},
    {name:'井陉之战', year:'204', lon:114.30, lat:38.06, place:'井陉（河北井陉北）', sides:'韩信 vs 赵（陈余）', result:'背水一战，大破赵军二十万', nudge:[-14,10]},
    {name:'泜水之战', year:'204', lon:114.60, lat:37.55, place:'泜水（河北高邑南）', sides:'韩信 vs 赵', result:'追斩成安君陈余于泜水，赵地遂定'},
    {name:'历下之战', year:'204', lon:117.05, lat:36.67, place:'历下（山东济南）', sides:'韩信（袭齐） vs 齐', result:'齐历下军溃散，韩信乘虚直入临淄'},
    {name:'潍水之战', year:'203', lon:119.60, lat:36.42, place:'潍水（山东高密一带）', sides:'韩信 vs 楚（龙且）', result:'壅水断流、半渡而击，龙且败死，齐地底定'},
    {name:'荥阳之围', year:'204', lon:113.39, lat:34.79, place:'荥阳（河南荥阳）', sides:'项羽 vs 刘邦', result:'纪信诈降代死，刘邦得以脱走成皋', nudge:[-14,10]},
    {name:'成皋之战', year:'204', lon:113.19, lat:34.76, place:'成皋（河南荥阳汜水镇）', sides:'刘邦 vs 曹咎（楚）', result:'曹咎渡汜水半渡被击，楚军覆没，成皋归汉', nudge:[14,8]},
    {name:'广武对峙·鸿沟之约', year:'203', lon:113.36, lat:34.86, place:'广武、鸿沟（河南荥阳北）', sides:'刘邦 vs 项羽', result:'相持经年，约中分天下：鸿沟以西属汉、以东属楚', nudge:[-12,-10]},
    {name:'固陵之战', year:'202', lon:114.85, lat:34.06, place:'固陵（河南太康南）', sides:'项羽（反击） vs 刘邦', result:'汉军追击败绩，张良献策裂土封韩信、彭越'},
    {name:'陈下之战', year:'202', lon:114.87, lat:33.73, place:'陈下（河南淮阳）', sides:'刘邦、灌婴等 vs 项羽', result:'楚军再败，项羽退保垓下', nudge:[-14,-10]},
    {name:'垓下之战', year:'202', lon:117.55, lat:33.33, place:'垓下（安徽固镇濠城·一说灵璧）', sides:'刘邦（韩信为主将） vs 项羽', result:'十面埋伏、四面楚歌，楚军崩溃，项羽夜遁'},
    {name:'乌江自刎', year:'202', lon:118.42, lat:31.83, place:'乌江（安徽和县东北·长江北岸）', sides:'项羽 vs 汉军追兵', result:'项羽愧见江东父老，自刎乌江，楚汉战争终以汉胜', nudge:[14,8]},
    {name:'田荣并三齐', year:'206-205', lon:118.33, lat:36.89, place:'临淄（齐地）', sides:'田荣 vs 田都、田市、田安', result:'击杀三齐王，并地自立；项羽北上伐齐，刘邦得以东出', nudge:[-14,10]},
    {name:'灭临江之战', year:'202', lon:112.19, lat:30.35, place:'江陵（湖北荆州）', sides:'汉（刘贾、卢绾） vs 共尉（临江）', result:'江陵城破，共尉被擒，临江亡', nudge:[-16,-10]}
  ]
};
