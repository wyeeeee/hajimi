import os
import pathlib
from app.config import settings
from app.utils.logging import vertex_log

# 确保设置中存在所需的配置项，如果不存在则使用默认值
if not hasattr(settings, 'CREDENTIALS_DIR'):
    # 设置默认目录为storage_dir下的credentials
    settings.CREDENTIALS_DIR = os.path.join(settings.STORAGE_DIR, "credentials")

# 使用settings中的配置，保持原有变量名
CREDENTIALS_DIR = settings.CREDENTIALS_DIR
vertex_log('info', f"Using credentials directory: {CREDENTIALS_DIR}")

# API Key 配置
API_KEY = settings.PASSWORD if hasattr(settings, 'PASSWORD') else ""
if API_KEY:
    vertex_log('info', "Using API Key authentication")
else:
    vertex_log('info', "No API Key found, falling back to credentials file")

# Google Credentials JSON
GOOGLE_CREDENTIALS_JSON = settings.GOOGLE_CREDENTIALS_JSON if hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') else ""
if GOOGLE_CREDENTIALS_JSON:
    vertex_log('info', "Using GOOGLE_CREDENTIALS_JSON environment variable for authentication")

# 项目和位置配置
PROJECT_ID = os.environ.get('VERTEX_PROJECT_ID', '')
LOCATION = os.environ.get('VERTEX_LOCATION', 'us-central1')

# 模型配置URL
default_models_config_url = "https://raw.githubusercontent.com/gzzhongqi/vertex2openai/refs/heads/main/vertexModels.json"
MODELS_CONFIG_URL = os.environ.get('VERTEX_MODELS_CONFIG_URL', default_models_config_url)
vertex_log('info', f"Using models config URL: {MODELS_CONFIG_URL}")

# Vertex Express API Key 配置
VERTEX_EXPRESS_API_KEY_VAL = []
if hasattr(settings, 'VERTEX_EXPRESS_API_KEY') and settings.VERTEX_EXPRESS_API_KEY:
    VERTEX_EXPRESS_API_KEY_VAL = [key.strip() for key in settings.VERTEX_EXPRESS_API_KEY.split(',') if key.strip()]
    if VERTEX_EXPRESS_API_KEY_VAL:
        vertex_log('info', f"Loaded {len(VERTEX_EXPRESS_API_KEY_VAL)} Vertex Express API keys from settings")

# 假流式响应配置
FAKE_STREAMING_ENABLED = settings.FAKE_STREAMING if hasattr(settings, 'FAKE_STREAMING') else False
FAKE_STREAMING_INTERVAL_SECONDS = settings.FAKE_STREAMING_INTERVAL if hasattr(settings, 'FAKE_STREAMING_INTERVAL') else 1.0
FAKE_STREAMING_CHUNK_SIZE = settings.FAKE_STREAMING_CHUNK_SIZE if hasattr(settings, 'FAKE_STREAMING_CHUNK_SIZE') else 10
FAKE_STREAMING_DELAY_PER_CHUNK = settings.FAKE_STREAMING_DELAY_PER_CHUNK if hasattr(settings, 'FAKE_STREAMING_DELAY_PER_CHUNK') else 0.1
vertex_log('info', f"Fake streaming is {'enabled' if FAKE_STREAMING_ENABLED else 'disabled'} with interval {FAKE_STREAMING_INTERVAL_SECONDS} seconds, chunk size {FAKE_STREAMING_CHUNK_SIZE}, delay per chunk {FAKE_STREAMING_DELAY_PER_CHUNK} seconds")

def update_env_var(name, value):
    """Update environment variable in memory."""
    os.environ[name] = value
    vertex_log('info', f"Updated environment variable: {name}")

