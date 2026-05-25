import os
import json
import urllib.request
from typing import Dict, Any
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from simple_rag_system import get_rag_system

# 直接从web_server.py中复制需要的函数，避免循环导入
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
    return None

def get_weather_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Asia%2FShanghai"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"获取天气失败: {e}")
        return None

def weather_code_to_text(code):
    if code == 0:
        return "晴朗"
    elif 1 <= code <= 3:
        return "多云"
    elif 45 <= code <= 48:
        return "雾"
    elif 51 <= code <= 57:
        return "毛毛雨"
    elif 61 <= code <= 67:
        return "小雨"
    elif 71 <= code <= 77:
        return "雪"
    elif 80 <= code <= 82:
        return "阵雨"
    elif 95 <= code <= 99:
        return "雷暴"
    return "未知"

def wind_direction(deg):
    dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    return dirs[int((deg + 22.5) / 45) % 8]

def analyze_outfit(temp, humidity, wind_scale, rain_days, uv):
    temp = int(temp) if temp else 20
    if temp >= 28:
        category = "炎热夏季"
        top = "短袖T恤/衬衫"
        bottom = "短裤/薄长裤"
        shoes = "凉鞋/帆布鞋"
        accessory = "帽子、太阳镜"
        fabric = "棉麻/轻薄透气"
        comfort = "炎热"
    elif temp >= 20:
        category = "春秋季"
        top = "长袖T恤/薄外套"
        bottom = "长裤"
        shoes = "运动鞋/休闲鞋"
        accessory = "薄围巾"
        fabric = "棉/混纺"
        comfort = "舒适"
    elif temp >= 10:
        category = "早春/深秋"
        top = "厚毛衣/风衣/大衣"
        bottom = "保暖长裤/加绒裤"
        shoes = "靴子/保暖鞋"
        accessory = "围巾/手套"
        fabric = "羊毛/呢子/加绒"
        comfort = "较凉"
    elif temp >= 5:
        category = "初冬"
        top = "羽绒服/厚棉服/大衣"
        bottom = "加绒裤/保暖裤"
        shoes = "保暖靴子"
        accessory = "围巾/手套/帽子"
        fabric = "羽绒服/厚棉"
        comfort = "寒冷"
    else:
        category = "严寒冬季"
        top = "羽绒服(厚款)/滑雪服"
        bottom = "加厚保暖裤"
        shoes = "雪地靴/保暖靴"
        accessory = "厚围巾/手套/帽子/耳罩"
        fabric = "专业防寒"
        comfort = "极寒"
    
    tips = []
    if rain_days > 0:
        tips.append("记得带伞☔")
    if uv == "高":
        tips.append("注意防晒🧴")
    
    return {
        "category": category,
        "top": top,
        "bottom": bottom,
        "shoes": shoes,
        "accessory": accessory,
        "fabric": fabric,
        "comfort": comfort,
        "tips": tips
    }

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY")

# 全局存储当前天气数据
current_weather_data = {}


