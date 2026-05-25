import os
import sys
import json
import base64
import time
import urllib.request
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_sock import Sock
from weather_api import fetch_weather_data, get_mock_weather_data
from analyzer import analyze_weather
from outfit_recommender import recommend_outfit
from conversation_manager import get_conversation_manager
from tts_service import synthesize_speech, get_voice_types, get_tts_service
from asr_service import recognize_speech
from streaming_tts import synthesize_speech_stream_base64, synthesize_speech_sentences_stream

app = Flask(__name__)
sock = Sock(app)

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


CHINA_CITIES = {
    "北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安",
    "重庆", "南京", "天津", "苏州", "郑州", "长沙", "青岛", "沈阳",
    "大连", "厦门", "宁波", "昆明", "哈尔滨", "长春", "石家庄",
    "太原", "济南", "合肥", "福州", "南昌", "贵阳", "南宁", "海口",
    "拉萨", "乌鲁木齐", "呼和浩特", "银川", "西宁", "兰州"
}


def normalize_city_name(city):
    if not city:
        return None
    city = city.strip().replace("市", "").replace("省", "")
    if city in CHINA_CITIES:
        return city
    for china_city in CHINA_CITIES:
        if china_city in city or city in china_city:
            return china_city
    return city


def get_city_from_coords(lat, lon):
    try:
        url = (
            f"https://api.bigdatacloud.net/data/reverse-geocode-client"
            f"?latitude={lat}&longitude={lon}&localityLanguage=zh"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "WeatherOutfitAgent/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            city = (
                data.get("city")
                or data.get("locality")
                or data.get("principalSubdivision")
                or ""
            )
            return normalize_city_name(city)
    except Exception as e:
        print(f"坐标反查城市失败: {e}")
    return None


def get_city_from_ip():
    apis = [
        ("https://ip.useragentinfo.com/json", "useragentinfo"),
        ("http://ip-api.com/json/?fields=status,country,city,lat,lon", "ip-api"),
        ("http://ipwho.is/", "ipwho"),
    ]

    for url, api_name in apis:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))

                city = None
                lat = None
                lon = None

                if api_name == "useragentinfo":
                    city = data.get("city", "")
                    lat = data.get("lat")
                    lon = data.get("lon")
                elif api_name == "ip-api":
                    if data.get("status") != "success":
                        continue
                    city = data.get("city", "")
                    lat = data.get("lat")
                    lon = data.get("lon")
                elif api_name == "ipwho":
                    if not data.get("success"):
                        continue
                    city = data.get("city", "")
                    lat = data.get("latitude")
                    lon = data.get("longitude")

                normalized = normalize_city_name(city)
                if normalized:
                    print(f"IP定位成功 ({api_name}): {normalized}")
                    return normalized

                if lat is not None and lon is not None:
                    coord_city = get_city_from_coords(lat, lon)
                    if coord_city:
                        print(f"IP坐标反查成功 ({api_name}): {coord_city}")
                        return coord_city

        except Exception as e:
            print(f"定位API {api_name} 失败: {e}")
            continue

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
    original_message = message
    message = message.lower().strip()
    
    print(f"DEBUG: 原始消息: {original_message}")
    print(f"DEBUG: city_data: {city_data}")
    
    if '一周' in original_message or '7天' in original_message or '七天' in original_message or '未来' in original_message:
        print("DEBUG: 匹配到一周/7天关键词")
        if city_data:
            forecast = city_data.get("forecast", [])
            print(f"DEBUG: forecast数据: {forecast}")
            result = f"📅 {city_data['city']}未来一周天气预报：\n\n"
            for day in forecast:
                result += f"• {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
            print(f"DEBUG: 返回结果: {result}")
            return result
        return "请先告诉我你想查询的城市~"
    
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
                    forecast = city_data.get("forecast", [])
                    result = f"当前{city_data['city']}的天气是：{current.get('condition', '未知')}，温度{current.get('temp', '--')}°C，湿度{current.get('humidity', '--')}%。\n\n"
                    if forecast:
                        result += "未来几天预报：\n"
                        for day in forecast[:3]:
                            result += f"• {day['date']}: {day['condition']} {day['tempMin']}~{day['tempMax']}°C\n"
                    return result
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
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if lat is not None and lon is not None:
        city = get_city_from_coords(lat, lon)
        if city:
            return jsonify({"city": city, "source": "gps"})
        return jsonify({"city": None, "error": "无法根据坐标解析城市，请手动输入"})

    city = get_city_from_ip()
    if not city:
        return jsonify({"city": None, "error": "自动定位失败，请手动输入城市或允许浏览器定位权限"})

    return jsonify({"city": city, "source": "ip"})


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
    import json
    try:
        body = request.get_data().decode('utf-8')
        data = json.loads(body)
    except:
        data = request.json
    
    message = data.get('message', '')
    city_data = data.get('cityData')
    conv_id = data.get('convId', '')
    
    cm = get_conversation_manager()
    
    if not conv_id:
        city = city_data.get('city', '') if city_data else ''
        conv_id = cm.create_conversation(city)
    
    cm.add_message(conv_id, "user", message)
    
    reply = process_chat_message(message, city_data)
    
    cm.add_message(conv_id, "bot", reply)
    
    token_check = cm.check_token_limit(conv_id)
    
    return jsonify({
        "reply": reply,
        "convId": conv_id,
        "tokenWarning": token_check.get("warning", False),
        "tokenMessage": token_check.get("message", ""),
        "messageCount": cm.get_conversation(conv_id).get("message_count", 0),
        "totalTokens": cm.get_conversation(conv_id).get("total_tokens", 0)
    })


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    data = request.get_json(silent=True) or {}
    message = data.get('message', '')
    city_data = data.get('cityData')
    conv_id = data.get('convId', '')

    def generate():
        try:
            cm = get_conversation_manager()

            if not conv_id:
                city = city_data.get('city', '') if city_data else ''
                new_conv_id = cm.create_conversation(city)
            else:
                new_conv_id = conv_id

            cm.add_message(new_conv_id, 'user', message)
            reply = process_chat_message(message, city_data)
            cm.add_message(new_conv_id, 'bot', reply)

            yield ': connected\n\n'

            if reply:
                for i in range(0, len(reply), 2):
                    chunk = reply[i:i + 2]
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"
                    time.sleep(0.03)

            yield f"data: {json.dumps({'type': 'done', 'convId': new_conv_id}, ensure_ascii=False)}\n\n"

        except Exception as e:
            print(f'Stream error: {e}')
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Content-Type': 'text/event-stream; charset=utf-8',
        },
    )


