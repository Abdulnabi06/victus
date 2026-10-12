import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_read_root_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "Zyricon" in response.text

def test_list_chats():
    response = client.get("/api/chats")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_and_get_chat():
    create_res = client.post("/api/chats", json={"title": "Test Chat", "model": "ChatGPT v4.0"})
    assert create_res.status_code == 200
    chat_data = create_res.json()
    assert "id" in chat_data
    
    get_res = client.get(f"/api/chats/{chat_data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Test Chat"

def test_config_endpoints():
    get_res = client.get("/api/config")
    assert get_res.status_code == 200
    
    post_res = client.post("/api/config", json={"search_provider": "tavily"})
    assert post_res.status_code == 200
    assert post_res.json()["search_provider"] == "tavily"

def test_tools_endpoints():
    search_res = client.post("/api/search", json={"query": "AI Desktop Agent"})
    assert search_res.status_code == 200
    assert "results" in search_res.json()
    
    auto_res = client.post("/api/automation/run", json={"action": "click", "target": "submit_button"})
    assert auto_res.status_code == 200
    assert auto_res.json()["status"] == "success"
    
    img_res = client.post("/api/image/generate", json={"prompt": "Futuristic neon city"})
    assert img_res.status_code == 200
    assert "image_url" in img_res.json()
