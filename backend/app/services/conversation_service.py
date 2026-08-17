"""
Conversation memory — sliding-window per conversation_id.

Stored in-process memory only (conversations restart when the server
restarts, which is acceptable for this application).
"""
from __future__ import annotations

import uuid
from typing import Dict, List


class ConversationService:
    def __init__(self, max_turns: int = 6):
        self.max_turns = max_turns
        self._store: Dict[str, List[Dict[str, str]]] = {}

    def get_or_create(self, conversation_id: str | None) -> str:
        cid = conversation_id or f"conv_{uuid.uuid4().hex[:10]}"
        if cid not in self._store:
            self._store[cid] = []
        return cid

    def add_turn(self, cid: str, question: str, answer: str):
        self._store.setdefault(cid, [])
        self._store[cid].append({"user": question, "assistant": answer})
        # Trim to sliding window
        if len(self._store[cid]) > self.max_turns:
            self._store[cid] = self._store[cid][-self.max_turns:]

    def format_history(self, cid: str) -> str:
        turns = self._store.get(cid, [])
        if not turns:
            return "(no prior conversation)"
        lines = []
        for t in turns:
            lines.append(f"User: {t['user']}")
            lines.append(f"Assistant: {t['assistant']}")
        return "\n".join(lines)

    def clear(self, cid: str):
        self._store.pop(cid, None)


# ── singleton ─────────────────────────────────────────────────
from app.core.config import settings
conversation_service = ConversationService(max_turns=settings.MAX_CONVERSATION_TURNS)