@tool
def get_weather_info(city: str) -> str:
    """获取指定城市的当前天气信息和穿搭建议
    
    Args:
        city: 城市名称，如"北京"、"上海"、"成都"等
    
    Returns:
        包含天气信息和穿搭建议的字符串
    """
    global current_weather_data
    
    city_info = get_city_location(city)
    if not city_info:
        return f"未找到城市: {city}"
    
    weather = get_weather_data(city_info["lat"], city_info["lon"])
    if not weather:
        return f"获取{city}天气失败"
    
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
        })
    
    month = 5
    uv = "高" if month in [5, 6, 7, 8] else "中等" if month in [3, 4, 9, 10] else "低"
    outfit = analyze_outfit(temp, humidity, wind_scale, rain_days, uv)
    
    current_weather_data = {
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
    
    result = f"📅 {city}今日天气：{weather_code_to_text(weather_code)} {temp}°C\n\n"
    result += f"湿度：{humidity}%，风力：{wind_direction(current.get('wind_direction_10m', 0))} {wind_scale}级\n\n"
    result += "未来几天预报：\n"
    for day in forecast_list[:5]:
        result += f"- {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
    result += f"\n👔 今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
    
    return result


@tool
def get_outfit_recommendation(city: str) -> str:
    """获取指定城市的穿搭建议
    
    Args:
        city: 城市名称
    
    Returns:
        包含穿搭建议的字符串
    """
    global current_weather_data
    
    if not current_weather_data or current_weather_data.get("city") != city:
        # 先获取天气信息
        weather_result = get_weather_info.invoke({"city": city})
        if "未找到城市" in weather_result or "获取天气失败" in weather_result:
            return weather_result
    
    outfit = current_weather_data.get("outfit", {})
    return f"👔 {city}今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"


@tool
def get_weekly_forecast(city: str) -> str:
    """获取指定城市的一周天气预报
    
    Args:
        city: 城市名称
    
    Returns:
        包含一周天气预报的字符串
    """
    global current_weather_data
    
    if not current_weather_data or current_weather_data.get("city") != city:
        weather_result = get_weather_info.invoke({"city": city})
        if "未找到城市" in weather_result or "获取天气失败" in weather_result:
            return weather_result
    
    forecast = current_weather_data.get("forecast", [])
    outfit = current_weather_data.get("outfit", {})
    
    result = f"📅 {city}未来一周天气预报：\n\n"
    for day in forecast:
        result += f"- {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
    result += f"\n👔 今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
    
    return result


@tool
def get_rain_info(city: str) -> str:
    """获取指定城市的降雨信息和建议
    
    Args:
        city: 城市名称
    
    Returns:
        包含降雨信息和建议的字符串
    """
    global current_weather_data
    
    if not current_weather_data or current_weather_data.get("city") != city:
        weather_result = get_weather_info.invoke({"city": city})
        if "未找到城市" in weather_result or "获取天气失败" in weather_result:
            return weather_result
    
    rain = current_weather_data.get("analysis", {}).get("rainDays", 0)
    if rain > 0:
        return f"本周{city}有{rain}天可能下雨，建议带伞!☔"
    return f"本周{city}没有明显降水，不需要带伞~ 🌞"


@tool
def get_uv_info(city: str) -> str:
    """获取指定城市的紫外线信息和建议
    
    Args:
        city: 城市名称
    
    Returns:
        包含紫外线信息和建议的字符串
    """
    global current_weather_data
    
    if not current_weather_data or current_weather_data.get("city") != city:
        weather_result = get_weather_info.invoke({"city": city})
        if "未找到城市" in weather_result or "获取天气失败" in weather_result:
            return weather_result
    
    uv = current_weather_data.get("analysis", {}).get("uv", "低")
    if uv == "高":
        return "紫外线强度较高!建议涂抹防晒霜、戴遮阳帽 🧴🕶️"
    elif uv == "中等":
        return "紫外线中等强度，建议涂防晒霜~ 🧴"
    return "紫外线强度较低，正常活动即可~ ☀️"


# 定义工具列表
tools = [
    get_weather_info,
    get_outfit_recommendation,
    get_weekly_forecast,
    get_rain_info,
    get_uv_info
]

# 创建LLM
llm = ChatOpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    api_key=ZHIPU_API_KEY,
    model="glm-4-flash",
    temperature=0.7,
    max_tokens=800
)

# 将工具绑定到LLM
llm_with_tools = llm.bind_tools(tools)


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


