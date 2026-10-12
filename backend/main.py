import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.db import database as db
from backend.services import stream_chat_response, generate_placeholder_image, web_search_handler, automation_handler
from backend.api.ollama_routes import router as ollama_router

from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zyricon-backend")

app = FastAPI(title="Zyricon AI Desktop Agent API", version="1.0.0")

# Register Routers
app.include_router(ollama_router)


# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def read_root_ui():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/index.html")

@app.get("/style.css")
def get_style():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/style.css")

@app.get("/app.js")
def get_app_js():
    from fastapi.responses import FileResponse
    return FileResponse("frontend/app.js")


# Schemas
class ChatRequest(BaseModel):
    chat_id: Optional[str] = None
    prompt: str
    model: Optional[str] = "ChatGPT v4.0"

class SearchRequest(BaseModel):
    query: str

class AutomationRequest(BaseModel):
    action: str
    target: str

class ImageRequest(BaseModel):
    prompt: str

class TranscribeRequest(BaseModel):
    audio_base64: Optional[str] = None

class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US"

@app.get("/")
def read_root():
    return {"status": "online", "app": "Zyricon AI Desktop Agent"}

# Chat Endpoints
@app.get("/api/chats")
def list_chats():
    return db.get_all_chats()

@app.post("/api/chats")
def create_chat(payload: Dict[str, Any] = Body(default={})):
    title = payload.get("title", "New Chat")
    model = payload.get("model", "ChatGPT v4.0")
    return db.create_chat(title, model)

@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    chat = db.get_chat_with_messages(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    chat_id = req.chat_id or f"chat_{uuid.uuid4().hex[:8]}"
    return StreamingResponse(
        stream_chat_response(chat_id, req.prompt, req.model),
        media_type="text/event-stream"
    )

# Voice Endpoints
@app.post("/api/voice/transcribe")
def voice_transcribe(req: TranscribeRequest):
    return {"text": "What is the latest update on AI agents?", "confidence": 0.98}

@app.post("/api/voice/speak")
def voice_speak(req: SpeakRequest):
    return {"status": "speaking", "text": req.text, "audio_url": None}

# Search & Tools
@app.post("/api/search")
def search_endpoint(req: SearchRequest):
    results = web_search_handler(req.query)
    return {"query": req.query, "results": results}

@app.post("/api/automation/run")
def automation_endpoint(req: AutomationRequest):
    res = automation_handler(req.action, req.target)
    return {"status": "success", "output": res}

@app.post("/api/image/generate")
def image_generate(req: ImageRequest):
    img_url = generate_placeholder_image(req.prompt)
    return {"prompt": req.prompt, "image_url": img_url}

# Config Endpoints
@app.get("/api/config")
def get_config():
    return db.get_config()

@app.post("/api/config")
def update_config(payload: Dict[str, str]):
    return db.update_config(payload)

# Task Endpoint
@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
