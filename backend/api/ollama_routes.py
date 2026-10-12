from typing import List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.models.chat import (
    OllamaStatusResponse, OllamaModelInfo, OllamaChatRequest,
    OllamaGenerateRequest, OllamaPullRequest, OllamaDeleteRequest,
    OllamaEmbeddingsRequest, OllamaVisionRequest
)
from backend.services.ollama_service import ollama_service

router = APIRouter(prefix="/api/ollama", tags=["ollama"])

@router.get("/status", response_model=OllamaStatusResponse)
async def get_ollama_status():
    return await ollama_service.get_status()

@router.get("/models", response_model=List[OllamaModelInfo])
async def list_ollama_models():
    return await ollama_service.list_models()

@router.post("/chat")
async def chat_ollama(req: OllamaChatRequest):
    return StreamingResponse(
        ollama_service.chat_stream(req),
        media_type="text/event-stream"
    )

@router.post("/generate")
async def generate_ollama(req: OllamaGenerateRequest):
    # Convert generate to single chat message structure
    chat_req = OllamaChatRequest(
        model=req.model,
        messages=[{"role": "user", "content": req.prompt}],
        system=req.system,
        stream=req.stream
    )
    return StreamingResponse(
        ollama_service.chat_stream(chat_req),
        media_type="text/event-stream"
    )

@router.post("/pull")
async def pull_ollama_model(req: OllamaPullRequest):
    return StreamingResponse(
        ollama_service.pull_model_stream(req.model),
        media_type="text/event-stream"
    )

@router.delete("/model")
async def delete_ollama_model(req: OllamaDeleteRequest):
    success = await ollama_service.delete_model(req.model)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to delete model {req.model}")
    return {"status": "success", "message": f"Model {req.model} deleted."}

@router.post("/embeddings")
async def embeddings_ollama(req: OllamaEmbeddingsRequest):
    embedding = await ollama_service.embeddings(req)
    return {"model": req.model, "embedding": embedding, "dimensions": len(embedding)}

@router.post("/vision")
async def vision_ollama(req: OllamaVisionRequest):
    response_text = await ollama_service.vision(req)
    return {"model": req.model, "prompt": req.prompt, "response": response_text}
