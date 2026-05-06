import os
import sys
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from zhipuai import ZhipuAI

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "88cada5e688149409c0804146761dc1b.RBFp01gPwFzSI5ZK")
zhipu_client = ZhipuAI(api_key=ZHIPU_API_KEY)

IP_API_URL = "http://ip-api.com/json/"
OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_DAYS = 7
API_TIMEOUT = 10

CITY_KEYWORDS = {
    "北京": "北京", "上海": "上海", "广州": "广州", "深圳": "深圳",
    "杭州": "杭州", "成都": "成都", "武汉": "武汉", "西安": "西安",
    "重庆": "重庆", "南京": "南京", "天津": "天津", "苏州": "苏州",
    "郑州": "郑州", "长沙": "长沙", "青岛": "青岛", "沈阳": "沈阳",
    "大连": "大连", "厦门": "厦门", "宁波": "宁波", "昆明": "昆明",
}

CITY_TOURISM = {
    "北京": {
        "attractions": [
            {"name": "故宫博物院", "price": 60, "image": "https://picsum.photos/seed/forbidden/400/300", "desc": "明清皇家宫殿，世界文化遗产", "type": "文化"},
            {"name": "长城", "price": 45, "image": "https://picsum.photos/seed/greatwall/400/300", "desc": "万里长城，世界七大奇迹之一", "type": "户外"},
            {"name": "天坛公园", "price": 15, "image": "https://picsum.photos/seed/temple/400/300", "desc": "明清皇帝祭天场所", "type": "文化"},
            {"name": "颐和园", "price": 30, "image": "https://picsum.photos/seed/summer/400/300", "desc": "中国古典园林之首", "type": "休闲"},
            {"name": "南锣鼓巷", "price": 0, "image": "https://picsum.photos/seed/nanluo/400/300", "desc": "老北京胡同文化街区", "type": "美食"},
        ],
        "hotel_avg": 400,
        "food_avg": 80,
        "transport_avg": 30,
        "suggested_days": 4,
        "food_specialties": ["烤鸭", "炸酱面", "豆汁焦圈", "卤煮"],
        "transport_from": {"成都": {"flight": 1200, "train": 800, "hours_flight": 2.5, "hours_train": 8}},
    },
    "上海": {
        "attractions": [
            {"name": "外滩", "price": 0, "image": "https://picsum.photos/seed/bund/400/300", "desc": "上海标志性景观，万国建筑群", "type": "文化"},
            {"name": "东方明珠", "price": 199, "image": "https://picsum.photos/seed/pearl/400/300", "desc": "上海地标性建筑", "type": "文化"},
            {"name": "迪士尼乐园", "price": 399, "image": "https://picsum.photos/seed/disney/400/300", "desc": "中国首个迪士尼主题乐园", "type": "亲子"},
            {"name": "豫园", "price": 40, "image": "https://picsum.photos/seed/yuyuan/400/300", "desc": "江南古典园林", "type": "文化"},
            {"name": "城隍庙美食街", "price": 0, "image": "https://picsum.photos/seed/templefood/400/300", "desc": "上海传统美食聚集地", "type": "美食"},
        ],
        "hotel_avg": 500,
        "food_avg": 100,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["小笼包", "生煎", "本帮菜", "蟹壳黄"],
        "transport_from": {"成都": {"flight": 1000, "train": 600, "hours_flight": 2.5, "hours_train": 10}},
    },
    "成都": {
        "attractions": [
            {"name": "大熊猫繁育研究基地", "price": 55, "image": "https://picsum.photos/seed/panda/400/300", "desc": "近距离观赏国宝大熊猫", "type": "亲子"},
            {"name": "宽窄巷子", "price": 0, "image": "https://picsum.photos/seed/kuanzhai/400/300", "desc": "成都历史文化街区", "type": "美食"},
            {"name": "武侯祠", "price": 50, "image": "https://picsum.photos/seed/wuhou/400/300", "desc": "三国文化圣地", "type": "文化"},
            {"name": "锦里古街", "price": 0, "image": "https://picsum.photos/seed/jinli/400/300", "desc": "成都版清明上河图", "type": "美食"},
            {"name": "春熙路", "price": 0, "image": "https://picsum.photos/seed/chunxi/400/300", "desc": "成都最繁华商业街", "type": "休闲"},
        ],
        "hotel_avg": 300,
        "food_avg": 60,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["火锅", "串串香", "担担面", "龙抄手"],
        "transport_from": {},
    },
    "杭州": {
        "attractions": [
            {"name": "西湖", "price": 0, "image": "https://picsum.photos/seed/westlake/400/300", "desc": "人间天堂，世界文化遗产", "type": "休闲"},
            {"name": "灵隐寺", "price": 75, "image": "https://picsum.photos/seed/lingyin/400/300", "desc": "江南著名佛教寺院", "type": "文化"},
            {"name": "千岛湖", "price": 130, "image": "https://picsum.photos/seed/qiandao/400/300", "desc": "天下第一秀水", "type": "户外"},
            {"name": "宋城", "price": 300, "image": "https://picsum.photos/seed/songcheng/400/300", "desc": "大型宋代文化主题公园", "type": "亲子"},
            {"name": "河坊街", "price": 0, "image": "https://picsum.photos/seed/hefang/400/300", "desc": "杭州历史文化街区", "type": "美食"},
        ],
        "hotel_avg": 350,
        "food_avg": 70,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["西湖醋鱼", "龙井虾仁", "东坡肉", "叫花鸡"],
        "transport_from": {"成都": {"flight": 1100, "train": 700, "hours_flight": 2.5, "hours_train": 9}},
    },
    "西安": {
        "attractions": [
            {"name": "兵马俑", "price": 150, "image": "https://picsum.photos/seed/terracotta/400/300", "desc": "世界第八大奇迹", "type": "文化"},
            {"name": "大雁塔", "price": 50, "image": "https://picsum.photos/seed/pagoda/400/300", "desc": "唐代佛教建筑代表", "type": "文化"},
            {"name": "华清宫", "price": 120, "image": "https://picsum.photos/seed/huaqing/400/300", "desc": "唐代皇家园林", "type": "文化"},
            {"name": "回民街", "price": 0, "image": "https://picsum.photos/seed/muslim/400/300", "desc": "西安美食文化街区", "type": "美食"},
            {"name": "城墙", "price": 54, "image": "https://picsum.photos/seed/wall/400/300", "desc": "中国现存最完整古城墙", "type": "户外"},
        ],
        "hotel_avg": 280,
        "food_avg": 50,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["肉夹馍", "羊肉泡馍", "凉皮", "biangbiang面"],
        "transport_from": {"成都": {"flight": 600, "train": 400, "hours_flight": 1.5, "hours_train": 4}},
    },
    "重庆": {
        "attractions": [
            {"name": "洪崖洞", "price": 0, "image": "https://picsum.photos/seed/hongya/400/300", "desc": "山城夜景地标", "type": "文化"},
            {"name": "长江索道", "price": 20, "image": "https://picsum.photos/seed/cableway/400/300", "desc": "万里长江上唯一索道", "type": "休闲"},
            {"name": "武隆天生三桥", "price": 125, "image": "https://picsum.photos/seed/wulong/400/300", "desc": "世界自然遗产", "type": "户外"},
            {"name": "磁器口古镇", "price": 0, "image": "https://picsum.photos/seed/ciqikou/400/300", "desc": "千年古镇，重庆缩影", "type": "美食"},
            {"name": "解放碑", "price": 0, "image": "https://picsum.photos/seed/jiefang/400/300", "desc": "重庆地标性建筑", "type": "文化"},
        ],
        "hotel_avg": 250,
        "food_avg": 50,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["火锅", "小面", "酸辣粉", "毛血旺"],
        "transport_from": {"成都": {"flight": 400, "train": 200, "hours_flight": 1, "hours_train": 2}},
    },
    "天津": {
        "attractions": [
            {"name": "天津之眼", "price": 70, "image": "https://picsum.photos/seed/tianjin-eye/400/300", "desc": "世界唯一桥上摩天轮", "type": "休闲"},
            {"name": "古文化街", "price": 0, "image": "https://picsum.photos/seed/ancient-culture/400/300", "desc": "天津传统民俗文化街区", "type": "美食"},
            {"name": "五大道", "price": 0, "image": "https://picsum.photos/seed/five-avenues/400/300", "desc": "万国建筑博览会", "type": "文化"},
            {"name": "意式风情区", "price": 0, "image": "https://picsum.photos/seed/italian-style/400/300", "desc": "亚洲唯一意大利风格历史街区", "type": "文化"},
            {"name": "滨海新区", "price": 0, "image": "https://picsum.photos/seed/binhai/400/300", "desc": "现代化海滨旅游区", "type": "户外"},
        ],
        "hotel_avg": 300,
        "food_avg": 60,
        "transport_avg": 20,
        "suggested_days": 2,
        "food_specialties": ["狗不理包子", "十八街麻花", "耳朵眼炸糕", "煎饼果子"],
        "transport_from": {"成都": {"flight": 1100, "train": 700, "hours_flight": 2.5, "hours_train": 7}},
    },
    "广州": {
        "attractions": [
            {"name": "广州塔", "price": 150, "image": "https://picsum.photos/seed/canton-tower/400/300", "desc": "中国第一高塔", "type": "文化"},
            {"name": "长隆旅游度假区", "price": 300, "image": "https://picsum.photos/seed/chimelong/400/300", "desc": "大型综合旅游度假区", "type": "亲子"},
            {"name": "沙面岛", "price": 0, "image": "https://picsum.photos/seed/shamian/400/300", "desc": "欧陆风情历史街区", "type": "文化"},
            {"name": "上下九步行街", "price": 0, "image": "https://picsum.photos/seed/shangxiajiu/400/300", "desc": "广州最繁华商业街", "type": "美食"},
            {"name": "白云山", "price": 5, "image": "https://picsum.photos/seed/baiyun/400/300", "desc": "广州第一秀山", "type": "户外"},
        ],
        "hotel_avg": 350,
        "food_avg": 80,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["早茶", "肠粉", "云吞面", "烧鹅"],
        "transport_from": {"成都": {"flight": 1000, "train": 600, "hours_flight": 2.5, "hours_train": 8}},
    },
    "深圳": {
        "attractions": [
            {"name": "世界之窗", "price": 200, "image": "https://picsum.photos/seed/window-world/400/300", "desc": "世界著名景点微缩景观", "type": "文化"},
            {"name": "欢乐谷", "price": 230, "image": "https://picsum.photos/seed/happy-valley/400/300", "desc": "大型主题乐园", "type": "亲子"},
            {"name": "东部华侨城", "price": 200, "image": "https://picsum.photos/seed/oct-east/400/300", "desc": "山海度假胜地", "type": "户外"},
            {"name": "深圳湾公园", "price": 0, "image": "https://picsum.photos/seed/shenzhen-bay/400/300", "desc": "海滨休闲公园", "type": "休闲"},
            {"name": "华强北", "price": 0, "image": "https://picsum.photos/seed/huaqiangbei/400/300", "desc": "中国电子第一街", "type": "文化"},
        ],
        "hotel_avg": 400,
        "food_avg": 70,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["椰子鸡", "潮汕牛肉火锅", "肠粉", "早茶"],
        "transport_from": {"成都": {"flight": 1100, "train": 700, "hours_flight": 2.5, "hours_train": 8}},
    },
    "武汉": {
        "attractions": [
            {"name": "黄鹤楼", "price": 80, "image": "https://picsum.photos/seed/yellow-crane/400/300", "desc": "江南三大名楼之一", "type": "文化"},
            {"name": "东湖", "price": 0, "image": "https://picsum.photos/seed/east-lake/400/300", "desc": "中国最大城中湖", "type": "休闲"},
            {"name": "户部巷", "price": 0, "image": "https://picsum.photos/seed/hubuxiang/400/300", "desc": "武汉特色小吃街", "type": "美食"},
            {"name": "武汉大学", "price": 0, "image": "https://picsum.photos/seed/whu/400/300", "desc": "中国最美大学校园", "type": "文化"},
            {"name": "长江大桥", "price": 0, "image": "https://picsum.photos/seed/yangtze-bridge/400/300", "desc": "万里长江第一桥", "type": "户外"},
        ],
        "hotel_avg": 250,
        "food_avg": 50,
        "transport_avg": 20,
        "suggested_days": 2,
        "food_specialties": ["热干面", "豆皮", "鸭脖", "汤包"],
        "transport_from": {"成都": {"flight": 800, "train": 500, "hours_flight": 2, "hours_train": 6}},
    },
    "南京": {
        "attractions": [
            {"name": "中山陵", "price": 0, "image": "https://picsum.photos/seed/sun-yat-sen/400/300", "desc": "中国近代建筑史上第一陵", "type": "文化"},
            {"name": "夫子庙", "price": 0, "image": "https://picsum.photos/seed/confucius/400/300", "desc": "南京历史文化名片", "type": "美食"},
            {"name": "明孝陵", "price": 70, "image": "https://picsum.photos/seed/ming-tomb/400/300", "desc": "明朝开国皇帝朱元璋陵墓", "type": "文化"},
            {"name": "玄武湖", "price": 0, "image": "https://picsum.photos/seed/xuanwu/400/300", "desc": "江南三大名湖之一", "type": "休闲"},
            {"name": "南京博物院", "price": 0, "image": "https://picsum.photos/seed/nanjing-museum/400/300", "desc": "中国三大博物馆之一", "type": "文化"},
        ],
        "hotel_avg": 300,
        "food_avg": 60,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["盐水鸭", "鸭血粉丝汤", "小笼包", "梅花糕"],
        "transport_from": {"成都": {"flight": 1000, "train": 600, "hours_flight": 2.5, "hours_train": 8}},
    },
    "苏州": {
        "attractions": [
            {"name": "拙政园", "price": 70, "image": "https://picsum.photos/seed/humble-admin/400/300", "desc": "中国四大名园之一", "type": "文化"},
            {"name": "虎丘", "price": 60, "image": "https://picsum.photos/seed/tiger-hill/400/300", "desc": "吴中第一名胜", "type": "文化"},
            {"name": "周庄古镇", "price": 100, "image": "https://picsum.photos/seed/zhouzhuang/400/300", "desc": "中国第一水乡", "type": "文化"},
            {"name": "平江路", "price": 0, "image": "https://picsum.photos/seed/pingjiang/400/300", "desc": "苏州历史老街", "type": "美食"},
            {"name": "金鸡湖", "price": 0, "image": "https://picsum.photos/seed/jinji/400/300", "desc": "苏州现代城市景观", "type": "休闲"},
        ],
        "hotel_avg": 300,
        "food_avg": 60,
        "transport_avg": 20,
        "suggested_days": 2,
        "food_specialties": ["松鼠桂鱼", "苏式面", "阳澄湖大闸蟹", "桂花糖藕"],
        "transport_from": {"成都": {"flight": 1100, "train": 700, "hours_flight": 2.5, "hours_train": 9}},
    },
    "长沙": {
        "attractions": [
            {"name": "岳麓山", "price": 0, "image": "https://picsum.photos/seed/yuelu/400/300", "desc": "南岳七十二峰之一", "type": "户外"},
            {"name": "橘子洲", "price": 0, "image": "https://picsum.photos/seed/orange-isle/400/300", "desc": "湘江中心名洲", "type": "休闲"},
            {"name": "太平街", "price": 0, "image": "https://picsum.photos/seed/taiping/400/300", "desc": "长沙历史文化街区", "type": "美食"},
            {"name": "湖南省博物馆", "price": 0, "image": "https://picsum.photos/seed/hunan-museum/400/300", "desc": "马王堆汉墓出土地", "type": "文化"},
            {"name": "世界之窗", "price": 200, "image": "https://picsum.photos/seed/changsha-window/400/300", "desc": "大型主题乐园", "type": "亲子"},
        ],
        "hotel_avg": 250,
        "food_avg": 50,
        "transport_avg": 20,
        "suggested_days": 2,
        "food_specialties": ["臭豆腐", "口味虾", "糖油粑粑", "辣椒炒肉"],
        "transport_from": {"成都": {"flight": 700, "train": 400, "hours_flight": 1.5, "hours_train": 5}},
    },
    "青岛": {
        "attractions": [
            {"name": "栈桥", "price": 0, "image": "https://picsum.photos/seed/zhanqiao/400/300", "desc": "青岛标志性建筑", "type": "文化"},
            {"name": "崂山", "price": 90, "image": "https://picsum.photos/seed/laoshan/400/300", "desc": "海上第一名山", "type": "户外"},
            {"name": "八大关", "price": 0, "image": "https://picsum.photos/seed/badaguan/400/300", "desc": "万国建筑博览", "type": "文化"},
            {"name": "啤酒博物馆", "price": 50, "image": "https://picsum.photos/seed/beer-museum/400/300", "desc": "青岛啤酒发源地", "type": "文化"},
            {"name": "金沙滩", "price": 0, "image": "https://picsum.photos/seed/golden-beach/400/300", "desc": "亚洲第一滩", "type": "休闲"},
        ],
        "hotel_avg": 300,
        "food_avg": 70,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["海鲜", "青岛啤酒", "鲅鱼水饺", "烤鱿鱼"],
        "transport_from": {"成都": {"flight": 1200, "train": 800, "hours_flight": 2.5, "hours_train": 9}},
    },
    "厦门": {
        "attractions": [
            {"name": "鼓浪屿", "price": 0, "image": "https://picsum.photos/seed/gulangyu/400/300", "desc": "海上花园，万国建筑", "type": "文化"},
            {"name": "南普陀寺", "price": 0, "image": "https://picsum.photos/seed/nanputuo/400/300", "desc": "闽南佛教胜地", "type": "文化"},
            {"name": "环岛路", "price": 0, "image": "https://picsum.photos/seed/huandao/400/300", "desc": "最美马拉松赛道", "type": "休闲"},
            {"name": "曾厝垵", "price": 0, "image": "https://picsum.photos/seed/zengcuoan/400/300", "desc": "文艺渔村", "type": "美食"},
            {"name": "厦门大学", "price": 0, "image": "https://picsum.photos/seed/xmu/400/300", "desc": "中国最美大学", "type": "文化"},
        ],
        "hotel_avg": 350,
        "food_avg": 60,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["沙茶面", "海蛎煎", "土笋冻", "花生汤"],
        "transport_from": {"成都": {"flight": 1200, "train": 700, "hours_flight": 2.5, "hours_train": 10}},
    },
    "昆明": {
        "attractions": [
            {"name": "石林", "price": 130, "image": "https://picsum.photos/seed/stone-forest/400/300", "desc": "世界自然遗产", "type": "户外"},
            {"name": "滇池", "price": 0, "image": "https://picsum.photos/seed/dianchi/400/300", "desc": "云贵高原明珠", "type": "休闲"},
            {"name": "翠湖公园", "price": 0, "image": "https://picsum.photos/seed/green-lake/400/300", "desc": "城中碧玉，红嘴鸥栖息地", "type": "休闲"},
            {"name": "云南民族村", "price": 90, "image": "https://picsum.photos/seed/ethnic-village/400/300", "desc": "云南26个民族文化展示", "type": "文化"},
            {"name": "金马碧鸡坊", "price": 0, "image": "https://picsum.photos/seed/jinma/400/300", "desc": "昆明地标建筑", "type": "文化"},
        ],
        "hotel_avg": 250,
        "food_avg": 50,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["过桥米线", "鲜花饼", "汽锅鸡", "烤乳扇"],
        "transport_from": {"成都": {"flight": 600, "train": 400, "hours_flight": 1.5, "hours_train": 5}},
    },
    "郑州": {
        "attractions": [
            {"name": "少林寺", "price": 80, "image": "https://picsum.photos/seed/shaolin/400/300", "desc": "天下第一名刹", "type": "文化"},
            {"name": "河南博物院", "price": 0, "image": "https://picsum.photos/seed/henan-museum/400/300", "desc": "国家级重点博物馆", "type": "文化"},
            {"name": "嵩山", "price": 80, "image": "https://picsum.photos/seed/songshan/400/300", "desc": "五岳之中岳", "type": "户外"},
            {"name": "二七纪念塔", "price": 0, "image": "https://picsum.photos/seed/erqi/400/300", "desc": "郑州地标性建筑", "type": "文化"},
            {"name": "黄河风景区", "price": 30, "image": "https://picsum.photos/seed/yellow-river/400/300", "desc": "中华民族母亲河", "type": "户外"},
        ],
        "hotel_avg": 250,
        "food_avg": 50,
        "transport_avg": 20,
        "suggested_days": 2,
        "food_specialties": ["烩面", "胡辣汤", "道口烧鸡", "桶子鸡"],
        "transport_from": {"成都": {"flight": 800, "train": 500, "hours_flight": 2, "hours_train": 6}},
    },
    "大连": {
        "attractions": [
            {"name": "星海广场", "price": 0, "image": "https://picsum.photos/seed/xinghai/400/300", "desc": "亚洲最大城市广场", "type": "休闲"},
            {"name": "老虎滩海洋公园", "price": 220, "image": "https://picsum.photos/seed/tiger-beach/400/300", "desc": "大型海洋主题公园", "type": "亲子"},
            {"name": "金石滩", "price": 0, "image": "https://picsum.photos/seed/golden-pebble/400/300", "desc": "国家级旅游度假区", "type": "户外"},
            {"name": "有轨电车", "price": 1, "image": "https://picsum.photos/seed/tram/400/300", "desc": "百年历史有轨电车", "type": "文化"},
            {"name": "俄罗斯风情街", "price": 0, "image": "https://picsum.photos/seed/russian-street/400/300", "desc": "俄式建筑风情街", "type": "美食"},
        ],
        "hotel_avg": 300,
        "food_avg": 60,
        "transport_avg": 20,
        "suggested_days": 3,
        "food_specialties": ["海鲜", "大连焖子", "咸鱼饼子", "海胆"],
        "transport_from": {"成都": {"flight": 1300, "train": 800, "hours_flight": 3, "hours_train": 10}},
    },
    "沈阳": {
        "attractions": [
            {"name": "沈阳故宫", "price": 50, "image": "https://picsum.photos/seed/shenyang-palace/400/300", "desc": "清朝初期皇宫", "type": "文化"},
            {"name": "北陵公园", "price": 50, "image": "https://picsum.photos/seed/beiling/400/300", "desc": "清太宗皇太极陵墓", "type": "文化"},
            {"name": "中街", "price": 0, "image": "https://picsum.photos/seed/zhongjie/400/300", "desc": "中国第一条商业步行街", "type": "美食"},
            {"name": "张氏帅府", "price": 50, "image": "https://picsum.photos/seed/marshal/400/300", "desc": "张作霖、张学良官邸", "type": "文化"},
            {"name": "沈阳世博园", "price": 50, "image": "https://picsum.photos/seed/expo-garden/400/300", "desc": "世界园艺博览会会址", "type": "户外"},
        ],
        "hotel_avg": 250,
        "food_avg": 50,
        "transport_avg": 20,
        "suggested_days": 2,
        "food_specialties": ["老边饺子", "李连贵熏肉大饼", "马家烧麦", "锅包肉"],
        "transport_from": {"成都": {"flight": 1300, "train": 800, "hours_flight": 3, "hours_train": 10}},
    },
    "宁波": {
        "attractions": [
            {"name": "天一阁", "price": 30, "image": "https://picsum.photos/seed/tianyi/400/300", "desc": "中国现存最古老私家藏书楼", "type": "文化"},
            {"name": "溪口古镇", "price": 120, "image": "https://picsum.photos/seed/xikou/400/300", "desc": "蒋氏故里，弥勒道场", "type": "文化"},
            {"name": "东钱湖", "price": 0, "image": "https://picsum.photos/seed/dongqian/400/300", "desc": "浙江最大淡水湖", "type": "休闲"},
            {"name": "老外滩", "price": 0, "image": "https://picsum.photos/seed/ningbo-bund/400/300", "desc": "中国最早外滩之一", "type": "美食"},
            {"name": "普陀山", "price": 160, "image": "https://picsum.photos/seed/putuo/400/300", "desc": "中国佛教四大名山之一", "type": "文化"},
        ],
        "hotel_avg": 300,
        "food_avg": 60,
        "transport_avg": 20,
        "suggested_days": 2,
        "food_specialties": ["宁波汤圆", "海鲜", "奉化芋艿头", "慈城年糕"],
        "transport_from": {"成都": {"flight": 1200, "train": 700, "hours_flight": 2.5, "hours_train": 9}},
    },
}

