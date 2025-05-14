from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
import time
import asyncio
import random
import threading
from app.utils import (
    log_manager,
    ResponseCacheManager,
    ActiveRequestsManager,
    clean_expired_stats
)
import app.config.settings as settings
from app.services import GeminiClient
from app.utils.auth import verify_web_password
from app.utils.maintenance import api_call_stats_clean
from app.utils.logging import log, vertex_log_manager
from app.config.persistence import save_settings
from app.utils.stats import api_stats_manager
# 创建路由器
dashboard_router = APIRouter(prefix="/api", tags=["dashboard"])

# 全局变量引用，将在init_dashboard_router中设置
key_manager = None
response_cache_manager = None
active_requests_manager = None

# 用于存储API密钥检测的进度信息
api_key_test_progress = {
    "is_running": False,
    "completed": 0,
    "total": 0,
    "valid": 0,
    "invalid": 0,
    "is_completed": False
}

def init_dashboard_router(
    key_mgr,
    cache_mgr,
    active_req_mgr
):
    """初始化仪表盘路由器"""
    global key_manager, response_cache_manager, active_requests_manager
    key_manager = key_mgr
    response_cache_manager = cache_mgr
    active_requests_manager = active_req_mgr
    return dashboard_router

@dashboard_router.get("/dashboard-data")
async def get_dashboard_data():
    """获取仪表盘数据的API端点，用于动态刷新"""
    # 先清理过期数据，确保统计数据是最新的
    await api_stats_manager.maybe_cleanup()
    await response_cache_manager.clean_expired()  # 使用管理器清理缓存
    active_requests_manager.clean_completed()  # 使用管理器清理活跃请求
    
    # 获取当前统计数据
    now = datetime.now()
    
    # 使用新的统计系统获取调用数据
    last_24h_calls = api_stats_manager.get_calls_last_24h()
    hourly_calls = api_stats_manager.get_calls_last_hour(now)
    minute_calls = api_stats_manager.get_calls_last_minute(now)
    
    # 获取时间序列数据
    time_series_data, tokens_time_series = api_stats_manager.get_time_series_data(30, now)
    
    # 获取API密钥使用统计
    api_key_stats = api_stats_manager.get_api_key_stats(key_manager.api_keys)
    
    # 根据ENABLE_VERTEX设置决定返回哪种日志
    if settings.ENABLE_VERTEX:
        recent_logs = vertex_log_manager.get_recent_logs(500)  # 获取最近500条Vertex日志
    else:
        recent_logs = log_manager.get_recent_logs(500)  # 获取最近500条普通日志
    
    # 获取缓存统计
    total_cache = response_cache_manager.cur_cache_num
    
    # 获取活跃请求统计
    active_count = len(active_requests_manager.active_requests)
    active_done = sum(1 for task in active_requests_manager.active_requests.values() if task.done())
    active_pending = active_count - active_done
    
    # 返回JSON格式的数据
    return {
        "key_count": len(key_manager.api_keys),
        "model_count": len(GeminiClient.AVAILABLE_MODELS),
        "retry_count": settings.MAX_RETRY_NUM,
        "last_24h_calls": last_24h_calls,
        "hourly_calls": hourly_calls,
        "minute_calls": minute_calls,
        "calls_time_series": time_series_data,      # 添加API调用时间序列
        "tokens_time_series": tokens_time_series,   # 添加Token使用时间序列
        "current_time": datetime.now().strftime('%H:%M:%S'),
        "logs": recent_logs,
        "api_key_stats": api_key_stats,
        # 添加配置信息
        "max_requests_per_minute": settings.MAX_REQUESTS_PER_MINUTE,
        "max_requests_per_day_per_ip": settings.MAX_REQUESTS_PER_DAY_PER_IP,
        # 添加版本信息
        "local_version": settings.version["local_version"],
        "remote_version": settings.version["remote_version"],
        "has_update": settings.version["has_update"],
        # 添加流式响应配置
        "fake_streaming": settings.FAKE_STREAMING,
        "fake_streaming_interval": settings.FAKE_STREAMING_INTERVAL,
        # 添加随机字符串配置
        "random_string": settings.RANDOM_STRING,
        "random_string_length": settings.RANDOM_STRING_LENGTH,
        # 添加联网搜索配置
        "search_mode": settings.search["search_mode"],
        "search_prompt": settings.search["search_prompt"],
        # 添加缓存信息
        "cache_entries": total_cache,
        "cache_expiry_time": settings.CACHE_EXPIRY_TIME,
        "max_cache_entries": settings.MAX_CACHE_ENTRIES,
        # 添加活跃请求池信息
        "active_count": active_count,
        "active_done": active_done,
        "active_pending": active_pending,
        # 添加并发请求配置
        "concurrent_requests": settings.CONCURRENT_REQUESTS,
        "increase_concurrent_on_failure": settings.INCREASE_CONCURRENT_ON_FAILURE,
        "max_concurrent_requests": settings.MAX_CONCURRENT_REQUESTS,
        # 启用vertex
        "enable_vertex": settings.ENABLE_VERTEX,
        # 添加Vertex Express配置
        "enable_vertex_express": settings.ENABLE_VERTEX_EXPRESS,
        "vertex_express_api_key": bool(settings.VERTEX_EXPRESS_API_KEY),  # 只返回是否设置的状态
        "google_credentials_json": bool(settings.GOOGLE_CREDENTIALS_JSON),  # 只返回是否设置的状态
        # 添加最大重试次数
        "max_retry_num": settings.MAX_RETRY_NUM,
        # 添加空响应重试次数限制
        "max_empty_responses": settings.MAX_EMPTY_RESPONSES,
    }

