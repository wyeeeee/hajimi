import json
import time


def openAI_from_text(
    model="gemini",
    content=None,
    finish_reason=None,
    total_token_count=0,
    stream=True,
    role="assistant",
):
    """
    根据传入参数，创建 OpenAI 标准响应对象块
    """

    now_time = int(time.time())
    content_chunk = {}
    formatted_chunk = {
        "id": f"chatcmpl-{now_time}",
        "created": now_time,
        "model": model,
        "choices": [{"index": 0, "finish_reason": finish_reason}],
    }

    if content:
        content_chunk = {"role": role, "content": content}

    if finish_reason:
        formatted_chunk["usage"] = {"total_tokens": total_token_count}

    if stream:
        formatted_chunk["choices"][0]["delta"] = content_chunk
        formatted_chunk["object"] = "chat.completion.chunk"
        return f"data: {json.dumps(formatted_chunk, ensure_ascii=False)}\n\n"
    else:
        formatted_chunk["choices"][0]["message"] = content_chunk
        formatted_chunk["object"] = "chat.completion"
        return formatted_chunk


def gemini_from_text(
    content=None, finish_reason=None, total_token_count=0, stream=True
):
    """
    根据传入参数，创建 Gemini API 标准响应对象块 (GenerateContentResponse 格式)。
    """
    gemini_response = {
        "candidates": {"index": 0, "content": {"parts": [], "role": "model"}}
    }
    if content:
        gemini_response["candidates"]["content"]["parts"].append({"text": content})

    if finish_reason:
        gemini_response["usageMetadata"] = {"totalTokenCount": total_token_count}

    if stream:
        return f"data: {json.dumps(gemini_response, ensure_ascii=False)}\n\n"
    else:
        return gemini_response


def openAI_from_Gemini(response, stream=True):
    """
    根据 GeminiResponseWrapper 对象创建 OpenAI 标准响应对象块。

    Args:
        response: GeminiResponseWrapper 对象，包含响应数据。

    Returns:
        OpenAI 标准响应
    """
    now_time = int(time.time())
    chunk_id = f"chatcmpl-{now_time}"  # 使用时间戳生成唯一 ID
    content_chunk = {}
    formatted_chunk = {
        "id": chunk_id,
        "created": now_time,
        "model": response.model,
        "choices": [{"index": 0, "finish_reason": response.finish_reason}],
    }

    # 准备 usage 数据，处理属性缺失或为 None 的情况
    prompt_tokens_raw = getattr(response, "prompt_token_count", None)
    candidates_tokens_raw = getattr(response, "candidates_token_count", None)
    total_tokens_raw = getattr(response, "total_token_count", None)

    usage_data = {
        "prompt_tokens": int(prompt_tokens_raw) if prompt_tokens_raw else 0,
        "completion_tokens": int(candidates_tokens_raw) if candidates_tokens_raw else 0,
        "total_tokens": int(total_tokens_raw) if total_tokens_raw else 0,
    }

    if response.function_call:
        tool_calls = []
        # 处理函数调用的每一部分
        for part in response.function_call:
            function_name = part.get("name")
            # Gemini 的 args 是 dict, OpenAI 需要 string
            function_args_str = json.dumps(part.get("args", {}), ensure_ascii=False)

            tool_call_id = f"call_{function_name}"  # 编码函数名到 ID
            tool_calls.append(
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": function_args_str,
                    },
                }
            )

        content_chunk = {
            "role": "assistant",
            "content": None,  # 函数调用时 content 为 null
            "tool_calls": tool_calls,
        }
    elif response.text or response.thoughts:
        content_chunk = {"role": "assistant", "content": response.text}
        if response.thoughts:
            content_chunk["reasoning_content"] = response.thoughts
    
    if stream:
        formatted_chunk["choices"][0]["delta"] = content_chunk
        formatted_chunk["object"] = "chat.completion.chunk"
        # 仅在流结束时添加 usage 字段
        if response.finish_reason:
            formatted_chunk["usage"] = usage_data
        return f"data: {json.dumps(formatted_chunk, ensure_ascii=False)}\n\n"

    else:
        formatted_chunk["choices"][0]["message"] = content_chunk
        formatted_chunk["object"] = "chat.completion"
        # 非流式响应总是包含 usage 字段，以满足 response_model 验证
        formatted_chunk["usage"] = usage_data
        return formatted_chunk
