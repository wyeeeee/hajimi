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
            current_api_keys = settings.GEMINI_API_KEYS.split(',') if settings.GEMINI_API_KEYS else []
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
                        if not current_google_credentials_json:  # 只有当环境变量中没有值时才使用持久化的值
                            setattr(settings, name, value)
                            # 更新环境变量，确保其他模块能够访问到
                            os.environ["GOOGLE_CREDENTIALS_JSON"] = value
                    # 特殊处理VERTEX_EXPRESS_API_KEY，如果当前环境变量中有值，则优先使用环境变量中的值
                    elif name == "VERTEX_EXPRESS_API_KEY":
                        if not current_vertex_express_api_key:  # 只有当环境变量中没有值时才使用持久化的值
                            setattr(settings, name, value)
                            # 更新环境变量，确保其他模块能够访问到
                            os.environ["VERTEX_EXPRESS_API_KEY"] = value
                    else:
                        setattr(settings, name, value)
            
            # 在加载完设置后，检查是否需要刷新模型配置
            try:
                # 如果加载了Google Credentials JSON或Vertex Express API Key，需要刷新模型配置
                if (hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') and settings.GOOGLE_CREDENTIALS_JSON) or \
                   (hasattr(settings, 'VERTEX_EXPRESS_API_KEY') and settings.VERTEX_EXPRESS_API_KEY):
                    log('info', "检测到Google Credentials JSON或Vertex Express API Key，准备刷新模型配置")
                    
                    # 导入必要的模块
                    from app.vertex.model_loader import refresh_models_config_cache
                    from app.vertex.vertex_ai_init import init_vertex_ai
                    from app.vertex.credentials_manager import CredentialManager
                    
                    # 创建新的CredentialManager实例
                    credential_manager = CredentialManager()
                    
                    # 如果有Google Credentials JSON，加载到CredentialManager
                    if hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') and settings.GOOGLE_CREDENTIALS_JSON:
                        from app.vertex.credentials_manager import parse_multiple_json_credentials
                        parsed_json_objects = parse_multiple_json_credentials(settings.GOOGLE_CREDENTIALS_JSON)
                        if parsed_json_objects:
                            loaded_count = credential_manager.load_credentials_from_json_list(parsed_json_objects)
                            log('info', f"从持久化的Google Credentials JSON中加载了{loaded_count}个凭据")
                    
                    # 初始化Vertex AI
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # 确保app.vertex.config中的值已更新
                        import app.vertex.config as app_config
                        # 更新app_config中的GOOGLE_CREDENTIALS_JSON
                        if hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') and settings.GOOGLE_CREDENTIALS_JSON:
                            app_config.GOOGLE_CREDENTIALS_JSON = settings.GOOGLE_CREDENTIALS_JSON
                            log('info', "已更新app_config中的GOOGLE_CREDENTIALS_JSON")
                        
                        # 更新app_config中的VERTEX_EXPRESS_API_KEY_VAL
                        if hasattr(settings, 'VERTEX_EXPRESS_API_KEY') and settings.VERTEX_EXPRESS_API_KEY:
                            app_config.VERTEX_EXPRESS_API_KEY_VAL = [key.strip() for key in settings.VERTEX_EXPRESS_API_KEY.split(',') if key.strip()]
                            log('info', f"已更新app_config中的VERTEX_EXPRESS_API_KEY_VAL，共{len(app_config.VERTEX_EXPRESS_API_KEY_VAL)}个有效密钥")
                        
                        success = loop.run_until_complete(init_vertex_ai(credential_manager=credential_manager))
                        if success:
                            log('info', "成功初始化Vertex AI服务")
                        else:
                            log('warning', "初始化Vertex AI服务失败")
                    finally:
                        loop.close()
                    
                    # 刷新模型配置缓存
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        refresh_success = loop.run_until_complete(refresh_models_config_cache())
                        if refresh_success:
                            log('info', "成功刷新模型配置缓存")
                        else:
                            log('warning', "刷新模型配置缓存失败")
                    finally:
                        loop.close()
            except Exception as e:
                log('error', f"刷新模型配置时出错: {str(e)}")
            
            log('info', f"加载设置成功")
            return True
        except Exception as e:
            log('error', f"加载设置时出错: {e}")
            return False 