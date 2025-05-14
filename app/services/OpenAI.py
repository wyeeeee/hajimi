import json
import os
import asyncio
from app.models.schemas import ChatCompletionRequest
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import httpx
import logging
import secrets
import string
from app.utils import format_log_message
import app.config.settings as settings

from app.utils.logging import log

def generate_secure_random_string(length):
    all_characters = string.ascii_letters + string.digits
    secure_random_string = ''.join(secrets.choice(all_characters) for _ in range(length))
    return secure_random_string

@dataclass
class GeneratedText:
    text: str
    finish_reason: Optional[str] = None

class OpenAIClient:

    AVAILABLE_MODELS = []
    EXTRA_MODELS = os.environ.get("EXTRA_MODELS", "").split(",")

    def __init__(self, api_key: str):
        self.api_key = api_key

    def filter_data_by_whitelist(data, allowed_keys):
        """
        根据白名单过滤字典。
        Args:
            data (dict): 原始的 Python 字典 (代表 JSON 对象)。
            allowed_keys (list or set): 包含允许保留的键名的列表或集合。
                                        使用集合 (set) 进行查找通常更快。
        Returns:
            dict: 只包含白名单中键的新字典。
        """
        # 使用集合(set)可以提高查找效率，特别是当白名单很大时
        allowed_keys_set = set(allowed_keys)
        # 使用字典推导式创建过滤后的新字典
        filtered_data = {key: value for key, value in data.items() if key in allowed_keys_set}
        return filtered_data
    
    # 真流式处理
    async def stream_chat(self, request: ChatCompletionRequest):
        whitelist = ["model", "messages", "temperature", "max_tokens","stream","tools","reasoning_effort","top_k","presence_penalty"]
        
        data = self.filter_data_by_whitelist(request, whitelist)

        
        if settings.search["search_mode"] and data.model.endswith("-search"):
            log('INFO', "开启联网搜索模式", extra={'key': self.api_key[:8], 'model':request.model})
            data.setdefault("tools", []).append({"google_search": {}})
                
        data.model = data.model.removesuffix("-search")
                
        # 真流式请求处理逻辑
        extra_log = {'key': self.api_key[:8], 'request_type': 'stream', 'model': request.model}
        log('INFO', "流式请求开始", extra=extra_log)

        
        url = f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, headers=headers, json=data, timeout=600) as response:
                buffer = b"" # 用于累积可能不完整的 JSON 数据
                try:
                    async for line in response.aiter_lines():
                        if not line.strip(): # 跳过空行 (SSE 消息分隔符)
                            continue
                        if line.startswith("data: "):
                            line = line[len("data: "):].strip() # 去除 "data: " 前缀
                        
                        # 检查是否是结束标志，如果是，结束循环
                        if line == "[DONE]":
                            break 
                        
                        buffer += line.encode('utf-8')
                        try:
                            # 尝试解析整个缓冲区
                            data = json.loads(buffer.decode('utf-8'))
                            # 解析成功，清空缓冲区
                            buffer = b"" 
                            
                            yield data

                        except json.JSONDecodeError:
                            # JSON 不完整，继续累积到 buffer
                            continue 
                        except Exception as e:
                            log('ERROR', f"流式处理期间发生错误", 
                                extra={'key': self.api_key[:8], 'request_type': 'stream', 'model': request.model})
                            raise e
                except Exception as e:
                    raise e
                finally:
                    log('info', "流式请求结束")
