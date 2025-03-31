# app/services/langflow_client.py
import httpx
import json
import logging
import platform
import asyncio
import io
import PyPDF2
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Generic
from pydantic import BaseModel
from enum import Enum
import sys
from dataclasses import dataclass
from core.config import settings

logger = logging.getLogger(__name__)

# Similar to the TypeScript error classes
class LangflowError(Exception):
    """Base exception for Langflow errors."""
    def __init__(self, message: str, response=None):
        self.message = message
        self.response = response
        super().__init__(message)

class LangflowRequestError(LangflowError):
    """Exception for request errors."""
    def __init__(self, message: str, original_error=None):
        self.original_error = original_error
        super().__init__(message)

@dataclass
class LangflowClientOptions:
    """Options for the Langflow client."""
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: Optional[float] = None
    default_headers: Optional[Dict[str, str]] = None
    http_client: Optional[httpx.AsyncClient] = None

@dataclass
class RequestOptions:
    """Options for requests to the Langflow API."""
    path: str
    method: str
    body: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[float] = None

class Tweaks(Dict[str, Any]):
    """Tweaks for flows."""
    pass

# Flow class (similar to flow.ts)
class Flow:
    """Represents a Langflow flow."""
    def __init__(self, client, flow_id: str, tweaks: Optional[Tweaks] = None):
        self.client = client
        self.flow_id = flow_id
        self.tweaks = tweaks or {}
    
    async def run(self, inputs: Optional[Dict[str, Any]] = None, stream: bool = False):
        """Run the flow with the given inputs."""
        payload = {
            "tweaks": self.tweaks,
        }
        
        if inputs:
            payload.update(inputs)
            
        headers = {"Content-Type": "application/json"}
        path = f"/run/{self.flow_id}"
        
        if stream:
            return await self.client.stream(RequestOptions(
                path=path,
                method="POST",
                body=payload,
                headers=headers
            ))
        else:
            return await self.client.request(RequestOptions(
                path=path,
                method="POST",
                body=payload,
                headers=headers
            ))

# Main client class
class LangflowClient:
    """Client for interacting with Langflow API."""
    
    def __init__(self, opts: Optional[LangflowClientOptions] = None):
        if opts is None:
            opts = LangflowClientOptions()
            
        self.base_url = settings.LANGFLOW_API_URL
        self.base_path = "/api/v1"
        self.api_key = opts.api_key or settings.LANGFLOW_API_KEY
        self.timeout = opts.timeout or settings.LANGFLOW_TIMEOUT or 60.0
        self.default_headers = opts.default_headers or {}
        
        # Set User-Agent if not provided
        if "User-Agent" not in self.default_headers:
            self.default_headers["User-Agent"] = self._get_user_agent()
            
        # HTTP client
        self.http_client = opts.http_client
    
    def _get_user_agent(self) -> str:
        """Get User-Agent string."""
        return f"langflow-python-client/1.0.0 ({platform.system()} {platform.machine()}) Python/{platform.python_version()}"
    
    def _set_api_key(self, api_key: str, headers: Dict[str, str]) -> None:
        """Set API key in headers."""
        headers["x-api-key"] = api_key
    
    def _set_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Set default headers."""
        # Combine default headers with provided headers
        combined_headers = {**self.default_headers}
        
        if headers:
            for key, value in headers.items():
                combined_headers[key] = value
                
        # Set API key if available
        if self.api_key:
            self._set_api_key(self.api_key, combined_headers)
            
        return combined_headers
    
    def flow(self, flow_id: str, tweaks: Optional[Tweaks] = None) -> Flow:
        """Create a Flow instance."""
        return Flow(self, flow_id, tweaks)
    
    async def request(self, options: RequestOptions) -> Any:
        """Make a request to the Langflow API."""
        path, method = options.path, options.method
        body = options.body
        headers = self._set_headers(options.headers or {})
        timeout = options.timeout or self.timeout
        
        url = f"{self.base_url}{self.base_path}{path}"
        
        async with (self.http_client or httpx.AsyncClient(timeout=timeout)) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=body,
                        headers=headers
                    )
                
                if not response.is_success:
                    raise LangflowError(
                        f"{response.status_code} - {response.reason_phrase}",
                        response
                    )
                
                return response.json()
                
            except httpx.TimeoutException as e:
                raise LangflowRequestError(f"Request timed out after {timeout}s", e)
            except httpx.RequestError as e:
                raise LangflowRequestError(f"Request failed: {str(e)}", e)
            except LangflowError:
                raise
            except Exception as e:
                raise LangflowRequestError(f"Unexpected error: {str(e)}", e)
    
    async def stream(self, options: RequestOptions) -> Any:
        """Stream a response from the Langflow API."""
        path, method = options.path, options.method
        body = options.body
        headers = self._set_headers(options.headers or {})
        timeout = options.timeout or self.timeout
        
        url = f"{self.base_url}{self.base_path}{path}"
        
        # Add streaming parameter
        if "?" in url:
            url += "&stream=true"
        else:
            url += "?stream=true"
        
        async with (self.http_client or httpx.AsyncClient(timeout=timeout)) as client:
            try:
                response = await client.stream(
                    method=method,
                    url=url,
                    json=body,
                    headers=headers
                )
                
                if not response.is_success:
                    error_text = ""
                    async for chunk in response.aiter_text():
                        error_text += chunk
                    
                    raise LangflowError(
                        f"{response.status_code} - {response.reason_phrase}: {error_text}",
                        response
                    )
                
                # Return async generator for streaming
                async def stream_response():
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to decode JSON from stream: {line}")
                
                return stream_response()
                
            except httpx.TimeoutException as e:
                raise LangflowRequestError(f"Stream request timed out after {timeout}s", e)
            except httpx.RequestError as e:
                raise LangflowRequestError(f"Stream request failed: {str(e)}", e)
            except LangflowError:
                raise
            except Exception as e:
                raise LangflowRequestError(f"Unexpected stream error: {str(e)}", e)
    
# Singleton instance 
langflow_client = LangflowClient(
    LangflowClientOptions(
        base_url=settings.LANGFLOW_API_URL,
        api_key=settings.LANGFLOW_API_KEY,
        timeout=settings.LANGFLOW_TIMEOUT
    )
)