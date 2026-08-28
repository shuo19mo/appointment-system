"""Small replaceable in-memory session store with TTL isolation."""

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from time import monotonic


@dataclass
class _Session:
    data: dict = field(default_factory=dict)
    touched_at: float = field(default_factory=monotonic)


class SessionStore:
    def __init__(self, ttl_seconds: int = 1800, clock=monotonic):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._sessions: dict[str, _Session] = {}
        self._lock = RLock()

    def get(self, session_id: str) -> dict:
        session_id = self._session_key(session_id)
        with self._lock:
            self.cleanup()
            session = self._sessions.get(session_id)
            if session is None:
                return {}
            session.touched_at = self._clock()
            return deepcopy(session.data)

    def update(self, session_id: str, values: dict) -> dict:
        session_id = self._session_key(session_id)
        with self._lock:
            self.cleanup()
            session = self._sessions.setdefault(session_id, _Session(touched_at=self._clock()))
            session.data.update(values)
            session.touched_at = self._clock()
            return deepcopy(session.data)

    def reset(self, session_id: str) -> None:
        session_id = self._session_key(session_id)
        with self._lock:
            self._sessions.pop(session_id, None)

    def cleanup(self) -> int:
        with self._lock:
            cutoff = self._clock() - self.ttl_seconds
            expired = [key for key, value in self._sessions.items() if value.touched_at < cutoff]
            for key in expired:
                self._sessions.pop(key, None)
            return len(expired)

    @staticmethod
    def _session_key(session_id: str) -> str:
        key = (session_id or "").strip()
        if not key:
            raise ValueError("session_id must not be blank")
        return key
