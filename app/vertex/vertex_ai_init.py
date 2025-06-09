import json
import asyncio # Added for await
from google import genai
from app.vertex.credentials_manager import CredentialManager, parse_multiple_json_credentials
import app.vertex.config as app_config
from app.vertex.model_loader import refresh_models_config_cache # Import new model loader function
from app.utils.logging import vertex_log

# VERTEX_EXPRESS_MODELS list is now dynamically loaded via model_loader
# The constant VERTEX_EXPRESS_MODELS previously defined here is removed.
# Consumers should use get_vertex_express_models() from model_loader.

# 全局客户端，用于作为回退
global_fallback_client = None

def reset_global_fallback_client():
    """重置全局回退客户端"""
    global global_fallback_client
    global_fallback_client = None
    vertex_log('info', "全局回退客户端已重置")

async def init_vertex_ai(credential_manager=None) -> bool: # Made async
    """
    Initializes the credential manager with credentials from GOOGLE_CREDENTIALS_JSON (if provided)
    and verifies if any credentials (environment or file-based through the manager) are available.
    The CredentialManager itself handles loading file-based credentials upon its instantiation.
    This function primarily focuses on augmenting the manager with env var credentials.

    Returns True if any credentials seem available in the manager, False otherwise.
    """
    global global_fallback_client

    # 如果未传入credential_manager，则创建一个新的实例
    if credential_manager is None:
        vertex_log('info', "Creating new CredentialManager instance")
        credential_manager = CredentialManager()
    else:
        vertex_log('info', "Using provided CredentialManager instance")

    try:
        credentials_json_str = app_config.GOOGLE_CREDENTIALS_JSON
        env_creds_loaded_into_manager = False

        # 更严格的检查：确保不为None、不为空字符串、且去除空白后不为空
        if credentials_json_str and credentials_json_str.strip():
            vertex_log('info', "Found GOOGLE_CREDENTIALS_JSON environment variable. Attempting to load into CredentialManager.")
            try:
                # Attempt 1: Parse as multiple JSON objects
                json_objects = parse_multiple_json_credentials(credentials_json_str)
                if json_objects:
                    vertex_log('debug', f"Parsed {len(json_objects)} potential credential objects from GOOGLE_CREDENTIALS_JSON.")
                    success_count = credential_manager.load_credentials_from_json_list(json_objects)
                    if success_count > 0:
                        vertex_log('info', f"Successfully loaded {success_count} credentials from GOOGLE_CREDENTIALS_JSON into manager.")
                        env_creds_loaded_into_manager = True
                
                # Attempt 2: If multiple parsing/loading didn't add any, try parsing/loading as a single JSON object
                if not env_creds_loaded_into_manager:
                    vertex_log('debug', "Multi-JSON loading from GOOGLE_CREDENTIALS_JSON did not add to manager or was empty. Attempting single JSON load.")
                    try:
                        credentials_info = json.loads(credentials_json_str)
                        # Basic validation (CredentialManager's add_credential_from_json does more thorough validation)

                        if isinstance(credentials_info, dict) and \
                           all(field in credentials_info for field in ["type", "project_id", "private_key_id", "private_key", "client_email"]):
                            if credential_manager.add_credential_from_json(credentials_info):
                                vertex_log('info', "Successfully loaded single credential from GOOGLE_CREDENTIALS_JSON into manager.")
                                # env_creds_loaded_into_manager = True # Redundant, as this block is conditional on it being False
                            else:
                                vertex_log('warning', "Single JSON from GOOGLE_CREDENTIALS_JSON failed to load into manager via add_credential_from_json.")
                        else:
                             vertex_log('warning', "Single JSON from GOOGLE_CREDENTIALS_JSON is not a valid dict or missing required fields for basic check.")
                    except json.JSONDecodeError as single_json_err:
                        vertex_log('warning', f"GOOGLE_CREDENTIALS_JSON could not be parsed as a single JSON object: {single_json_err}.")
                    except Exception as single_load_err:
                        vertex_log('warning', f"Error trying to load single JSON from GOOGLE_CREDENTIALS_JSON into manager: {single_load_err}.")
            except Exception as e_json_env:
                # This catches errors from parse_multiple_json_credentials or load_credentials_from_json_list
                vertex_log('warning', f"Error processing GOOGLE_CREDENTIALS_JSON env var: {e_json_env}.")
        else:
            vertex_log('info', "GOOGLE_CREDENTIALS_JSON environment variable not found, is empty, or contains only whitespace.")

        # Attempt to pre-warm the model configuration cache
        vertex_log('info', "Attempting to pre-warm model configuration cache during startup...")
        models_loaded_successfully = await refresh_models_config_cache()
        if models_loaded_successfully:
            vertex_log('info', "Model configuration cache pre-warmed successfully.")
        else:
            vertex_log('warning', "Failed to pre-warm model configuration cache during startup. It will be loaded lazily on first request.")
            # We don't necessarily fail the entire init_vertex_ai if model list fetching fails,
            # as credential validation might still be important, and model list can be fetched later.

        # CredentialManager's __init__ calls load_credentials_list() for files.
        # refresh_credentials_list() re-scans files and combines with in-memory (already includes env creds if loaded above).
        # The return value of refresh_credentials_list indicates if total > 0
        if credential_manager.refresh_credentials_list():
            total_creds = credential_manager.get_total_credentials()
            vertex_log('info', f"Credential Manager reports {total_creds} credential(s) available (from files and/or GOOGLE_CREDENTIALS_JSON).")
            
            # Optional: Attempt to validate one of the credentials by creating a temporary client.
            # This adds a check that at least one credential is functional.
            vertex_log('info', "Attempting to validate a random credential by creating a temporary client...")
            temp_creds_val, temp_project_id_val = credential_manager.get_random_credentials()
            if temp_creds_val and temp_project_id_val:
                try:
                    _ = genai.Client(vertexai=True, credentials=temp_creds_val, project=temp_project_id_val, location="global")
                    vertex_log('info', f"Successfully validated a credential from Credential Manager (Project: {temp_project_id_val}). Initialization check passed.")
                    return True
                except Exception as e_val:
                    vertex_log('warning', f"Failed to validate a random credential from manager by creating a temp client: {e_val}. App may rely on non-validated credentials.")
                    # Still return True if credentials exist, as the app might still function with other valid credentials.
                    # The per-request client creation will be the ultimate test for a specific credential.
                    return True # Credentials exist, even if one failed validation here.
            elif total_creds > 0 : # Credentials listed but get_random_credentials returned None
                 vertex_log('warning', f"{total_creds} credentials reported by manager, but could not retrieve one for validation. Problems might occur.")
                 return True # Still, credentials are listed.
            else: # No creds from get_random_credentials and total_creds is 0
                 vertex_log('error', "No credentials available after attempting to load from all sources.")
                 return False # No credentials reported by manager and get_random_credentials gave none.
        else:
            vertex_log('error', "Credential Manager reports no available credentials after processing all sources.")
            return False

    except Exception as e:
        vertex_log('error', f"CRITICAL ERROR during Vertex AI credential setup: {e}")
        return False

