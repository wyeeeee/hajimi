import json
from typing import Optional, Union
from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Path,
    Query,
    Request,
    Depends,
    status,
)
from fastapi.responses import StreamingResponse
from app.services import GeminiClient
from app.utils import protect_from_abuse, generate_cache_key, log
from app.utils.response import openAI_from_Gemini
from app.utils.auth import custom_verify_password
from app.utils.error_handling import sanitize_string
from .stream_handlers import process_stream_request
from .nonstream_handlers import process_request, process_nonstream_with_keepalive_stream
from app.models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelList,
    AIRequest,
    ChatRequestGemini,
    EmbeddingRequest,
    EmbeddingResponse,
)
from app.services.embedding import EmbeddingClient
import app.config.settings as settings
import asyncio
from app.vertex.routes import chat_api, models_api
from app.vertex.models import OpenAIRequest, OpenAIMessage

# 创建路由器
router = APIRouter()

# 全局变量引用 - 这些将在main.py中初始化并传递给路由
key_manager = None
response_cache_manager = None
active_requests_manager = None
safety_settings = None
safety_settings_g2 = None
current_api_key = None
FAKE_STREAMING = None
FAKE_STREAMING_INTERVAL = None
PASSWORD = None
MAX_REQUESTS_PER_MINUTE = None
MAX_REQUESTS_PER_DAY_PER_IP = None


# 初始化路由器的函数
def init_router(
    _key_manager,
    _response_cache_manager,
    _active_requests_manager,
    _safety_settings,
    _safety_settings_g2,
    _current_api_key,
    _fake_streaming,
    _fake_streaming_interval,
    _password,
    _max_requests_per_minute,
    _max_requests_per_day_per_ip,
):
    global key_manager, response_cache_manager, active_requests_manager
    global safety_settings, safety_settings_g2, current_api_key
    global FAKE_STREAMING, FAKE_STREAMING_INTERVAL
    global PASSWORD, MAX_REQUESTS_PER_MINUTE, MAX_REQUESTS_PER_DAY_PER_IP

    key_manager = _key_manager
    response_cache_manager = _response_cache_manager
    active_requests_manager = _active_requests_manager
    safety_settings = _safety_settings
    safety_settings_g2 = _safety_settings_g2
    current_api_key = _current_api_key
    FAKE_STREAMING = _fake_streaming
    FAKE_STREAMING_INTERVAL = _fake_streaming_interval
    PASSWORD = _password
    MAX_REQUESTS_PER_MINUTE = _max_requests_per_minute
    MAX_REQUESTS_PER_DAY_PER_IP = _max_requests_per_day_per_ip


async def verify_user_agent(request: Request):
    if not settings.WHITELIST_USER_AGENT:
        return
    if request.headers.get("User-Agent") not in settings.WHITELIST_USER_AGENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed client"
        )


# todo : 添加 gemini 支持(流式返回)
async def get_cache(cache_key, is_stream: bool, is_gemini=False):
    # 检查缓存是否存在，如果存在，返回缓存
    assert response_cache_manager is not None
    cached_response, cache_hit = await response_cache_manager.get_and_remove(cache_key)

    if cache_hit and cached_response:
        log(
            "info",
            f"缓存命中: {cache_key[:8]}...",
            extra={"request_type": "non-stream", "model": cached_response.model},
        )

        if is_gemini:
            if is_stream:
                data = (
                    f"data: {json.dumps(cached_response.data, ensure_ascii=False)}\n\n"
                )
                return StreamingResponse(data, media_type="text/event-stream")
            else:
                return cached_response.data

        if is_stream:
            chunk = openAI_from_Gemini(cached_response, stream=True)
            return StreamingResponse(chunk, media_type="text/event-stream")
        else:
            return openAI_from_Gemini(cached_response, stream=False)

    return None