@app.route('/api/asr/stream', methods=['POST'])
def asr_stream():
    import json

    audio_file = request.files.get('file')
    audio_data = audio_file.read() if audio_file else request.get_data()
    format = request.form.get('format', 'pcm')

    def generate():
        try:
            if not audio_data:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有收到音频数据'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'start'})}\n\n"

            result = recognize_speech(audio_data, format)

            if not result.get('success'):
                yield f"data: {json.dumps({'type': 'error', 'message': result.get('error', '语音识别失败')})}\n\n"
                return

            text = result.get('text', '')
            for char in text:
                yield f"data: {json.dumps({'type': 'text', 'content': char})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'text': text, 'request_id': result.get('request_id')})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@app.route('/api/asr', methods=['POST'])
def asr_api():
    try:
        audio_file = request.files.get('file')
        if not audio_file:
            audio_data = request.get_data()
        else:
            audio_data = audio_file.read()
        
        format = request.form.get('format', 'mp3')
        
        if not audio_data:
            return jsonify({"success": False, "error": "没有收到音频数据"}), 400
        
        result = recognize_speech(audio_data, format)
        
        if result['success']:
            return jsonify({
                "success": True,
                "text": result['text'],
                "request_id": result.get('request_id')
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', '语音识别失败')
            }), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tts', methods=['POST'])
def tts_api():
    try:
        data = request.json
        text = data.get('text', '')
        voice_type = data.get('voice_type')
        speed = data.get('speed')
        volume = data.get('volume')
        
        if not text:
            return jsonify({"error": "请提供要转换的文本"}), 400
        
        result = synthesize_speech(text, voice_type, speed, volume)
        
        if result['success']:
            audio_base64 = base64.b64encode(result['audio']).decode('utf-8')
            return jsonify({
                "success": True,
                "audio": audio_base64,
                "format": "mp3",
                "request_id": result.get('request_id')
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'TTS合成失败')
            }), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tts/stream', methods=['GET', 'POST'])
