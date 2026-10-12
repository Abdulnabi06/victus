import json
import logging
from typing import Dict
from backend.services.ollama_service import ollama_service
from backend.config.settings import settings

logger = logging.getLogger("zyricon-backend.router")

class IntelligenceRouter:
    def __init__(self):
        self.web_keywords = ["latest", "news", "price", "who won", "today", "current", "weather", "search", "lookup"]
        self.memory_keywords = ["remember", "forget", "my name", "my project", "i like", "i prefer", "what do you know", "what did i say", "my current"]

    async def route(self, query: str) -> Dict[str, str]:
        """Classify the user intent: CHAT, WEB_SEARCH, MEMORY, MIXED"""
        query_lower = query.lower()
        
        # 1. Fast heuristics
        is_web = any(kw in query_lower for kw in self.web_keywords)
        is_memory = any(kw in query_lower for kw in self.memory_keywords)
        
        if is_web and is_memory:
            return {"mode": "MIXED", "reason": "Query contains both fresh info and memory keywords"}
        elif is_web:
            return {"mode": "WEB_SEARCH", "reason": "Query asks for current or latest info"}
        elif is_memory:
            return {"mode": "MEMORY", "reason": "Query asks to remember or recall user context"}

        # 2. If ambiguous, we default to CHAT.
        return {"mode": "CHAT", "reason": "Default casual conversation"}

intelligence_router = IntelligenceRouter()