@router.get("/aistudio/models", response_model=ModelList)
async def aistudio_list_models(
    _=Depends(custom_verify_password), _2=Depends(verify_user_agent)
):
    if settings.WHITELIST_MODELS:
        filtered_models = [
            model
            for model in GeminiClient.AVAILABLE_MODELS
            if model in settings.WHITELIST_MODELS
        ]
    else:
        filtered_models = [
            model
            for model in GeminiClient.AVAILABLE_MODELS
            if model not in settings.BLOCKED_MODELS
        ]
    return ModelList(
        data=[
            {
                "id": model,
                "object": "model",
                "created": 1678888888,
                "owned_by": "organization-owner",
            }
            for model in filtered_models
        ]
    )


@router.get("/vertex/models", response_model=ModelList)
async def vertex_list_models(
    request: Request, _=Depends(custom_verify_password), _2=Depends(verify_user_agent)
):
    # 使用vertex/routes/models_api的实现
    assert current_api_key is not None
    return await models_api.list_models(request, current_api_key)


# API路由
@router.get("/v1/models", response_model=ModelList)
@router.get("/models", response_model=ModelList)
async def list_models(
    request: Request, _=Depends(custom_verify_password), _2=Depends(verify_user_agent)
):
    if settings.ENABLE_VERTEX:
        return await vertex_list_models(request, _, _2)
    return await aistudio_list_models(_, _2)


@router.post("/aistudio/chat/completions", response_model=ChatCompletionResponse)
async def aistudio_chat_completions(
    request: Union[ChatCompletionRequest, AIRequest],
    http_request: Request,
    _=Depends(custom_verify_password),
    _2=Depends(verify_user_agent),
):
    format_type = getattr(request, "format_type", None)
    if format_type and (format_type == "gemini"):
        is_gemini = True
    else:
        is_gemini = False

    # 生成缓存键 - 用于匹配请求内容对应缓存
    if settings.PRECISE_CACHE:
        cache_key = generate_cache_key(request, is_gemini=is_gemini)
    else:
        cache_key = generate_cache_key(
            request,
            last_n_messages=settings.CALCULATE_CACHE_ENTRIES,
            is_gemini=is_gemini,
        )

    # 请求前基本检查
    await protect_from_abuse(
        http_request,
        settings.MAX_REQUESTS_PER_MINUTE,
        settings.MAX_REQUESTS_PER_DAY_PER_IP,
    )

    if request.model not in GeminiClient.AVAILABLE_MODELS:
        log("error", "无效的模型", extra={"model": request.model, "status_code": 400})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无效的模型"
        )

    # 记录请求缓存键信息
    log(
        "info",
        f"请求缓存键: {cache_key[:8]}...",
        extra={"request_type": "non-stream", "model": request.model},
    )

    # 检查缓存是否存在，如果存在，返回缓存
    cached_response = await get_cache(
        cache_key, is_stream=request.stream, is_gemini=is_gemini
    )
    if cached_response:
        return cached_response

    if not settings.PUBLIC_MODE:
        # 构建包含缓存键的活跃请求池键
        pool_key = f"{cache_key}"

        # 查找所有使用相同缓存键的活跃任务
        assert active_requests_manager is not None
        active_task = active_requests_manager.get(pool_key)
        if active_task and not active_task.done():
            log(
                "info",
                "发现相同请求的进行中任务",
                extra={
                    "request_type": "stream" if request.stream else "non-stream",
                    "model": request.model,
                },
            )

            # 等待已有任务完成
            try:
                # 设置超时，避免无限等待
                await asyncio.wait_for(active_task, timeout=240)

                # 使用任务结果
                if active_task.done() and not active_task.cancelled():
                    result = active_task.result()
                    active_requests_manager.remove(pool_key)
                    if result:
                        return result

            except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                # 任务超时或被取消的情况下，记录日志然后让代码继续执行
                error_type = "超时" if isinstance(e, asyncio.TimeoutError) else "被取消"
                log(
                    "warning",
                    f"等待已有任务{error_type}: {pool_key}",
                    extra={"request_type": "non-stream", "model": request.model},
                )

                # 从活跃请求池移除该任务
                if active_task.done() or active_task.cancelled():
                    active_requests_manager.remove(pool_key)
                    log(
                        "info",
                        f"已从活跃请求池移除{error_type}任务: {pool_key}",
                        extra={"request_type": "non-stream"},
                    )

    if request.stream:
        # 流式请求处理任务
        process_task = asyncio.create_task(
            process_stream_request(
                chat_request=request,
                key_manager=key_manager,
                response_cache_manager=response_cache_manager,
                safety_settings=safety_settings,
                safety_settings_g2=safety_settings_g2,
                cache_key=cache_key,
            )
        )

    else:
        # 检查是否启用非流式保活功能
        if settings.NONSTREAM_KEEPALIVE_ENABLED:
            # 使用带保活功能的非流式请求处理
            process_task = asyncio.create_task(
                process_nonstream_with_keepalive_stream(
                    chat_request=request,
                    key_manager=key_manager,
                    response_cache_manager=response_cache_manager,
                    safety_settings=safety_settings,
                    safety_settings_g2=safety_settings_g2,
                    cache_key=cache_key,
                    is_gemini=is_gemini,
                )
            )
        else:
            # 创建非流式请求处理任务
            process_task = asyncio.create_task(
                process_request(
                    chat_request=request,
                    key_manager=key_manager,
                    response_cache_manager=response_cache_manager,
                    safety_settings=safety_settings,
                    safety_settings_g2=safety_settings_g2,
                    cache_key=cache_key,
                )
            )

    if not settings.PUBLIC_MODE:
        # 将任务添加到活跃请求池
        active_requests_manager.add(pool_key, process_task)

    # 等待任务完成
    try:
        response = await process_task
        if not settings.PUBLIC_MODE:
            active_requests_manager.remove(pool_key)

        return response
    except Exception as e:
        if not settings.PUBLIC_MODE:
            # 如果任务失败，从活跃请求池中移除
            active_requests_manager.remove(pool_key)

        # 检查是否已有缓存的结果（可能是由另一个任务创建的）
        cached_response = await get_cache(
            cache_key, is_stream=request.stream, is_gemini=is_gemini
        )
        if cached_response:
            return cached_response

        sanitized_detail = sanitize_string(f" hajimi 内部处理时发生错误\n具体原因:{e}")
        # 发送错误信息给客户端
        raise HTTPException(status_code=500, detail=sanitized_detail)


