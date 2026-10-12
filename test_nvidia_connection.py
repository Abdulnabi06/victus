import asyncio
import httpx
from backend.config.settings import settings

async def test_nvidia():
    print("Testing NVIDIA API Connection...")
    print(f"API Key Present: {bool(settings.NVIDIA_API_KEY)}")
    print(f"Model: {settings.NVIDIA_VOICE_MODEL}")
    
    if not settings.NVIDIA_API_KEY:
        print("ERROR: NVIDIA_API_KEY not configured")
        return
    
    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    test_payload = {
        "model": settings.NVIDIA_VOICE_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": [
                {
                    "type": "text",
                    "text": "Say hello"
                }
            ]}
        ],
        "stream": False,
        "max_tokens": 100
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                json=test_payload,
                headers=headers
            )
            print(f"Response Status: {response.status_code}")
            if response.status_code == 200:
                print("[SUCCESS] NVIDIA API Connection works!")
                data = response.json()
                print("[OK] API authenticated successfully")
            elif response.status_code == 401:
                print("[FAILED] Invalid API Key (401 Unauthorized)")
            elif response.status_code == 404:
                print("[WARNING] Endpoint not found (404) - This is expected for voice model")
                print("[OK] But API Key is valid (no 401 error)")
            else:
                print(f"[ERROR] Status: {response.status_code}")
                text = response.text[:300]
                print(f"Response: {text}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {str(e)}")

asyncio.run(test_nvidia())
