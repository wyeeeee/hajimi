from typing import List, Dict, Optional, Union, Literal, Any
from pydantic import BaseModel, Field


# openAI 请求
class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    temperature: float = 0.7
    top_p: Optional[float] = None
    top_k: Optional[float] = None
    n: int = 1
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    seed: Optional[int] = None
    logprobs: Optional[int] = None
    response_logprobs: Optional[bool] = None
    thinking_budget: Optional[int] = -1
    enable_thinking: Optional[bool] = True
    reasoning_effort: Optional[str] = None
    # 函数调用
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[Literal["none", "auto"], Dict[str, Any]]] = "auto"


# gemini 请求
class ChatRequestGemini(BaseModel):
    contents: List[Dict[str, Any]]
    system_instruction: Optional[Dict[str, Any]] = None
    systemInstruction: Optional[Dict[str, Any]] = None
    safetySettings: Optional[List[Dict[str, Any]]] = None
    generationConfig: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None


# AI模型请求包装
class AIRequest(BaseModel):
    payload: Optional[ChatRequestGemini] = None
    model: Optional[str] = None
    stream: bool = False
    format_type: Optional[str] = "gemini"


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ResponseMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    reasoning_content: Optional[str] = None


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ResponseMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"]
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Usage = Field(default_factory=Usage)


class ResponseDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    reasoning_content: Optional[str] = None


class ChatCompletionStreamResponseChoice(BaseModel):
    index: int
    delta: ResponseDelta
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"]
    created: int
    model: str
    choices: List[ChatCompletionStreamResponseChoice]
    usage: Optional[Usage] = None


class ErrorResponse(BaseModel):
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ModelList(BaseModel):
    object: str = "list"
    data: List[Dict[str, Any]]


class ChatResponseGemini(BaseModel):
    candidates: Optional[List[Any]] = None
    promptFeedback: Optional[Any] = None
    usageMetadata: Optional[Dict[str, int]] = None


class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str
    encoding_format: Optional[str] = "float"


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: Usage
