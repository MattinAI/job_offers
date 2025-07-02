# app/services/langflow_client.py
import logging
from langflow_client import LangflowClient

from core.config import settings

logger = logging.getLogger(__name__)

langflow_client = LangflowClient(
    base_url=settings.LANGFLOW_API_URL,
    api_key=settings.LANGFLOW_API_KEY,  
    timeout=settings.LANGFLOW_TIMEOUT
)