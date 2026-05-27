from typing import Any, Dict, Iterator, Optional

from chat_chains import invoke_runnable_chain, stream_runnable_chain
from chat_common import is_weather_related, format_weather_context

__all__ = [
    'is_weather_related',
    'format_weather_context',
    'stream_chat_message',
    'process_chat_message',
]


def stream_chat_message(
    message: str,
    city_data: Optional[Dict[str, Any]] = None,
) -> Iterator[str]:
    message = (message or '').strip()
    if not message:
        yield '请输入你的问题~'
        return

    print(f'[chat] 消息: {message}')
    print(f'[chat] 路由: {"RAG+天气 Runnable" if is_weather_related(message) else "LLM通用 Runnable"}')
    yield from stream_runnable_chain(message, city_data)


def process_chat_message(message: str, city_data: Optional[Dict[str, Any]] = None) -> str:
    message = (message or '').strip()
    if not message:
        return '请输入你的问题~'
    return invoke_runnable_chain(message, city_data)
