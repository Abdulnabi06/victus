from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Application settings, overriding from env vars or a .env file.
    Default to Ollama for the LLM provider.
    """
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "llama3" # Default model
    OLLAMA_API_URL: str = "http://localhost:11434"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
