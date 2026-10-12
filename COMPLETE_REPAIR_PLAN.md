# ZYRICON COMPLETE REPAIR PLAN
## HTTP 410 + Wrong Model + Slow Voice

---

## ROOT CAUSE ANALYSIS

### HTTP 410 (Model Reached End of Life)
**Problem**: Frontend shows "Assistant returned an unexpected response (HTTP 410)."

**Root Cause**: 
- `backend/services/nemotron_service.py` line 27 hardcodes: `self.model = "meta/llama-3.1-8b-instruct"`
- This model reached end-of-life on **2026-08-26** (already expired)
- NVIDIA returns 410 Gone error
- User expects: `nvidia/nemotron-voicechat`

**Proof**:
```
Testing meta/llama-3.1-8b-instruct:
Response: HTTP 410 Gone
Details: The model 'meta/llama-3.1-8b-instruct' has reached its end of life 
on 2026-08-26T09:00:00Z and is no longer available.
```

### Authorization Header Not Sent
**Problem**: Both services send placeholder "Authorization": "Bearer ******"

**Root Cause**:
- `nemotron_service.py` line 43: `"Authorization": f"******"`
- `nvidia_voicechat.py` line 77: `"Authorization": f"******"`
- API key is never sent, only placeholder string

**Impact**: Even if model was correct, API would reject as unauthorized

### Wrong Model Configured  
**Problem**: UI shows "meta/llama-3.1-8b-instruct" instead of "nvidia/nemotron-voicechat"

**Root Cause**:
- `nemotron_service.py` line 27: Hardcoded model override
- `settings.py` line 30: Correct setting `NVIDIA_VOICE_MODEL=nvidia/nemotron-voicechat` exists but ignored
- System status endpoint reports wrong model

### Ollama Code Still Present
**Problem**: Requirement says "DO NOT use Ollama" but code still references it

**Root Cause**:
- `settings.py` lines 9-14: Ollama configuration still exists
- `ollama_service.py`, `ollama_manager.py`: Files still present
- `main.py` line 48: Ollama router commented out but not removed

---

## ISSUES INVENTORY

| # | Severity | File | Line | Issue | Fix |
|---|----------|------|------|-------|-----|
| 1 | 🔴 CRITICAL | nemotron_service.py | 43 | `"Authorization": f"***"` | Use actual API key: `f"Bearer {self.api_key}"` |
| 2 | 🔴 CRITICAL | nvidia_voicechat.py | 77 | `"Authorization": f"***"` | Use actual API key: `f"Bearer {self.api_key}"` |
| 3 | 🔴 CRITICAL | nemotron_service.py | 16 | Default model hardcoded | Use settings: `settings.NVIDIA_VOICE_MODEL` |
| 4 | 🔴 CRITICAL | nemotron_service.py | 27 | Model hardcoded to llama | Use settings: `settings.NVIDIA_VOICE_MODEL` |
| 5 | 🟠 HIGH | settings.py | 14 | Default model is `qwen3:latest` | Change to `nvidia/nemotron-voicechat` |
| 6 | 🟠 HIGH | settings.py | 9-14 | Ollama config present | Remove Ollama settings completely |
| 7 | 🟠 HIGH | backend/services | - | ollama_service.py, ollama_manager.py | Delete both files |
| 8 | 🟠 HIGH | main.py | 48 | Ollama router commented | Remove line completely |
| 9 | 🟡 MEDIUM | main.py | 114 | Reports wrong model | Report actual model being used |
| 10 | 🟡 MEDIUM | frontend/app.js | 140, 158 | Sends model="Zyricon" | Send actual model name |

---

## REPAIR PROCEDURE

### PHASE 1: Fix Authorization Headers (CRITICAL)

**File: `backend/services/nemotron_service.py` (Line 43)**
```python
BEFORE:
headers = {
    "Authorization": f"******",
    "Content-Type": "application/json"
}

AFTER:
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json"
}
```

**File: `backend/services/nvidia_voicechat.py` (Line 77)**
```python
BEFORE:
headers = {
    "Authorization": f"******",
    "Content-Type": "application/json",
    "Accept": "text/event-stream"
}

AFTER:
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json",
    "Accept": "text/event-stream"
}
```

### PHASE 2: Fix Model Configuration (CRITICAL)

**File: `backend/services/nemotron_service.py` (Lines 16, 27)**
```python
BEFORE (Line 16):
class NemotronChatRequest(BaseModel):
    model: str = "meta/llama-3.1-8b-instruct"  # WRONG!
    messages: List[NemotronChatMessage]

AFTER (Line 16):
class NemotronChatRequest(BaseModel):
    model: str = ""  # Will be set from settings or user selection
    messages: List[NemotronChatMessage]
```

