import json
import logging
from typing import List, Dict, Any, Optional
from mem0 import Memory
from pydantic import BaseModel
from backend.config.settings import settings
from backend.db import database as db
import google.generativeai as genai

logger = logging.getLogger("zyricon-backend.memory_service")

class MemoryExtractionResult(BaseModel):
    should_store: bool
    memories: List[Dict[str, Any]]

class MemoryService:
    def __init__(self):
        self.enabled = settings.MEMORY_ENABLED
        self.api_key = settings.MEM0_API_KEY
        
        # Configure Mem0 to use Gemini since OpenAI key is missing
        if self.enabled and settings.GEMINI_API_KEY:
            mem0_config = {
                "llm": {
                    "provider": "gemini",
                    "config": {
                        "model": "gemini-2.5-flash",
                        "api_key": settings.GEMINI_API_KEY
                    }
                },
                "embedder": {
                    "provider": "gemini",
                    "config": {
                        "model": "models/embedding-001",
                        "api_key": settings.GEMINI_API_KEY
                    }
                }
            }
            self.memory = Memory.from_config(mem0_config)
        else:
            self.memory = None
        
        # Configure Gemini for extraction
        if settings.GEMINI_ENABLED and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.extractor_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            self.extractor_model = None

    async def add_memory(self, text: str, user_id: str = "local_user"):
        if not self.enabled or not self.memory:
            return
            
        logger.info(f"Adding memory to Mem0 for {user_id}: {text}")
        res = self.memory.add(text, user_id=user_id)
        
        # Sync to SQLite
        if isinstance(res, list) and len(res) > 0:
            mem0_id = res[0].get("id", "unknown")
            db.add_memory_db(mem0_id, text, user_id)
        elif isinstance(res, dict) and "id" in res:
            db.add_memory_db(res["id"], text, user_id)
            
    async def search_memories(self, query: str, user_id: str = "local_user") -> str:
        if not self.enabled or not self.memory:
            return ""
            
        logger.info(f"Searching Mem0 for: {query}")
        try:
            results = self.memory.search(query, filters={"user_id": user_id})
            if not results:
                return ""
                
            formatted = []
            for r in results:
                if isinstance(r, dict) and "memory" in r:
                    formatted.append(f"- {r['memory']}")
                elif hasattr(r, "memory"):
                    formatted.append(f"- {r.memory}")
                    
            if not formatted:
                return ""
                
            return "Relevant user memories:\n" + "\n".join(formatted)
        except Exception as e:
            logger.error(f"Mem0 search error: {e}")
            return ""

    async def delete_all_memories(self, user_id: str = "local_user"):
        if not self.enabled or not self.memory:
            return
            
        self.memory.delete_all(user_id=user_id)
        # Assuming db method for all deleted
        pass

    async def extract_memory(self, user_message: str, assistant_response: str, user_id: str = "local_user"):
        """Run post-chat async memory extraction using Gemini."""
        if not self.enabled or not self.extractor_model:
            return
            
        prompt = f"""
Analyze the following conversation segment and determine if any long-term memory should be stored about the user.
Store explicit preferences, ongoing projects, constraints, or facts. Do NOT store casual conversation (hello, thanks), temporary state, or one-off facts.

User: {user_message}
Assistant: {assistant_response}

Return ONLY valid JSON matching this schema:
{{
  "should_store": true/false,
  "memories": [
    {{
      "text": "The fact to remember",
      "type": "preference|project|fact|constraint"
    }}
  ]
}}
"""
        try:
            res = self.extractor_model.generate_content(prompt)
            text = res.text
            # Simple JSON parse attempt
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            data = json.loads(text.strip())
            
            if data.get("should_store") and data.get("memories"):
                for mem in data["memories"]:
                    await self.add_memory(mem.get("text", ""), user_id)
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")

memory_service = MemoryService()
