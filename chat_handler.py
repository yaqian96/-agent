import os
from typing import Any, Dict, Optional

import env_config  # noqa: F401
from simple_rag_system import get_rag_system

LLM_UNAVAILABLE_REPLY = '大模型暂不可用，请稍后重试'

WEATHER_KEYWORDS = [
    '天气', '气温', '温度', '下雨', '降雨', '降水', '伞', '雷暴', '下雪', '下雪',
    '穿搭', '穿衣', '穿什么', '怎么穿', '搭配', '衣服', '外套', '鞋子',
    '紫外线', '防晒', '遮阳', '冷暖', '冷不冷', '热不热', '多少度', '几度',
    '预报', 'forecast', 'weather', '湿度', '风力', '刮风',
    '旅游', '出行', '户外', '防风', '保暖', '闷热', '潮湿',
    '明天', '后天', '一周', '七天', '未来几天',
]

_llm = None


def is_weather_related(message: str) -> bool:
    text = (message or '').strip().lower()
    if not text:
        return False
    return any(kw in text for kw in WEATHER_KEYWORDS)


def format_weather_context(city_data: Optional[Dict[str, Any]]) -> str:
    if not city_data:
        return '暂无实时天气数据，请结合知识库回答通用穿搭建议。'

    current = city_data.get('current', {})
    forecast = city_data.get('forecast', [])
    outfit = city_data.get('outfit', {})
    analysis = city_data.get('analysis', {})

    context = f"""【实时天气信息】
城市：{city_data.get('city', '未知')}
当前温度：{current.get('temp', 'N/A')}°C
天气状况：{current.get('condition', '未知')}
湿度：{current.get('humidity', 'N/A')}%
风力：{current.get('wind', 'N/A')}
体感：{analysis.get('comfort', 'N/A')}
紫外线：{analysis.get('uv', 'N/A')}
本周可能降雨天数：{analysis.get('precipitation', {}).get('rainy_days', analysis.get('rainDays', 0))}天

【当前穿搭建议】
上衣：{outfit.get('top', 'N/A')}
下装：{outfit.get('bottom', 'N/A')}
鞋子：{outfit.get('shoes', 'N/A')}
配饰：{outfit.get('accessory', 'N/A')}"""

    if forecast:
        context += '\n\n【未来几天预报】\n'
        for day in forecast[:7]:
            context += (
                f"- {day.get('date', '')}: {day.get('condition', '')} "
                f"{day.get('tempMin', '')}~{day.get('tempMax', '')}°C\n"
            )

    return context


def _get_llm():
    global _llm
    if _llm is not None:
        return _llm

    api_key = os.environ.get('ZHIPU_API_KEY')
    if not api_key:
        return None

    from langchain_openai import ChatOpenAI

    _llm = ChatOpenAI(
        base_url='https://open.bigmodel.cn/api/paas/v4/',
        api_key=api_key,
        model='glm-4-flash',
        temperature=0.7,
        max_tokens=800,
    )
    return _llm


def answer_weather_with_rag(message: str, city_data: Optional[Dict[str, Any]]) -> str:
    rag = get_rag_system()
    weather_context = format_weather_context(city_data)
    city_name = city_data.get('city', '') if city_data else ''
    current = city_data.get('current', {}) if city_data else {}
    weather_hint = (
        f'{city_name} 当前{current.get("temp", "N/A")}°C '
        f'{current.get("condition", "")}'
    )

    retrieved_docs = rag.retrieve(message, weather_context=weather_hint, k=3)
    rag_context = rag.format_retrieved_context(retrieved_docs)

    llm = _get_llm()
    if not llm:
        return _fallback_weather_reply(message, city_data, rag_context)

    from langchain_core.messages import HumanMessage, SystemMessage

    system_prompt = """你是「小智」，专业的智能天气穿搭助手。
你的职责仅包括：天气解读、穿搭建议、出行与防晒提醒、旅游穿搭参考。

回答要求：
1. 必须结合【实时天气信息】与【知识库】作答，知识库优先
2. 语气友好、简洁，可适当使用 emoji
3. 不要回答与天气、穿搭、出行无关的内容
4. 若缺少城市天气数据，说明需先选择城市，仍可引用知识库给通用建议"""

    user_content = (
        f'{weather_context}\n\n'
        f'【知识库检索结果】\n{rag_context}\n\n'
        f'用户问题：{message}'
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ])
        return response.content.strip()
    except Exception as e:
        print(f'天气 RAG+LLM 调用失败: {e}')
        return _fallback_weather_reply(message, city_data, rag_context)


def answer_general_with_llm(message: str) -> str:
    llm = _get_llm()
    if not llm:
        print('[chat] 通用 LLM 不可用：未配置 ZHIPU_API_KEY')
        return LLM_UNAVAILABLE_REPLY

    from langchain_core.messages import HumanMessage, SystemMessage

    system_prompt = """你是「小智」，一个友好、简洁的智能助手。
当前用户的问题与天气、穿搭无关，请直接根据你的知识如实回答。
要求：语气自然友好，回答简洁有重点，可适当使用 emoji。"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message),
        ])
        text = (response.content or '').strip()
        if not text:
            print('[chat] 通用 LLM 返回空内容')
            return LLM_UNAVAILABLE_REPLY
        print(f'[chat] 通用 LLM 回复长度: {len(text)}')
        return text
    except Exception as e:
        print(f'通用 LLM 调用失败: {e}')
        return LLM_UNAVAILABLE_REPLY


def _fallback_weather_reply(
    message: str,
    city_data: Optional[Dict[str, Any]],
    rag_context: str,
) -> str:
    if not city_data:
        if rag_context and rag_context != '未找到相关知识':
            return f'请先选择城市以获取实时天气。参考知识库：\n\n{rag_context[:500]}'
        return '请先告诉我你在哪个城市，或点击上方获取天气后再提问~'

    city = city_data.get('city', '')
    current = city_data.get('current', {})
    outfit = city_data.get('outfit', {})
    return (
        f'关于{city}：当前{current.get("condition", "未知")}，'
        f'温度{current.get("temp", "--")}°C。\n'
        f'推荐：{outfit.get("top", "")} / {outfit.get("bottom", "")}。'
        f'（大模型暂不可用，以上为实时数据摘要）'
    )


def process_chat_message(message: str, city_data: Optional[Dict[str, Any]] = None) -> str:
    message = (message or '').strip()
    if not message:
        return '请输入你的问题~'

    print(f'[chat] 消息: {message}')
    print(f'[chat] 路由: {"RAG+天气" if is_weather_related(message) else "LLM通用"}')

    if is_weather_related(message):
        return answer_weather_with_rag(message, city_data)

    return answer_general_with_llm(message)
