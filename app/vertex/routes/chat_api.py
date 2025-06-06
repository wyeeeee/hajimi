import asyncio
import json # Needed for error streaming
import random
import time
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any

from app.utils.logging import vertex_log
from app.config import settings

# Google and OpenAI specific imports
from google.genai import types
from google import genai
import openai
from app.vertex.credentials_manager import _refresh_auth, CredentialManager

# Local module imports
from app.vertex.models import OpenAIRequest, OpenAIMessage
from app.vertex.auth import get_api_key
import app.vertex.config as app_config
from app.vertex.model_loader import get_vertex_models, get_vertex_express_models
from app.vertex.message_processing import (
    create_gemini_prompt,
    create_encrypted_gemini_prompt,
    create_encrypted_full_gemini_prompt,
    parse_gemini_response_for_reasoning_and_content
)
from app.vertex.api_helpers import (
    create_generation_config,
    create_openai_error_response,
    execute_gemini_call
)

router = APIRouter()

@router.post("/v1/chat/completions")
async def chat_completions(fastapi_request: Request, request: OpenAIRequest, api_key: str = Depends(get_api_key)):
    try:
        # 获取credential_manager，如果不存在则创建一个新的
        try:
            credential_manager_instance = fastapi_request.app.state.credential_manager
            vertex_log('info', "Using existing credential manager from app state")
        except AttributeError:
            # 如果app.state中没有credential_manager，则创建一个新的
            vertex_log('warning', "No credential_manager found in app.state, creating a new one")
            credential_manager_instance = CredentialManager()
        
        OPENAI_DIRECT_SUFFIX = "-openai"
        EXPERIMENTAL_MARKER = "-exp-"
        PAY_PREFIX = "[PAY]"
        EXPRESS_PREFIX = "[EXPRESS] " # Note the space for easier stripping
        
        # Model validation based on a predefined list has been removed as per user request.
        # The application will now attempt to use any provided model string.
        # We still need to fetch vertex_express_model_ids for the Express Mode logic.
        # vertex_express_model_ids = await get_vertex_express_models() # We'll use the prefix now

        # Updated logic for is_openai_direct_model
        is_openai_direct_model = False
        if request.model.endswith(OPENAI_DIRECT_SUFFIX):
            temp_name_for_marker_check = request.model[:-len(OPENAI_DIRECT_SUFFIX)]
            if temp_name_for_marker_check.startswith(PAY_PREFIX):
                is_openai_direct_model = True
            elif EXPERIMENTAL_MARKER in temp_name_for_marker_check:
                is_openai_direct_model = True
        is_auto_model = request.model.endswith("-auto")
        is_grounded_search = request.model.endswith("-search")
        is_encrypted_model = request.model.endswith("-encrypt")
        is_encrypted_full_model = request.model.endswith("-encrypt-full")
        is_nothinking_model = request.model.endswith("-nothinking")
        is_max_thinking_model = request.model.endswith("-max")
        base_model_name = request.model # Start with the full model name

        # Determine base_model_name by stripping known prefixes and suffixes
        # Order of stripping: Prefixes first, then suffixes.
        
        is_express_model_request = False
        if base_model_name.startswith(EXPRESS_PREFIX):
            is_express_model_request = True
            base_model_name = base_model_name[len(EXPRESS_PREFIX):]

        if base_model_name.startswith(PAY_PREFIX):
            base_model_name = base_model_name[len(PAY_PREFIX):]

        # Suffix stripping (applied to the name after prefix removal)
        # This order matters if a model could have multiple (e.g. -encrypt-auto, though not currently a pattern)
        if is_openai_direct_model: # This check is based on request.model, so it's fine here
            # If it was an OpenAI direct model, its base name is request.model minus suffix.
            # We need to ensure PAY_PREFIX or EXPRESS_PREFIX are also stripped if they were part of the original.
            temp_base_for_openai = request.model[:-len(OPENAI_DIRECT_SUFFIX)]
            if temp_base_for_openai.startswith(EXPRESS_PREFIX):
                temp_base_for_openai = temp_base_for_openai[len(EXPRESS_PREFIX):]
            if temp_base_for_openai.startswith(PAY_PREFIX):
                temp_base_for_openai = temp_base_for_openai[len(PAY_PREFIX):]
            base_model_name = temp_base_for_openai # Assign the fully stripped name
        elif is_auto_model: base_model_name = base_model_name[:-len("-auto")]
        elif is_grounded_search: base_model_name = base_model_name[:-len("-search")]
        elif is_encrypted_full_model: base_model_name = base_model_name[:-len("-encrypt-full")] # Must be before -encrypt
        elif is_encrypted_model: base_model_name = base_model_name[:-len("-encrypt")]
        elif is_nothinking_model:
            base_model_name = base_model_name[:-len("-nothinking")]
        elif is_max_thinking_model:
            base_model_name = base_model_name[:-len("-max")]
        
        # Define supported models for these specific variants
        supported_flash_variants = [
            "gemini-2.5-flash-preview-04-17",
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-pro-preview-06-05"
        ]
        supported_flash_variants_str = "' or '".join(supported_flash_variants)

        # Specific model variant checks (if any remain exclusive and not covered dynamically)
        if is_nothinking_model and base_model_name not in supported_flash_variants:
            return JSONResponse(status_code=400, content=create_openai_error_response(400, f"Model '{request.model}' (-nothinking) is only supported for '{supported_flash_variants_str}'.", "invalid_request_error"))
        if is_max_thinking_model and base_model_name not in supported_flash_variants:
            return JSONResponse(status_code=400, content=create_openai_error_response(400, f"Model '{request.model}' (-max) is only supported for '{supported_flash_variants_str}'.", "invalid_request_error"))

        generation_config = create_generation_config(request)

        client_to_use = None
        
        # 优先从settings获取配置，如果没有则使用app_config中的配置
        express_api_keys_list = []
        if hasattr(settings, 'VERTEX_EXPRESS_API_KEY') and settings.VERTEX_EXPRESS_API_KEY:
            express_api_keys_list = [key.strip() for key in settings.VERTEX_EXPRESS_API_KEY.split(',') if key.strip()]
            vertex_log('info', f"Using {len(express_api_keys_list)} Express API keys from settings")
        # 如果settings中没有配置，则使用app_config中的配置
        if not express_api_keys_list and app_config.VERTEX_EXPRESS_API_KEY_VAL:
            express_api_keys_list = app_config.VERTEX_EXPRESS_API_KEY_VAL
            vertex_log('info', f"Using {len(express_api_keys_list)} Express API keys from app_config")

        # This client initialization logic is for Gemini models.
        # OpenAI Direct models have their own client setup and will return before this.
        if is_openai_direct_model:
            # OpenAI Direct logic is self-contained and will return.
            # If it doesn't return, it means we proceed to Gemini logic, which shouldn't happen
            # if is_openai_direct_model is true. The main if/elif/else for model types handles this.
            pass
        elif is_express_model_request:
            if not express_api_keys_list:
                error_msg = f"Model '{request.model}' is an Express model and requires an Express API key, but none are configured."
                vertex_log('error', error_msg)
                return JSONResponse(status_code=401, content=create_openai_error_response(401, error_msg, "authentication_error"))

            vertex_log('info', f"INFO: Attempting Vertex Express Mode for model request: {request.model} (base: {base_model_name})")
            indexed_keys = list(enumerate(express_api_keys_list))
            random.shuffle(indexed_keys)
            
            for original_idx, key_val in indexed_keys:
                try:
                    client_to_use = genai.Client(vertexai=True, api_key=key_val)
                    vertex_log('info', f"INFO: Using Vertex Express Mode for model {request.model} (base: {base_model_name}) with API key (original index: {original_idx}).")
                    break # Successfully initialized client
                except Exception as e:
                    vertex_log('warning', f"WARNING: Vertex Express Mode client init failed for API key (original index: {original_idx}) for model {request.model}: {e}. Trying next key.")
                    client_to_use = None # Ensure client_to_use is None for this attempt

            if client_to_use is None: # All configured Express keys failed
                error_msg = f"All configured Express API keys failed to initialize for model '{request.model}'."
                vertex_log('error', error_msg)
                return JSONResponse(status_code=500, content=create_openai_error_response(500, error_msg, "server_error"))
        
        else: # Not an Express model request, therefore an SA credential model request for Gemini
            vertex_log('info', f"INFO: Model '{request.model}' is an SA credential request for Gemini. Attempting SA credentials.")
            rotated_credentials, rotated_project_id = credential_manager_instance.get_random_credentials()
            
            if rotated_credentials and rotated_project_id:
                try:
                    client_to_use = genai.Client(vertexai=True, credentials=rotated_credentials, project=rotated_project_id, location="global")
                    vertex_log('info', f"INFO: Using SA credential for Gemini model {request.model} (project: {rotated_project_id})")
                except Exception as e:
                    client_to_use = None # Ensure it's None on failure
                    error_msg = f"SA credential client initialization failed for Gemini model '{request.model}': {e}."
                    vertex_log('error', error_msg)
                    return JSONResponse(status_code=500, content=create_openai_error_response(500, error_msg, "server_error"))
            else: # No SA credentials available for an SA model request
                error_msg = f"Model '{request.model}' requires SA credentials for Gemini, but none are available or loaded."
                vertex_log('error', error_msg)
                return JSONResponse(status_code=401, content=create_openai_error_response(401, error_msg, "authentication_error"))

        # If we reach here and client_to_use is still None, it means it's an OpenAI Direct Model,
        # which handles its own client and responses.
        # For Gemini models (Express or SA), client_to_use must be set, or an error returned above.
        if not is_openai_direct_model and client_to_use is None:
             # This case should ideally not be reached if the logic above is correct,
             # as each path (Express/SA for Gemini) should either set client_to_use or return an error.
             # This is a safeguard.
            vertex_log('critical', f"CRITICAL ERROR: Client for Gemini model '{request.model}' was not initialized, and no specific error was returned. This indicates a logic flaw.")
            return JSONResponse(status_code=500, content=create_openai_error_response(500, "Critical internal server error: Gemini client not initialized.", "server_error"))

        encryption_instructions_placeholder = ["// Protocol Instructions Placeholder //"] # Actual instructions are in message_processing
        if is_openai_direct_model:
            vertex_log('info', f"INFO: Using OpenAI Direct Path for model: {request.model}")
            # This mode exclusively uses rotated credentials, not express keys.
            rotated_credentials, rotated_project_id = credential_manager_instance.get_random_credentials()

            if not rotated_credentials or not rotated_project_id:
                error_msg = "OpenAI Direct Mode requires GCP credentials, but none were available or loaded successfully."
                vertex_log('error', error_msg)
                return JSONResponse(status_code=500, content=create_openai_error_response(500, error_msg, "server_error"))

            vertex_log('info', f"INFO: [OpenAI Direct Path] Using credentials for project: {rotated_project_id}")
            gcp_token = _refresh_auth(rotated_credentials)

            if not gcp_token:
                error_msg = f"Failed to obtain valid GCP token for OpenAI client (Source: Credential Manager, Project: {rotated_project_id})."
                vertex_log('error', error_msg)
                return JSONResponse(status_code=500, content=create_openai_error_response(500, error_msg, "server_error"))

            PROJECT_ID = rotated_project_id
            LOCATION = "global" # Fixed as per user confirmation
            VERTEX_AI_OPENAI_ENDPOINT_URL = (
                f"https://aiplatform.googleapis.com/v1beta1/"
                f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/openapi"
            )
            # base_model_name is already extracted (e.g., "gemini-1.5-pro-exp-v1")
            UNDERLYING_MODEL_ID = f"google/{base_model_name}"

            openai_client = openai.AsyncOpenAI(
                base_url=VERTEX_AI_OPENAI_ENDPOINT_URL,
                api_key=gcp_token, # OAuth token
            )

            openai_safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
                {"category": 'HARM_CATEGORY_CIVIC_INTEGRITY', "threshold": 'OFF'}
            ]

            openai_params = {
                "model": UNDERLYING_MODEL_ID,
                "messages": [msg.model_dump(exclude_unset=True) for msg in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "stream": request.stream,
                "stop": request.stop,
                "seed": request.seed,
                "n": request.n,
            }
            openai_params = {k: v for k, v in openai_params.items() if v is not None}

            openai_extra_body = {
                'google': {
                    'safety_settings': openai_safety_settings
                }
            }

            if request.stream:
                # 每次调用时直接从settings获取最新的FAKE_STREAMING值
                fake_streaming_enabled = False
                if hasattr(settings, 'FAKE_STREAMING'):
                    fake_streaming_enabled = settings.FAKE_STREAMING
                else:
                    fake_streaming_enabled = app_config.FAKE_STREAMING_ENABLED
                
                vertex_log('info', f"DEBUG: FAKE_STREAMING setting is {fake_streaming_enabled} for OpenAI model {request.model}")
                
                if fake_streaming_enabled:
                    vertex_log('info', f"INFO: OpenAI Fake Streaming (SSE Simulation) ENABLED for model '{request.model}'.")
                    # openai_params already has "stream": True from initial setup,
                    # but openai_fake_stream_generator will make a stream=False call internally.
                    # Call the now async generator
                    return StreamingResponse(
                        openai_fake_stream_generator(
                            openai_client=openai_client,
                            openai_params=openai_params,
                            openai_extra_body=openai_extra_body,
                            request_obj=request,
                            is_auto_attempt=False,
                            # --- New parameters for tokenizer and reasoning split ---
                            gcp_credentials=rotated_credentials,
                            gcp_project_id=PROJECT_ID, # This is rotated_project_id
                            gcp_location=LOCATION,     # This is "global"
                            base_model_id_for_tokenizer=base_model_name # Stripped model ID for tokenizer
                        ),
                        media_type="text/event-stream"
                    )
                else: # Regular OpenAI streaming
                    vertex_log('info', f"INFO: OpenAI True Streaming ENABLED for model '{request.model}'.")
                    async def openai_true_stream_generator(): # Renamed to avoid conflict
                        try:
                            # Ensure stream=True is explicitly passed for real streaming
                            openai_params_for_true_stream = {**openai_params, "stream": True}
                            stream_response = await openai_client.chat.completions.create(
                                **openai_params_for_true_stream,
                                extra_body=openai_extra_body
                            )
                            async for chunk in stream_response:
                                try:
                                    chunk_as_dict = chunk.model_dump(exclude_unset=True, exclude_none=True)
                                    
                                    choices = chunk_as_dict.get('choices')
                                    if choices and isinstance(choices, list) and len(choices) > 0:
                                        delta = choices[0].get('delta')
                                        if delta and isinstance(delta, dict):
                                            extra_content = delta.get('extra_content')
                                            if isinstance(extra_content, dict):
                                                google_content = extra_content.get('google')
                                                if isinstance(google_content, dict) and google_content.get('thought') is True:
                                                    reasoning_text = delta.get('content')
                                                    if reasoning_text is not None:
                                                        delta['reasoning_content'] = reasoning_text
                                                    if 'content' in delta: del delta['content']
                                                    if 'extra_content' in delta: del delta['extra_content']
                                    
                                    # vertex_log('debug', f"DEBUG OpenAI Stream Chunk: {chunk_as_dict}") # Potential verbose log
                                    yield f"data: {json.dumps(chunk_as_dict)}\n\n"

                                except Exception as chunk_processing_error:
                                    error_msg_chunk = f"Error processing/serializing OpenAI chunk for {request.model}: {str(chunk_processing_error)}. Chunk: {str(chunk)[:200]}"
                                    vertex_log('error', error_msg_chunk)
                                    if len(error_msg_chunk) > 1024: error_msg_chunk = error_msg_chunk[:1024] + "..."
                                    error_response_chunk = create_openai_error_response(500, error_msg_chunk, "server_error")
                                    json_payload_for_chunk_error = json.dumps(error_response_chunk)
                                    yield f"data: {json_payload_for_chunk_error}\n\n"
                                    yield "data: [DONE]\n\n"
                                    return
                            yield "data: [DONE]\n\n"
                        except Exception as stream_error:
                            original_error_message = str(stream_error)
                            if len(original_error_message) > 1024: original_error_message = original_error_message[:1024] + "..."
                            error_msg_stream = f"Error during OpenAI client true streaming for {request.model}: {original_error_message}"
                            vertex_log('error', error_msg_stream)
                            error_response_content = create_openai_error_response(500, error_msg_stream, "server_error")
                            json_payload_for_stream_error = json.dumps(error_response_content)
                            yield f"data: {json_payload_for_stream_error}\n\n"
                            yield "data: [DONE]\n\n"
                    return StreamingResponse(openai_true_stream_generator(), media_type="text/event-stream")
            else: # Not streaming (is_openai_direct_model and not request.stream)
                try:
                    # Ensure stream=False is explicitly passed for non-streaming
                    openai_params_for_non_stream = {**openai_params, "stream": False}
                    response = await openai_client.chat.completions.create(
                        **openai_params_for_non_stream,
                        # Removed redundant **openai_params spread
                        extra_body=openai_extra_body
                    )
                    response_dict = response.model_dump(exclude_unset=True, exclude_none=True)
                    
                    try:
                        # Extract reasoning directly from the response
                        choices = response_dict.get('choices')
                        if choices and isinstance(choices, list) and len(choices) > 0:
                            message_dict = choices[0].get('message')
                            if message_dict and isinstance(message_dict, dict):
                                # Always remove extra_content from the message if it exists
                                if 'extra_content' in message_dict:
                                    extra_content = message_dict.get('extra_content', {})
                                    google_content = extra_content.get('google', {})
                                    
                                    # If this is a thought, move content to reasoning_content
                                    if google_content and google_content.get('thought') is True:
                                        message_dict['reasoning_content'] = message_dict.get('content', '')
                                        message_dict['content'] = ''
                                    
                                    # Always remove extra_content
                                    del message_dict['extra_content']
                                    vertex_log('debug', "DEBUG: Processed 'extra_content' from response message.")
                                    
                    except Exception as e_reasoning_processing:
                        vertex_log('warning', f"WARNING: Error during non-streaming reasoning processing for model {request.model} due to: {e_reasoning_processing}.")
                        
                    return JSONResponse(content=response_dict)
                except Exception as generate_error:
                    error_msg_generate = f"Error calling OpenAI client for {request.model}: {str(generate_error)}"
                    vertex_log('error', error_msg_generate)
                    error_response = create_openai_error_response(500, error_msg_generate, "server_error")
                    return JSONResponse(status_code=500, content=error_response)
        elif is_auto_model:
            vertex_log('info', f"Processing auto model: {request.model}")
            attempts = [
                {"name": "base", "model": base_model_name, "prompt_func": create_gemini_prompt, "config_modifier": lambda c: c},
                {"name": "encrypt", "model": base_model_name, "prompt_func": create_encrypted_gemini_prompt, "config_modifier": lambda c: {**c, "system_instruction": encryption_instructions_placeholder}},
                {"name": "old_format", "model": base_model_name, "prompt_func": create_encrypted_full_gemini_prompt, "config_modifier": lambda c: c}                  
            ]
            last_err = None
            for attempt in attempts:
                vertex_log('info', f"Auto-mode attempting: '{attempt['name']}' for model {attempt['model']}")
                current_gen_config = attempt["config_modifier"](generation_config.copy())
                try:
                    # Pass is_auto_attempt=True for auto-mode calls
                    return await execute_gemini_call(client_to_use, attempt["model"], attempt["prompt_func"], current_gen_config, request, is_auto_attempt=True)
                except Exception as e_auto:
                    last_err = e_auto
                    vertex_log('info', f"Auto-attempt '{attempt['name']}' for model {attempt['model']} failed: {e_auto}")
                    await asyncio.sleep(1)
            
            vertex_log('info', f"All auto attempts failed. Last error: {last_err}")
            err_msg = f"All auto-mode attempts failed for model {request.model}. Last error: {str(last_err)}"
            if not request.stream and last_err:
                 return JSONResponse(status_code=500, content=create_openai_error_response(500, err_msg, "server_error"))
            elif request.stream: 
                # This is the final error handling for auto-mode if all attempts fail AND it was a streaming request
                async def final_auto_error_stream():
                    err_content = create_openai_error_response(500, err_msg, "server_error")
                    json_payload_final_auto_error = json.dumps(err_content)
                    # Log the final error being sent to client after all auto-retries failed
                    vertex_log('debug', f"DEBUG: Auto-mode all attempts failed. Yielding final error JSON: {json_payload_final_auto_error}")
                    yield f"data: {json_payload_final_auto_error}\n\n"
                    yield "data: [DONE]\n\n"
                return StreamingResponse(final_auto_error_stream(), media_type="text/event-stream")
            return JSONResponse(status_code=500, content=create_openai_error_response(500, "All auto-mode attempts failed without specific error.", "server_error"))

        else: # Not an auto model
            current_prompt_func = create_gemini_prompt
            # Determine the actual model string to call the API with (e.g., "gemini-1.5-pro-search")
            api_model_string = request.model 

            if is_grounded_search:
                search_tool = types.Tool(google_search=types.GoogleSearch())
                generation_config["tools"] = [search_tool]
            elif is_encrypted_model:
                generation_config["system_instruction"] = encryption_instructions_placeholder
                current_prompt_func = create_encrypted_gemini_prompt
            elif is_encrypted_full_model:
                generation_config["system_instruction"] = encryption_instructions_placeholder
                current_prompt_func = create_encrypted_full_gemini_prompt
            elif is_nothinking_model:
                # 为gemini-2.5-pro-preview-06-05设置特定的thinking_budget
                if base_model_name == "gemini-2.5-pro-preview-06-05":
                    generation_config["thinking_config"] = {"thinking_budget": 128}
                else:
                    generation_config["thinking_config"] = {"thinking_budget": 0}
            elif is_max_thinking_model:
                # 为gemini-2.5-pro-preview-06-05设置特定的thinking_budget
                if base_model_name == "gemini-2.5-pro-preview-06-05":
                    generation_config["thinking_config"] = {"thinking_budget": 32768}
                else:
                    generation_config["thinking_config"] = {"thinking_budget": 24576}
            
            # For non-auto models, the 'base_model_name' might have suffix stripped.
            # We should use the original 'request.model' for API call if it's a suffixed one,
            # or 'base_model_name' if it's truly a base model without suffixes.
            # The current logic uses 'base_model_name' for the API call in the 'else' block.
            # This means if `request.model` was "gemini-1.5-pro-search", `base_model_name` becomes "gemini-1.5-pro"
            # but the API call might need the full "gemini-1.5-pro-search".
            # Let's use `request.model` for the API call here, and `base_model_name` for checks like Express eligibility.
            # For non-auto mode, is_auto_attempt defaults to False in execute_gemini_call
            return await execute_gemini_call(client_to_use, base_model_name, current_prompt_func, generation_config, request)

    except Exception as e:
        error_msg = f"Unexpected error in chat_completions endpoint: {str(e)}"
        vertex_log('error', error_msg)
        return JSONResponse(status_code=500, content=create_openai_error_response(500, error_msg, "server_error"))

async def _base_fake_stream_engine(
    api_call_task_creator,
    extract_text_from_response_func,
    is_valid_response_func,
    response_id,
    sse_model_name,
    keep_alive_interval_seconds=0,
    is_auto_attempt=False,
    reasoning_text_to_yield="",
    actual_content_text_to_yield=""
):
    """Base engine for fake streaming that handles common logic for both Gemini and OpenAI."""
    try:
        # Wait for the API call to complete
        api_response = await api_call_task_creator()
        
        # Validate the response
        if not is_valid_response_func(api_response):
            error_msg = f"Invalid response structure from API for model {sse_model_name}"
            vertex_log('error', error_msg)
            err_resp = create_openai_error_response(500, error_msg, "server_error")
            yield f"data: {json.dumps(err_resp)}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # Get the full text from the response
        full_text = ""
        if reasoning_text_to_yield or actual_content_text_to_yield:
            # If we already have separated reasoning and content, use them
            if reasoning_text_to_yield:
                # First yield the reasoning content in a separate chunk
                reasoning_chunk = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": sse_model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"reasoning_content": reasoning_text_to_yield},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(reasoning_chunk)}\n\n"
                
            # Then use the actual content for streaming
            full_text = actual_content_text_to_yield
        else:
            # Otherwise extract the full text from the response
            full_text = extract_text_from_response_func(api_response)
        
        if not full_text:
            # If there's no text to stream, just send an empty delta and finish
            empty_chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": sse_model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content": ""},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(empty_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # Simulate streaming by yielding chunks of the full text
        chunk_size = app_config.FAKE_STREAMING_CHUNK_SIZE
        delay_per_chunk = app_config.FAKE_STREAMING_DELAY_PER_CHUNK
        
        # Initial chunk with role
        initial_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": sse_model_name,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(initial_chunk)}\n\n"
        
        # Stream the content in chunks
        for i in range(0, len(full_text), chunk_size):
            chunk_text = full_text[i:i+chunk_size]
            content_chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": sse_model_name,
                "choices": [{
                    "index": 0,
                    "delta": {"content": chunk_text},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(content_chunk)}\n\n"
            
            if i + chunk_size < len(full_text) and delay_per_chunk > 0:
                await asyncio.sleep(delay_per_chunk)
        
        # Final chunk to indicate completion
        final_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": sse_model_name,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_msg = f"Error in _base_fake_stream_engine for model {sse_model_name}: {str(e)}"
        vertex_log('error', error_msg)
        if not is_auto_attempt:  # Only yield error for non-auto attempts
            err_resp = create_openai_error_response(500, error_msg, "server_error")
            yield f"data: {json.dumps(err_resp)}\n\n"
            yield "data: [DONE]\n\n"

async def openai_fake_stream_generator(
    openai_client: openai.AsyncOpenAI,
    openai_params: Dict[str, Any], 
    openai_extra_body: Dict[str, Any],
    request_obj: OpenAIRequest,
    is_auto_attempt: bool,
    gcp_credentials: Any, 
    gcp_project_id: str, 
    gcp_location: str,
    base_model_id_for_tokenizer: str 
):
    api_model_name = openai_params.get("model", "unknown-openai-model")
    vertex_log('info', f"FAKE STREAMING (OpenAI): Prep for '{request_obj.model}' (API model: '{api_model_name}')")
    response_id = f"chatcmpl-{int(time.time())}"
    
    async def _openai_api_call_wrapper():
        params_for_non_stream_call = openai_params.copy()
        params_for_non_stream_call['stream'] = False
        
        _api_call_task = asyncio.create_task(
            openai_client.chat.completions.create(**params_for_non_stream_call, extra_body=openai_extra_body)
        )
        raw_response = await _api_call_task
        
        # Extract reasoning and content directly from the response
        full_content_from_api = ""
        reasoning_text = ""
        
        if raw_response.choices and raw_response.choices[0].message:
            # Check for extra_content with google.thought
            message = raw_response.choices[0].message
            if hasattr(message, 'extra_content') and message.extra_content:
                google_content = message.extra_content.get('google', {})
                if google_content and google_content.get('thought') is True:
                    reasoning_text = message.content
                    full_content_from_api = ""  # Clear content as it's reasoning
                else:
                    full_content_from_api = message.content
            else:
                full_content_from_api = message.content
        
        return raw_response, reasoning_text, full_content_from_api

    temp_task_for_keepalive_check = asyncio.create_task(_openai_api_call_wrapper())
    outer_keep_alive_interval = app_config.FAKE_STREAMING_INTERVAL_SECONDS
    if outer_keep_alive_interval > 0:
        while not temp_task_for_keepalive_check.done():
            keep_alive_data = {"id": "chatcmpl-keepalive", "object": "chat.completion.chunk", "created": int(time.time()), "model": request_obj.model, "choices": [{"delta": {"content": ""}, "index": 0, "finish_reason": None}]}
            yield f"data: {json.dumps(keep_alive_data)}\n\n"
            await asyncio.sleep(outer_keep_alive_interval)

    try:
        full_api_response, separated_reasoning_text, separated_actual_content_text = await temp_task_for_keepalive_check
        def _extract_openai_full_text(response: Any) -> str: 
            if response.choices and response.choices[0].message and response.choices[0].message.content is not None:
                return response.choices[0].message.content
            return ""
        def _is_openai_response_valid(response: Any) -> bool:
            return bool(response.choices and response.choices[0].message is not None)

        async for chunk in _base_fake_stream_engine(
            api_call_task_creator=lambda: asyncio.create_task(asyncio.sleep(0, result=full_api_response)), 
            extract_text_from_response_func=_extract_openai_full_text, 
            is_valid_response_func=_is_openai_response_valid,
            response_id=response_id,
            sse_model_name=request_obj.model,
            keep_alive_interval_seconds=0, 
            is_auto_attempt=is_auto_attempt,
            reasoning_text_to_yield=separated_reasoning_text,
            actual_content_text_to_yield=separated_actual_content_text
        ):
            yield chunk
            
    except Exception as e_outer: 
        err_msg_detail = f"Error in openai_fake_stream_generator outer (model: '{request_obj.model}'): {type(e_outer).__name__} - {str(e_outer)}"
        vertex_log('error', err_msg_detail)
        sse_err_msg_display = str(e_outer)
        if len(sse_err_msg_display) > 512: sse_err_msg_display = sse_err_msg_display[:512] + "..."
        err_resp_sse = create_openai_error_response(500, sse_err_msg_display, "server_error")
        json_payload_error = json.dumps(err_resp_sse)
        if not is_auto_attempt:
            yield f"data: {json_payload_error}\n\n"
            yield "data: [DONE]\n\n"
