import os
import pathlib
import logging
from datetime import datetime, timedelta
import asyncio 
GEMINI_API_KEYS = os.environ.get("GEMINI_API_KEYS", "")
#失效的API密钥
INVALID_API_KEYS = os.environ.get("INVALID_API_KEYS", "")
# 基础目录设置
BASE_DIR = pathlib.Path(__file__).parent.parent
# 存储目录
STORAGE_DIR = os.environ.get("STORAGE_DIR", "/hajimi/settings/")
ENABLE_STORAGE = os.environ.get("ENABLE_STORAGE", "false").lower() in ["true", "1", "yes"]
# 流式响应配置
FAKE_STREAMING = os.environ.get("FAKE_STREAMING", "true").lower() in ["true", "1", "yes"]
# 假流式请求的空内容返回间隔（秒）
FAKE_STREAMING_INTERVAL = float(os.environ.get("FAKE_STREAMING_INTERVAL", "1"))
# 假流式响应的每个块大小
FAKE_STREAMING_CHUNK_SIZE = int(os.environ.get("FAKE_STREAMING_CHUNK_SIZE", "10"))
# 假流式响应的每个块之间的延迟（秒）
FAKE_STREAMING_DELAY_PER_CHUNK = float(os.environ.get("FAKE_STREAMING_DELAY_PER_CHUNK", "0.1"))

# HuggingFace模式配置
HUGGINGFACE = os.environ.get("HUGGINGFACE", "false").lower() in ["true", "1", "yes"]
# HuggingFace API密钥
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

# 空响应重试次数限制
MAX_EMPTY_RESPONSES = int(os.environ.get("MAX_EMPTY_RESPONSES", "5"))  # 默认最多允许5次空响应

#随机字符串
RANDOM_STRING = os.environ.get("RANDOM_STRING", "true").lower() in ["true", "1", "yes"]
RANDOM_STRING_LENGTH = int(os.environ.get("RANDOM_STRING_LENGTH", "5"))

# 是否启用Vertex AI
ENABLE_VERTEX = os.environ.get("ENABLE_VERTEX", "false").lower() in ["true", "1", "yes"]
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
ENABLE_VERTEX_EXPRESS = os.environ.get("ENABLE_VERTEX_EXPRESS", "false").lower() in ["true", "1", "yes"]
VERTEX_EXPRESS_API_KEY = os.environ.get("VERTEX_EXPRESS_API_KEY", "")
# 日志配置
logging.getLogger("uvicorn").disabled = True
logging.getLogger("uvicorn.access").disabled = True

# 安全配置
PASSWORD = os.environ.get("PASSWORD", "123").strip('"')
WEB_PASSWORD = os.environ.get("WEB_PASSWORD", PASSWORD).strip('"')
MAX_REQUESTS_PER_MINUTE = int(os.environ.get("MAX_REQUESTS_PER_MINUTE", "30"))
MAX_REQUESTS_PER_DAY_PER_IP = int(os.environ.get("MAX_REQUESTS_PER_DAY_PER_IP", "600"))
RETRY_DELAY = 1
MAX_RETRY_DELAY = 16 # 网络错误 5xx 重试时的最大等待时间
MAX_RETRY_NUM = int(os.environ.get("MAX_RETRY_NUM", "15")) # 请求时的最大总轮询 key 数

# 并发请求配置
CONCURRENT_REQUESTS = int(os.environ.get("CONCURRENT_REQUESTS", "1"))  # 默认并发请求数
INCREASE_CONCURRENT_ON_FAILURE = int(os.environ.get("INCREASE_CONCURRENT_ON_FAILURE", "0"))  # 失败时增加的并发数
MAX_CONCURRENT_REQUESTS = int(os.environ.get("MAX_CONCURRENT_REQUESTS", "3"))  # 最大并发请求数

# API密钥使用限制
# 默认每个API密钥每24小时可使用次数
API_KEY_DAILY_LIMIT = int(os.environ.get("API_KEY_DAILY_LIMIT", "100"))

# 缓存配置
CACHE_EXPIRY_TIME = int(os.environ.get("CACHE_EXPIRY_TIME", "21600"))  # 默认缓存 6 小时 (21600 秒)
MAX_CACHE_ENTRIES = int(os.environ.get("MAX_CACHE_ENTRIES", "500"))  # 默认最多缓存500条响应
PRECISE_CACHE = os.environ.get("PRECISE_CACHE", "false").lower() in ["true", "1", "yes"] #是否取所有消息来算缓存键
CALCULATE_CACHE_ENTRIES = int(os.environ.get("CALCULATE_CACHE_ENTRIES", "6"))  # 默认取最后 6 条消息算缓存键

search={
    "search_mode":os.environ.get("SEARCH_MODE", "false").lower() in ["true", "1", "yes"],
    "search_prompt":os.environ.get("SEARCH_PROMPT", "（使用搜索工具联网搜索，需要在content中结合搜索内容）").strip('"')
}

version={
    "local_version":"0.0.0",
    "remote_version":"0.0.0",
    "has_update":False
}

# API调用统计
# 这个对象保留为空结构以保持向后兼容性
# 实际统计数据已迁移到 app/utils/stats.py 中的 ApiStatsManager 类
api_call_stats = {
    'calls': []  # 兼容旧版代码结构
}

# 用于保护 api_call_stats 并发访问的锁
stats_lock = asyncio.Lock() 

# 模型屏蔽列表配置
# 默认屏蔽的模型列表
DEFAULT_BLOCKED_MODELS = []

# 从环境变量中读取屏蔽模型列表，如果未设置则使用默认列表
# 环境变量格式应为逗号分隔的模型名称字符串
BLOCKED_MODELS = os.environ.get("BLOCKED_MODELS", ",".join(DEFAULT_BLOCKED_MODELS))
# 将字符串转换为列表
BLOCKED_MODELS = { model.strip() for model in BLOCKED_MODELS.split(",") if model.strip() }
#公益站模式
PUBLIC_MODE = os.environ.get("PUBLIC_MODE", "false").lower() in ["true", "1", "yes"]
#前端地址
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "")
# 白名单模式
WHITELIST_MODELS = { x.strip() for x in os.environ.get("WHITELIST_MODELS", "").split(",") if x.strip() }
# 白名单User-Agent
WHITELIST_USER_AGENT = { x.strip().lower() for x in os.environ.get("WHITELIST_USER_AGENT", "").split(",") if x.strip() }

# 跨域配置
# 允许的源列表，逗号分隔，例如 "http://localhost:3000,https://example.com"
ALLOWED_ORIGINS_STR = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]