DEFAULT_TOURISM = {
    "attractions": [
        {"name": "市中心广场", "price": 0, "image": "https://picsum.photos/seed/square/400/300", "desc": "城市中心地标"},
        {"name": "博物馆", "price": 30, "image": "https://picsum.photos/seed/museum/400/300", "desc": "了解城市历史文化"},
        {"name": "公园", "price": 0, "image": "https://picsum.photos/seed/park/400/300", "desc": "休闲放松好去处"},
        {"name": "美食街", "price": 0, "image": "https://picsum.photos/seed/foodstreet/400/300", "desc": "品尝当地特色美食"},
    ],
    "hotel_avg": 250,
    "food_avg": 50,
    "transport_avg": 20,
    "suggested_days": 2,
}


# 中国主要城市列表，用于验证定位结果
CHINA_CITIES = set(CITY_KEYWORDS.keys()) | {
    "哈尔滨", "长春", "石家庄", "太原", "济南", "合肥", "福州", "南昌",
    "贵阳", "南宁", "海口", "拉萨", "乌鲁木齐", "呼和浩特", "银川", "西宁",
    "兰州", "温州", "无锡", "佛山", "东莞", "珠海", "汕头", "湛江",
    "烟台", "洛阳", "开封", "桂林", "三亚", "丽江", "大理", "香格里拉",
}

