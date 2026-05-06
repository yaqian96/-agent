import os
import sys
import json
from flask import Flask, render_template, request, jsonify
from weather_api import fetch_weather_data, get_mock_weather_data
from analyzer import analyze_weather
from outfit_recommender import recommend_outfit

app = Flask(__name__)

IP_API_URL = "http://ip-api.com/json/"
OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"

CITY_KEYWORDS = {
    "北京": "北京", "beijing": "北京", "bj": "北京",
    "上海": "上海", "shanghai": "上海", "sh": "上海",
    "广州": "广州", "guangzhou": "广州", "gz": "广州",
    "深圳": "深圳", "shenzhen": "深圳", "sz": "深圳",
    "杭州": "杭州", "hangzhou": "杭州", "hz": "杭州",
    "成都": "成都", "chengdu": "成都", "cd": "成都",
    "武汉": "武汉", "wuhan": "武汉", "wh": "武汉",
    "西安": "西安", "xian": "西安", "xa": "西安",
    "重庆": "重庆", "chongqing": "重庆", "cq": "重庆",
    "南京": "南京", "nanjing": "南京", "nj": "南京",
    "天津": "天津", "tianjin": "天津", "tj": "天津",
    "苏州": "苏州", "suzhou": "苏州", "sz": "苏州",
    "郑州": "郑州", "zhengzhou": "郑州", "zz": "郑州",
    "长沙": "长沙", "changsha": "长沙", "cs": "长沙",
    "青岛": "青岛", "qingdao": "青岛", "qd": "青岛",
    "沈阳": "沈阳", "shenyang": "沈阳", "sy": "沈阳",
    "大连": "大连", "dalian": "大连", "dl": "大连",
    "厦门": "厦门", "xiamen": "厦门", "xm": "厦门",
    "宁波": "宁波", "ningbo": "宁波", "nb": "宁波",
    "昆明": "昆明", "kunming": "昆明", "km": "昆明",
}


def get_city_from_ip():
    try:
        import urllib.request
        import urllib.parse
        
        url = f"{IP_API_URL}?fields=status,country,city,lat,lon"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            
            if data.get("status") == "success":
                city = data.get("city", "")
                if city:
                    return city
    except Exception as e:
        print(f"IP定位失败: {e}")
    
    return None


def get_weather_for_city(city_name):
    weather_data = fetch_weather_data(city_name)
    
    if not weather_data:
        weather_data = get_mock_weather_data(city_name)
    
    return weather_data


def prepare_response_data(weather_data):
    analysis = analyze_weather(weather_data)
    
    from outfit_recommender import OutfitRecommender
    recommender = OutfitRecommender(weather_data, analysis)
    outfit_summary = recommender.get_outfit_summary()
    
    forecast_data = []
    for day in weather_data.get("forecast", [])[:7]:
        date = day.get("fxDate", "")[-5:].replace("-", "/")
        forecast_data.append({
            "date": date,
            "tempMax": day.get("tempMax", "--"),
            "tempMin": day.get("tempMin", "--"),
            "condition": day.get("textDay", "未知"),
            "icon": get_weather_icon(day.get("textDay", "")),
        })
    
    tips = []
    if analysis.get("precipitation", {}).get("rainy_days", 0) > 0:
        tips.append(f"☔ 本周有{analysis['precipitation']['rainy_days']}天可能下雨，记得带伞!")
    if analysis.get("uv") == "高":
        tips.append("☀️ 紫外线较强，建议涂防晒霜!")
    if analysis.get("wind", {}).get("level") in ["较大", "强风"]:
        tips.append("💨 风速较大，建议穿防风外套")
    temp = int(analysis.get("current", {}).get("temp", 20))
    if temp >= 30:
        tips.append("🥵 天气炎热，注意防暑降温，多喝水!")
    elif temp <= 10:
        tips.append("❄️ 天气较冷，注意保暖!")
    
    return {
        "city": weather_data.get("city", {}).get("name", ""),
        "current": analysis.get("current", {}),
        "analysis": analysis,
        "forecast": forecast_data,
        "outfit": outfit_summary.get("outfit", {}),
        "tips": tips,
    }


def get_weather_icon(condition):
    icons = {
        "晴": "☀️", "多云": "⛅", "阴": "☁️",
        "小雨": "🌧️", "中雨": "🌧️", "大雨": "⛈️",
        "小雪": "🌨️", "雪": "❄️",
        "雾": "🌫️", "霾": "🌫️",
    }
    return icons.get(condition, "🌤️")


