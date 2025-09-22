import asyncio
import json
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatCompletionRequest
from app.services import GeminiClient
from app.utils import handle_gemini_error, update_api_call_stats, log, openAI_from_text
from app.utils.response import openAI_from_Gemini, gemini_from_text
from app.utils.stats import get_api_key_usage
import app.config.settings as settings


async def stream_response_generator(
    chat_request,
    key_manager,
    response_cache_manager,
    safety_settings,
    safety_settings_g2,
    cache_key: str,
):
    format_type = getattr(chat_request, "format_type", None)
    if format_type and (format_type == "gemini"):
        is_gemini = True
        contents, system_instruction = None, None
    else:
        is_gemini = False
        # 转换消息格式
        contents, system_instruction = GeminiClient.convert_messages(
            GeminiClient, chat_request.messages, model=chat_request.model
        )
    # 设置初始并发数
    current_concurrent = settings.CONCURRENT_REQUESTS
    max_retry_num = settings.MAX_RETRY_NUM

    # 当前请求次数
    current_try_num = 0

    # 空响应计数
    empty_response_count = 0

    # (假流式) 尝试使用不同API密钥，直到达到最大重试次数或空响应限制
    while (
        settings.FAKE_STREAMING
        and (current_try_num < max_retry_num)
        and (empty_response_count < settings.MAX_EMPTY_RESPONSES)
    ):
        # 获取当前批次的密钥数量
        batch_num = min(max_retry_num - current_try_num, current_concurrent)

        # 获取当前批次的密钥
        valid_keys = []
        checked_keys = set()  # 用于记录已检查过的密钥
        all_keys_checked = False  # 标记是否已检查所有密钥

        # 尝试获取足够数量的有效密钥
        while len(valid_keys) < batch_num:
            api_key = await key_manager.get_available_key()
            if not api_key:
                break

            # 如果这个密钥已经检查过，说明已经检查了所有密钥
            if api_key in checked_keys:
                all_keys_checked = True
                break

            checked_keys.add(api_key)
            # 获取API密钥的调用次数
            usage = await get_api_key_usage(settings.api_call_stats, api_key)
            # 如果调用次数小于限制，则添加到有效密钥列表
            if usage < settings.API_KEY_DAILY_LIMIT:
                valid_keys.append(api_key)
            else:
                log(
                    "warning",
                    f"API密钥 {api_key[:8]}... 已达到每日调用限制 ({usage}/{settings.API_KEY_DAILY_LIMIT})",
                    extra={
                        "key": api_key[:8],
                        "request_type": "stream",
                        "model": chat_request.model,
                    },
                )

        # 如果已经检查了所有密钥且没有找到有效密钥，则重置密钥栈
        if all_keys_checked and not valid_keys:
            log(
                "warning",
                "所有API密钥已达到每日调用限制，重置密钥栈",
                extra={"request_type": "stream", "model": chat_request.model},
            )
            key_manager._reset_key_stack()
            # 重置后重新获取一个密钥
            api_key = await key_manager.get_available_key()
            if api_key:
                valid_keys = [api_key]

        # 如果没有获取到任何有效密钥，跳出循环
        if not valid_keys:
            break

        # 更新当前尝试次数
        current_try_num += len(valid_keys)

        # 创建并发任务
        tasks = []
        tasks_map = {}
        for api_key in valid_keys:
            # 假流式模式的处理逻辑
            log(
                "info",
                f"假流式请求开始，使用密钥: {api_key[:8]}...",
                extra={
                    "key": api_key[:8],
                    "request_type": "fake-stream",
                    "model": chat_request.model,
                },
            )

            task = asyncio.create_task(
                handle_fake_streaming(
                    api_key,
                    chat_request,
                    contents,
                    response_cache_manager,
                    system_instruction,
                    safety_settings,
                    safety_settings_g2,
                    cache_key,
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
                return_when=asyncio.FIRST_COMPLETED,
            )

            # 如果没有任务完成，发送保活消息
            if not done:
                if is_gemini:
                    yield gemini_from_text(content="", stream=True)
                else:
                    yield openAI_from_text(
                        model=chat_request.model, content="", stream=True
                    )
                continue

            # 检查已完成的任务是否成功
            for task in done:
                api_key = tasks_map[task]
                if not task.cancelled():
                    try:
                        status = task.result()
                        # 如果有成功响应内容
                        if status == "success":
                            success = True
                            log(
                                "info",
                                "假流式请求成功",
                                extra={
                                    "key": api_key[:8],
                                    "request_type": "fake-stream",
                                    "model": chat_request.model,
                                },
                            )
                            (
                                cached_response,
                                cache_hit,
                            ) = await response_cache_manager.get_and_remove(cache_key)
                            if cache_hit and cached_response:
                                if is_gemini:
                                    json_payload = json.dumps(
                                        cached_response.data, ensure_ascii=False
                                    )
                                    data_to_yield = f"data: {json_payload}\n\n"
                                    yield data_to_yield
                                else:
                                    yield openAI_from_Gemini(
                                        cached_response, stream=True
                                    )
                            else:
                                success = False
                            break
                        elif status == "empty":
                            # 增加空响应计数
                            empty_response_count += 1
                            log(
                                "warning",
                                f"空响应计数: {empty_response_count}/{settings.MAX_EMPTY_RESPONSES}",
                                extra={
                                    "key": api_key[:8],
                                    "request_type": "stream",
                                    "model": chat_request.model,
                                },
                            )

                    except Exception as e:
                        error_detail = handle_gemini_error(e, api_key)
                        log(
                            "error",
                            f"请求失败: {error_detail}",
                            extra={
                                "key": api_key[:8],
                                "request_type": "stream",
                                "model": chat_request.model,
                            },
                        )

            # 如果找到成功的响应，跳出循环
            if success:
                return

            # 如果空响应次数达到限制，跳出循环
            if empty_response_count >= settings.MAX_EMPTY_RESPONSES:
                log(
                    "warning",
                    f"空响应次数达到限制 ({empty_response_count}/{settings.MAX_EMPTY_RESPONSES})，停止轮询",
                    extra={"request_type": "fake-stream", "model": chat_request.model},
                )
                if is_gemini:
                    yield gemini_from_text(
                        content="空响应次数达到上限\n请修改输入提示词",
                        finish_reason="STOP",
                        stream=True,
                    )
                else:
                    yield openAI_from_text(
                        model=chat_request.model,
                        content="空响应次数达到上限\n请修改输入提示词",
                        finish_reason="stop",
                        stream=True,
                        role="error",
                    )

                return

            # 更新任务列表，移除已完成的任务
            tasks = [(k, t) for k, t in tasks if not t.done()]

        # 如果所有请求都失败，增加并发数并继续尝试
        if not success and valid_keys:
            # 增加并发数，但不超过最大并发数
            current_concurrent = min(
                current_concurrent + settings.INCREASE_CONCURRENT_ON_FAILURE,
                settings.MAX_CONCURRENT_REQUESTS,
            )
            log(
                "info",
                f"所有假流式请求失败，增加并发数至: {current_concurrent}",
                extra={"request_type": "stream", "model": chat_request.model},
            )

    # (真流式) 尝试使用不同API密钥，直到达到最大重试次数或空响应限制
    while (
        not settings.FAKE_STREAMING
        and (current_try_num < max_retry_num)
        and (empty_response_count < settings.MAX_EMPTY_RESPONSES)
    ):
        # 获取当前批次的密钥
        valid_keys = []
        checked_keys = set()  # 用于记录已检查过的密钥
        all_keys_checked = False  # 标记是否已检查所有密钥

        # 尝试获取一个有效密钥
        while len(valid_keys) < 1:
            api_key = await key_manager.get_available_key()
            if not api_key:
                break

            # 如果这个密钥已经检查过，说明已经检查了所有密钥
            if api_key in checked_keys:
                all_keys_checked = True
                break

            checked_keys.add(api_key)
            # 获取API密钥的调用次数
            usage = await get_api_key_usage(settings.api_call_stats, api_key)
            # 如果调用次数小于限制，则添加到有效密钥列表
            if usage < settings.API_KEY_DAILY_LIMIT:
                valid_keys.append(api_key)
            else:
                log(
                    "warning",
                    f"API密钥 {api_key[:8]}... 已达到每日调用限制 ({usage}/{settings.API_KEY_DAILY_LIMIT})",
                    extra={
                        "key": api_key[:8],
                        "request_type": "stream",
                        "model": chat_request.model,
                    },
                )

        # 如果已经检查了所有密钥且没有找到有效密钥，则重置密钥栈
        if all_keys_checked and not valid_keys:
            log(
                "warning",
                "所有API密钥已达到每日调用限制，重置密钥栈",
                extra={"request_type": "stream", "model": chat_request.model},
            )
            key_manager._reset_key_stack()
            # 重置后重新获取一个密钥
            api_key = await key_manager.get_available_key()
            if api_key:
                valid_keys = [api_key]

        # 如果没有获取到任何有效密钥，跳出循环
        if not valid_keys:
            break

        # 更新当前尝试次数
        current_try_num += 1

        # 获取密钥
        api_key = valid_keys[0]

        success = False
        try:
            client = GeminiClient(api_key)

            # 获取流式响应
            stream_generator = client.stream_chat(
                chat_request,
                contents,
                safety_settings_g2
                if "gemini-2.5" in chat_request.model
                else safety_settings,
                system_instruction,
            )
            token = 0
            # 处理流式响应
            async for chunk in stream_generator:
                if chunk:
                    if chunk.total_token_count:
                        token = int(chunk.total_token_count)
                    success = True

                    if is_gemini:
                        json_payload = json.dumps(chunk.data, ensure_ascii=False)
                        data = f"data: {json_payload}\n\n"
                    else:
                        data = openAI_from_Gemini(chunk, stream=True)

                    # log('info', f"流式响应发送数据: {data}")
                    yield data

                else:
                    log(
                        "warning",
                        f"流式请求返回空响应，空响应计数: {empty_response_count}/{settings.MAX_EMPTY_RESPONSES}",
                        extra={
                            "key": api_key[:8],
                            "request_type": "stream",
                            "model": chat_request.model,
                        },
                    )
                    # 增加空响应计数
                    empty_response_count += 1
                    await update_api_call_stats(
                        settings.api_call_stats,
                        endpoint=api_key,
                        model=chat_request.model,
                        token=token,
                    )
                    break

        except Exception as e:
            error_detail = handle_gemini_error(e, api_key)
            log(
                "error",
                f"流式响应: API密钥 {api_key[:8]}... 请求失败: {error_detail}",
                extra={
                    "key": api_key[:8],
                    "request_type": "stream",
                    "model": chat_request.model,
                },
            )
        finally:
            # 如果成功获取相应，更新API调用统计
            if success:
                await update_api_call_stats(
                    settings.api_call_stats,
                    endpoint=api_key,
                    model=chat_request.model,
                    token=token,
                )
                return

            # 如果空响应次数达到限制，跳出循环
            if empty_response_count >= settings.MAX_EMPTY_RESPONSES:
                log(
                    "warning",
                    f"空响应次数达到限制 ({empty_response_count}/{settings.MAX_EMPTY_RESPONSES})，停止轮询",
                    extra={"request_type": "stream", "model": chat_request.model},
                )

                if is_gemini:
                    yield gemini_from_text(
                        content="空响应次数达到上限\n请修改输入提示词",
                        finish_reason="STOP",
                        stream=True,
                    )
                else:
                    yield openAI_from_text(
                        model=chat_request.model,
                        content="空响应次数达到上限\n请修改输入提示词",
                        finish_reason="stop",
                        stream=True,
                        role="error",
                    )

                return

    # 所有API密钥都尝试失败的处理
    log(
        "error",
        "所有 API 密钥均请求失败，请稍后重试",
        extra={"key": "ALL", "request_type": "stream", "model": chat_request.model},
    )

    if is_gemini:
        yield gemini_from_text(
            content="所有API密钥均请求失败\n具体错误请查看轮询日志",
            finish_reason="STOP",
            stream=True,
        )
    else:
        yield openAI_from_text(
            model=chat_request.model,
            content="所有API密钥均请求失败\n具体错误请查看轮询日志",
            finish_reason="stop",
            role="error",
        )


# 处理假流式模式
async def handle_fake_streaming(
    api_key,
    chat_request,
    contents,
    response_cache_manager,
    system_instruction,
    safety_settings,
    safety_settings_g2,
    cache_key,
):
    # 使用非流式请求内容
    gemini_client = GeminiClient(api_key)

    gemini_task = asyncio.create_task(
        gemini_client.complete_chat(
            chat_request,
            contents,
            safety_settings_g2
            if "gemini-2.5" in chat_request.model
            else safety_settings,
            system_instruction,
        )
    )
    gemini_task = asyncio.shield(gemini_task)

    try:
        # 获取响应内容
        response_content = await gemini_task
        response_content.set_model(chat_request.model)
        log(
            "info",
            "假流式成功获取响应，进行缓存",
            extra={
                "key": api_key[:8],
                "request_type": "fake-stream",
                "model": chat_request.model,
            },
        )

        # 更新API调用统计
        await update_api_call_stats(
            settings.api_call_stats,
            endpoint=api_key,
            model=chat_request.model,
            token=response_content.total_token_count,
        )

        # 检查响应内容是否为空
        if not response_content or (
            not response_content.text and not response_content.function_call
        ):
            log(
                "warning",
                "请求返回空响应",
                extra={
                    "key": api_key[:8],
                    "request_type": "fake-stream",
                    "model": chat_request.model,
                },
            )
            return "empty"

        # 缓存
        await response_cache_manager.store(cache_key, response_content)
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
    cache_key: str,
) -> StreamingResponse:
    """处理流式API请求"""

    return StreamingResponse(
        stream_response_generator(
            chat_request,
            key_manager,
            response_cache_manager,
            safety_settings,
            safety_settings_g2,
            cache_key,
        ),
        media_type="text/event-stream",
    )