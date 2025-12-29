import uuid
import asyncio
from typing import Dict, Tuple, Optional

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, asyncio.Queue] = {}

    def create_session(self) -> Tuple[str, asyncio.Queue]:
        session_id = str(uuid.uuid4())
        queue = asyncio.Queue()
        self.sessions[session_id] = queue
        return session_id, queue

    def get_session(self, session_id: str) -> Optional[asyncio.Queue]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

session_manager = SessionManager()
