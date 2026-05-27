from typing import Any, Dict, Iterator, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnableSerializable

from chat_common import (
    LLM_UNAVAILABLE_REPLY,
    fallback_weather_reply,
    format_weather_context,
    get_llm,
    is_weather_related,
)
from simple_rag_system import get_rag_system
from weather_prompt import build_weather_user_prompt, detect_weather_scenario

GENERAL_SYSTEM_PROMPT = """你是「小智」，一个友好、简洁的智能助手。
当前用户的问题与天气、穿搭无关，请直接根据你的知识如实回答。
要求：语气自然友好，回答简洁有重点，可适当使用 emoji。"""

WEATHER_SYSTEM_TEMPLATE = (
    '你是「小智」，智能天气穿搭助手。'
    '请严格依据用户消息中提供的实时天气、知识库与示例风格作答，'
    '当前场景：{scenario_desc}'
)

WEATHER_CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ('system', '{system_prompt}'),
    ('human', '{user_content}'),
])

GENERAL_CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ('system', GENERAL_SYSTEM_PROMPT),
    ('human', '{message}'),
])


def prepare_weather_inputs(data: Dict[str, Any]) -> Dict[str, Any]:
    message = data['message']
    city_data = data.get('city_data')

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

    scenario_key, scenario_desc = detect_weather_scenario(message)
    print(f'[chat] 天气场景: {scenario_key}')

    return {
        'message': message,
        'city_data': city_data,
        'rag_context': rag_context,
        'system_prompt': WEATHER_SYSTEM_TEMPLATE.format(scenario_desc=scenario_desc),
        'user_content': build_weather_user_prompt(message, weather_context, rag_context),
    }


def build_weather_chain(llm) -> RunnableSerializable:
    return (
        RunnableLambda(prepare_weather_inputs)
        | WEATHER_CHAT_PROMPT
        | llm
        | StrOutputParser()
    )


def build_general_chain(llm) -> RunnableSerializable:
    return GENERAL_CHAT_PROMPT | llm | StrOutputParser()


def build_router_chain(llm) -> RunnableSerializable:
    return RunnableBranch(
        (lambda x: is_weather_related(x.get('message', '')), build_weather_chain(llm)),
        build_general_chain(llm),
    )


_router_chain: Optional[RunnableSerializable] = None


def get_router_chain() -> Optional[RunnableSerializable]:
    global _router_chain
    llm = get_llm()
    if llm is None:
        _router_chain = None
        return None
    if _router_chain is None:
        _router_chain = build_router_chain(llm)
    return _router_chain


def _prepare_fallback_context(data: Dict[str, Any]) -> Dict[str, Any]:
    if is_weather_related(data.get('message', '')):
        return prepare_weather_inputs(data)
    return data


def stream_runnable_chain(
    message: str,
    city_data: Optional[Dict[str, Any]] = None,
) -> Iterator[str]:
    chain = get_router_chain()
    inputs: Dict[str, Any] = {'message': message, 'city_data': city_data}

    if chain is None:
        print('[chat] Runnable 链不可用：未配置 ZHIPU_API_KEY')
        if is_weather_related(message):
            prepared = _prepare_fallback_context(inputs)
            yield fallback_weather_reply(
                prepared['message'],
                prepared.get('city_data'),
                prepared.get('rag_context', ''),
            )
        else:
            yield LLM_UNAVAILABLE_REPLY
        return

    try:
        yielded = False
        for chunk in chain.stream(inputs):
            if chunk:
                yielded = True
                yield chunk
        if not yielded:
            if is_weather_related(message):
                prepared = _prepare_fallback_context(inputs)
                yield fallback_weather_reply(
                    prepared['message'],
                    prepared.get('city_data'),
                    prepared.get('rag_context', ''),
                )
            else:
                yield LLM_UNAVAILABLE_REPLY
    except Exception as e:
        print(f'[chat] Runnable 链流式调用失败: {e}')
        if is_weather_related(message):
            prepared = _prepare_fallback_context(inputs)
            yield fallback_weather_reply(
                prepared['message'],
                prepared.get('city_data'),
                prepared.get('rag_context', ''),
            )
        else:
            yield LLM_UNAVAILABLE_REPLY


def invoke_runnable_chain(
    message: str,
    city_data: Optional[Dict[str, Any]] = None,
) -> str:
    return ''.join(stream_runnable_chain(message, city_data)).strip()