def get_city_from_ip():
    apis = [
        ("https://ip.useragentinfo.com/json", "useragentinfo"),
        ("http://ip-api.com/json/?fields=status,country,city", "ip-api"),
        ("https://ipapi.co/json/", "ipapi"),
        ("http://ipwho.is/?fields=status,country,city", "ipwho"),
    ]
    
    for url, api_name in apis:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                city = None
                country = None
                
                if api_name == "useragentinfo":
                    city = data.get("city", "")
                    country = data.get("region", "")
                elif api_name == "ip-api":
                    if data.get("status") == "success":
                        city = data.get("city", "")
                        country = data.get("country", "")
                elif api_name == "ipapi":
                    city = data.get("city", "")
                    country = data.get("country_name", "")
                elif api_name == "ipwho":
                    if data.get("success"):
                        city = data.get("city", "")
                        country = data.get("country", "")
                
                if city:
                    if country and country not in ["中国", "China", "CN"]:
                        print(f"定位到国外: {country} {city}，跳过")
                        continue
                    if city in CHINA_CITIES:
                        print(f"定位成功: {city}")
                        return city
                    print(f"定位到未知城市: {city}，尝试匹配...")
                    for china_city in CHINA_CITIES:
                        if city.startswith(china_city) or china_city.startswith(city):
                            return china_city
        except Exception as e:
            print(f"{api_name} 定位失败: {e}")
            continue
    
    print("所有定位服务失败，使用默认城市")
    return "成都"