def reload_config():
    """重新加载配置，通常在持久化设置加载后调用"""
    global GOOGLE_CREDENTIALS_JSON, VERTEX_EXPRESS_API_KEY_VAL, API_KEY
    
    # 重新加载Google Credentials JSON
    GOOGLE_CREDENTIALS_JSON = settings.GOOGLE_CREDENTIALS_JSON if hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') else ""
    if GOOGLE_CREDENTIALS_JSON:
        vertex_log('info', "重新加载了GOOGLE_CREDENTIALS_JSON配置")
    
    # 重新加载Vertex Express API Key
    VERTEX_EXPRESS_API_KEY_VAL = []
    if hasattr(settings, 'VERTEX_EXPRESS_API_KEY') and settings.VERTEX_EXPRESS_API_KEY:
        VERTEX_EXPRESS_API_KEY_VAL = [key.strip() for key in settings.VERTEX_EXPRESS_API_KEY.split(',') if key.strip()]
        if VERTEX_EXPRESS_API_KEY_VAL:
            vertex_log('info', f"重新加载了{len(VERTEX_EXPRESS_API_KEY_VAL)}个Vertex Express API keys")
    
    # 重新加载API Key
    API_KEY = settings.PASSWORD if hasattr(settings, 'PASSWORD') else ""
    if API_KEY:
        vertex_log('info', "重新加载了API Key配置")

def update_config(name, value):
    """Update config variables in settings and environment variables."""
    if name == 'VERTEX_API_KEY':
        settings.PASSWORD = value  # 更新settings中的值
        global API_KEY
        API_KEY = value  # 更新本地变量
        vertex_log('info', "Updated API Key")
    elif name == 'GOOGLE_CREDENTIALS_JSON':
        settings.GOOGLE_CREDENTIALS_JSON = value
        global GOOGLE_CREDENTIALS_JSON
        GOOGLE_CREDENTIALS_JSON = value
        vertex_log('info', "Updated Google Credentials JSON")
    elif name == 'VERTEX_PROJECT_ID':
        os.environ['VERTEX_PROJECT_ID'] = value  # 这个值只在环境变量中
        global PROJECT_ID
        PROJECT_ID = value
        vertex_log('info', f"Updated Project ID to {value}")
    elif name == 'VERTEX_LOCATION':
        os.environ['VERTEX_LOCATION'] = value
        global LOCATION
        LOCATION = value
        vertex_log('info', f"Updated Location to {value}")
    elif name == 'VERTEX_MODELS_CONFIG_URL':
        os.environ['VERTEX_MODELS_CONFIG_URL'] = value
        global MODELS_CONFIG_URL
        MODELS_CONFIG_URL = value
        vertex_log('info', f"Updated Models Config URL to {value}")
    elif name == 'VERTEX_EXPRESS_API_KEY':
        settings.VERTEX_EXPRESS_API_KEY = value
        global VERTEX_EXPRESS_API_KEY_VAL
        VERTEX_EXPRESS_API_KEY_VAL = [key.strip() for key in value.split(',') if key.strip()]
        vertex_log('info', f"Updated Vertex Express API Key, now have {len(VERTEX_EXPRESS_API_KEY_VAL)} keys")
    elif name == 'FAKE_STREAMING':
        # 更新FAKE_STREAMING配置
        settings.FAKE_STREAMING = value
        global FAKE_STREAMING_ENABLED
        FAKE_STREAMING_ENABLED = value
        vertex_log('info', f"Updated FAKE_STREAMING to {value}")
        # 确保环境变量也被更新
        os.environ['FAKE_STREAMING'] = str(value).lower()
    elif name == 'FAKE_STREAMING_INTERVAL':
        # 更新FAKE_STREAMING_INTERVAL配置
        settings.FAKE_STREAMING_INTERVAL = value
        global FAKE_STREAMING_INTERVAL_SECONDS
        FAKE_STREAMING_INTERVAL_SECONDS = value
        vertex_log('info', f"Updated FAKE_STREAMING_INTERVAL to {value}")
    elif name == 'FAKE_STREAMING_CHUNK_SIZE':
        settings.FAKE_STREAMING_CHUNK_SIZE = value
        global FAKE_STREAMING_CHUNK_SIZE
        FAKE_STREAMING_CHUNK_SIZE = value
        vertex_log('info', f"Updated FAKE_STREAMING_CHUNK_SIZE to {value}")
    elif name == 'FAKE_STREAMING_DELAY_PER_CHUNK':
        settings.FAKE_STREAMING_DELAY_PER_CHUNK = value
        global FAKE_STREAMING_DELAY_PER_CHUNK
        FAKE_STREAMING_DELAY_PER_CHUNK = value
        vertex_log('info', f"Updated FAKE_STREAMING_DELAY_PER_CHUNK to {value}")
    else:
        vertex_log('warning', f"Unknown config variable: {name}")
        return

    # 更新环境变量
    update_env_var(name, value)

# Validation logic moved to app/auth.py