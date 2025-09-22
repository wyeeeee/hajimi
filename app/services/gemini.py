import json
import os
from app.models.schemas import ChatCompletionRequest
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
import httpx
import secrets
import string
import app.config.settings as settings

from app.utils.logging import log


def generate_secure_random_string(length):
    all_characters = string.ascii_letters + string.digits
    secure_random_string = "".join(
        secrets.choice(all_characters) for _ in range(length)
    )
    return secure_random_string


@dataclass
class GeneratedText:
    text: str
    finish_reason: Optional[str] = None


class GeminiResponseWrapper:
    def __init__(self, data: Dict[Any, Any]):
        self._data = data
        self._text = self._extract_text()
        self._finish_reason = self._extract_finish_reason()
        self._prompt_token_count = self._extract_prompt_token_count()
        self._candidates_token_count = self._extract_candidates_token_count()
        self._total_token_count = self._extract_total_token_count()
        self._thoughts = self._extract_thoughts()
        self._function_call = self._extract_function_call()
        self._json_dumps = json.dumps(self._data, indent=4, ensure_ascii=False)
        self._model = "gemini"

    def _extract_thoughts(self) -> Optional[str]:
        try:
            thoughts = []
            for part in self._data["candidates"][0]["content"]["parts"]:
                if part.get("thought"):
                    thoughts.append(part.get("text", ""))
            return "".join(thoughts) if thoughts else None
        except (KeyError, IndexError):
            return None

    def _extract_text(self) -> str:
        try:
            text = ""
            for part in self._data["candidates"][0]["content"]["parts"]:
                if not part.get("thought") and "text" in part:
                    text += part["text"]
            return text
        except (KeyError, IndexError):
            return ""

    def _extract_function_call(self) -> Optional[List[Dict[str, Any]]]:
        try:
            parts = (
                self._data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            # 使用列表推导式查找所有包含 'functionCall' 的 part，并提取其值
            function_calls = [
                part["functionCall"]
                for part in parts
                if isinstance(part, dict) and "functionCall" in part
            ]
            # 如果列表不为空，则返回列表；否则返回 None
            return function_calls if function_calls else None
        except (KeyError, IndexError, TypeError):
            return None

    def _extract_finish_reason(self) -> Optional[str]:
        try:
            return self._data["candidates"][0].get("finishReason")
        except (KeyError, IndexError):
            return None

    def _extract_prompt_token_count(self) -> Optional[int]:
        try:
            return self._data["usageMetadata"].get("promptTokenCount")
        except KeyError:
            return None

    def _extract_candidates_token_count(self) -> Optional[int]:
        try:
            return self._data["usageMetadata"].get("candidatesTokenCount")
        except KeyError:
            return None

    def _extract_total_token_count(self) -> Optional[int]:
        try:
            return self._data["usageMetadata"].get("totalTokenCount")
        except KeyError:
            return None

    def set_model(self, model) -> Optional[str]:
        self._model = model

    @property
    def data(self) -> Dict[Any, Any]:
        return self._data

    @property
    def text(self) -> str:
        return self._text

    @property
    def finish_reason(self) -> Optional[str]:
        return self._finish_reason

    @property
    def prompt_token_count(self) -> Optional[int]:
        return self._prompt_token_count

    @property
    def candidates_token_count(self) -> Optional[int]:
        return self._candidates_token_count

    @property
    def total_token_count(self) -> Optional[int]:
        return self._total_token_count

    @property
    def thoughts(self) -> Optional[str]:
        return self._thoughts

    @property
    def json_dumps(self) -> str:
        return self._json_dumps

    @property
    def model(self) -> str:
        return self._model

    @property
    def function_call(self) -> Optional[List[Dict[str, Any]]]:
        return self._function_call


class GeminiClient:
    AVAILABLE_MODELS = []
    extra_models_str = os.environ.get("EXTRA_MODELS", "")
    EXTRA_MODELS = [
        model.strip() for model in extra_models_str.split(",") if model.strip()
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key

    # 请求参数处理
    def _convert_request_data(
        self, request, contents, safety_settings, system_instruction
    ):
        model = request.model
        format_type = getattr(request, "format_type", None)
        if format_type and (format_type == "gemini"):
            api_version = "v1alpha" if "think" in request.model else "v1beta"
            if request.payload:
                # 将 Pydantic 模型转换为字典, 假设 Pydantic V2+
                data = request.payload.model_dump(exclude_none=True)
            # # 注入搜索提示
            # if settings.search["search_mode"] and request.model and request.model.endswith("-search"):
            #     data.insert(len(data)-2,{'role': 'user', 'parts': [{'text':settings.search["search_prompt"]}]})

            # # 注入随机字符串
            # if settings.RANDOM_STRING:
            #     data.insert(1,{'role': 'user', 'parts': [{'text': generate_secure_random_string(settings.RANDOM_STRING_LENGTH)}]})
            #     data.insert(len(data)-1,{'role': 'user', 'parts': [{'text': generate_secure_random_string(settings.RANDOM_STRING_LENGTH)}]})
            #     log('INFO', "伪装消息成功")

        else:
            api_version, data = self._convert_openAI_request(
                request, contents, safety_settings, system_instruction
            )

        # 联网模式
        if settings.search["search_mode"] and request.model.endswith("-search"):
            log(
                "INFO",
                "开启联网搜索模式",
                extra={"key": self.api_key[:8], "model": request.model},
            )

            data.setdefault("tools", []).append({"google_search": {}})
            model = request.model.removesuffix("-search")

        return api_version, model, data

    def _convert_openAI_request(
        self,
        request: ChatCompletionRequest,
        contents,
        safety_settings,
        system_instruction,
    ):
        config_params = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
            "topP": request.top_p,
            "topK": request.top_k,
            "stopSequences": request.stop
            if isinstance(request.stop, list)
            else [request.stop]
            if request.stop is not None
            else None,
            "candidateCount": request.n,
        }
        thinking_config = {}
        if settings.ENABLE_THINKING:
            if request.thinking_budget is not None:
                thinking_config["thinkingBudget"] = request.thinking_budget
            
            if getattr(request, "enable_thinking", False):
                thinking_config["include_thoughts"] = True

        if thinking_config:
            config_params["thinkingConfig"] = thinking_config
            
        generationConfig = {k: v for k, v in config_params.items() if v is not None}

        api_version = "v1alpha" if "think" in request.model else "v1beta"

        data = {
            "contents": contents,
            "generationConfig": generationConfig,
            "safetySettings": safety_settings,
        }

        # --- 函数调用处理 ---
        # 1. 添加 tools (函数声明)
        function_declarations = []
        if request.tools:
            # 显式提取 Gemini API 所需的字段，避免包含 'id' 等无效字段
            function_declarations = []
            for tool in request.tools:
                if tool.get("type") == "function":
                    func_def = tool.get("function")
                    if func_def:
                        # 只包含 Gemini API 接受的字段
                        declaration = {
                            "name": func_def.get("name"),
                            "description": func_def.get("description"),
                        }
                        # 获取 parameters 并移除可能存在的 $schema 字段
                        parameters = func_def.get("parameters")
                        if isinstance(parameters, dict) and "$schema" in parameters:
                            parameters = parameters.copy()
                            del parameters["$schema"]
                        if parameters is not None:
                            declaration["parameters"] = parameters

                        # 移除值为 None 的键，以保持 payload 清洁
                        declaration = {
                            k: v for k, v in declaration.items() if v is not None
                        }
                        if declaration.get("name"):  # 确保 name 存在
                            function_declarations.append(declaration)

        if function_declarations:
            data["tools"] = [{"function_declarations": function_declarations}]

        # 2. 添加 tool_config (基于 tool_choice)
        tool_config = None
        if request.tool_choice:
            choice = request.tool_choice
            mode = None
            allowed_functions = None
            if isinstance(choice, str):
                if choice == "none":
                    mode = "NONE"
                elif choice == "auto":
                    mode = "AUTO"
            elif isinstance(choice, dict) and choice.get("type") == "function":
                func_name = choice.get("function", {}).get("name")
                if func_name:
                    mode = "ANY"  # 'ANY' 模式用于强制调用特定函数
                    allowed_functions = [func_name]

            # 如果成功解析出有效的 mode，构建 tool_config
            if mode:
                config: Dict[str, Union[str, List[str]]] = {"mode": mode}
                if allowed_functions:
                    config["allowed_function_names"] = allowed_functions
                tool_config = {"function_calling_config": config}

        # 3. 添加 tool_config 到 data
        if tool_config and function_declarations:
            data["tool_config"] = tool_config

        if system_instruction:
            data["system_instruction"] = system_instruction

        return api_version, data

    # 流式请求
    async def stream_chat(self, request, contents, safety_settings, system_instruction):
        # 真流式请求处理逻辑
        extra_log = {
            "key": self.api_key[:8],
            "request_type": "stream",
            "model": request.model,
        }
        log("INFO", "流式请求开始", extra=extra_log)

        api_version, model, data = self._convert_request_data(
            request, contents, safety_settings, system_instruction
        )
        #log("INFO", f"Request body to Google: {json.dumps(data, ensure_ascii=False)}")

        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"
        headers = {
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", url, headers=headers, json=data, timeout=600
            ) as response:
                try:
                    # 检查响应状态码，如果不是成功，则先消费响应体再抛出异常
                    if response.status_code != 200:
                        await response.aread()
                        response.raise_for_status()

                    buffer = b""  # 用于累积可能不完整的 JSON 数据
                    async for line in response.aiter_lines():
                        if not line.strip():  # 跳过空行 (SSE 消息分隔符)
                            continue
                        if line.startswith("data: "):
                            line = line[len("data: ") :].strip()  # 去除 "data: " 前缀

                        # 检查是否是结束标志，如果是，结束循环
                        if line == "[DONE]":
                            break

                        buffer += line.encode("utf-8")
                        try:
                            # 尝试解析整个缓冲区
                            data = json.loads(buffer.decode("utf-8"))
                            # 解析成功，清空缓冲区
                            buffer = b""
                            yield GeminiResponseWrapper(data)

                        except json.JSONDecodeError:
                            # JSON 不完整，继续累积到 buffer
                            continue

                except Exception as e:
                    # 在重新抛出异常之前，确保响应体被完全读取
                    if not response.is_closed:
                        await response.aread()
                    raise e
                finally:
                    log("info", "流式请求结束")

    # 非流式处理
    async def complete_chat(
        self, request, contents, safety_settings, system_instruction
    ):
        api_version, model, data = self._convert_request_data(
            request, contents, safety_settings, system_instruction
        )
        #log("INFO", f"Request body to Google: {json.dumps(data, ensure_ascii=False)}")

        url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=data, timeout=600
                )
                response.raise_for_status()  # 检查 HTTP 错误状态

            return GeminiResponseWrapper(response.json())
        except Exception:
            raise

    # OpenAI 格式请求转换为 gemini 格式请求
    def convert_messages(self, messages, use_system_prompt=False, model=None):
        gemini_history = []
        errors = []

        system_instruction_text = ""
        system_instruction_parts = []  # 用于收集系统指令文本

        # 处理系统指令
        if use_system_prompt:
            # 遍历消息列表，查找开头的连续 system 消息
            for i, message in enumerate(messages):
                # 必须是 system 角色且内容是字符串
                if message.get("role") == "system" and isinstance(
                    message.get("content"), str
                ):
                    system_instruction_parts.append(message.get("content"))
                else:
                    break  # 遇到第一个非 system 或内容非字符串的消息就停止

        # 将收集到的系统指令合并为一个字符串
        system_instruction_text = "\n".join(system_instruction_parts)
        system_instruction = (
            {"parts": [{"text": system_instruction_text}]}
            if system_instruction_text
            else None
        )

        # 转换主要消息

        for i, message in enumerate(messages):
            role = message.get("role")
            content = message.get("content")
            if isinstance(content, str):
                if role == "tool":
                    role_to_use = "function"
                    tool_call_id = message.get("tool_call_id")

                    prefix = "call_"
                    if tool_call_id.startswith(prefix):
                        # 假设 tool_call_id = f"call_{function_name}" (response.py中的处理)
                        function_name = tool_call_id[len(prefix) :]
                    else:
                        continue

                    function_response_part = {
                        "functionResponse": {
                            "name": function_name,
                            "response": {"content": content},
                        }
                    }

                    gemini_history.append(
                        {"role": role_to_use, "parts": [function_response_part]}
                    )

                    continue
                elif role in ["user", "system"]:
                    role_to_use = "user"
                elif role == "assistant":
                    role_to_use = "model"

                else:
                    errors.append(f"Invalid role: {role}")
                    continue

                # Gemini 的一个重要规则：连续的同角色消息需要合并
                # 如果 gemini_history 已有内容，并且最后一条消息的角色和当前要添加的角色相同
                if gemini_history and gemini_history[-1]["role"] == role_to_use:
                    gemini_history[-1]["parts"].append({"text": content})
                else:
                    gemini_history.append(
                        {"role": role_to_use, "parts": [{"text": content}]}
                    )
            elif isinstance(content, list):
                parts = []
                for item in content:
                    if item.get("type") == "text":
                        parts.append({"text": item.get("text")})
                    elif item.get("type") == "image_url":
                        image_data = item.get("image_url", {}).get("url", "")
                        if image_data.startswith("data:image/"):
                            try:
                                mime_type, base64_data = (
                                    image_data.split(";")[0].split(":")[1],
                                    image_data.split(",")[1],
                                )
                                parts.append(
                                    {
                                        "inline_data": {
                                            "mime_type": mime_type,
                                            "data": base64_data,
                                        }
                                    }
                                )
                            except (IndexError, ValueError):
                                errors.append(
                                    f"Invalid data URI for image: {image_data}"
                                )
                        else:
                            errors.append(f"Invalid image URL format for item: {item}")

                if parts:
                    if role in ["user", "system"]:
                        role_to_use = "user"
                    elif role == "assistant":
                        role_to_use = "model"
                    else:
                        errors.append(f"Invalid role: {role}")
                        continue

                    if gemini_history and gemini_history[-1]["role"] == role_to_use:
                        gemini_history[-1]["parts"].extend(parts)
                    else:
                        gemini_history.append({"role": role_to_use, "parts": parts})
        if errors:
            return errors

        # --- 后处理 ---

        # 注入搜索提示
        if settings.search["search_mode"] and model and model.endswith("-search"):
            gemini_history.insert(
                len(gemini_history) - 2,
                {"role": "user", "parts": [{"text": settings.search["search_prompt"]}]},
            )

        # 注入随机字符串
        if settings.RANDOM_STRING:
            gemini_history.insert(
                1,
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": generate_secure_random_string(
                                settings.RANDOM_STRING_LENGTH
                            )
                        }
                    ],
                },
            )
            gemini_history.insert(
                len(gemini_history) - 1,
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": generate_secure_random_string(
                                settings.RANDOM_STRING_LENGTH
                            )
                        }
                    ],
                },
            )
            log("INFO", "伪装消息成功")

        return gemini_history, system_instruction

    @staticmethod
    async def list_available_models(api_key) -> list:
        url = "https://generativelanguage.googleapis.com/v1beta/models?key={}".format(
            api_key
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            models = []
            for model in data.get("models", []):
                models.append(model["name"])
                if (
                    model["name"].startswith("models/gemini-2")
                    and settings.search["search_mode"]
                ):
                    models.append(model["name"] + "-search")
            models.extend(GeminiClient.EXTRA_MODELS)

            return models

    @staticmethod
    async def list_native_models(api_key):
        """
        获取原生Gemini模型列表
        """
        url = "https://generativelanguage.googleapis.com/v1beta/models?key={}".format(
            api_key
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
