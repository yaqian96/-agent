import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

_APP_DIR = Path(__file__).resolve().parent


def get_env(name: str, default: str = '') -> str:
    return (os.environ.get(name) or default).strip()


def get_int_env(name: str, default: int = 0) -> int:
    raw = get_env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def is_production() -> bool:
    return bool(get_env('RENDER'))


def load_env() -> None:
    if load_dotenv is None:
        return
    env_path = _APP_DIR / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)


load_env()


def get_tencent_credentials():
    return (
        get_env('TENCENT_SECRET_ID'),
        get_env('TENCENT_SECRET_KEY'),
        get_env('TENCENT_APP_ID') or '0',
    )


def is_tencent_configured() -> bool:
    secret_id, secret_key, _ = get_tencent_credentials()
    return bool(secret_id and secret_key)


def is_zhipu_configured() -> bool:
    return bool(get_env('ZHIPU_API_KEY'))


def tencent_config_error() -> str:
    if is_production() or not (_APP_DIR / '.env').exists():
        return (
            '语音服务未配置。请在 Render 控制台 Environment 中设置 '
            'TENCENT_SECRET_ID、TENCENT_SECRET_KEY、TENCENT_APP_ID（可选）。'
        )
    return (
        '语音服务未配置。请在项目目录创建 .env 并设置 '
        'TENCENT_SECRET_ID、TENCENT_SECRET_KEY、TENCENT_APP_ID，参考 .env.example'
    )


def zhipu_config_error() -> str:
    if is_production() or not (_APP_DIR / '.env').exists():
        return '大模型未配置。请在 Render 控制台 Environment 中设置 ZHIPU_API_KEY。'
    return '大模型未配置。请在 .env 中设置 ZHIPU_API_KEY，参考 .env.example'


def safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
        safe = message.encode(encoding, errors='replace').decode(encoding, errors='replace')
        print(safe)


def log_startup_config() -> None:
    safe_print(f"[config] ZHIPU_API_KEY: {'set' if is_zhipu_configured() else 'missing'}")
    safe_print(f"[config] Tencent voice: {'configured' if is_tencent_configured() else 'not set (optional)'}")
    if is_production():
        safe_print('[config] Running on cloud — use platform Environment variables, not .env file')