@router.post("/vertex/chat/completions", response_model=ChatCompletionResponse)
async def vertex_chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
    _dp=Depends(custom_verify_password),
    _du=Depends(verify_user_agent),
):
    # 使用vertex/routes/chat_api的实现

    # 转换消息格式
    openai_messages = []
    for message in request.messages:
        openai_messages.append(
            OpenAIMessage(
                role=message.get("role", ""), content=message.get("content", "")
            )
        )

    # 转换请求格式
    vertex_request = OpenAIRequest(
        model=request.model,
        messages=openai_messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
        top_k=request.top_k,
        stream=request.stream,
        stop=request.stop,
        presence_penalty=request.presence_penalty,
        frequency_penalty=request.frequency_penalty,
        seed=getattr(request, "seed", None),
        logprobs=getattr(request, "logprobs", None),
        response_logprobs=getattr(request, "response_logprobs", None),
        n=request.n,
    )

    # 调用vertex/routes/chat_api的实现
    assert current_api_key is not None
    return await chat_api.chat_completions(
        http_request, vertex_request, current_api_key
    )


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
    _dp=Depends(custom_verify_password),
    _du=Depends(verify_user_agent),
):
    """处理API请求的主函数，根据需要处理流式或非流式请求"""
    if settings.ENABLE_VERTEX:
        return await vertex_chat_completions(request, http_request, _dp, _du)
    return await aistudio_chat_completions(request, http_request, _dp, _du)


