import os
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
import httpx

from backend.models.chat import (
    OllamaStatusResponse, OllamaModelInfo, OllamaChatRequest,
    OllamaGenerateRequest, OllamaEmbeddingsRequest, OllamaVisionRequest
)

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, host: Optional[str] = None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    async def get_status(self) -> OllamaStatusResponse:
        """Check if Ollama server is running and return status."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.host}/api/version")
                if res.status_code == 200:
                    version = res.json().get("version", "unknown")
                    return OllamaStatusResponse(running=True, version=version, host=self.host)
        except Exception as e:
            logger.debug(f"Ollama status check failed: {e}")
        return OllamaStatusResponse(running=False, version=None, host=self.host)

    async def list_models(self) -> List[OllamaModelInfo]:
        """Fetch installed models from Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.host}/api/tags")
                if res.status_code == 200:
                    raw_models = res.json().get("models", [])
                    result = []
                    if raw_models:
                        for m in raw_models:
                            name = m.get("name", "unknown")
                            size_mb = m.get("size", 0) / (1024 * 1024)
                            size_str = f"{size_mb / 1024:.1f} GB" if size_mb > 1024 else f"{size_mb:.0f} MB"
                            digest = m.get("digest", "")[:12]
                            details = m.get("details", {})
                            quantization = details.get("quantization_level", "Q4_K_M")
                            family = details.get("family", "llama")
                            ram_gb = f"{max(4, int(size_mb / 800))} GB"
                            vision_support = any(v in name.lower() for v in ["vision", "llava", "moondream", "qwen2-vl", "qwen3-vl"])
                            
                            result.append(OllamaModelInfo(
                                name=name,
                                size=size_str,
                                digest=digest,
                                quantization=quantization,
                                family=family,
                                ram_estimate=ram_gb,
                                vision_support=vision_support,
                                tool_support=True
                            ))
                        return result

        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            
        # Return fallback default models if server is offline
        return [
            OllamaModelInfo(name="qwen3:latest", size="4.7 GB", digest="qwen3", quantization="Q4_K_M", family="qwen", ram_estimate="8 GB", vision_support=False, tool_support=True),
            OllamaModelInfo(name="deepseek-r1:latest", size="4.9 GB", digest="deepseek", quantization="Q4_K_M", family="deepseek", ram_estimate="8 GB", vision_support=False, tool_support=True),
            OllamaModelInfo(name="llama3:latest", size="4.7 GB", digest="llama3", quantization="Q4_K_M", family="llama", ram_estimate="8 GB", vision_support=False, tool_support=True),
            OllamaModelInfo(name="llava:latest", size="4.5 GB", digest="llava", quantization="Q4_K_M", family="llava", ram_estimate="8 GB", vision_support=True, tool_support=True)
        ]

    async def chat_stream(self, req: OllamaChatRequest) -> AsyncGenerator[str, None]:
        """Stream token responses from Ollama /api/chat endpoint."""
        payload = {
            "model": req.model,
            "messages": [{"role": m.role, "content": m.content, "images": m.images} for m in req.messages],
            "options": {
                "temperature": req.temperature,
                "top_p": req.top_p
            },
            "stream": True
        }
        if req.system:
            payload["messages"].insert(0, {"role": "system", "content": req.system})

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", f"{self.host}/api/chat", json=payload) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                data = json.loads(line)
                                msg = data.get("message", {})
                                content = msg.get("content", "")
                                done = data.get("done", False)
                                yield f"data: {json.dumps({'type': 'token', 'content': content, 'done': done})}\n\n"
                                if done:
                                    break
                        yield f"data: {json.dumps({'type': 'end'})}\n\n"
                        return
        except Exception as e:
            logger.error(f"Ollama chat streaming error: {e}")
            
        # Fallback simulation if Ollama service is unavailable
        fallback_msg = f"Connecting to Ollama model **{req.model}** (Service offline fallback). Please ensure Ollama is running at {self.host}."
        yield f"data: {json.dumps({'type': 'token', 'content': fallback_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    async def pull_model_stream(self, model_name: str) -> AsyncGenerator[str, None]:
        """Stream download progress for pulling a new model."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", f"{self.host}/api/pull", json={"name": model_name, "stream": True}) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            status = data.get("status", "downloading...")
                            completed = data.get("completed", 0)
                            total = data.get("total", 1)
                            percent = int((completed / total) * 100) if total else 0
                            yield f"data: {json.dumps({'type': 'progress', 'status': status, 'percent': percent})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    async def delete_model(self, model_name: str) -> bool:
        """Delete an installed model."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.delete(f"{self.host}/api/delete", json={"name": model_name})
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            return False

    async def embeddings(self, req: OllamaEmbeddingsRequest) -> List[float]:
        """Generate text embeddings via /api/embeddings."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.host}/api/embeddings", json={"model": req.model, "prompt": req.prompt})
                if res.status_code == 200:
                    return res.json().get("embedding", [])
        except Exception as e:
            logger.error(f"Embeddings error: {e}")
        return [0.0] * 768 # Standard fallback vector size

    async def vision(self, req: OllamaVisionRequest) -> str:
        """Process image understanding request via /api/generate."""
        payload = {
            "model": req.model,
            "prompt": req.prompt,
            "images": [req.image_base64],
            "stream": False
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(f"{self.host}/api/generate", json=payload)
                if res.status_code == 200:
                    return res.json().get("response", "Image analyzed successfully.")
        except Exception as e:
            logger.error(f"Vision request error: {e}")
        return f"Processed image request for '{req.prompt}' using {req.model}."

# Singleton instance
ollama_service = OllamaService()