CITY_COORDINATES = {
    "北京": {"lat": 39.9042, "lon": 116.4074},
    "上海": {"lat": 31.2304, "lon": 121.4737},
    "广州": {"lat": 23.1291, "lon": 113.2644},
    "深圳": {"lat": 22.5431, "lon": 114.0579},
    "杭州": {"lat": 30.2741, "lon": 120.1551},
    "成都": {"lat": 30.5728, "lon": 104.0668},
    "武汉": {"lat": 30.5928, "lon": 114.3055},
    "西安": {"lat": 34.3416, "lon": 108.9398},
    "重庆": {"lat": 29.5630, "lon": 106.5516},
    "南京": {"lat": 32.0603, "lon": 118.7969},
    "天津": {"lat": 39.3434, "lon": 117.3616},
    "苏州": {"lat": 31.2989, "lon": 120.5853},
    "郑州": {"lat": 34.7466, "lon": 113.6253},
    "长沙": {"lat": 28.2282, "lon": 112.9388},
    "青岛": {"lat": 36.0671, "lon": 120.3826},
    "沈阳": {"lat": 41.8057, "lon": 123.4315},
    "大连": {"lat": 38.9140, "lon": 121.6147},
    "厦门": {"lat": 24.4798, "lon": 118.0894},
    "宁波": {"lat": 29.8683, "lon": 121.5440},
    "昆明": {"lat": 25.0389, "lon": 102.7183},
}


def get_city_location(city_name):
    if city_name in CITY_COORDINATES:
        coords = CITY_COORDINATES[city_name]
        return {
            "name": city_name,
            "lat": coords["lat"],
            "lon": coords["lon"],
            "country": "中国",
        }
    
    try:
        url = f"{OPEN_METEO_GEO_URL}?name={urllib.parse.quote(city_name)}&count=1&language=zh&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("results"):
                loc = data["results"][0]
                return {
                    "name": loc.get("name"),
                    "lat": loc.get("latitude"),
                    "lon": loc.get("longitude"),
                    "country": loc.get("country"),
                }
    except Exception as e:
        print(f"获取城市位置失败: {e}")
    return None


def get_weather_data(lat, lon):
    try:
        url = f"{OPEN_METEO_WEATHER_URL}?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum&timezone=auto&forecast_days={DEFAULT_DAYS}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"获取天气数据失败: {e}")
    return None


def weather_code_to_text(code):
    weather_codes = {
        0: "晴", 1: "晴", 2: "多云", 3: "阴",
        45: "雾", 48: "雾",
        51: "小雨", 53: "中雨", 55: "大雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "小雨", 81: "中雨", 82: "大雨",
        95: "雷暴", 96: "雷暴", 99: "雷暴",
    }
    return weather_codes.get(code, "多云")


def weather_code_to_icon(code):
    icons = {
        0: "☀️", 1: "☀️", 2: "⛅", 3: "☁️",
        45: "🌫️", 48: "🌫️",
        51: "🌧️", 53: "🌧️", 55: "🌧️",
        61: "🌧️", 63: "🌧️", 65: "🌧️",
        71: "🌨️", 73: "🌨️", 75: "🌨️",
        80: "🌧️", 81: "🌧️", 82: "🌧️",
        95: "⛈️", 96: "⛈️", 99: "⛈️",
    }
    return icons.get(code, "🌤️")


def wind_direction(degrees):
    directions = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]


def analyze_outfit(temp, humidity, wind_scale, rain_days, uv_level):
    temp = int(temp)
    
    if temp >= 35:
        category = "盛夏酷暑"
        top = "透气短袖/背心"
        bottom = "轻薄短裤/短裙"
        shoes = "凉鞋/拖鞋"
        accessory = "遮阳帽/太阳镜/防晒伞"
    elif temp >= 30:
        category = "夏季炎热"
        top = "短袖T恤/薄衬衫"
        bottom = "短裤/轻薄长裤"
        shoes = "透气运动鞋/凉鞋"
        accessory = "太阳镜/遮阳帽"
    elif temp >= 25:
        category = "春末夏初"
        top = "长袖T恤/薄款卫衣/衬衫"
        bottom = "长裤/牛仔裤/长裙"
        shoes = "运动鞋/休闲鞋"
        accessory = "薄外套(早晚备)"
    elif temp >= 18:
        category = "春秋温和"
        top = "毛衣/针织衫/薄外套"
        bottom = "牛仔裤/长裤"
        shoes = "运动鞋/皮鞋"
        accessory = "可增减衣物"
    elif temp >= 10:
        category = "早春/深秋"
        top = "厚毛衣/风衣/大衣"
        bottom = "保暖长裤/加绒裤"
        shoes = "靴子/保暖鞋"
        accessory = "围巾/手套"
    else:
        category = "冬季寒冷"
        top = "羽绒服/厚棉服/大衣"
        bottom = "加绒裤/保暖裤"
        shoes = "保暖靴子"
        accessory = "围巾/手套/帽子"
    
    tips = []
    if rain_days > 0:
        tips.append(f"☔ 本周{rain_days}天有雨，记得带伞!")
    if uv_level == "高":
        tips.append("☀️ 紫外线强，建议涂防晒霜!")
    if wind_scale >= 4:
        tips.append("💨 风速较大，建议穿防风外套")
    if temp >= 30:
        tips.append("🥵 注意防暑，多喝水!")
    elif temp <= 10:
        tips.append("❄️ 注意保暖!")
    
    comfort_score = 100
    if temp < 5 or temp > 35: comfort_score -= 30
    elif temp < 10 or temp > 30: comfort_score -= 15
    if humidity < 30 or humidity > 80: comfort_score -= 20
    elif humidity < 40 or humidity > 70: comfort_score -= 10
    if wind_scale >= 5: comfort_score -= 15
    elif wind_scale >= 3: comfort_score -= 5
    
    comfort = "舒适" if comfort_score >= 80 else "较舒适" if comfort_score >= 60 else "不太舒适" if comfort_score >= 40 else "不舒适"
    
    return {
        "category": category,
        "top": top,
        "bottom": bottom,
        "shoes": shoes,
        "accessory": accessory,
        "comfort": comfort,
        "tips": tips
    }


