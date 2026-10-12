from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class OllamaStatusResponse(BaseModel):
    running: bool
    version: Optional[str] = None
    host: str

class OllamaModelInfo(BaseModel):
    name: str
    size: str
    digest: str
    quantization: str
    family: str
    ram_estimate: str
    vision_support: bool = False
    tool_support: bool = True

class OllamaChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None

class OllamaChatRequest(BaseModel):
    model: str = "qwen3"
    messages: List[OllamaChatMessage]
    temperature: float = 0.7
    top_p: float = 0.9
    stream: bool = True
    system: Optional[str] = None

class OllamaGenerateRequest(BaseModel):
    model: str = "qwen3"
    prompt: str
    system: Optional[str] = None
    stream: bool = True

class OllamaPullRequest(BaseModel):
    model: str

class OllamaDeleteRequest(BaseModel):
    model: str

class OllamaEmbeddingsRequest(BaseModel):
    model: str = "qwen3"
    prompt: str

class OllamaVisionRequest(BaseModel):
    model: str = "llava"
    prompt: str
    image_base64: str