```python
BEFORE (Lines 22-27):
class NemotronService:
    def __init__(self):
        from backend.config.settings import settings
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.status = "online" if self.api_key else "offline"
        self.model = "meta/llama-3.1-8b-instruct"  # HARDCODED - WRONG!

AFTER (Lines 22-27):
class NemotronService:
    def __init__(self):
        from backend.config.settings import settings
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.status = "online" if self.api_key else "offline"
        self.model = settings.NVIDIA_VOICE_MODEL  # Use settings: nvidia/nemotron-voicechat
```

### PHASE 3: Fix Default Model (HIGH)

**File: `backend/config/settings.py` (Line 14)**
```python
BEFORE:
OLLAMA_MODEL: str = "qwen3:latest"

AFTER:
# Removed - use NVIDIA_VOICE_MODEL instead
```

### PHASE 4: Remove Ollama (HIGH)

**File: `backend/config/settings.py` (Lines 9-14)**
```python
BEFORE:
# Ollama Local Configuration
OLLAMA_AUTO_START: bool = True
OLLAMA_AUTO_PULL: bool = False
OLLAMA_WARMUP: bool = True
OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
OLLAMA_MODEL: str = "qwen3:latest"

AFTER:
# Ollama removed per requirements - use NVIDIA instead
```

**Delete Files**:
- `backend/services/ollama_service.py` (DELETE)
- `backend/services/ollama_manager.py` (DELETE)

**File: `backend/main.py` (Line 48)**
```python
BEFORE:
# Register Routers
# app.include_router(ollama_router)

AFTER:
# Ollama removed - using NVIDIA Nemotron only
```

### PHASE 5: Fix Frontend Model Selection

**File: `frontend/app.js` (Lines 140, 158)**
```javascript
BEFORE (Line 140):
body: JSON.stringify({ title: prompt.slice(0, 25), model: "Zyricon" })

AFTER (Line 140):
body: JSON.stringify({ title: prompt.slice(0, 25), model: "nvidia/nemotron-voicechat" })
```

```javascript
BEFORE (Line 158):
body: JSON.stringify({ chat_id: currentChatId, prompt: prompt, model: "Zyricon" })

AFTER (Line 158):
body: JSON.stringify({ chat_id: currentChatId, prompt: prompt, model: "nvidia/nemotron-voicechat" })
```

---

## VERIFICATION STEPS

### Step 1: Verify Authorization
```bash
curl -H "Authorization: Bearer nvapi-6pw_..." \
  https://integrate.api.nvidia.com/v1/chat/completions \
  -d '{"model": "nvidia/nemotron-voicechat", "messages": [{"role":"user","content":"test"}]}'
```
Expected: 200 OK (or stream response)

### Step 2: Check Model Configuration
```bash
curl http://localhost:5000/api/system/status
```
Expected: `"model": "nvidia/nemotron-voicechat"`

### Step 3: Test Text Chat
1. Open browser: http://localhost:5000
2. Type: "Hello"
3. Expected: Response appears (not HTTP 410)

### Step 4: Test Voice Chat
1. Click "Voice" button
2. Say: "Hello"
3. Expected: Response in 1.5-2.2 seconds

### Step 5: Verify Ollama Removed
```bash
grep -r "ollama\|OLLAMA" backend/ --exclude-dir=__pycache__
```
Expected: No results (or only comments)

---

## EXPECTED OUTCOMES AFTER REPAIR

| Before | After |
|--------|-------|
| HTTP 410 error | ✅ Real responses |
| Model: meta/llama-3.1-8b-instruct | ✅ Model: nvidia/nemotron-voicechat |
| No authorization header sent | ✅ Bearer token sent correctly |
| Ollama config present | ✅ Removed completely |
| Slow/broken voice chat | ✅ 1.5-2.2s latency voice chat |
| UI shows wrong model | ✅ UI shows nvidia/nemotron-voicechat |

---

## TESTING CHECKLIST

- [ ] Authorization headers corrected in both services
- [ ] Model configuration updated in nemotron_service.py
- [ ] Settings.py has NVIDIA as default (not Ollama)
- [ ] Ollama files deleted
- [ ] Frontend sends correct model name
- [ ] Server starts without Ollama errors
- [ ] Text chat works: "Hello" → real response
- [ ] Voice chat works: Speak → real response in 1.5-2.2s
- [ ] Status endpoint shows correct model
- [ ] No HTTP 410 errors
- [ ] No references to llama-3.1-8b or Ollama remain

