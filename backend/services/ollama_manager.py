import os
import time
import asyncio
import httpx
import psutil
import subprocess
import logging
from backend.config.settings import settings

logger = logging.getLogger("zyricon-backend.ollama_manager")

class OllamaManager:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.status = "starting" # starting, online, degraded, offline

    def is_process_running(self):
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                name = proc.info.get('name', '').lower()
                cmdline = proc.info.get('cmdline', [])
                if name == 'ollama' or name == 'ollama.exe':
                    if cmdline and 'serve' in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    async def ensure_running(self):
        """Ensure the ollama serve process is running, start it if not."""
        if not settings.OLLAMA_AUTO_START:
            return
            
        if self.is_process_running():
            logger.info("Ollama process is already running.")
            return

        logger.info("Starting Ollama background process...")
        try:
            # We start ollama serve in the background
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                start_new_session=True if os.name != 'nt' else False
            )
            # Give it a few seconds to bind port
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start Ollama automatically: {e}")
            self.status = "error"

    async def check_api(self):
        """Check if the API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                return res.status_code == 200
        except Exception:
            return False

    async def ensure_model_available(self):
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m['name'] for m in res.json().get('models', [])]
                    if self.model in models or f"{self.model}:latest" in models:
                        return True
                    else:
                        logger.warning(f"Ollama model '{self.model}' is not installed.")
                        if settings.OLLAMA_AUTO_PULL:
                            logger.info(f"Pulling model {self.model}...")
                            await client.post(f"{self.base_url}/api/pull", json={"name": self.model}, timeout=300.0)
                            return True
                        else:
                            logger.error(f"Please run 'ollama pull {self.model}' manually.")
                            return False
        except Exception as e:
            logger.error(f"Error checking models: {e}")
            return False
            
    async def warmup(self):
        if not settings.OLLAMA_WARMUP:
            return True
        logger.info(f"Warming up Ollama model '{self.model}'...")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hello"}],
                    "stream": False
                }
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                if res.status_code == 200:
                    logger.info("Ollama warmup successful.")
                    return True
        except Exception as e:
            logger.error(f"Ollama warmup failed: {e}")
        return False

    async def initialize(self):
        await self.ensure_running()
        is_up = await self.check_api()
        if not is_up:
            logger.error("Ollama API is unreachable.")
            self.status = "offline"
            return
            
        has_model = await self.ensure_model_available()
        if not has_model:
            self.status = "degraded"
            return
            
        warmed_up = await self.warmup()
        if warmed_up:
            self.status = "online"
        else:
            self.status = "degraded"

ollama_manager = OllamaManager()
