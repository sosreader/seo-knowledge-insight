"""
Chat session storage — JSON file-based implementation

Design:
- Repository Pattern: SessionRepository Protocol -> FileSessionStore
- One JSON file per session: output/sessions/{session_id}.json
- Append-only messages: read + append + write
- Future: swap to Supabase with zero router change
"""
from __future__ import annotations

import html
import json
import logging
import re
import threading
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol, Tuple

from app import config

logger = logging.getLogger(__name__)

MAX_MESSAGES_PER_SESSION = 100

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

_session_locks: dict = defaultdict(threading.Lock)


def _now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _sanitize_title(raw: str) -> str:
    """Sanitize user content for use as a session title."""
    return html.escape(raw[:50]).strip()


@dataclass(frozen=True)
class SessionMessage:
    role: str  # "user" | "assistant"
    content: str
    sources: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)


@dataclass
class Session:
    id: str
    title: str
    messages: list[SessionMessage] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [asdict(m) for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        messages = [SessionMessage(**m) for m in data.get("messages", [])]
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            messages=messages,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class SessionRepository(Protocol):
    def list_sessions(
        self, limit: int = 20, offset: int = 0
    ) -> Tuple[list[Session], int]: ...

    def get_session(self, session_id: str) -> Optional[Session]: ...

    def create_session(self, title: str = "") -> Session: ...

    def add_message(
        self, session_id: str, msg: SessionMessage
    ) -> Optional[Session]: ...

    def delete_session(self, session_id: str) -> bool: ...


class FileSessionStore:
    """JSON file-based session storage: output/sessions/{session_id}.json"""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or config.SESSIONS_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_id(self, session_id: str) -> None:
        """Validate session_id is a strict UUID v4 to prevent path traversal."""
        if not _UUID_RE.match(session_id):
            raise ValueError(f"Invalid session_id format: {session_id!r}")

    def _path(self, session_id: str) -> Path:
        self._validate_id(session_id)
        return self._base_dir / f"{session_id}.json"

    def _read(self, session_id: str) -> Optional[Session]:
        try:
            path = self._path(session_id)
        except ValueError:
            return None
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Session.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("session_store: read failed %s — %s", path, exc)
            return None

    def _write(self, session: Session) -> None:
        path = self._path(session.id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("session_store: write failed %s — %s", path, exc)

    def list_sessions(
        self, limit: int = 20, offset: int = 0
    ) -> Tuple[list[Session], int]:
        files = sorted(
            self._base_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        # Parse all files, skip corrupt ones, count only valid sessions
        all_sessions = [
            s for f in files if (s := self._read(f.stem)) is not None
        ]
        total = len(all_sessions)
        return all_sessions[offset : offset + limit], total

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._read(session_id)

    def create_session(self, title: str = "") -> Session:
        session = Session(
            id=str(uuid.uuid4()),
            title=_sanitize_title(title) if title else "New Chat",
        )
        self._write(session)
        return session

    def add_message(
        self, session_id: str, msg: SessionMessage
    ) -> Optional[Session]:
        with _session_locks[session_id]:
            session = self._read(session_id)
            if session is None:
                return None
            if len(session.messages) >= MAX_MESSAGES_PER_SESSION:
                logger.warning(
                    "session_store: session %s reached max messages (%d)",
                    session_id,
                    MAX_MESSAGES_PER_SESSION,
                )
                return None
            # Immutable update: create new list
            new_title = session.title
            if new_title == "New Chat" and msg.role == "user":
                new_title = _sanitize_title(msg.content)

            updated = Session(
                id=session.id,
                title=new_title,
                messages=[*session.messages, msg],
                created_at=session.created_at,
                updated_at=_now_iso(),
            )
            self._write(updated)
            return updated

    def delete_session(self, session_id: str) -> bool:
        try:
            path = self._path(session_id)
        except ValueError:
            return False
        if not path.exists():
            return False
        try:
            path.unlink()
            return True
        except OSError as exc:
            logger.warning("session_store: delete failed %s — %s", path, exc)
            return False


# Module-level singleton
session_store = FileSessionStore()