def parse_travel_requirements(message):
    adults = 2
    children = 0
    budget = None
    departure = None
    days = None
    style = "舒适"
    food_preference = False
    
    import re
    
    adult_match = re.search(r'(\d+)\s*个?\s*大\s*人', message)
    if adult_match:
        adults = int(adult_match.group(1))
    
    child_match = re.search(r'(\d+)\s*个?\s*小\s*孩', message)
    if child_match:
        children = int(child_match.group(1))
    
    budget_match = re.search(r'预算\s*(\d+)', message)
    if not budget_match:
        budget_match = re.search(r'(\d+)\s*块', message)
    if not budget_match:
        budget_match = re.search(r'(\d{4,})', message)
    if budget_match:
        budget = int(budget_match.group(1))
    
    for city in CITY_KEYWORDS.keys():
        if city + "出发" in message or "从" + city in message:
            departure = city
            break
    
    days_match = re.search(r'(\d+)\s*天', message)
    if days_match:
        days = int(days_match.group(1))
    
    if "穷游" in message or "经济" in message or "便宜" in message:
        style = "经济"
    elif "豪华" in message or "高端" in message or "奢侈" in message:
        style = "豪华"
    elif "舒适" in message or "休闲" in message:
        style = "舒适"
    elif "紧凑" in message or "特种兵" in message:
        style = "紧凑"
    
    if "美食" in message or "吃" in message or "小吃" in message:
        food_preference = True
    
    return {
        "adults": adults,
        "children": children,
        "budget": budget,
        "departure": departure,
        "days": days,
        "style": style,
        "food_preference": food_preference,
    }


