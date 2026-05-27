from typing import Any, Dict, Optional

from app_env import get_env

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


def get_llm():
    global _llm
    if _llm is not None:
        return _llm

    api_key = get_env('ZHIPU_API_KEY')
    if not api_key:
        return None

    from langchain_openai import ChatOpenAI

    _llm = ChatOpenAI(
        base_url='https://open.bigmodel.cn/api/paas/v4/',
        api_key=api_key,
        model='glm-4-flash',
        temperature=0.7,
        max_tokens=800,
        streaming=True,
    )
    return _llm


def fallback_weather_reply(
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