@router.get("/gemini/v1beta/models")
@router.get("/gemini/v1/models")
async def gemini_list_models(
    request: Request, _=Depends(custom_verify_password), _2=Depends(verify_user_agent)
):
    """gemini 端点的模型获取"""
    assert key_manager is not None
    api_key = await key_manager.get_available_key()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid API keys available.",
        )

    return await GeminiClient.list_native_models(api_key)


@router.post("/gemini/{api_version:str}/models/{model_and_responseType:path}")
async def gemini_chat_completions(
    request: Request,
    model_and_responseType: str = Path(...),
    key: Optional[str] = Query(None),
    alt: Optional[str] = Query(None, description=" sse 或 None"),
    payload: ChatRequestGemini = Body(...),
    _dp=Depends(custom_verify_password),
    _du=Depends(verify_user_agent),
):
    # 提取路径参数
    is_stream = False
    try:
        model_name, action_type = model_and_responseType.split(":", 1)
        model_name = model_name.removeprefix("models/")
        if action_type == "streamGenerateContent":
            is_stream = True

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的请求路径")

    geminiRequest = AIRequest(
        payload=payload, model=model_name, stream=is_stream, format_type="gemini"
    )
    return await aistudio_chat_completions(geminiRequest, request, _dp, _du)


@router.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embedding(
    request: EmbeddingRequest,
    http_request: Request,
    _du=Depends(verify_user_agent),
    _dp=Depends(custom_verify_password),
):
    await protect_from_abuse(
        http_request,
        settings.MAX_REQUESTS_PER_MINUTE,
        settings.MAX_REQUESTS_PER_DAY_PER_IP,
    )

    assert key_manager is not None
    api_key = await key_manager.get_available_key()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: No available API keys",
        )

    client = EmbeddingClient(api_key)
    try:
        return await client.create_embeddings(request)
    except Exception as e:
        log("ERROR", f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/api/vector/query")
async def vector_query(
    request: Request,
    _du=Depends(verify_user_agent),
    _dp=Depends(custom_verify_password),
):
    log("INFO", f"Received vector query request with headers: {request.headers}")
    body = await request.json()
    search_text = body.get("searchText")
    model = body.get("model")

    assert key_manager is not None
    api_key = await key_manager.get_available_key()

    if not all([search_text, model, api_key]):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing required parameters or no available API keys")

    client = EmbeddingClient(api_key)
    embedding_request = EmbeddingRequest(input=search_text, model=model)
    
    try:
        embedding_response = await client.create_embeddings(embedding_request)
        # Adapt the response to the format expected by the plugin
        adapted_response = {
            "hashes": [],
            "metadata": [],
            "items": [
                {"text": "", "score": 0, "metadata": {"embedding": data.embedding}}
                for data in embedding_response.data
            ],
            "similarities": [0] * len(embedding_response.data),
        }
        return adapted_response
    except Exception as e:
        log("ERROR", f"An unexpected error occurred during vector query: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/api/vector/insert")
async def vector_insert(
    request: Request,
    _du=Depends(verify_user_agent),
    _dp=Depends(custom_verify_password),
):
    log("INFO", f"Received vector insert request with headers: {request.headers}")
    body = await request.json()
    items = body.get("items", [])
    model = body.get("model")

    assert key_manager is not None
    api_key = await key_manager.get_available_key()

    if not all([items, model, api_key]):
        raise HTTPException(status_code=401, detail="Unauthorized: Missing required parameters or no available API keys")

    texts = [item.get("text") for item in items]
    client = EmbeddingClient(api_key)
    embedding_request = EmbeddingRequest(input=texts, model=model)

    try:
        await client.create_embeddings(embedding_request)
        # The plugin doesn't seem to care about the response, so we can return a simple success message
        return {"success": True}
    except Exception as e:
        log("ERROR", f"An unexpected error occurred during vector insert: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
