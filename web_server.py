import os
import sys
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from zhipuai import ZhipuAI
from simple_rag_system import get_rag_system
from langchain_agent import chat_with_agent

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY")
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
    
    rag = get_rag_system()
    weather_context_str = f"{weather_data.get('city', '')} 当前温度{weather_data.get('current', {}).get('temp', 'N/A')}°C，{weather_data.get('current', {}).get('condition', 'N/A')}"
    
    retrieved_docs = rag.retrieve_with_scores(message, weather_context=weather_context_str, k=3)
    rag_context = rag.format_retrieved_context(retrieved_docs)
    
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
- 回答简洁明了，不要过长
- 优先使用【知识库】中的信息回答问题"""
    
    user_message = f"{context}\n\n【知识库信息】\n{rag_context}\n\n用户问题：{message}"
    
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
    """处理聊天消息，使用LangChain Agent
    
    Args:
        message: 用户输入的消息
        weather_data: 当前的天气数据
    
    Returns:
        包含回复的字典
    """
    try:
        # 使用LangChain Agent处理
        llm_response = chat_with_agent(message, weather_data)
        return {"type": "text", "content": llm_response}
    except Exception as e:
        print(f"Agent 调用失败: {e}")
        # 降级处理
        if not weather_data:
            return {"type": "text", "content": "请先告诉我你在哪个城市，我来帮你查询天气~ 😊"}
        city = weather_data.get("city", "")
        cond = weather_data.get("current", {}).get("condition", "")
        temp = weather_data.get("current", {}).get("temp", "0")
        return {"type": "text", "content": f"关于{city}的天气：现在是{cond}，温度{temp}°C。你可以问我穿衣、带伞、紫外线等问题~"}


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
    print("  智能天气穿搭助手 Web版 (legacy HTTP server)")
    print(f"  http://0.0.0.0:{port}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)
    httpd.serve_forever()


def run_production_server():
    """Render/Heroku 生产入口：先绑定端口，再加载 Flask 应用。"""
    port = os.environ.get('PORT', '5000')
    argv = [
        sys.executable, '-m', 'gunicorn',
        'web_app:app',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '1',
        '--threads', '2',
        '--timeout', '120',
        '--max-requests', '500',
        '--access-logfile', '-',
        '--error-logfile', '-',
    ]
    print('=' * 50)
    print('  启动生产服务 (gunicorn -> web_app)')
    print(f'  bind 0.0.0.0:{port}')
    print('=' * 50)
    os.execvp(sys.executable, argv)


if __name__ == '__main__':
    run_production_server()
