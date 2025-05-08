import asyncio
from fastapi import HTTPException, Request
from app.models import ChatCompletionRequest
from app.services import GeminiClient
from app.utils import update_api_call_stats
from app.utils.error_handling import handle_gemini_error
from app.utils.logging import log
import app.config.settings as settings
import random
from typing import Literal
from app.utils.response import openAI_from_Gemini, openAI_from_text
from app.utils.stats import get_api_key_usage, api_stats_manager


# 非流式请求处理函数
async def process_nonstream_request(
    chat_request: ChatCompletionRequest,
    contents,
    system_instruction,
    current_api_key: str,
    response_cache_manager,
    safety_settings,
    safety_settings_g2,
    cache_key: str
):
    """处理非流式API请求"""
    gemini_client = GeminiClient(current_api_key)
    # 创建调用 Gemini API 的主任务
    gemini_task = asyncio.create_task(
        gemini_client.complete_chat(
            chat_request,
            contents,
            safety_settings_g2 if 'gemini-2.5' in chat_request.model else safety_settings,
            system_instruction
        )
    )
    # 使用 shield 保护任务不被外部轻易取消
    shielded_gemini_task = asyncio.shield(gemini_task)

    try:
        # 等待受保护的 API 调用任务完成
        response_content = await shielded_gemini_task
        response_content.set_model(chat_request.model)
        
        # 检查响应内容是否为空
        if not response_content or not response_content.text:
            log('warning', f"API密钥 {current_api_key[:8]}... 返回空响应",
                extra={'key': current_api_key[:8], 'request_type': 'non-stream', 'model': chat_request.model})
            return "empty"
        
        # 缓存响应结果
        await response_cache_manager.store(cache_key, response_content)
        
        # 更新 API 调用统计（只使用新版本）
        try:
            tokens = response_content.total_token_count or 0
            await api_stats_manager.update_stats(current_api_key, chat_request.model, tokens)
        except Exception as stats_error:
            log('error', f"更新API调用统计失败: {str(stats_error)}",
                extra={'key': current_api_key[:8], 'model': chat_request.model})
        
        return "success"

    except Exception as e:
        # 处理 API 调用过程中可能发生的任何异常
        handle_gemini_error(e, current_api_key) 
        return "error" 
    
    
