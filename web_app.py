import os
import json
import base64

import app_env  # noqa: F401  加载 .env
from app_env import is_tencent_configured, is_zhipu_configured, log_startup_config
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_sock import Sock
from weather_api import fetch_weather_data, get_mock_weather_data
from analyzer import analyze_weather
from conversation_manager import get_conversation_manager
from location_service import get_city_from_ip, get_city_from_coords, DEFAULT_CITY

app = Flask(__name__)
sock = Sock(app)
log_startup_config()


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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/locate')
def locate():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if lat is not None and lon is not None:
        city, source = get_city_from_coords(lat, lon)
        return jsonify({
            'city': city,
            'source': source,
            'lat': lat,
            'lon': lon,
        })

    city, source = get_city_from_ip()
    return jsonify({
        'city': city,
        'source': source,
    })


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

    msg_limit = cm.check_message_limit(conv_id)
    if msg_limit.get('limit_reached'):
        return jsonify({
            'reply': msg_limit.get('message', '本对话消息已达上限'),
            'convId': conv_id,
            'limitReached': True,
            'messageCount': msg_limit.get('message_count', 0),
            'totalTokens': msg_limit.get('total_tokens', 0),
            'messageLimit': msg_limit.get('message_limit', 10),
            'limitWarning': True,
            'limitMessage': msg_limit.get('message', ''),
        })

    cm.add_message(conv_id, 'user', message)
    from chat_handler import process_chat_message
    reply = process_chat_message(message, city_data)
    cm.add_message(conv_id, 'bot', reply)

    conv = cm.get_conversation(conv_id)
    msg_limit = cm.check_message_limit(conv_id)
    token_check = cm.check_token_limit(conv_id)

    return jsonify({
        'reply': reply,
        'convId': conv_id,
        'tokenWarning': token_check.get('warning', False),
        'tokenMessage': token_check.get('message', ''),
        'messageCount': conv.get('message_count', 0),
        'totalTokens': conv.get('total_tokens', 0),
        'messageLimit': msg_limit.get('message_limit', 10),
        'limitReached': msg_limit.get('limit_reached', False),
        'limitWarning': msg_limit.get('warning', False),
        'limitMessage': msg_limit.get('message', ''),
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

            msg_limit = cm.check_message_limit(new_conv_id)
            if msg_limit.get('limit_reached'):
                yield ': connected\n\n'
                yield f"data: {json.dumps({
                    'type': 'limit',
                    'message': msg_limit.get('message', ''),
                    'convId': new_conv_id,
                    'messageCount': msg_limit.get('message_count', 0),
                    'totalTokens': msg_limit.get('total_tokens', 0),
                    'messageLimit': msg_limit.get('message_limit', 10),
                }, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'convId': new_conv_id}, ensure_ascii=False)}\n\n"
                return

            cm.add_message(new_conv_id, 'user', message)

            yield ': connected\n\n'
            yield f"data: {json.dumps({'type': 'status', 'status': 'thinking'}, ensure_ascii=False)}\n\n"

            reply_parts = []
            from chat_handler import stream_chat_message
            for chunk in stream_chat_message(message, city_data):
                reply_parts.append(chunk)
                yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"

            reply = ''.join(reply_parts).strip()
            if reply:
                cm.add_message(new_conv_id, 'bot', reply)

            conv = cm.get_conversation(new_conv_id)
            msg_limit = cm.check_message_limit(new_conv_id)
            token_check = cm.check_token_limit(new_conv_id)

            yield f"data: {json.dumps({
                'type': 'done',
                'convId': new_conv_id,
                'messageCount': conv.get('message_count', 0),
                'totalTokens': conv.get('total_tokens', 0),
                'messageLimit': msg_limit.get('message_limit', 10),
                'limitReached': msg_limit.get('limit_reached', False),
                'limitWarning': msg_limit.get('warning', False),
                'limitMessage': msg_limit.get('message', ''),
                'tokenWarning': token_check.get('warning', False),
                'tokenMessage': token_check.get('message', ''),
            }, ensure_ascii=False)}\n\n"

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

            from asr_service import recognize_speech
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
        
        format = request.form.get('format', 'pcm')
        
        if not audio_data:
            return jsonify({"success": False, "error": "没有收到音频数据"}), 400

        from asr_service import recognize_speech
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

        from tts_service import synthesize_speech
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

    from streaming_tts import synthesize_speech_stream_base64, synthesize_speech_sentences_stream

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
    from streaming_tts import synthesize_speech_sentences_stream, sanitize_tts_text
    from app_env import safe_print

    safe_print('WebSocket voice connection established')

    try:
        while True:
            message = ws.receive()
            safe_print(f'Received WebSocket message ({len(message)} bytes)')

            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'start':
                text = sanitize_tts_text(data.get('text', ''))
                voice_type = data.get('voice_type')
                speed = data.get('speed')
                volume = data.get('volume')
                token = data.get('token')

                if not text:
                    ws.send(json.dumps({'type': 'done', 'token': token}, ensure_ascii=False))
                    continue

                safe_print(f'Starting streaming TTS, length={len(text)}')
                ws.send(json.dumps({'type': 'start', 'token': token}, ensure_ascii=False))

                for item in synthesize_speech_sentences_stream(text, voice_type, speed, volume):
                    if item['success']:
                        ws.send(json.dumps({
                            'type': 'audio',
                            'index': item['index'],
                            'text': item['text'],
                            'data': item['audio_base64'],
                            'token': token,
                        }, ensure_ascii=False))
                    else:
                        ws.send(json.dumps({
                            'type': 'error',
                            'message': item.get('error', 'TTS合成失败'),
                            'token': token,
                        }, ensure_ascii=False))
                        break

                ws.send(json.dumps({'type': 'done', 'token': token}, ensure_ascii=False))
                safe_print('TTS streaming completed')

            elif msg_type == 'sentence':
                text = sanitize_tts_text(data.get('text', ''))
                voice_type = data.get('voice_type')
                speed = data.get('speed')
                volume = data.get('volume')
                index = data.get('index', 0)
                token = data.get('token')

                if not text:
                    continue

                try:
                    for item in synthesize_speech_sentences_stream(text, voice_type, speed, volume):
                        if item['success']:
                            ws.send(json.dumps({
                                'type': 'audio',
                                'index': index,
                                'text': item['text'],
                                'data': item['audio_base64'],
                                'token': token,
                            }, ensure_ascii=False))
                        else:
                            ws.send(json.dumps({
                                'type': 'error',
                                'message': item.get('error', 'TTS合成失败'),
                                'token': token,
                            }, ensure_ascii=False))
                            break
                except Exception as exc:
                    safe_print(f'TTS sentence error: {exc}')
                    ws.send(json.dumps({
                        'type': 'error',
                        'message': str(exc),
                        'token': token,
                    }, ensure_ascii=False))

            elif msg_type == 'end':
                token = data.get('token')
                ws.send(json.dumps({'type': 'done', 'token': token}, ensure_ascii=False))

            elif msg_type == 'stop':
                ws.send(json.dumps({'type': 'stopped'}, ensure_ascii=False))

    except Exception as e:
        safe_print(f'WebSocket error: {e}')
        try:
            ws.send(json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False))
        except Exception:
            pass


@app.route('/api/tts/voices', methods=['GET'])
def tts_voices():
    from tts_service import get_voice_types
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
    payload = {
        'status': 'ok',
        'llm_configured': is_zhipu_configured(),
        'tts_configured': is_tencent_configured(),
        'asr_configured': is_tencent_configured(),
    }
    if is_tencent_configured():
        from tts_service import get_voice_types
        payload['voice_types'] = get_voice_types()
    else:
        payload['voice_types'] = {}
    return jsonify(payload)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    print('=' * 50)
    print('  智能天气穿搭助手 Web版')
    print('  支持语音输入和流式语音输出')
    print('  启动中...')
    if not is_tencent_configured():
        print('  未检测到腾讯云密钥，语音功能不可用（可选）')
        print('  本地：复制 .env.example 为 .env 并填写密钥')
        print('  Render：在 Environment 中设置 TENCENT_SECRET_ID 等变量')
    if not is_zhipu_configured():
        print('  未检测到 ZHIPU_API_KEY，AI 对话不可用')
        print('  Render：在 Environment 中设置 ZHIPU_API_KEY')
    print('=' * 50)

    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True, use_reloader=False)
