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
            
            # 更新settings模块中的变量，但排除特定配置项
            for name, value in loaded_settings.items():
                if hasattr(settings, name) and name not in EXCLUDED_SETTINGS:
                    # 特殊处理GEMINI_API_KEYS，进行合并去重
                    if name == "GEMINI_API_KEYS":
                        loaded_api_keys = value.split(',') if value else []
                        loaded_api_keys = [key.strip() for key in loaded_api_keys if key.strip()]
                        all_keys = list(set(current_api_keys + loaded_api_keys))
                        setattr(settings, name, ','.join(all_keys))
                    else:
                        setattr(settings, name, value)
            
            log('info', f"加载设置成功")
            return True
        except Exception as e:
            log('error', f"加载设置时出错: {e}")
            return False 