# 处理 route 中发起请求的函数
async def process_request(
    chat_request: ChatCompletionRequest,
    key_manager,
    response_cache_manager,
    safety_settings,
    safety_settings_g2,
    cache_key: str
):
    """处理非流式请求"""
    global current_api_key

    # 转换消息格式
    contents, system_instruction = GeminiClient.convert_messages(
        GeminiClient, chat_request.messages,model=chat_request.model)

    # --- 在开始处理前检查缓存 ---
    cached_response, cache_hit = await response_cache_manager.get_and_remove(cache_key)
    if cache_hit:
        log('info', f"请求命中缓存 : {cache_key[:8]}...，直接返回缓存结果。",
            extra={'request_type': 'non-stream', 'model': chat_request.model, 'cache_operation': 'hit_and_remove'})
        return openAI_from_Gemini(cached_response,stream=False)

    # 设置初始并发数
    current_concurrent = settings.CONCURRENT_REQUESTS
    max_retry_num = settings.MAX_RETRY_NUM
    
    # 获取有效的API密钥
    valid_keys = []
    for _ in range(len(key_manager.api_keys)):
        api_key = await key_manager.get_available_key()
        if api_key:
            # 获取API密钥的调用次数
            usage = await get_api_key_usage(settings.api_call_stats, api_key)
            # 如果调用次数小于限制，则添加到有效密钥列表
            if usage < settings.API_KEY_DAILY_LIMIT:
                valid_keys.append(api_key)
            else:
                log('warning', f"API密钥 {api_key[:8]}... 已达到每日调用限制 ({usage}/{settings.API_KEY_DAILY_LIMIT})",
                    extra={'key': api_key[:8], 'request_type': 'non-stream', 'model': chat_request.model})
    
    # 如果没有有效密钥，则随机使用一个密钥
    if not valid_keys:
        log('warning', "所有API密钥已达到每日调用限制，将随机使用一个密钥",
            extra={'request_type': 'non-stream', 'model': chat_request.model})
        # 重置密钥栈并获取一个密钥
        key_manager._reset_key_stack()
        get_key = await key_manager.get_available_key()
        valid_keys = [get_key] if get_key else []
    
    # 如果可用密钥数量小于并发数，则使用所有可用密钥
    if len(valid_keys) < current_concurrent:
        current_concurrent = len(valid_keys)

    # 当前请求次数
    current_try_num = 0
    
    # 空响应计数
    empty_response_count = 0
    
    # 尝试使用不同API密钥，直到所有密钥都尝试过
    while valid_keys and (current_try_num < max_retry_num) and (empty_response_count < settings.MAX_EMPTY_RESPONSES):
        # 获取当前批次的密钥
        batch_num = min(max_retry_num - current_try_num, current_concurrent)
        
        current_batch = valid_keys[:batch_num]
        valid_keys = valid_keys[batch_num:]
        
        # 更新当前尝试次数
        current_try_num += batch_num
        
        # 创建并发任务
        tasks = []
        tasks_map = {}
        for api_key in current_batch:
            # 记录当前尝试的密钥信息
            log('info', f"非流式请求开始，使用密钥: {api_key[:8]}...", 
                extra={'key': api_key[:8], 'request_type': 'non-stream', 'model': chat_request.model})
            
            # 创建任务
            task = asyncio.create_task(
                process_nonstream_request(
                    chat_request,
                    contents,
                    system_instruction,
                    api_key,
                    response_cache_manager,
                    safety_settings,
                    safety_settings_g2,
                    cache_key
                )
            )
            tasks.append((api_key, task))
            tasks_map[task] = api_key
        
        # 等待所有任务完成或找到成功响应
        success = False
        while tasks and not success:
            # 短时间等待任务完成
            done, pending = await asyncio.wait(
                [task for _, task in tasks],
                return_when=asyncio.FIRST_COMPLETED
            )
            # 检查已完成的任务是否成功
            for task in done:
                api_key = tasks_map[task]
                try:
                    status = task.result()                    
                    # 如果有成功响应内容
                    if status == "success" :  
                        success = True
                        log('info', f"非流式请求成功", 
                            extra={'key': api_key[:8],'request_type': 'non-stream', 'model': chat_request.model})
                        cached_response, cache_hit = await  response_cache_manager.get_and_remove(cache_key)
                        return openAI_from_Gemini(cached_response,stream=False)
                    elif status == "empty":
                        # 增加空响应计数
                        empty_response_count += 1
                        log('warning', f"空响应计数: {empty_response_count}/{settings.MAX_EMPTY_RESPONSES}",
                            extra={'key': api_key[:8], 'request_type': 'non-stream', 'model': chat_request.model})
                
                except Exception as e:
                    handle_gemini_error(e, api_key)
                
                # 更新任务列表，移除已完成的任务
                tasks = [(k, t) for k, t in tasks if not t.done()]
                
        # 如果当前批次没有成功响应，并且还有密钥可用，则继续尝试
        if not success and valid_keys:
            # 增加并发数，但不超过最大并发数
            current_concurrent = min(current_concurrent + settings.INCREASE_CONCURRENT_ON_FAILURE, settings.MAX_CONCURRENT_REQUESTS)
            log('info', f"所有并发请求失败或返回空响应，增加并发数至: {current_concurrent}", 
                extra={'request_type': 'non-stream', 'model': chat_request.model})
        
        # 如果空响应次数达到限制，跳出循环，并返回酒馆正常响应(包含错误信息)
        if empty_response_count >= settings.MAX_EMPTY_RESPONSES:
            log('warning', f"空响应次数达到限制 ({empty_response_count}/{settings.MAX_EMPTY_RESPONSES})，停止轮询",
                extra={'request_type': 'non-stream', 'model': chat_request.model})
            
            return openAI_from_text(model=chat_request.model,content="空响应次数达到上限\n请修改输入提示词或开启防截断",finish_reason="stop",stream=False)
    
    # 如果所有尝试都失败
    log('error', "API key 替换失败，所有API key都已尝试，请重新配置或稍后重试", extra={'request_type': 'switch_key'})
    
    return openAI_from_text(model=chat_request.model,content="所有 API 密钥均请求失败\n具体错误请查看轮询日志",finish_reason="stop",stream=False)

    # raise HTTPException(status_code=500, detail=f"API key 替换失败，所有API key都已尝试，请重新配置或稍后重试")
