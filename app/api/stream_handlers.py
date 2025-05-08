import asyncio
from fastapi.responses import StreamingResponse
from app.models import ChatCompletionRequest
from app.services import GeminiClient
from app.utils import handle_gemini_error, update_api_call_stats,log,openAI_from_text
from app.utils.response import openAI_from_Gemini
from app.utils.stats import get_api_key_usage, api_stats_manager
import app.config.settings as settings

async def stream_response_generator(
    chat_request: ChatCompletionRequest,
    key_manager,
    response_cache_manager,
    safety_settings,
    safety_settings_g2,
    cache_key: str
):
    # 转换消息格式
    contents, system_instruction = GeminiClient.convert_messages(
    GeminiClient, chat_request.messages,model=chat_request.model)


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
                    extra={'key': api_key[:8], 'request_type': 'stream', 'model': chat_request.model})
    
    # 如果没有有效密钥，则随机使用一个密钥
    if not valid_keys:
        log('warning', "所有API密钥已达到每日调用限制，将随机使用一个密钥",
            extra={'request_type': 'stream', 'model': chat_request.model})
        # 重置密钥栈并获取一个密钥
        key_manager._reset_key_stack() 
        get_key = await key_manager.get_available_key()
        valid_keys = [get_key] if get_key else []

    # 设置初始并发数
    current_concurrent = settings.CONCURRENT_REQUESTS
    max_retry_num =  settings.MAX_RETRY_NUM
    
    
    # 如果可用密钥数量小于并发数，则使用所有可用密钥
    keys_num = len(valid_keys)
    if keys_num < current_concurrent:
        current_concurrent = keys_num
    
    # 当前请求次数
    current_try_num = 0
    
    # 空响应计数
    empty_response_count = 0
    
    # (假流式) 尝试使用不同API密钥，直到所有密钥都尝试过
    while (valid_keys and settings.FAKE_STREAMING and (current_try_num < min(max_retry_num,keys_num)) ):
        
        # 获取当前批次的密钥
        batch_num= min(max_retry_num - current_try_num, current_concurrent)
        
        current_batch = valid_keys[:batch_num]
        valid_keys = valid_keys[batch_num:]
        
        # 更新当前尝试次数
        current_try_num += batch_num
        
        # 创建并发任务
        tasks = []
        tasks_map = {}
        for api_key in current_batch:
            # 假流式模式的处理逻辑
            log('info', f"假流式请求开始，使用密钥: {api_key[:8]}...",
                extra={'key': api_key[:8], 'request_type': 'fake-stream', 'model': chat_request.model})
            
            task = asyncio.create_task(
                handle_fake_streaming(
                    api_key, 
                    chat_request, 
                    contents, 
                    response_cache_manager,
                    system_instruction, 
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
            # 等待任务完成
            done, pending = await asyncio.wait(
                [task for _, task in tasks],
                timeout=settings.FAKE_STREAMING_INTERVAL,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 如果没有任务完成，发送保活消息
            if not done : 
                yield openAI_from_text(model=chat_request.model,content='',stream=True)
                continue
            
            # 检查已完成的任务是否成功
            for task in done:
                api_key = tasks_map[task]
                if not task.cancelled():
                    try:
                        status = task.result()
                        # 如果有成功响应内容
                        if status == "success" :  
                            success = True
                            log('info', f"假流式请求成功", 
                                extra={'key': api_key[:8],'request_type': "fake-stream", 'model': chat_request.model})
                            cached_response, cache_hit = await response_cache_manager.get_and_remove(cache_key)
                            if cache_hit and cached_response: 
                                yield openAI_from_Gemini(cached_response,stream=True)
                            else:
                                success = False
                            break
                        elif status == "empty":
                            # 增加空响应计数
                            empty_response_count += 1
                            log('warning', f"空响应计数: {empty_response_count}/{settings.MAX_EMPTY_RESPONSES}",
                                extra={'key': api_key[:8], 'request_type': 'stream', 'model': chat_request.model})
                        
                    except Exception as e:
                        error_detail = handle_gemini_error(e, api_key)
                        log('error', f"请求失败: {error_detail}",
                            extra={'key': api_key[:8], 'request_type': 'stream', 'model': chat_request.model})

            # 如果找到成功的响应，跳出循环
            if success:
                return
            
            # 如果空响应次数达到限制，跳出循环
            if empty_response_count >= settings.MAX_EMPTY_RESPONSES:
                log('warning', f"空响应次数达到限制 ({empty_response_count}/{settings.MAX_EMPTY_RESPONSES})，停止轮询",
                    extra={'request_type': 'fake-stream', 'model': chat_request.model})
                yield openAI_from_text(model=chat_request.model,content="空响应次数达到上限\n请修改输入提示词",finish_reason="stop",stream=True)
                
                return
            
            # 更新任务列表，移除已完成的任务
            tasks = [(k, t) for k, t in tasks if not t.done()]
        
        # 如果所有请求都失败，增加并发数并继续尝试
        if not success and valid_keys:
            # 增加并发数，但不超过最大并发数
            current_concurrent = min(current_concurrent + settings.INCREASE_CONCURRENT_ON_FAILURE, settings.MAX_CONCURRENT_REQUESTS)
            log('info', f"所有假流式请求失败，增加并发数至: {current_concurrent}", 
                extra={'request_type': 'stream', 'model': chat_request.model})

    # (真流式) 尝试使用不同API密钥，直到所有密钥都尝试过或达到尝试上限
    while (valid_keys and not settings.FAKE_STREAMING and (current_try_num < min(max_retry_num,keys_num)) ):
        # 获取密钥
        api_key = valid_keys[0]
        valid_keys = valid_keys[1:]
        current_try_num += 1
        
        success = False
        try:            
            client = GeminiClient(api_key)
            
            # 获取流式响应
            stream_generator = client.stream_chat(
                chat_request,
                contents,
                safety_settings_g2 if 'gemini-2.5' in chat_request.model else safety_settings,
                system_instruction
            )
            token=0
            # 处理流式响应
            async for chunk in stream_generator:
                if chunk :
                    
                    if chunk.total_token_count:
                        token = int(chunk.total_token_count)
                    success = True
                    data = openAI_from_Gemini(chunk,stream=True)
                    # log('info', f"流式响应发送数据: {data}")
                    yield data
                
                else:
                    log('warning', f"流式请求返回空响应，空响应计数: {empty_response_count}/{settings.MAX_EMPTY_RESPONSES}",
                        extra={'key': api_key[:8], 'request_type': 'stream', 'model': chat_request.model})
                    # 增加空响应计数
                    empty_response_count += 1
                    # 使用新版API统计更新
                    try:
                        await api_stats_manager.update_stats(api_key, chat_request.model, token)
                    except Exception as stats_error:
                        log('error', f"更新API调用统计失败: {str(stats_error)}",
                            extra={'key': api_key[:8], 'model': chat_request.model})
                    break
        
        except Exception as e:
            error_detail = handle_gemini_error(e, api_key)
            log('error', f"流式响应: API密钥 {api_key[:8]}... 请求失败: {error_detail}",
                extra={'key': api_key[:8], 'request_type': 'stream', 'model': chat_request.model})
            return
        finally: 
            # 如果成功获取相应，更新API调用统计
            if success:
                # 只使用新版统计系统
                try:
                    await api_stats_manager.update_stats(api_key, chat_request.model, token)
                except Exception as stats_error:
                    log('error', f"更新API调用统计失败: {str(stats_error)}",
                        extra={'key': api_key[:8], 'model': chat_request.model})
                
                return
            
            # 如果空响应次数达到限制，跳出循环
            if empty_response_count >= settings.MAX_EMPTY_RESPONSES:
                
                log('warning', f"空响应次数达到限制 ({empty_response_count}/{settings.MAX_EMPTY_RESPONSES})，停止轮询",
                    extra={'request_type': 'stream', 'model': chat_request.model})
                
                yield openAI_from_text(model=chat_request.model,content="空响应次数达到上限\n请修改输入提示词",finish_reason="stop",stream=True)
                
                return
    
    # 所有API密钥都尝试失败的处理
    log('error', "所有 API 密钥均请求失败，请稍后重试",
        extra={'key': 'ALL', 'request_type': 'stream', 'model': chat_request.model})
    yield openAI_from_text(model=chat_request.model,content="所有API密钥均请求失败\n具体错误请查看轮询日志",finish_reason="stop")

# 处理假流式模式
async def handle_fake_streaming(api_key,chat_request, contents, response_cache_manager,system_instruction, safety_settings, safety_settings_g2, cache_key):
    
    # 使用非流式请求内容
    gemini_client = GeminiClient(api_key)
    
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
            log('warning', f"API密钥 {api_key[:8]}... 返回空响应",
                extra={'key': api_key[:8], 'request_type': 'fake-stream', 'model': chat_request.model})
            return "empty"
        
        # 缓存响应结果
        await response_cache_manager.store(cache_key, response_content)
        
        # 只使用新版API统计更新
        try:
            tokens = response_content.total_token_count or 0
            await api_stats_manager.update_stats(api_key, chat_request.model, tokens)
        except Exception as stats_error:
            log('error', f"更新API调用统计失败: {str(stats_error)}",
                extra={'key': api_key[:8], 'model': chat_request.model})
            
        return "success"
    
    except Exception as e:
        handle_gemini_error(e, api_key)
        # log('error', f"假流式模式: API密钥 {api_key[:8]}... 请求失败: {error_detail}",
        #     extra={'key': api_key[:8], 'request_type': 'fake-stream', 'model': chat_request.model})
        return "error"
        


# 流式请求处理函数
async def process_stream_request(
    chat_request: ChatCompletionRequest,
    key_manager,
    response_cache_manager,
    safety_settings,
    safety_settings_g2,
    cache_key: str
) -> StreamingResponse:
    """处理流式API请求"""
    
    return StreamingResponse(stream_response_generator(
                chat_request,
                key_manager,
                response_cache_manager,
                safety_settings,
                safety_settings_g2,
                cache_key
            ), media_type="text/event-stream")