def tts_stream():
    if request.method == 'POST':
        data = request.json or {}
        text = data.get('text', '')
        voice_type = data.get('voice_type')
        speed = data.get('speed')
        volume = data.get('volume')
        stream_mode = data.get('stream', 'sse')
    else:
        text = request.args.get('text', '')
        voice_type = request.args.get('voice_type', type=int)
        speed = request.args.get('speed', type=float)
        volume = request.args.get('volume', type=int)
        stream_mode = 'binary'

    if not text:
        return jsonify({'error': '请提供要转换的文本'}), 400

    if stream_mode == 'sse' or request.method == 'POST':
        def generate_sse():
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            try:
                for item in synthesize_speech_sentences_stream(text, voice_type, speed, volume):
                    if item['success']:
                        yield f"data: {json.dumps({'type': 'audio', 'index': item['index'], 'text': item['text'], 'data': item['audio_base64']})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': item.get('error', 'TTS合成失败')})}\n\n"
                        return
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                print(f'TTS stream error: {e}')
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return Response(
            stream_with_context(generate_sse()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        )

    def generate_binary():
        try:
            for chunk in synthesize_speech_stream_base64(text, voice_type, speed, volume):
                if chunk:
                    yield chunk
                else:
                    break
        except Exception as e:
            print(f'TTS stream error: {e}')
            yield b''

    return Response(
        generate_binary(),
        mimetype='audio/mpeg',
        headers={
            'Content-Disposition': 'attachment',
            'Content-Type': 'audio/mpeg',
        },
    )


@sock.route('/ws/voice')
def websocket_voice(ws):
    print('WebSocket voice connection established')

    try:
        while True:
            message = ws.receive()
            print(f'Received WebSocket message: {message[:100]}...')

            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'start':
                text = data.get('text', '')
                voice_type = data.get('voice_type')
                speed = data.get('speed')
                volume = data.get('volume')

                print(f'Starting streaming TTS for text: {text[:50]}...')
                ws.send(json.dumps({'type': 'start'}))

                for item in synthesize_speech_sentences_stream(text, voice_type, speed, volume):
                    if item['success']:
                        ws.send(json.dumps({
                            'type': 'audio',
                            'index': item['index'],
                            'text': item['text'],
                            'data': item['audio_base64'],
                        }))
                    else:
                        ws.send(json.dumps({
                            'type': 'error',
                            'message': item.get('error', 'TTS合成失败'),
                        }))
                        break

                ws.send(json.dumps({'type': 'done'}))
                print('TTS streaming completed')

            elif msg_type == 'sentence':
                text = data.get('text', '').strip()
                voice_type = data.get('voice_type')
                speed = data.get('speed')
                volume = data.get('volume')
                index = data.get('index', 0)

                if not text:
                    continue

                for item in synthesize_speech_sentences_stream(text, voice_type, speed, volume):
                    if item['success']:
                        ws.send(json.dumps({
                            'type': 'audio',
                            'index': index,
                            'text': item['text'],
                            'data': item['audio_base64'],
                        }))
                    else:
                        ws.send(json.dumps({
                            'type': 'error',
                            'message': item.get('error', 'TTS合成失败'),
                        }))
                        break

            elif msg_type == 'end':
                ws.send(json.dumps({'type': 'done'}))

            elif msg_type == 'stop':
                ws.send(json.dumps({'type': 'stopped'}))

    except Exception as e:
        print(f'WebSocket error: {e}')
        try:
            ws.send(json.dumps({'type': 'error', 'message': str(e)}))
        except Exception:
            pass


@app.route('/api/tts/voices', methods=['GET'])
def tts_voices():
    return jsonify(get_voice_types())


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    cm = get_conversation_manager()
    conversations = cm.get_all_conversations()
    
    simplified_convs = []
    for conv in conversations:
        first_message = conv.get("messages", [])[0]["content"][:30] + "..." if conv.get("messages") else ""
        simplified_convs.append({
            "id": conv.get("id"),
            "city": conv.get("city", ""),
            "messageCount": conv.get("message_count", 0),
            "totalTokens": conv.get("total_tokens", 0),
            "lastUpdated": conv.get("last_updated", 0),
            "preview": first_message
        })
    
    return jsonify({"conversations": simplified_convs})


@app.route('/api/conversations/<conv_id>', methods=['GET'])
def get_conversation(conv_id):
    cm = get_conversation_manager()
    conversation = cm.get_conversation(conv_id)
    
    if not conversation:
        return jsonify({"error": "对话不存在"}), 404
    
    return jsonify(conversation)


@app.route('/api/conversations/<conv_id>/compress', methods=['POST'])
def compress_conversation(conv_id):
    cm = get_conversation_manager()
    data = request.json
    keep_recent = data.get('keepRecent', 10)
    
    result = cm.compress_conversation(conv_id, keep_recent)
    return jsonify(result)


@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    cm = get_conversation_manager()
    cm.delete_conversation(conv_id)
    return jsonify({"success": True, "message": "对话已删除"})


@app.route('/api/conversations/stats', methods=['GET'])
def get_stats():
    cm = get_conversation_manager()
    stats = cm.get_stats()
    return jsonify(stats)


@app.route('/api/conversations/new', methods=['POST'])
def create_conversation():
    cm = get_conversation_manager()
    data = request.json
    city = data.get('city', '')
    
    conv_id = cm.create_conversation(city)
    return jsonify({"convId": conv_id})


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "tts_configured": True,
        "asr_configured": True,
        "voice_types": get_voice_types()
    })


if __name__ == '__main__':
    print("=" * 50)
    print("  智能天气穿搭助手 Web版")
    print("  支持语音输入和流式语音输出")
    print("  启动中...")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
