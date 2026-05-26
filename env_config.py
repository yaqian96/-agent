import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def load_env():
    if load_dotenv is None:
        return
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)


load_env()


def get_tencent_credentials():
    return (
        (os.environ.get('TENCENT_SECRET_ID') or '').strip(),
        (os.environ.get('TENCENT_SECRET_KEY') or '').strip(),
        (os.environ.get('TENCENT_APP_ID') or '0').strip(),
    )


def is_tencent_configured():
    secret_id, secret_key, _ = get_tencent_credentials()
    return bool(secret_id and secret_key)


def tencent_config_error():
    return (
        '语音识别服务未配置。请在项目目录创建 .env 文件并设置 '
        'TENCENT_SECRET_ID、TENCENT_SECRET_KEY、TENCENT_APP_ID，'
        '参考 .env.example'
    )
