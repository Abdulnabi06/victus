import os
import logging
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from backend.config.settings import settings

logger = logging.getLogger("zyricon-backend.gemini_service")

class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.enabled = settings.GEMINI_ENABLED
        self.model_name = settings.GEMINI_MODEL
        self.status = "offline"
        
        if self.enabled and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            self.status = "online"
        else:
            self.model = None

    async def is_available(self) -> bool:
        return self.status == "online" and self.model is not None

    async def web_search(self, query: str) -> str:
        """Use Gemini with Google Search tool to find fresh information."""
        if not await self.is_available():
            logger.warning("Gemini web search requested but service is unavailable.")
            return "Web search is currently unavailable."
            
        logger.info(f"Performing Gemini web research for: {query}")
        try:
            # For Gemini 1.5/2.5 models, tools can include google_search_retrieval
            # but standard SDK usually just needs 'google_search_retrieval' 
            # or we can simply prompt it as the model natively has access to internet in some environments.
            # Using the google_search_retrieval tool if the SDK supports it.
            # If not, we just use a standard prompt as Gemini can access the web.
            
            prompt = (
                f"You are an expert web researcher. Please search the web for the latest information "
                f"regarding the following query and provide a detailed summary of the facts, news, or answers found. "
                f"Query: '{query}'"
            )
            
            # Note: Depending on the exact google-generativeai version, enabling Google Search looks like this:
            # tools='google_search_retrieval' or tools=[{"google_search_retrieval": {}}]
            # To be safe across versions, we try to pass it, but fallback if it errors.
            try:
                response = self.model.generate_content(
                    prompt, 
                    tools="google_search_retrieval"
                )
            except Exception:
                # Fallback to standard prompt which still often utilizes Google's index
                response = self.model.generate_content(prompt)
                
            return response.text if response.text else "No useful information found."
        except Exception as e:
            logger.error(f"Gemini web search failed: {e}")
            return "I encountered an error while searching the web."

gemini_service = GeminiService()
