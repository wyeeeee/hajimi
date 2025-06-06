import json
import os
import inspect
import pathlib
from app.config import settings
from app.utils.logging import log

# 定义不应该被保存或加载的配置项
EXCLUDED_SETTINGS = [
    "STORAGE_DIR", 
    "ENABLE_STORAGE", 
    "BASE_DIR", 
    "PASSWORD", 
    "WEB_PASSWORD", 
    "WHITELIST_MODELS", 
    "BLOCKED_MODELS", 
    "DEFAULT_BLOCKED_MODELS", 
    "PUBLIC_MODE", 
    "DASHBOARD_URL",
    "version"
]

def save_settings():
    """
    将settings中所有的从os.environ.get获取的配置保存到JSON文件中，
    但排除特定的配置项
    """
    if settings.ENABLE_STORAGE:
        # 确保存储目录存在
        storage_dir = pathlib.Path(settings.STORAGE_DIR)
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置JSON文件路径
        settings_file = storage_dir / "settings.json"
        
        # 获取settings模块中的所有变量
        settings_dict = {}
        for name, value in inspect.getmembers(settings):
            # 跳过内置和私有变量，以及函数/模块/类，以及排除列表中的配置项
            if (not name.startswith('_') and 
                not inspect.isfunction(value) and 
                not inspect.ismodule(value) and 
                not inspect.isclass(value) and
                name not in EXCLUDED_SETTINGS):
                
                # 尝试将可序列化的值添加到字典中
                try:
                    json.dumps({name: value})  # 测试是否可序列化
                    settings_dict[name] = value
                except (TypeError, OverflowError):
                    # 如果不可序列化，则跳过
                    continue
        log('info', f"保存设置到JSON文件: {settings_file}")
        
        # 保存到JSON文件
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=4)
        
        return settings_file

