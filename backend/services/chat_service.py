import json
import random
import time
import asyncio
import base64
from io import BytesIO
from typing import Dict, Any, List, AsyncGenerator
from PIL import Image, ImageDraw, ImageFont

from backend.agent.graph import agent_graph
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.db import database as db
from backend.tools.registry import registry, Tool
from pydantic import BaseModel

# Register default tools for search and image generation
class WebSearchArgs(BaseModel):
    query: str

def web_search_handler(query: str) -> str:
    """Mock web search tool returning structured simulated search results."""
    results = [
        {"title": f"Latest insights on {query}", "snippet": f"Here is a comprehensive summary of key developments regarding {query} with up-to-date analysis and findings.", "url": f"https://example.com/search?q={query}"},
        {"title": f"Deep Dive: {query} Guide", "snippet": f"A step-by-step walkthrough covering architecture, best practices, and implementation strategies for {query}.", "url": f"https://techdocs.org/guide/{query}"}
    ]
    return json.dumps(results)

search_tool = Tool(
    name="web_search",
    description="Search the web for real-time information, news, research, or documentation.",
    args_schema=WebSearchArgs,
    handler=web_search_handler
)
registry.register(search_tool)

class DesktopAutomationArgs(BaseModel):
    action: str
    target: str

def automation_handler(action: str, target: str) -> str:
    return f"Desktop Action '{action}' on target '{target}' executed successfully."

auto_tool = Tool(
    name="desktop_automation",
    description="Control windows, applications, mouse, keyboard, or file operations.",
    args_schema=DesktopAutomationArgs,
    handler=automation_handler,
    requires_permission=True
)
registry.register(auto_tool)

def generate_placeholder_image(prompt: str) -> str:
    """Generates a dynamic base64-encoded SVG image based on prompt styling."""
    bg_colors = ["#4C1D95", "#312E81", "#1E1B4B", "#581C87", "#2E1065"]
    bg = random.choice(bg_colors)
    prompt_short = prompt[:40] + ("..." if len(prompt) > 40 else "")
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
      <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:{bg};stop-opacity:1" />
          <stop offset="100%" style="stop-color:#0F0728;stop-opacity:1" />
        </linearGradient>
      </defs>
      <rect width="600" height="400" rx="16" fill="url(#grad)" />
      <circle cx="300" cy="180" r="80" fill="#A855F7" opacity="0.3" filter="blur(20px)" />
      <circle cx="300" cy="180" r="50" fill="#C084FC" opacity="0.8" />
      <text x="300" y="310" font-family="sans-serif" font-size="20" font-weight="bold" fill="#F3E8FF" text-anchor="middle">AI Art Generated</text>
      <text x="300" y="340" font-family="sans-serif" font-size="14" fill="#C084FC" text-anchor="middle">"{prompt_short}"</text>
    </svg>"""
    
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"

async def stream_chat_response(chat_id: str, prompt: str, model: str = "ChatGPT v4.0") -> AsyncGenerator[str, None]:
    """Streams SSE events (tokens, tool calls, images, final result) to the client."""
    # Ensure chat exists
    chat = db.get_chat_with_messages(chat_id)
    if not chat:
        db.create_chat(title=prompt[:30] + ("..." if len(prompt) > 30 else ""), model=model)
        
    # Save user message
    db.add_message(chat_id, "user", prompt)
    
    # Check special trigger modes
    prompt_lower = prompt.lower()
    
    if "image" in prompt_lower or "generate image" in prompt_lower or "draw" in prompt_lower:
        yield f"data: {json.dumps({'type': 'tool_start', 'name': 'image_generator', 'status': 'Generating image from prompt...'})}\n\n"
        await asyncio.sleep(0.1)
        img_url = generate_placeholder_image(prompt)
        reply = f"Here is the generated image based on your request: '{prompt}'."
        db.add_message(chat_id, "assistant", reply, image_url=img_url)
        yield f"data: {json.dumps({'type': 'image', 'url': img_url})}\n\n"
        yield f"data: {json.dumps({'type': 'token', 'content': reply})}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
        return

    if "search" in prompt_lower or "latest" in prompt_lower or "news" in prompt_lower:
        yield f"data: {json.dumps({'type': 'tool_start', 'name': 'web_search', 'status': 'Searching web for query...'})}\n\n"
        search_res = web_search_handler(prompt)
        yield f"data: {json.dumps({'type': 'tool_end', 'name': 'web_search', 'output': search_res})}\n\n"
        
        reply = f"Based on recent search results:\n- Insights and latest updates were retrieved regarding '{prompt}'.\n- The key findings indicate rapid advancements and structured documentation."
        db.add_message(chat_id, "assistant", reply, tool_output=search_res)
        yield f"data: {json.dumps({'type': 'token', 'content': reply})}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
        return

    # Route through Ollama service if Ollama is running or model is local
    from backend.services.ollama_service import ollama_service
    from backend.models.chat import OllamaChatRequest, OllamaChatMessage

    
    ollama_status = await ollama_service.get_status()
    if ollama_status.running:
        # Build chat request for Ollama
        messages_history = []
        if chat and "messages" in chat:
            for m in chat["messages"]:
                messages_history.append(OllamaChatMessage(role=m["role"], content=m["content"]))
        messages_history.append(OllamaChatMessage(role="user", content=prompt))
        
        req = OllamaChatRequest(model=model if ":" in model or "qwen" in model.lower() or "llama" in model.lower() or "deepseek" in model.lower() else "qwen3:latest", messages=messages_history)
        
        full_response = ""
        async for chunk in ollama_service.chat_stream(req):
            if chunk.startswith("data: "):
                try:
                    data = json.loads(chunk.replace("data: ", "").strip())
                    if data.get("type") == "token":
                        full_response += data.get("content", "")
                except Exception:
                    pass
            yield chunk
            
        if full_response:
            db.add_message(chat_id, "assistant", full_response)
        return

    # Fallback when Ollama service is not running locally
    full_response = ""
    simulated_reply = (
        f"Hello! I received your message: **'{prompt}'** using model **{model}**.\n\n"
        "⚡ **Note**: Local Ollama server is currently offline or starting up.\n"
        "To enable real local LLM generation (Qwen3, DeepSeek-R1, Llama3), ensure `ollama serve` is running on your machine!\n\n"
        "How else can I assist you with tools, web search, or desktop automation?"
    )
    
    words = simulated_reply.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        full_response += chunk
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        await asyncio.sleep(0.01)

    db.add_message(chat_id, "assistant", full_response)
    yield f"data: {json.dumps({'type': 'end'})}\n\n"