def process_chat_message(message, city_data):
    message = message.lower().strip()
    
    keywords = {
        "天气": ["天气", "weather", "怎么样", "如何"],
        "温度": ["温度", "temp", "冷", "热", "多少度"],
        "穿衣": ["穿", " outfits", " clothes", "打扮", "搭配"],
        "带伞": ["伞", "rain", "下雨", "雨"],
        "紫外线": ["晒", "sun", "防晒", "紫外线", "uv"],
        "明天": ["tomorrow", "明天", "明儿"],
        "建议": ["建议", "recommend", "应该", "怎么样"],
    }
    
    for intent, words in keywords.items():
        if any(word in message for word in words):
            if intent == "天气":
                if city_data:
                    current = city_data.get("current", {})
                    return f"当前{city_data['city']}的天气是：{current.get('condition', '未知')}，温度{current.get('temp', '--')}°C，湿度{current.get('humidity', '--')}%。"
                return "请先告诉我你在哪个城市，我来帮你查询天气~"
            
            elif intent == "温度":
                if city_data:
                    current = city_data.get("current", {})
                    temp = current.get("temp", "--")
                    cond = current.get("condition", "")
                    if int(temp) if temp.isdigit() else 0 > 28:
                        return f"现在{city_data['city']}温度是{temp}°C({cond})，有点热哦!建议穿轻薄的衣服。"
                    elif int(temp) if temp.isdigit() else 0 < 10:
                        return f"现在{city_data['city']}温度是{temp}°C({cond})，比较冷!建议穿厚一点的衣服。"
                    return f"现在{city_data['city']}温度是{temp}°C({cond})，体感舒适。"
                return "请先告诉我你在哪个城市~"
            
            elif intent == "穿衣":
                if city_data:
                    outfit = city_data.get("outfit", {})
                    return f"根据当前天气，推荐穿：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
                return "请先告诉我你想查询哪个城市的穿搭建议？"
            
            elif intent == "带伞":
                if city_data:
                    rainy = city_data.get("analysis", {}).get("precipitation", {}).get("rainy_days", 0)
                    if rainy > 0:
                        return f"本周{city_data['city']}有{rainy}天可能下雨，建议出门带伞哦!☔"
                    return f"本周{city_data['city']}没有明显降水，不需要带伞~ 🌞"
                return "请告诉我你在哪个城市，我帮你查查要不要带伞~"
            
            elif intent == "紫外线":
                if city_data:
                    uv = city_data.get("analysis", {}).get("uv", "低")
                    if uv == "高":
                        return "紫外线强度较高!建议涂抹防晒霜、戴遮阳帽和太阳镜 🧴🕶️"
                    elif uv == "中等":
                        return "紫外线中等强度，建议涂防晒霜~ 🧴"
                    return "紫外线强度较低，正常活动即可~ ☀️"
                return "请告诉我你在哪个城市~"
            
            elif intent == "明天":
                if city_data:
                    forecast = city_data.get("forecast", [])
                    if len(forecast) > 1:
                        tomorrow = forecast[1]
                        return f"明天{city_data['city']}天气：{tomorrow['condition']}，温度{tomorrow['tempMin']}~{tomorrow['tempMax']}°C"
                    return "暂时没有明天的天气预报数据"
                return "请先告诉我你在哪个城市~"
            
            elif intent == "建议":
                if city_data:
                    tips = city_data.get("tips", [])
                    if tips:
                        return "今日建议：\n" + "\n".join(tips)
                    return "今天天气不错，穿着方面没有特别建议~"
                return "请先告诉我你想查询的城市~"
    
    if city_data:
        current = city_data.get("current", {})
        return f"关于{city_data['city']}的天气：现在是{current.get('condition', '未知')}，温度{current.get('temp', '--')}°C。你可以问我关于穿衣、带伞、紫外线等问题~"
    
    return "你好!请告诉我你想查询的城市，我来给你提供天气和穿搭建议~ 😊"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/locate')
def locate():
    city = get_city_from_ip()
    
    if not city:
        return jsonify({"city": None, "error": "定位失败"})
    
    return jsonify({"city": city})


@app.route('/api/weather')
def weather():
    city = request.args.get('city', '')
    
    if not city:
        return jsonify({"error": "请提供城市名称"})
    
    try:
        weather_data = get_weather_for_city(city)
        
        if not weather_data:
            return jsonify({"error": f"未找到城市: {city}"})
        
        result = prepare_response_data(weather_data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    city_data = data.get('cityData')
    
    reply = process_chat_message(message, city_data)
    
    return jsonify({"reply": reply})


if __name__ == '__main__':
    print("=" * 50)
    print("  智能天气穿搭助手 Web版")
    print("  启动中...")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
