# Utils package initialization

from app.utils.logging import logger, log_manager, format_log_message,log
from app.utils.api_key import APIKeyManager, test_api_key
from app.utils.error_handling import handle_gemini_error, translate_error, handle_api_error
from app.utils.rate_limiting import protect_from_abuse
from app.utils.cache import ResponseCacheManager, generate_cache_key
from app.utils.request import ActiveRequestsManager
from app.utils.stats import clean_expired_stats, update_api_call_stats
from app.utils.version import check_version
from app.utils.maintenance import handle_exception, schedule_cache_cleanup
from app.utils.response import openAI_from_text