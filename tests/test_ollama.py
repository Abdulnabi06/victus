import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_ollama_status():
    response = client.get("/api/ollama/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert "host" in data

def test_ollama_models():
    response = client.get("/api/ollama/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "name" in models[0]
    assert "ram_estimate" in models[0]

def test_ollama_chat_streaming():
    payload = {
        "model": "qwen3",
        "messages": [{"role": "user", "content": "Hello Ollama"}],
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": True
    }
    response = client.post("/api/ollama/chat", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "data:" in response.text

def test_ollama_generate():
    payload = {
        "model": "qwen3",
        "prompt": "Write a python function",
        "stream": True
    }
    response = client.post("/api/ollama/generate", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

def test_ollama_embeddings():
    payload = {"model": "qwen3", "prompt": "Embed this string"}
    response = client.post("/api/ollama/embeddings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "embedding" in data
    assert len(data["embedding"]) > 0

def test_ollama_vision():
    payload = {
        "model": "llava",
        "prompt": "What is in this image?",
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    }
    response = client.post("/api/ollama/vision", json=payload)
    assert response.status_code == 200
    assert "response" in response.json()
