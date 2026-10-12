"""
NVIDIA VoiceChat Service - Optimized for Low Latency
Implements connection pooling and latency tracking
"""
import os
import json
import base64
import logging
import asyncio
import time
from typing import AsyncGenerator, Optional
import httpx
from pydantic import BaseModel

from backend.config.settings import settings
from backend.services.request_manager import request_manager
from backend.services.latency_profiler import latency_profiler

logger = logging.getLogger("zyricon-backend.nvidia_voicechat")

class NvidiaVoiceChatService:
    def __init__(self):
        self.api_key = settings.NVIDIA_API_KEY
        self.model = settings.NVIDIA_VOICE_MODEL
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        
        # Connection pool: Keep a persistent client to reuse connections
        self.client: Optional[httpx.AsyncClient] = None
        self.client_lock = asyncio.Lock()

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create a reusable HTTP client with connection pooling"""
        if self.client is None:
            async with self.client_lock:
                if self.client is None:
                    # Reuse connections, longer timeout for NVIDIA API
                    limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
                    self.client = httpx.AsyncClient(
                        timeout=60.0,
                        limits=limits,
                        http2=True  # Use HTTP/2 for multiplexing
                    )
        return self.client

    async def close_client(self):
        """Close the persistent client"""
        if self.client:
            async with self.client_lock:
                if self.client:
                    await self.client.aclose()
                    self.client = None

    async def get_status(self) -> dict:
        return {
            "status": "online" if self.api_key else "offline",
            "model": self.model,
            "configured": bool(self.api_key)
        }

    async def process_voice_chat(
        self, 
        base64_audio: str, 
        system_prompt: str = None, 
        cancel_event: asyncio.Event = None, 
        request_id: str = ""
    ) -> AsyncGenerator[str, None]:
        
        if not self.api_key:
            yield f"data: {json.dumps({'type': 'error', 'content': 'NVIDIA_API_KEY is missing'})}\n\n"
            return

        # Create latency profile
        profile = latency_profiler.create_profile(request_id)
        start_time = time.time()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }

        headers["Authorization"] = f"Bearer {self.api_key}"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # OpenAI-compatible audio payload
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": base64_audio,
                        "format": "wav"
                    }
                }
            ]
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": 1024
        }

        logger.info(f"[NVIDIA] {request_id[:8]} Connecting to {self.model} for voicechat...")
        request_send_time = time.time()
        profile.request_receive_ms = (request_send_time - start_time) * 1000

        try:
            # Get reusable client instead of creating new one
            client = await self.get_client()
            first_token_received = False
            first_token_time = None
            
            async with client.stream("POST", self.base_url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"[NVIDIA] {request_id[:8]} Error {response.status_code}: {error_text}")
                    yield f"data: {json.dumps({'type': 'error', 'content': f'NVIDIA API Error {response.status_code}'})}\n\n"
                    return

                logger.info(f"[VOICE] {request_id[:8]} Session established. Streaming response...")
                response_start = time.time()
                
                async for line in response.aiter_lines():
                    if cancel_event and cancel_event.is_set():
                        logger.info(f"[VOICE] {request_id[:8]} Session closed (interrupted)")
                        break
                        
                    if line.startswith("data: "):
                        data_str = line.replace("data: ", "").strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            # Capture first token timing
                            if not first_token_received:
                                first_token_time = time.time()
                                profile.api_first_token_ms = (first_token_time - request_send_time) * 1000
                                first_token_received = True
                                logger.debug(f"[NVIDIA] {request_id[:8]} First token: {profile.api_first_token_ms:.0f}ms")
                            
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                
                                # Output audio chunk
                                audio = delta.get("audio", {})
                                audio_data = audio.get("data")
                                audio_transcript = audio.get("transcript")
                                
                                # Text fallback if audio object not used
                                text_content = delta.get("content")
                                
                                if audio_data:
                                    yield f"data: {json.dumps({'type': 'audio', 'request_id': request_id, 'data': audio_data})}\n\n"
                                if audio_transcript:
                                    yield f"data: {json.dumps({'type': 'token', 'request_id': request_id, 'content': audio_transcript})}\n\n"
                                if text_content and not audio_transcript:
                                    yield f"data: {json.dumps({'type': 'token', 'request_id': request_id, 'content': text_content})}\n\n"
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            logger.debug(f"[NVIDIA] {request_id[:8]} Parse error: {e}")
                            
                        # Yield control to allow cancellation
                        await asyncio.sleep(0)
                
                # Final timing
                profile.api_total_ms = (time.time() - request_send_time) * 1000
                profile.response_stream_ms = (time.time() - response_start) * 1000
                    
        except asyncio.CancelledError:
            logger.info(f"[VOICE] {request_id[:8]} Session closed (cancelled)")
            raise
        except httpx.TimeoutException:
            logger.error(f"[NVIDIA] {request_id[:8]} Request timed out")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Request timed out'})}\n\n"
        except Exception as e:
            logger.error(f"[NVIDIA] {request_id[:8]} Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Streaming failed'})}\n\n"
        finally:
            # Log final metrics
            latency_profiler.finalize(request_id)

nvidia_voicechat_service = NvidiaVoiceChatService()
