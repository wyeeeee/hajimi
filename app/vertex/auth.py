from fastapi import HTTPException, Header, Depends
from fastapi.security import APIKeyHeader
from typing import Optional
from app.config import settings
import app.vertex.config as config
import os
import json
from app.utils.logging import vertex_log

# API Key security scheme
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

# Function to validate API key
def validate_api_key(api_key_to_validate: str) -> bool:

    return True

# Dependency for API key validation
async def get_api_key(authorization: Optional[str] = Header(None)):
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Please include 'Authorization: Bearer YOUR_API_KEY' header."
        )
    
    # Check if the header starts with "Bearer "
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format. Use 'Authorization: Bearer YOUR_API_KEY'"
        )
    
    # Extract the API key
    api_key = authorization.replace("Bearer ", "")
    
    # Validate the API key
    if not validate_api_key(api_key): # Call local validate_api_key
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return api_key

def validate_settings():
    """Validate settings for Vertex API access."""
    
    # 检查API key
    api_key = None
    if hasattr(settings, 'API_KEY') and settings.API_KEY:
        api_key = settings.API_KEY
    else:
        api_key = config.API_KEY
    
    if not api_key:
        vertex_log('warning', "API key is not set. Some functionality may be limited.")
    
    # 检查Google credentials JSON
    google_credentials_json = None
    if hasattr(settings, 'GOOGLE_CREDENTIALS_JSON') and settings.GOOGLE_CREDENTIALS_JSON:
        google_credentials_json = settings.GOOGLE_CREDENTIALS_JSON
    else:
        google_credentials_json = config.GOOGLE_CREDENTIALS_JSON
    
    if google_credentials_json:
        try:
            # 尝试解析JSON确保其有效
            json.loads(google_credentials_json)
            vertex_log('info', "Google Credentials JSON is valid")
        except json.JSONDecodeError:
            vertex_log('error', "Google Credentials JSON is not valid JSON. Please check the format.")
            return False
    
    # 检查project ID
    project_id = None
    if hasattr(settings, 'PROJECT_ID') and settings.PROJECT_ID:
        project_id = settings.PROJECT_ID
    else:
        project_id = config.PROJECT_ID
    
    if not project_id:
        vertex_log('warning', "Vertex AI Project ID is not set. Required for non-API key methods.")
    
    # 检查location
    location = None
    if hasattr(settings, 'LOCATION') and settings.LOCATION:
        location = settings.LOCATION
    else:
        location = config.LOCATION
    
    if not location:
        vertex_log('warning', "Vertex AI Location is not set, using default: us-central1")
    
    # 验证凭证目录
    credentials_dir = None
    if hasattr(settings, 'CREDENTIALS_DIR') and settings.CREDENTIALS_DIR:
        credentials_dir = settings.CREDENTIALS_DIR
    else:
        credentials_dir = config.CREDENTIALS_DIR
    
    if not os.path.exists(credentials_dir):
        try:
            os.makedirs(credentials_dir, exist_ok=True)
            vertex_log('info', f"Created credentials directory at: {credentials_dir}")
        except Exception as e:
            vertex_log('error', f"Failed to create credentials directory: {e}")
            return False
    
    return True