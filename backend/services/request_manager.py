import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger("zyricon-backend.request_manager")

@dataclass
class ActiveRequest:
    request_id: str
    chat_id: str
    task: Optional[asyncio.Task] = None
    cancel_event: asyncio.Event = None

class RequestManager:
    def __init__(self):
        # Maps chat_id -> ActiveRequest
        self.active_requests: Dict[str, ActiveRequest] = {}
        # Global lock for state transitions
        self.lock = asyncio.Lock()

    async def register_request(self, chat_id: str, request_id: str) -> asyncio.Event:
        """Register a new request for the conversation, returning its cancellation event."""
        async with self.lock:
            # Create a new event for this request
            cancel_event = asyncio.Event()
            self.active_requests[chat_id] = ActiveRequest(
                request_id=request_id,
                chat_id=chat_id,
                cancel_event=cancel_event
            )
            return cancel_event

    async def set_task(self, chat_id: str, request_id: str, task: asyncio.Task):
        """Associate the executing asyncio.Task with the active request."""
        async with self.lock:
            active = self.active_requests.get(chat_id)
            if active and active.request_id == request_id:
                active.task = task

    async def cancel_previous(self, chat_id: str):
        """Cancel any existing request running for the given chat_id."""
        async with self.lock:
            active = self.active_requests.get(chat_id)
            if not active:
                return

            logger.info(f"generation_cancelled request_id={active.request_id} for chat_id={chat_id}")
            # Signal any internal loops to break
            active.cancel_event.set()
            
            # Cancel the asyncio task if one is registered
            if active.task and not active.task.done():
                active.task.cancel()
                # We don't await the task here because we don't want to block the new request.
                # The task will catch CancelledError and exit cleanly.

            # Remove from tracking
            del self.active_requests[chat_id]

    async def finish_request(self, chat_id: str, request_id: str):
        """Mark a request as finished and remove it from tracking."""
        async with self.lock:
            active = self.active_requests.get(chat_id)
            if active and active.request_id == request_id:
                del self.active_requests[chat_id]

request_manager = RequestManager()
