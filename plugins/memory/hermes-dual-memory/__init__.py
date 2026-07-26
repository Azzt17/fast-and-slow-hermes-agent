"""Hermes dual-process memory provider scaffold."""

from __future__ import annotations

import importlib.util
import logging
import threading
from pathlib import Path
from typing import Any, Optional, List, Dict

try:
    from agent.memory_provider import MemoryProvider as BaseMemoryProvider
except ModuleNotFoundError:
    class BaseMemoryProvider:  # type: ignore[too-many-ancestors]
        """Fallback base class for local development when Hermes is absent."""

        pass

logger = logging.getLogger(__name__)


def _load_storage_module() -> Any:
    """Load the sibling storage module without relying on package import rules."""

    storage_path = Path(__file__).with_name("storage.py")
    spec = importlib.util.spec_from_file_location(
        "hermes_dual_memory.storage",
        storage_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load storage module from {storage_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_storage = _load_storage_module()
HotSessionStore = _storage.HotSessionStore


def _estimate_token_count(content: str) -> int:
    return len(content.split())


class MemoryProvider(BaseMemoryProvider):
    """Memory provider scaffold with a hot-session SQLite store."""

    def __init__(self) -> None:
        self._session_id = ""
        self._hermes_home: Path | None = None
        self._store: HotSessionStore | None = None
        self._sync_threads: list[threading.Thread] = []
        self._sync_lock = threading.Lock()

    @property
    def name(self) -> str:
        return "hermes-dual-memory"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        hermes_home = kwargs.get("hermes_home")
        if not hermes_home:
            raise ValueError("initialize() requires hermes_home")

        self._session_id = session_id
        self._hermes_home = Path(hermes_home)
        self._store = HotSessionStore(self._hermes_home / self.name)

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        del messages

        store = self._store
        target_session_id = session_id or self._session_id
        if store is None:
            logger.warning("sync_turn() ignored because storage is not initialized")
            return
        if not target_session_id:
            logger.warning("sync_turn() ignored because no session_id is available")
            return

        def _sync() -> None:
            try:
                if user_content:
                    store.add_turn(
                        target_session_id,
                        user_content,
                        role="user",
                        token_count=_estimate_token_count(user_content),
                    )
                if assistant_content:
                    store.add_turn(
                        target_session_id,
                        assistant_content,
                        role="assistant",
                        token_count=_estimate_token_count(assistant_content),
                    )
            except Exception:
                logger.exception("Failed to persist hot turn for session %s", target_session_id)

        thread = threading.Thread(
            target=_sync,
            name=f"{self.name}-sync-{target_session_id}",
            daemon=True,
        )
        with self._sync_lock:
            self._sync_threads = [t for t in self._sync_threads if t.is_alive()]
            self._sync_threads.append(thread)
        thread.start()

    def get_config_schema(self) -> list[dict[str, Any]]:
        return []

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return []

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs) -> None:
        del tool_name, args, kwargs
        return None

    def shutdown(self) -> None:
        with self._sync_lock:
            threads = list(self._sync_threads)
        for thread in threads:
            thread.join(timeout=1.0)
        with self._sync_lock:
            self._sync_threads = [t for t in self._sync_threads if t.is_alive()]
        self._store = None


def register(ctx) -> None:
    """Register the memory provider with Hermes discovery."""
    ctx.register_memory_provider(MemoryProvider())