def load_settings():
    """
    从JSON文件中加载设置并更新settings模块，
    排除特定的配置项，并合并GEMINI_API_KEYS
    """
    if settings.ENABLE_STORAGE:
        # 设置JSON文件路径
        storage_dir = pathlib.Path(settings.STORAGE_DIR)
        settings_file = storage_dir / "settings.json"
        
        # 如果文件不存在，则返回
        if not settings_file.exists():
            return False
        
        # 从JSON文件中加载设置
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
            
            # 保存当前环境变量中的GEMINI_API_KEYS
            current_api_keys = []
            if hasattr(settings, 'GEMINI_API_KEYS') and settings.GEMINI_API_KEYS:
                current_api_keys = settings.GEMINI_API_KEYS.split(',')
                current_api_keys = [key.strip() for key in current_api_keys if key.strip()]
            
            # 保存当前环境变量中的GOOGLE_CREDENTIALS_JSON和VERTEX_EXPRESS_API_KEY
            current_google_credentials_json = settings.GOOGLE_CREDENTIALS_JSON if hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') else ""
            current_vertex_express_api_key = settings.VERTEX_EXPRESS_API_KEY if hasattr(settings, 'VERTEX_EXPRESS_API_KEY') else ""
            
            # 更新settings模块中的变量，但排除特定配置项
            for name, value in loaded_settings.items():
                if hasattr(settings, name) and name not in EXCLUDED_SETTINGS:
                    # 特殊处理GEMINI_API_KEYS，进行合并去重
                    if name == "GEMINI_API_KEYS":
                        loaded_api_keys = value.split(',') if value else []
                        loaded_api_keys = [key.strip() for key in loaded_api_keys if key.strip()]
                        all_keys = list(set(current_api_keys + loaded_api_keys))
                        setattr(settings, name, ','.join(all_keys))
                    # 特殊处理GOOGLE_CREDENTIALS_JSON，如果当前环境变量中有值，则优先使用环境变量中的值
                    elif name == "GOOGLE_CREDENTIALS_JSON":
                        # 检查当前值是否为空（None、空字符串、只有空白字符，或者是"''"这样的空引号）
                        is_empty = (not current_google_credentials_json or 
                                   not current_google_credentials_json.strip() or 
                                   current_google_credentials_json.strip() in ['""', "''"])
                        log('debug', f"is_empty检查结果: {is_empty}")
                        if is_empty:
                            log('debug', f"当前GOOGLE_CREDENTIALS_JSON为空，将使用持久化的值")
                            setattr(settings, name, value)
                            # 更新环境变量，确保其他模块能够访问到
                            if value:  # 只有当value不为空时才设置环境变量
                                os.environ["GOOGLE_CREDENTIALS_JSON"] = value
                                log('info', f"从持久化存储加载了GOOGLE_CREDENTIALS_JSON配置")
                            else:
                                log('warning', f"持久化的GOOGLE_CREDENTIALS_JSON值为空")
                        else:
                            log('debug', f"当前GOOGLE_CREDENTIALS_JSON不为空，保持现有值")
                    # 特殊处理VERTEX_EXPRESS_API_KEY，如果当前环境变量中有值，则优先使用环境变量中的值
                    elif name == "VERTEX_EXPRESS_API_KEY":
                        # 检查当前值是否为空（None、空字符串或只有空白字符）
                        if not current_vertex_express_api_key or not current_vertex_express_api_key.strip():
                            setattr(settings, name, value)
                            # 更新环境变量，确保其他模块能够访问到
                            if value:  # 只有当value不为空时才设置环境变量
                                os.environ["VERTEX_EXPRESS_API_KEY"] = value
                                log('info', f"从持久化存储加载了VERTEX_EXPRESS_API_KEY配置")
                    else:
                        setattr(settings, name, value)
            
            # 在加载完设置后，检查是否需要刷新模型配置
            try:
                # 如果加载了Google Credentials JSON或Vertex Express API Key，需要刷新模型配置
                if (hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') and settings.GOOGLE_CREDENTIALS_JSON) or \
                   (hasattr(settings, 'VERTEX_EXPRESS_API_KEY') and settings.VERTEX_EXPRESS_API_KEY):
                    log('info', "检测到Google Credentials JSON或Vertex Express API Key，准备更新配置")
                    
                    # 更新配置
                    import app.vertex.config as app_config
                    
                    # 重新加载vertex配置
                    app_config.reload_config()
                    
                    # 更新app_config中的GOOGLE_CREDENTIALS_JSON
                    if hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') and settings.GOOGLE_CREDENTIALS_JSON:
                        app_config.GOOGLE_CREDENTIALS_JSON = settings.GOOGLE_CREDENTIALS_JSON
                        # 同时更新环境变量，确保其他模块能够访问到
                        os.environ["GOOGLE_CREDENTIALS_JSON"] = settings.GOOGLE_CREDENTIALS_JSON
                        log('info', "已更新app_config和环境变量中的GOOGLE_CREDENTIALS_JSON")
                    
                    # 更新app_config中的VERTEX_EXPRESS_API_KEY_VAL
                    if hasattr(settings, 'VERTEX_EXPRESS_API_KEY') and settings.VERTEX_EXPRESS_API_KEY:
                        app_config.VERTEX_EXPRESS_API_KEY_VAL = [key.strip() for key in settings.VERTEX_EXPRESS_API_KEY.split(',') if key.strip()]
                        # 同时更新环境变量
                        os.environ["VERTEX_EXPRESS_API_KEY"] = settings.VERTEX_EXPRESS_API_KEY
                        log('info', f"已更新app_config和环境变量中的VERTEX_EXPRESS_API_KEY_VAL，共{len(app_config.VERTEX_EXPRESS_API_KEY_VAL)}个有效密钥")
                    
                    log('info', "配置更新完成，Vertex AI将在下次请求时重新初始化")
                    
            except Exception as e:
                log('error', f"更新配置时出错: {str(e)}")
            
            log('info', f"加载设置成功")
            return True
        except Exception as e:
            log('error', f"加载设置时出错: {e}")
            return False 