@dashboard_router.post("/reset-stats")
async def reset_stats(password_data: dict):
    """
    重置API调用统计数据
    
    Args:
        password_data (dict): 包含密码的字典
        
    Returns:
        dict: 操作结果
    """
    try:
        if not isinstance(password_data, dict):
            raise HTTPException(status_code=422, detail="请求体格式错误：应为JSON对象")
            
        password = password_data.get("password")
        if not password:
            raise HTTPException(status_code=400, detail="缺少密码参数")
            
        if not isinstance(password, str):
            raise HTTPException(status_code=422, detail="密码参数类型错误：应为字符串")
            
        if not verify_web_password(password):
            raise HTTPException(status_code=401, detail="密码错误")
        
        # 调用重置函数
        await api_stats_manager.reset()
        
        return {"status": "success", "message": "API调用统计数据已重置"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败：{str(e)}")

@dashboard_router.post("/update-config")
async def update_config(config_data: dict):
    """
    更新配置项
    
    Args:
        config_data (dict): 包含配置项和密码的字典
        
    Returns:
        dict: 操作结果
    """
    try:
        if not isinstance(config_data, dict):
            raise HTTPException(status_code=422, detail="请求体格式错误：应为JSON对象")
            
        password = config_data.get("password")
        if not password:
            raise HTTPException(status_code=400, detail="缺少密码参数")
            
        if not isinstance(password, str):
            raise HTTPException(status_code=422, detail="密码参数类型错误：应为字符串")
            
        if not verify_web_password(password):
            raise HTTPException(status_code=401, detail="密码错误")
        
        # 获取要更新的配置项
        config_key = config_data.get("key")
        config_value = config_data.get("value")
        
        if not config_key:
            raise HTTPException(status_code=400, detail="缺少配置项键名")
            
        # 根据配置项类型进行类型转换和验证
        if config_key == "max_requests_per_minute":
            try:
                value = int(config_value)
                if value <= 0:
                    raise ValueError("每分钟请求限制必须大于0")
                settings.MAX_REQUESTS_PER_MINUTE = value
                log('info', f"每分钟请求限制已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "max_requests_per_day_per_ip":
            try:
                value = int(config_value)
                if value <= 0:
                    raise ValueError("每IP每日请求限制必须大于0")
                settings.MAX_REQUESTS_PER_DAY_PER_IP = value
                log('info', f"每IP每日请求限制已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "fake_streaming":
            if not isinstance(config_value, bool):
                raise HTTPException(status_code=422, detail="参数类型错误：应为布尔值")
            settings.FAKE_STREAMING = config_value
            log('info', f"假流式请求已更新为：{config_value}")
            
        elif config_key == "enable_vertex_express":
            if not isinstance(config_value, bool):
                raise HTTPException(status_code=422, detail="参数类型错误：应为布尔值")
            settings.ENABLE_VERTEX_EXPRESS = config_value
            log('info', f"Vertex Express已更新为：{config_value}")
            
        elif config_key == "vertex_express_api_key":
            if not isinstance(config_value, str):
                raise HTTPException(status_code=422, detail="参数类型错误：应为字符串")
            settings.VERTEX_EXPRESS_API_KEY = config_value
            log('info', f"Vertex Express API Key已更新")
            
        elif config_key == "fake_streaming_interval":
            try:
                value = float(config_value)
                if value <= 0:
                    raise ValueError("假流式间隔必须大于0")
                settings.FAKE_STREAMING_INTERVAL = value
                log('info', f"假流式间隔已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "random_string":
            if not isinstance(config_value, bool):
                raise HTTPException(status_code=422, detail="参数类型错误：应为布尔值")
            settings.RANDOM_STRING = config_value
            log('info', f"随机字符串已更新为：{config_value}")
        elif config_key == "random_string_length":
            try:
                value = int(config_value)
                if value <= 0:
                    raise ValueError("随机字符串长度必须大于0")
                settings.RANDOM_STRING_LENGTH = value
                log('info', f"随机字符串长度已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "search_mode":
            if not isinstance(config_value, bool):
                raise HTTPException(status_code=422, detail="参数类型错误：应为布尔值")
            settings.search["search_mode"] = config_value
            log('info', f"联网搜索模式已更新为：{config_value}")
            
            # 在切换search_mode时，重新获取一次可用模型列表
            try:
                # 重置密钥栈以确保随机性
                key_manager._reset_key_stack()
                # 获取一个随机API密钥
                for key in key_manager.api_keys:
                    log('info', f"使用API密钥 {key[:8]}... 刷新可用模型列表")
                    # 使用随机密钥获取可用模型
                    all_models = await GeminiClient.list_available_models(key)
                    GeminiClient.AVAILABLE_MODELS = [model.replace("models/", "") for model in all_models]
                    if len(GeminiClient.AVAILABLE_MODELS) > 0:
                        log('info', f"可用模型列表已更新，当前模型数量：{len(GeminiClient.AVAILABLE_MODELS)}")
                        break
                else:
                    log('warning', f"没有可用的API密钥，无法刷新可用模型列表")
            except Exception as e:
                log('warning', f"刷新可用模型列表时发生错误: {str(e)}")
                
        elif config_key == "concurrent_requests":
            try:
                value = int(config_value)
                if value <= 0:
                    raise ValueError("并发请求数必须大于0")
                settings.CONCURRENT_REQUESTS = value
                log('info', f"并发请求数已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "increase_concurrent_on_failure":
            try:
                value = int(config_value)
                if value < 0:
                    raise ValueError("失败时增加的并发数不能为负数")
                settings.INCREASE_CONCURRENT_ON_FAILURE = value
                log('info', f"失败时增加的并发数已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "max_concurrent_requests":
            try:
                value = int(config_value)
                if value <= 0:
                    raise ValueError("最大并发请求数必须大于0")
                settings.MAX_CONCURRENT_REQUESTS = value
                log('info', f"最大并发请求数已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "enable_vertex":
            if not isinstance(config_value, bool):
                raise HTTPException(status_code=422, detail="参数类型错误：应为布尔值")
            settings.ENABLE_VERTEX = config_value
            log('info', f"Vertex AI 已更新为：{config_value}")
        
        elif config_key == "max_retry_num":
            try:
                value = int(config_value)
                if value <= 0:
                    raise ValueError("最大重试次数必须大于0")
                settings.MAX_RETRY_NUM = value
                log('info', f"最大重试次数已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
                
        elif config_key == "search_prompt":
            if not isinstance(config_value, str):
                raise HTTPException(status_code=422, detail="参数类型错误：应为字符串")
            settings.search["search_prompt"] = config_value
            log('info', f"联网搜索提示已更新为：{config_value}")
        
        elif config_key == "gemini_api_keys":
            if not isinstance(config_value, str):
                raise HTTPException(status_code=422, detail="参数类型错误：API密钥应为逗号分隔的字符串")
            
            # 分割并清理API密钥
            new_keys = [key.strip() for key in config_value.split(',') if key.strip()]
            if not new_keys:
                raise HTTPException(status_code=400, detail="未提供有效的API密钥")
            
            # 添加到现有的API密钥字符串中
            current_keys = settings.GEMINI_API_KEYS.split(',') if settings.GEMINI_API_KEYS else []
            current_keys = [key.strip() for key in current_keys if key.strip()]
            
            # 合并新旧密钥并去重
            all_keys = list(set(current_keys + new_keys))
            settings.GEMINI_API_KEYS = ','.join(all_keys)
            
            # 计算新添加的密钥数量
            added_key_count = 0
            for key in new_keys:
                if key not in key_manager.api_keys:
                    key_manager.api_keys.append(key)
                    added_key_count += 1
            
            # 重置密钥栈
            key_manager._reset_key_stack()
            
            # 如果可用模型为空，尝试获取模型列表
            if not GeminiClient.AVAILABLE_MODELS:
                try:
                    # 使用新添加的密钥之一尝试获取可用模型
                    for key in new_keys:
                        log('info', f"使用新添加的API密钥 {key[:8]}... 获取可用模型列表")
                        all_models = await GeminiClient.list_available_models(key)
                        GeminiClient.AVAILABLE_MODELS = [model.replace("models/", "") for model in all_models]
                        if GeminiClient.AVAILABLE_MODELS:
                            log('info', f"成功获取可用模型列表，共 {len(GeminiClient.AVAILABLE_MODELS)} 个模型")
                            break
                except Exception as e:
                    log('warning', f"获取可用模型列表时发生错误: {str(e)}")
            
            log('info', f"已添加 {added_key_count} 个新API密钥，当前共有 {len(key_manager.api_keys)} 个")
                
        elif config_key == "max_empty_responses":
            try:
                value = int(config_value)
                if value < 0: # 通常至少为0或1，根据实际需求调整
                    raise ValueError("空响应重试次数不能为负数")
                settings.MAX_EMPTY_RESPONSES = value
                log('info', f"空响应重试次数已更新为：{value}")
            except ValueError as e:
                raise HTTPException(status_code=422, detail=f"参数类型错误：{str(e)}")
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的配置项：{config_key}")
        save_settings()
        return {"status": "success", "message": f"配置项 {config_key} 已更新"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")

@dashboard_router.post("/test-api-keys")
async def test_api_keys(password_data: dict):
    """
    测试所有API密钥的有效性
    
    Args:
        password_data (dict): 包含密码的字典
        
    Returns:
        dict: 操作结果
    """
    try:
        if not isinstance(password_data, dict):
            raise HTTPException(status_code=422, detail="请求体格式错误：应为JSON对象")
            
        password = password_data.get("password")
        if not password:
            raise HTTPException(status_code=400, detail="缺少密码参数")
            
        if not isinstance(password, str):
            raise HTTPException(status_code=422, detail="密码参数类型错误：应为字符串")
            
        if not verify_web_password(password):
            raise HTTPException(status_code=401, detail="密码错误")
        
        # 检查是否已经有测试在运行
        if api_key_test_progress["is_running"]:
            raise HTTPException(status_code=409, detail="已有API密钥检测正在进行中")
        
        # 获取有效密钥列表
        valid_keys = key_manager.api_keys.copy()
        
        # 启动异步测试
        threading.Thread(
            target=start_api_key_test_in_thread, 
            args=(valid_keys,), 
            daemon=True
        ).start()
        
        return {"status": "success", "message": "API密钥检测已启动，将同时检测有效密钥和无效密钥"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动API密钥检测失败：{str(e)}")

@dashboard_router.get("/test-api-keys/progress")
async def get_test_api_keys_progress():
    """
    获取API密钥检测进度
    
    Returns:
        dict: 进度信息
    """
    return api_key_test_progress

def check_api_key_in_thread(key):
    """在线程中检查单个API密钥的有效性"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        is_valid = loop.run_until_complete(test_api_key(key))
        if is_valid:
            log('info', f"API密钥 {key[:8]}... 有效")
            return key, True
        else:
            log('warning', f"API密钥 {key[:8]}... 无效")
            return key, False
    finally:
        loop.close()

async def test_api_key(key):
    """测试单个API密钥是否有效"""
    try:
        # 尝试列出可用模型来检查API密钥是否有效
        all_models = await GeminiClient.list_available_models(key)
        return len(all_models) > 0
    except Exception as e:
        log('error', f"测试API密钥 {key[:8]}... 时出错: {str(e)}")
        return False

def start_api_key_test_in_thread(keys):
    """在线程中启动API密钥检测过程"""
    # 重置进度信息
    api_key_test_progress.update({
        "is_running": True,
        "completed": 0,
        "total": 0,  # 稍后会更新
        "valid": 0,
        "invalid": 0,
        "is_completed": False
    })
    
    try:
        # 获取所有需要检测的密钥（包括当前GEMINI_API_KEYS和INVALID_API_KEYS）
        current_keys = keys
        
        # 获取当前无效密钥
        invalid_api_keys = settings.INVALID_API_KEYS.split(',') if settings.INVALID_API_KEYS else []
        invalid_api_keys = [key.strip() for key in invalid_api_keys if key.strip()]
        
        # 合并所有需要测试的密钥，去重
        all_keys_to_test = list(set(current_keys + invalid_api_keys))
        
        # 更新总数
        api_key_test_progress["total"] = len(all_keys_to_test)
        
        # 创建有效和无效密钥列表
        valid_keys = []
        invalid_keys = []
        
        # 检查每个密钥
        for key in all_keys_to_test:
            # 检查密钥
            _, is_valid = check_api_key_in_thread(key)
            
            # 更新进度
            api_key_test_progress["completed"] += 1
            
            # 将密钥添加到相应列表
            if is_valid:
                valid_keys.append(key)
                api_key_test_progress["valid"] += 1
            else:
                invalid_keys.append(key)
                api_key_test_progress["invalid"] += 1
        
        # 更新全局密钥列表
        key_manager.api_keys = valid_keys
        
        # 更新设置中的有效和无效密钥
        settings.GEMINI_API_KEYS = ','.join(valid_keys)
        settings.INVALID_API_KEYS = ','.join(invalid_keys)
        
        # 更新最大重试次数
        settings.MAX_RETRY_NUM = len(valid_keys)
        
        # 保存设置
        save_settings()
        
        # 重置密钥栈
        key_manager._reset_key_stack()
        
        log('info', f"API密钥检测完成。有效密钥: {len(valid_keys)}，无效密钥: {len(invalid_keys)}")
    except Exception as e:
        log('error', f"API密钥检测过程中发生错误: {str(e)}")
    finally:
        # 标记检测完成
        api_key_test_progress.update({
            "is_running": False,
            "is_completed": True
        })