async def get_vertex_ai_client(credential_manager=None):
    """
    Get a Vertex AI client using a credential from the manager.
    If no credential manager is passed, checks for a global fallback client.
    Returns None if no client could be created.
    """
    global global_fallback_client

    # If no credential manager, try to use global fallback client
    if credential_manager is None:
        if global_fallback_client is not None:
            vertex_log('info', "Using global fallback client")
            return global_fallback_client
        
        vertex_log('warning', "No credential manager provided and no global fallback client available")
        return None

    # Try to get a credential from the manager
    creds, project_id = credential_manager.get_random_credentials()
    if not creds or not project_id:
        vertex_log('error', "No valid credentials available in credential manager")
        return None

    try:
        # Create a client with the credentials
        vertex_log('info', f"Creating Vertex AI client with credentials for project: {project_id}")
        client = genai.Client(vertexai=True, credentials=creds, project=project_id, location="global")
        
        # If we don't have a global fallback client, set this as the fallback
        if global_fallback_client is None:
            vertex_log('info', "Setting new client as global fallback client")
            global_fallback_client = client
        
        return client
    except Exception as e:
        vertex_log('error', f"Error creating Vertex AI client: {e}")
        return None

async def re_init_vertex_ai(credential_manager=None) -> bool:
    """
    Re-initialize Vertex AI connections.
    Resets the global fallback client and reinitializes.
    """
    reset_global_fallback_client()
    return await init_vertex_ai(credential_manager)