def plan_tourism_advanced(city, weather_data, requirements):
    city_name = None
    for keyword in CITY_TOURISM.keys():
        if keyword in city:
            city_name = keyword
            break
    
    tourism = CITY_TOURISM.get(city_name, DEFAULT_TOURISM)
    
    adults = requirements.get("adults", 2)
    children = requirements.get("children", 0)
    budget = requirements.get("budget")
    departure = requirements.get("departure")
    days = requirements.get("days") or tourism["suggested_days"]
    style = requirements.get("style", "舒适")
    food_pref = requirements.get("food_preference", False)
    
    temp = int(weather_data.get("current", {}).get("temp", 20))
    condition = weather_data.get("current", {}).get("condition", "晴")
    rain_days = weather_data.get("analysis", {}).get("rainDays", 0)
    
    plans = []
    
    if style in ["舒适", "休闲"]:
        attractions = [a for a in tourism["attractions"] if a.get("type") in ["休闲", "文化", "美食"]]
        hotel_multiplier = 1.2
        food_multiplier = 1.3
        transport_multiplier = 1.2
        plan_name = "舒适休闲游"
        plan_desc = "节奏轻松，注重体验，适合家庭出游"
    elif style == "经济":
        attractions = [a for a in tourism["attractions"] if a.get("price", 0) <= 50]
        hotel_multiplier = 0.7
        food_multiplier = 0.8
        transport_multiplier = 0.8
        plan_name = "经济实惠游"
        plan_desc = "性价比高，精选免费/低价景点"
    elif style == "豪华":
        attractions = tourism["attractions"]
        hotel_multiplier = 2.0
        food_multiplier = 1.8
        transport_multiplier = 1.5
        plan_name = "豪华品质游"
        plan_desc = "高端体验，全程舒适"
    else:
        attractions = tourism["attractions"]
        hotel_multiplier = 0.9
        food_multiplier = 0.9
        transport_multiplier = 1.0
        plan_name = "经典紧凑游"
        plan_desc = "行程紧凑，最大化游玩时间"
    
    if food_pref:
        food_attractions = [a for a in tourism["attractions"] if a.get("type") == "美食"]
        for fa in food_attractions:
            if fa not in attractions:
                attractions.append(fa)
    
    if rain_days > 3 or "雨" in condition:
        attractions = [a for a in attractions if "博物馆" in a.get("name", "") or "室内" in a.get("desc", "") or a.get("type") == "美食"][:3]
    
    total_people = adults + children
    child_ticket_ratio = 0.5
    
    ticket_cost = sum(a["price"] for a in attractions[:days*2]) * adults
    ticket_cost += int(sum(a["price"] for a in attractions[:days*2]) * child_ticket_ratio * children)
    
    hotel_cost = int(tourism["hotel_avg"] * hotel_multiplier * days * (adults // 2 + children // 2 + 1))
    
    food_cost = int(tourism["food_avg"] * food_multiplier * days * total_people)
    
    local_transport = int(tourism["transport_avg"] * transport_multiplier * days * total_people)
    
    transport_to_city = 0
    transport_note = ""
    if departure and departure != city_name:
        transport_info = tourism.get("transport_from", {}).get(departure, {})
        if transport_info:
            if style == "豪华":
                transport_to_city = transport_info.get("flight", 0) * total_people
                transport_note = f"飞机往返 ({transport_info.get('hours_flight', 0)}h)"
            elif style == "经济":
                transport_to_city = transport_info.get("train", 0) * total_people
                transport_note = f"火车往返 ({transport_info.get('hours_train', 0)}h)"
            else:
                transport_to_city = transport_info.get("flight", 0) * adults + int(transport_info.get("flight", 0) * child_ticket_ratio * children)
                transport_note = f"飞机往返 ({transport_info.get('hours_flight', 0)}h)"
    
    total_cost = ticket_cost + hotel_cost + food_cost + local_transport + transport_to_city
    
    itinerary = []
    for i, attr in enumerate(attractions[:days*2]):
        day = i // 2 + 1
        period = "上午" if i % 2 == 0 else "下午"
        itinerary.append({
            "day": day,
            "period": period,
            "attraction": attr,
        })
    
    food_specialties = tourism.get("food_specialties", [])
    
    plan = {
        "name": plan_name,
        "desc": plan_desc,
        "city": city,
        "weatherNote": f"天气{condition}，温度{temp}°C",
        "attractions": attractions[:days*2],
        "itinerary": itinerary,
        "costBreakdown": {
            "tickets": ticket_cost,
            "hotel": hotel_cost,
            "food": food_cost,
            "localTransport": local_transport,
            "transportToCity": transport_to_city,
            "total": total_cost,
        },
        "suggestedDays": days,
        "foodSpecialties": food_specialties,
        "transportNote": transport_note,
        "people": {"adults": adults, "children": children},
    }
    
    if budget and total_cost > budget:
        plan["overBudget"] = True
        plan["budgetDiff"] = total_cost - budget
    elif budget:
        plan["overBudget"] = False
        plan["budgetDiff"] = budget - total_cost
    
    plans.append(plan)
    
    if style != "豪华":
        luxury_attractions = tourism["attractions"]
        luxury_hotel = int(tourism["hotel_avg"] * 2.0 * days * (adults // 2 + children // 2 + 1))
        luxury_food = int(tourism["food_avg"] * 1.8 * days * total_people)
        luxury_transport = int(tourism["transport_avg"] * 1.5 * days * total_people)
        luxury_tickets = sum(a["price"] for a in luxury_attractions[:days*2]) * adults
        luxury_tickets += int(sum(a["price"] for a in luxury_attractions[:days*2]) * child_ticket_ratio * children)
        luxury_transport_to = transport_to_city * 1.5 if transport_to_city else 0
        luxury_total = luxury_tickets + luxury_hotel + luxury_food + luxury_transport + luxury_transport_to
        
        luxury_itinerary = []
        for i, attr in enumerate(luxury_attractions[:days*2]):
            day = i // 2 + 1
            period = "上午" if i % 2 == 0 else "下午"
            luxury_itinerary.append({"day": day, "period": period, "attraction": attr})
        
        luxury_plan = {
            "name": "豪华品质游",
            "desc": "高端体验，全程舒适",
            "city": city,
            "weatherNote": f"天气{condition}，温度{temp}°C",
            "attractions": luxury_attractions[:days*2],
            "itinerary": luxury_itinerary,
            "costBreakdown": {
                "tickets": luxury_tickets,
                "hotel": luxury_hotel,
                "food": luxury_food,
                "localTransport": luxury_transport,
                "transportToCity": luxury_transport_to,
                "total": luxury_total,
            },
            "suggestedDays": days,
            "foodSpecialties": food_specialties,
            "transportNote": transport_note,
            "people": {"adults": adults, "children": children},
        }
        
        if budget and luxury_total > budget:
            luxury_plan["overBudget"] = True
            luxury_plan["budgetDiff"] = luxury_total - budget
        elif budget:
            luxury_plan["overBudget"] = False
            luxury_plan["budgetDiff"] = budget - luxury_total
        
        plans.append(luxury_plan)
    
    if style != "经济":
        budget_attractions = [a for a in tourism["attractions"] if a.get("price", 0) <= 50]
        if not budget_attractions:
            budget_attractions = tourism["attractions"][:2]
        budget_hotel = int(tourism["hotel_avg"] * 0.7 * days * (adults // 2 + children // 2 + 1))
        budget_food = int(tourism["food_avg"] * 0.8 * days * total_people)
        budget_transport = int(tourism["transport_avg"] * 0.8 * days * total_people)
        budget_tickets = sum(a["price"] for a in budget_attractions[:days*2]) * adults
        budget_tickets += int(sum(a["price"] for a in budget_attractions[:days*2]) * child_ticket_ratio * children)
        budget_transport_to = transport_to_city * 0.6 if transport_to_city else 0
        budget_total = budget_tickets + budget_hotel + budget_food + budget_transport + budget_transport_to
        
        budget_itinerary = []
        for i, attr in enumerate(budget_attractions[:days*2]):
            day = i // 2 + 1
            period = "上午" if i % 2 == 0 else "下午"
            budget_itinerary.append({"day": day, "period": period, "attraction": attr})
        
        budget_plan = {
            "name": "经济实惠游",
            "desc": "性价比高，精选免费/低价景点",
            "city": city,
            "weatherNote": f"天气{condition}，温度{temp}°C",
            "attractions": budget_attractions[:days*2],
            "itinerary": budget_itinerary,
            "costBreakdown": {
                "tickets": budget_tickets,
                "hotel": budget_hotel,
                "food": budget_food,
                "localTransport": budget_transport,
                "transportToCity": budget_transport_to,
                "total": budget_total,
            },
            "suggestedDays": days,
            "foodSpecialties": food_specialties,
            "transportNote": transport_note,
            "people": {"adults": adults, "children": children},
        }
        
        if budget and budget_total > budget:
            budget_plan["overBudget"] = True
            budget_plan["budgetDiff"] = budget_total - budget
        elif budget:
            budget_plan["overBudget"] = False
            budget_plan["budgetDiff"] = budget - budget_total
        
        plans.append(budget_plan)
    
    return plans[:3]


def plan_tourism(city, weather_data):
    city_name = None
    for keyword in CITY_TOURISM.keys():
        if keyword in city:
            city_name = keyword
            break
    
    tourism = CITY_TOURISM.get(city_name, DEFAULT_TOURISM)
    
    temp = int(weather_data.get("current", {}).get("temp", 20))
    condition = weather_data.get("current", {}).get("condition", "晴")
    rain_days = weather_data.get("analysis", {}).get("rainDays", 0)
    
    indoor_attractions = []
    outdoor_attractions = []
    
    for attr in tourism["attractions"]:
        if "博物馆" in attr["name"] or "室内" in attr["desc"]:
            indoor_attractions.append(attr)
        else:
            outdoor_attractions.append(attr)
    
    if rain_days > 3 or "雨" in condition:
        recommended = indoor_attractions[:2] + outdoor_attractions[:1]
        weather_note = "本周多雨，建议优先安排室内景点"
    elif temp >= 35:
        recommended = indoor_attractions[:2] + outdoor_attractions[:1]
        weather_note = "天气炎热，建议避开高温时段户外活动"
    elif temp <= 5:
        recommended = indoor_attractions[:1] + outdoor_attractions[:1]
        weather_note = "天气寒冷，建议减少户外停留时间"
    else:
        recommended = tourism["attractions"]
        weather_note = "天气适宜，可自由安排行程"
    
    total_ticket = sum(a["price"] for a in recommended)
    hotel_total = tourism["hotel_avg"] * tourism["suggested_days"]
    food_total = tourism["food_avg"] * tourism["suggested_days"]
    transport_total = tourism["transport_avg"] * tourism["suggested_days"]
    total_cost = total_ticket + hotel_total + food_total + transport_total
    
    itinerary = []
    for i, attr in enumerate(recommended):
        day = i // 2 + 1
        period = "上午" if i % 2 == 0 else "下午"
        itinerary.append({
            "day": day,
            "period": period,
            "attraction": attr,
        })
    
    return {
        "city": city,
        "weatherNote": weather_note,
        "attractions": recommended,
        "itinerary": itinerary,
        "costBreakdown": {
            "tickets": total_ticket,
            "hotel": hotel_total,
            "food": food_total,
            "transport": transport_total,
            "total": total_cost,
        },
        "suggestedDays": tourism["suggested_days"],
        "hotelAvg": tourism["hotel_avg"],
        "foodAvg": tourism["food_avg"],
        "transportAvg": tourism["transport_avg"],
    }


def format_weather_context(weather_data):
    if not weather_data:
        return "暂无天气数据"
    
    current = weather_data.get("current", {})
    forecast = weather_data.get("forecast", [])
    outfit = weather_data.get("outfit", {})
    analysis = weather_data.get("analysis", {})
    
    context = f"""【天气信息】
城市：{weather_data.get('city', '未知')}
当前温度：{current.get('temp', 'N/A')}°C
天气状况：{current.get('condition', 'N/A')}
湿度：{current.get('humidity', 'N/A')}%
风力：{current.get('wind', 'N/A')}
体感：{analysis.get('comfort', 'N/A')}
紫外线：{analysis.get('uv', 'N/A')}
本周降雨天数：{analysis.get('rainDays', 0)}天

【穿搭建议】
上衣：{outfit.get('top', 'N/A')}
下装：{outfit.get('bottom', 'N/A')}
鞋子：{outfit.get('shoes', 'N/A')}
配饰：{outfit.get('accessory', 'N/A')}"""
    
    if forecast:
        context += "\n\n【未来几天预报】\n"
        for day in forecast[:5]:
            context += f"- {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
    
    return context


def call_zhipu_llm(message, weather_data):
    context = format_weather_context(weather_data)
    
    system_prompt = """你是"小智"，一个专业的智能天气穿搭助手。
你的职责：
1. 根据天气数据提供穿搭建议
2. 规划旅游行程和推荐景点
3. 估算旅游费用
4. 回答天气相关问题

回答要求：
- 语气友好、专业、活泼
- 适当使用 emoji 增加可读性
- 结合天气数据给出实用建议
- 如果用户询问旅游，结合天气推荐合适的景点
- 回答简洁明了，不要过长"""
    
    user_message = f"{context}\n\n用户问题：{message}"
    
    response = zhipu_client.chat.completions.create(
        model="glm-4-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=800
    )
    
    return response.choices[0].message.content


def needs_structured_response(message):
    keywords = ["旅游", "攻略", "费用", "预算", "规划", "景点", "大人", "小孩", "出发", "舒适", "经济", "豪华"]
    return any(kw in message for kw in keywords)


def extract_city_from_message(message):
    for keyword in CITY_KEYWORDS.keys():
        if keyword in message:
            return keyword
    return None


def process_chat(message, weather_data):
    message = message.lower()
    
    chat_city = extract_city_from_message(message)
    
    if chat_city and chat_city != weather_data.get("city", ""):
        city_info = get_city_location(chat_city)
        if city_info:
            weather = get_weather_data(city_info["lat"], city_info["lon"])
            if weather:
                current = weather.get("current", {})
                daily = weather.get("daily", {})
                wind_speed = current.get("wind_speed_10m", 0)
                wind_scale = int(wind_speed / 10) if wind_speed else 0
                rain_days = sum(1 for p in daily.get("precipitation_sum", [0]) if p > 0)
                temp = int(current.get("temperature_2m", 20))
                humidity = int(current.get("relative_humidity_2m", 50))
                weather_code = current.get("weather_code", 0)
                
                forecast_list = []
                dates = daily.get("time", [])
                for i, date in enumerate(dates):
                    code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
                    forecast_list.append({
                        "date": date[-5:].replace("-", "/"),
                        "tempMax": str(int(daily.get("temperature_2m_max", [20])[i] if i < len(daily.get("temperature_2m_max", [])) else 20)),
                        "tempMin": str(int(daily.get("temperature_2m_min", [10])[i] if i < len(daily.get("temperature_2m_min", [])) else 10)),
                        "condition": weather_code_to_text(code),
                        "icon": weather_code_to_icon(code),
                    })
                
                month = 5
                uv = "高" if month in [5, 6, 7, 8] else "中等" if month in [3, 4, 9, 10] else "低"
                outfit = analyze_outfit(temp, humidity, wind_scale, rain_days, uv)
                
                weather_data = {
                    "city": city_info.get("name", chat_city),
                    "current": {
                        "temp": str(temp),
                        "condition": weather_code_to_text(weather_code),
                        "humidity": str(humidity),
                        "wind": f"{wind_direction(current.get('wind_direction_10m', 0))} {wind_scale}级",
                    },
                    "analysis": {
                        "rainDays": rain_days,
                        "uv": uv,
                        "comfort": outfit["comfort"],
                    },
                    "forecast": forecast_list,
                    "outfit": outfit,
                    "tips": outfit.get("tips", []),
                }
    
    if not weather_data:
        return {"type": "text", "content": "请先告诉我你在哪个城市，我来帮你查询天气~ 😊"}
    
    current = weather_data.get("current", {})
    city = weather_data.get("city", "")
    temp = current.get("temp", "0")
    cond = current.get("condition", "")
    humidity = current.get("humidity", "0")
    wind = current.get("wind", "")
    
    if "旅游" in message or "旅行" in message or "景点" in message or "玩" in message or "tourism" in message:
        has_advanced = any(k in message for k in ["大人", "小孩", "预算", "出发", "天", "舒适", "经济", "豪华", "美食"])
        
        if has_advanced:
            requirements = parse_travel_requirements(message)
            plans = plan_tourism_advanced(city, weather_data, requirements)
            outfit = weather_data.get("outfit", {})
            
            cards = []
            for plan in plans:
                plan_cards = []
                for attr in plan["attractions"]:
                    plan_cards.append({
                        "type": "image_card",
                        "image": attr["image"],
                        "title": attr["name"],
                        "desc": attr["desc"],
                        "price": f"门票: ¥{attr['price']}" if attr["price"] > 0 else "免费",
                    })
                
                cost = plan["costBreakdown"]
                breakdown = [
                    {"label": "门票", "value": f"¥{cost['tickets']}"},
                    {"label": "住宿", "value": f"¥{cost['hotel']}"},
                    {"label": "餐饮", "value": f"¥{cost['food']}"},
                    {"label": "当地交通", "value": f"¥{cost['localTransport']}"},
                ]
                if cost.get("transportToCity", 0) > 0:
                    breakdown.append({"label": "往返交通", "value": f"¥{cost['transportToCity']} ({plan.get('transportNote', '')})"})
                
                plan_cards.append({
                    "type": "cost_card",
                    "city": city,
                    "days": plan["suggestedDays"],
                    "breakdown": breakdown,
                    "total": f"¥{cost['total']}",
                })
                
                if plan.get("foodSpecialties"):
                    plan_cards.append({
                        "type": "food_card",
                        "city": city,
                        "specialties": plan["foodSpecialties"],
                    })
                
                itinerary_text = "\n".join([f"Day{item['day']} {item['period']}: {item['attraction']['name']}" for item in plan["itinerary"]])
                
                content = f"🗺️ {plan['name']} - {city}\n\n{plan['desc']}\n\n👥 人数: {plan['people']['adults']}大{plan['people']['children']}小\n📅 游玩: {plan['suggestedDays']}天\n\n{plan['weatherNote']}\n\n📅 行程安排:\n{itinerary_text}"
                
                if plan.get("overBudget"):
                    content += f"\n\n⚠️ 超出预算 ¥{plan['budgetDiff']}"
                elif plan.get("budgetDiff") is not None:
                    content += f"\n\n✅ 预算剩余 ¥{plan['budgetDiff']}"
                
                content += f"\n\n👔 穿搭建议: {outfit.get('top', '')} + {outfit.get('bottom', '')}"
                
                cards.append({
                    "type": "plan_card",
                    "content": content,
                    "sub_cards": plan_cards,
                })
            
            return {
                "type": "plans",
                "content": f"为您规划了{len(plans)}条{city}旅游路线：",
                "plans": cards,
            }
        else:
            tourism = plan_tourism(city, weather_data)
            outfit = weather_data.get("outfit", {})
            
            cards = []
            for attr in tourism["attractions"]:
                cards.append({
                    "type": "image_card",
                    "image": attr["image"],
                    "title": attr["name"],
                    "desc": attr["desc"],
                    "price": f"门票: ¥{attr['price']}" if attr["price"] > 0 else "免费",
                })
            
            cost = tourism["costBreakdown"]
            cards.append({
                "type": "cost_card",
                "city": city,
                "days": tourism["suggestedDays"],
                "breakdown": [
                    {"label": "门票", "value": f"¥{cost['tickets']}"},
                    {"label": "住宿", "value": f"¥{cost['hotel']} ({tourism['hotelAvg']}/晚 × {tourism['suggestedDays']}晚)"},
                    {"label": "餐饮", "value": f"¥{cost['food']} ({tourism['foodAvg']}/天 × {tourism['suggestedDays']}天)"},
                    {"label": "交通", "value": f"¥{cost['transport']} ({tourism['transportAvg']}/天 × {tourism['suggestedDays']}天)"},
                ],
                "total": f"¥{cost['total']}",
            })
            
            itinerary_text = "\n".join([f"Day{item['day']} {item['period']}: {item['attraction']['name']}" for item in tourism["itinerary"]])
            
            return {
                "type": "rich",
                "content": f"🗺️ {city}旅游规划建议\n\n{tourism['weatherNote']}\n\n📅 行程安排:\n{itinerary_text}\n\n👔 穿搭建议: {outfit.get('top', '')} + {outfit.get('bottom', '')}",
                "cards": cards,
            }
    
    if "费用" in message or "花费" in message or "预算" in message or "cost" in message:
        tourism = plan_tourism(city, weather_data)
        cost = tourism["costBreakdown"]
        
        cards = [{
            "type": "cost_card",
            "city": city,
            "days": tourism["suggestedDays"],
            "breakdown": [
                {"label": "门票", "value": f"¥{cost['tickets']}"},
                {"label": "住宿", "value": f"¥{cost['hotel']} ({tourism['hotelAvg']}/晚 × {tourism['suggestedDays']}晚)"},
                {"label": "餐饮", "value": f"¥{cost['food']} ({tourism['foodAvg']}/天 × {tourism['suggestedDays']}天)"},
                {"label": "交通", "value": f"¥{cost['transport']} ({tourism['transportAvg']}/天 × {tourism['suggestedDays']}天)"},
            ],
            "total": f"¥{cost['total']}",
        }]
        
        return {
            "type": "rich",
            "content": f"💰 {city}旅游费用估算\n\n建议游玩: {tourism['suggestedDays']}天",
            "cards": cards,
        }
    
    if "一周" in message or "week" in message or "7天" in message or "未来" in message:
        forecast = weather_data.get("forecast", [])
        outfit = weather_data.get("outfit", {})
        if forecast:
            result = f"📅 {city}未来一周天气预报：\n\n"
            for day in forecast:
                result += f"• {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
            result += f"\n👔 今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
            return {"type": "text", "content": result}
        return {"type": "text", "content": "暂时没有详细预报数据"}
    
    if "明天" in message or "tomorrow" in message:
        forecast = weather_data.get("forecast", [])
        if len(forecast) > 1:
            t = forecast[1]
            outfit = weather_data.get("outfit", {})
            result = f"明天{city}天气：{t['condition']}，温度{t['tempMin']}~{t['tempMax']}°C\n\n"
            result += f"👔 穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
            return {"type": "text", "content": result}
        return {"type": "text", "content": "暂时没有明天天气预报"}
    
    if "后天" in message or "day after" in message:
        forecast = weather_data.get("forecast", [])
        if len(forecast) > 2:
            t = forecast[2]
            outfit = weather_data.get("outfit", {})
            result = f"后天{city}天气：{t['condition']}，温度{t['tempMin']}~{t['tempMax']}°C\n\n"
            result += f"👔 穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
            return {"type": "text", "content": result}
        return {"type": "text", "content": "暂时没有后天天气预报"}
    
    if "温度" in message and "趋势" in message or "温度" in message and "变化" in message:
        forecast = weather_data.get("forecast", [])
        if forecast:
            result = f"📈 {city}未来一周温度变化：\n\n"
            for day in forecast:
                bar_len = int((int(day['tempMax']) - 10) / 2)
                bar = "█" * bar_len
                result += f"{day['date']}: {day['tempMin']:>2}°C ~ {day['tempMax']:>2}°C {bar}\n"
            return {"type": "text", "content": result}
        return {"type": "text", "content": "暂无温度数据"}
    
    if "天气" in message or "weather" in message:
        forecast = weather_data.get("forecast", [])
        outfit = weather_data.get("outfit", {})
        if forecast:
            result = f"📅 {city}今日天气：{cond} {temp}°C\n\n"
            result += "未来几天预报：\n"
            for day in forecast[:5]:
                result += f"• {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
            result += f"\n👔 今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
            return {"type": "text", "content": result}
        return {"type": "text", "content": f"当前{city}的天气是{cond}，温度{temp}°C，湿度{humidity}%。"}
    
    if "温度" in message or "冷" in message or "热" in message:
        t = int(temp) if temp.isdigit() else 0
        if t > 28:
            return {"type": "text", "content": f"现在{city}温度{temp}°C({cond})，有点热哦!建议穿轻薄的衣服。"}
        elif t < 10:
            return {"type": "text", "content": f"现在{city}温度{temp}°C({cond})，比较冷!建议穿厚一点的衣服。"}
        return {"type": "text", "content": f"现在{city}温度{temp}°C({cond})，体感舒适。"}
    
    if "穿" in message or "outfit" in message:
        outfit = weather_data.get("outfit", {})
        return {"type": "text", "content": f"推荐穿：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"}
    
    if "伞" in message or "雨" in message:
        rain = weather_data.get("analysis", {}).get("rainDays", 0)
        if rain > 0:
            return {"type": "text", "content": f"本周{city}有{rain}天可能下雨，建议带伞!☔"}
        return {"type": "text", "content": f"本周{city}没有明显降水，不需要带伞~ 🌞"}
    
    if "晒" in message or "紫外线" in message or "uv" in message:
        uv = weather_data.get("analysis", {}).get("uv", "低")
        if uv == "高":
            return {"type": "text", "content": "紫外线强度较高!建议涂抹防晒霜、戴遮阳帽 🧴🕶️"}
        elif uv == "中等":
            return {"type": "text", "content": "紫外线中等强度，建议涂防晒霜~ 🧴"}
        return {"type": "text", "content": "紫外线强度较低，正常活动即可~ ☀️"}
    
    if needs_structured_response(message):
        try:
            llm_response = call_zhipu_llm(message, weather_data)
            return {"type": "text", "content": llm_response}
        except Exception as e:
            print(f"LLM 调用失败: {e}")
    
    try:
        llm_response = call_zhipu_llm(message, weather_data)
        return {"type": "text", "content": llm_response}
    except Exception as e:
        print(f"LLM 调用失败: {e}")
        return {"type": "text", "content": f"关于{city}的天气：现在是{cond}，温度{temp}°C。你可以问我穿衣、带伞、紫外线、旅游规划等问题~"}


class WeatherHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/templates/index.html'
        elif self.path == '/api/locate':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            city = get_city_from_ip()
            self.wfile.write(json.dumps({"city": city}).encode())
            return
        elif self.path.startswith('/api/weather'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            city = query.get('city', [''])[0]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if not city:
                self.wfile.write(json.dumps({"error": "请提供城市名称"}).encode())
                return
            
            city_info = get_city_location(city)
            if not city_info:
                self.wfile.write(json.dumps({"error": f"未找到城市: {city}"}).encode())
                return
            
            weather = get_weather_data(city_info["lat"], city_info["lon"])
            if not weather:
                self.wfile.write(json.dumps({"error": "获取天气失败"}).encode())
                return
            
            current = weather.get("current", {})
            daily = weather.get("daily", {})
            
            wind_speed = current.get("wind_speed_10m", 0)
            wind_scale = int(wind_speed / 10) if wind_speed else 0
            
            rain_days = sum(1 for p in daily.get("precipitation_sum", [0]) if p > 0)
            
            temp = int(current.get("temperature_2m", 20))
            humidity = int(current.get("relative_humidity_2m", 50))
            weather_code = current.get("weather_code", 0)
            
            forecast_list = []
            dates = daily.get("time", [])
            for i, date in enumerate(dates):
                code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
                forecast_list.append({
                    "date": date[-5:].replace("-", "/"),
                    "tempMax": str(int(daily.get("temperature_2m_max", [20])[i] if i < len(daily.get("temperature_2m_max", [])) else 20)),
                    "tempMin": str(int(daily.get("temperature_2m_min", [10])[i] if i < len(daily.get("temperature_2m_min", [])) else 10)),
                    "condition": weather_code_to_text(code),
                    "icon": weather_code_to_icon(code),
                })
            
            month = 5
            uv = "高" if month in [5, 6, 7, 8] else "中等" if month in [3, 4, 9, 10] else "低"
            
            outfit = analyze_outfit(temp, humidity, wind_scale, rain_days, uv)
            
            tourism = plan_tourism(city_info.get("name", city), {
                "current": {"temp": str(temp), "condition": weather_code_to_text(weather_code)},
                "analysis": {"rainDays": rain_days},
            })
            
            result = {
                "city": city_info.get("name", city),
                "current": {
                    "temp": str(temp),
                    "condition": weather_code_to_text(weather_code),
                    "humidity": str(humidity),
                    "wind": f"{wind_direction(current.get('wind_direction_10m', 0))} {wind_scale}级",
                },
                "analysis": {
                    "rainDays": rain_days,
                    "uv": uv,
                    "comfort": outfit["comfort"],
                },
                "forecast": forecast_list,
                "outfit": outfit,
                "tips": outfit.get("tips", []),
                "tourism": tourism,
            }
            
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
            return
        
        return super().do_GET()
    
    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            message = data.get('message', '')
            city_data = data.get('cityData')
            
            reply = process_chat(message, city_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}, ensure_ascii=False).encode())
            return
        
        return super().do_GET()


def run_server(port=None):
    if port is None:
        port = int(os.environ.get("PORT", 5000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, partial(WeatherHandler, directory=os.path.dirname(os.path.abspath(__file__))))
    print("=" * 50)
    print("  智能天气穿搭助手 Web版")
    print(f"  http://localhost:{port}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)
    httpd.serve_forever()


if __name__ == '__main__':
    run_server()