def chat_with_agent(message: str, weather_data: Dict[str, Any] = None) -> str:
    """与Agent进行对话
    
    Args:
        message: 用户输入的消息
        weather_data: 当前的天气数据（可选）
    
    Returns:
        Agent的回复
    """
    global current_weather_data
    
    # 如果提供了天气数据，更新全局数据
    if weather_data:
        current_weather_data = weather_data
    
    # 如果有天气数据，直接根据消息类型进行回答
    if current_weather_data:
        city = current_weather_data.get('city', '')
        current = current_weather_data.get('current', {})
        forecast = current_weather_data.get('forecast', [])
        outfit = current_weather_data.get('outfit', {})
        analysis = current_weather_data.get('analysis', {})
        
        # 检查是否询问明天的天气
        if '明天' in message or 'tomorrow' in message:
            if len(forecast) > 1:
                t = forecast[1]
                result = f"📅 明天{city}天气：{t['condition']}，温度{t['tempMin']}~{t['tempMax']}°C\n\n"
                result += f"👔 穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
                return result
        
        # 检查是否询问后天的天气
        if '后天' in message or 'day after' in message:
            if len(forecast) > 2:
                t = forecast[2]
                result = f"📅 后天{city}天气：{t['condition']}，温度{t['tempMin']}~{t['tempMax']}°C\n\n"
                result += f"👔 穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
                return result
        
        # 检查是否询问一周/未来天气
        if '一周' in message or 'week' in message or '7天' in message or '未来' in message:
            if forecast:
                result = f"📅 {city}未来一周天气预报：\n\n"
                for day in forecast:
                    result += f"• {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
                result += f"\n👔 今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
                return result
        
        # 检查是否询问温度趋势/变化
        if '温度' in message and ('趋势' in message or '变化' in message):
            if forecast:
                result = f"📈 {city}未来一周温度变化：\n\n"
                for day in forecast:
                    bar_len = int((int(day['tempMax']) - 10) / 2)
                    bar = "█" * bar_len
                    result += f"{day['date']}: {day['tempMin']:>2}°C ~ {day['tempMax']:>2}°C {bar}\n"
                return result
        
        # 检查是否询问天气
        if '天气' in message or 'weather' in message:
            if forecast:
                result = f"📅 {city}今日天气：{current.get('condition', '')} {current.get('temp', '')}°C\n\n"
                result += "未来几天预报：\n"
                for day in forecast[:5]:
                    result += f"• {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
                result += f"\n👔 今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
                return result
        
        # 检查是否询问温度/冷热
        if '温度' in message or '冷' in message or '热' in message:
            t = int(current.get('temp', 0)) if current.get('temp', '0').isdigit() else 0
            if t > 28:
                return f"现在{city}温度{current.get('temp', '')}°C({current.get('condition', '')})，有点热哦!建议穿轻薄的衣服。"
            elif t < 10:
                return f"现在{city}温度{current.get('temp', '')}°C({current.get('condition', '')})，比较冷!建议穿厚一点的衣服。"
            return f"现在{city}温度{current.get('temp', '')}°C({current.get('condition', '')})，体感舒适。"
        
        # 检查是否询问穿搭
        if '穿' in message or 'outfit' in message:
            return f"👔 {city}今日穿搭建议：\n上衣：{outfit.get('top', '')}\n下装：{outfit.get('bottom', '')}\n鞋子：{outfit.get('shoes', '')}\n配饰：{outfit.get('accessory', '')}"
        
        # 检查是否询问伞/雨
        if '伞' in message or '雨' in message:
            rain = analysis.get('rainDays', 0)
            if rain > 0:
                return f"本周{city}有{rain}天可能下雨，建议带伞!☔"
            return f"本周{city}没有明显降水，不需要带伞~ 🌞"
        
        # 检查是否询问紫外线
        if '晒' in message or '紫外线' in message or 'uv' in message:
            uv = analysis.get('uv', '低')
            if uv == "高":
                return "紫外线强度较高!建议涂抹防晒霜、戴遮阳帽 🧴🕶️"
            elif uv == "中等":
                return "紫外线中等强度，建议涂防晒霜~ 🧴"
            return "紫外线强度较低，正常活动即可~ ☀️"
    
    # 如果没有匹配到特定问题，使用LLM回答
    try:
        # 获取RAG系统
        rag = get_rag_system()
        weather_context_str = f"{current_weather_data.get('city', '') if current_weather_data else ''} 当前温度{current_weather_data.get('current', {}).get('temp', 'N/A') if current_weather_data else 'N/A'}°C"
        
        retrieved_docs = rag.retrieve(message, weather_context=weather_context_str, k=3)
        rag_context = rag.format_retrieved_context(retrieved_docs)
        
        system_prompt = """你是"小智"，一个专业的智能天气穿搭助手。请根据上下文信息，用友好、活泼的语气回答用户的问题。"""
        
        user_input = f"{message}\n\n【上下文信息】\n{rag_context}"
        
        messages = [
            ("system", system_prompt),
            ("user", user_input)
        ]
        
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        print(f"LLM调用失败: {e}")
        if current_weather_data:
            city = current_weather_data.get('city', '')
            return f"关于{city}的天气：现在是{current.get('condition', '')}，温度{current.get('temp', '')}°C。你可以问我穿衣、带伞、紫外线等问题~"
        return "请先选择一个城市，我来帮你查询天气和穿搭建议~ 😊"
