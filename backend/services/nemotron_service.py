import os
import json
import logging
import asyncio
from typing import AsyncGenerator, Optional, List
import httpx
from pydantic import BaseModel

logger = logging.getLogger("zyricon-backend.nemotron")

class NemotronChatMessage(BaseModel):
    role: str
    content: str

class NemotronChatRequest(BaseModel):
    model: str = ""
    messages: List[NemotronChatMessage]
    system: str = ""
    temperature: float = 0.7
    top_p: float = 0.9

class NemotronService:
    def __init__(self):
        from backend.config.settings import settings; self.api_key = settings.NVIDIA_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.status = "online" if self.api_key else "offline"
        self.model = settings.NVIDIA_VOICE_MODEL

    async def get_status(self) -> dict:
        return {
            "status": self.status,
            "configured": bool(self.api_key),
            "model": self.model
        }

    async def chat_stream(self, req: NemotronChatRequest, cancel_event: asyncio.Event = None, request_id: str = "") -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield f"data: {json.dumps({'type': 'token', 'request_id': request_id, 'content': 'NVIDIA_API_KEY is not configured.'})}\n\n"
            yield f"data: {json.dumps({'type': 'end', 'request_id': request_id})}\n\n"
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        headers["Authorization"] = f"Bearer {self.api_key}"
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        if req.system:
            messages.insert(0, {"role": "system", "content": req.system})
            
        payload = {
            "model": req.model,
            "messages": messages,
            "temperature": req.temperature,
            "top_p": req.top_p,
            "stream": True,
            "max_tokens": 1024
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Nemotron error {response.status_code}: {error_text[:500]!r}")
                        yield f"data: {json.dumps({'type': 'error', 'request_id': request_id, 'content': f'NVIDIA API request failed (HTTP {response.status_code}).'})}\n\n"
                        yield f"data: {json.dumps({'type': 'end', 'request_id': request_id})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if cancel_event and cancel_event.is_set():
                            logger.info(f"Nemotron stream cancelled for {request_id}")
                            break
                        if line.startswith("data: "):
                            data_str = line.replace("data: ", "").strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield f"data: {json.dumps({'type': 'token', 'request_id': request_id, 'content': content})}\n\n"
                            except Exception:
                                pass
                            
                            await asyncio.sleep(0) # allow cancellation
                    
                    if not cancel_event or not cancel_event.is_set():
                        yield f"data: {json.dumps({'type': 'end', 'request_id': request_id})}\n\n"
                    
        except asyncio.CancelledError:
            logger.info(f"Nemotron task {request_id} was cancelled by asyncio.")
            raise
        except httpx.TimeoutException:
            yield f"data: {json.dumps({'type': 'token', 'request_id': request_id, 'content': 'The assistant took too long to respond.'})}\n\n"
            yield f"data: {json.dumps({'type': 'end', 'request_id': request_id})}\n\n"
        except httpx.RequestError as e:
            logger.error(f"Nemotron network error: {e}")
            yield f"data: {json.dumps({'type': 'token', 'request_id': request_id, 'content': 'Unable to reach NVIDIA services.'})}\n\n"
            yield f"data: {json.dumps({'type': 'end', 'request_id': request_id})}\n\n"
        except Exception as e:
            logger.error(f"Nemotron streaming error: {e}")
            yield f"data: {json.dumps({'type': 'token', 'request_id': request_id, 'content': 'Assistant returned an unexpected error.'})}\n\n"
            yield f"data: {json.dumps({'type': 'end', 'request_id': request_id})}\n\n"

nemotron_service = NemotronService()
