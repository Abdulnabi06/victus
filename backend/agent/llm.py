import logging
from langchain_core.language_models.chat_models import BaseChatModel

from backend.config.settings import settings

logger = logging.getLogger(__name__)

def get_llm() -> BaseChatModel:
    """
    Factory function to initialize and return the configured LLM.
    Defaults to Ollama but supports OpenAI/Anthropic based on config.
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=settings.LLM_MODEL,
                base_url=settings.OLLAMA_API_URL,
                temperature=0.0,
            )
        except ImportError:
            logger.warning("langchain-ollama not found. Falling back to langchain_community.chat_models.ChatOllama")
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(
                model=settings.LLM_MODEL,
                base_url=settings.OLLAMA_API_URL,
                temperature=0.0,
            )
    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.0,
        )
    elif provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.LLM_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.0,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
