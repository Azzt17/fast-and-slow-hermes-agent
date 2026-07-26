"""Hermes dual-process memory provider scaffold."""

from __future__ import annotations

import importlib.util
import logging
import os
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


def _load_consolidation_module() -> Any:
    """Load the sibling System-2 pipeline without package import assumptions."""

    path = Path(__file__).with_name("consolidation.py")
    spec = importlib.util.spec_from_file_location("hermes_dual_memory.consolidation", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load consolidation module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_storage = _load_storage_module()
HotSessionStore = _storage.HotSessionStore
_consolidation = _load_consolidation_module()


def _estimate_token_count(content: str) -> int:
    return len(content.split())


class MemoryProvider(BaseMemoryProvider):
    """Memory provider scaffold with a hot-session SQLite store."""

    def __init__(self) -> None:
        self._session_id = ""
        self._hermes_home: Path | None = None
        self._store: HotSessionStore | None = None
        self._sync_threads: list[threading.Thread] = []
        self._consolidation_threads: list[threading.Thread] = []
        self._sync_lock = threading.Lock()
        self._consolidation_lock = threading.Lock()
        self._consolidation_run_lock = threading.Lock()
        self._mem0: Any = None
        self._mem0_config: dict[str, Any] | None = None
        self._llm_call: Any = None

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
        self._mem0_config = kwargs.get("mem0_config") or self._default_mem0_config(self._hermes_home)
        self._mem0 = kwargs.get("mem0_client") or self._create_mem0_client(
            self._mem0_config, self._hermes_home
        )
        self._llm_call = kwargs.get("llm_callable") or self._load_llm_callable(self._mem0_config)

    @staticmethod
    def _load_llm_callable(config: dict[str, Any] | None = None) -> Any:
        llm_config = (config or {}).get("llm", {}).get("config", {})
        if llm_config.get("api_key") and llm_config.get("openai_base_url") and llm_config.get("model"):
            try:
                from openai import OpenAI

                client = OpenAI(
                    api_key=llm_config["api_key"],
                    base_url=llm_config["openai_base_url"],
                )
                model = llm_config["model"]

                def configured_call(**kwargs: Any) -> Any:
                    return client.chat.completions.create(
                        model=model,
                        messages=kwargs["messages"],
                        temperature=kwargs.get("temperature"),
                        max_tokens=kwargs.get("max_tokens"),
                    )

                return configured_call
            except (ImportError, TypeError, ValueError):
                logger.exception("Unable to create configured 9router LLM client")

        try:
            from agent.auxiliary_client import call_llm
        except ModuleNotFoundError:
            return None
        return call_llm

    @staticmethod
    def _default_mem0_config(hermes_home: Path) -> dict[str, Any] | None:
        """Resolve Mem0's runtime config from Hermes' active provider registry."""

        try:
            from hermes_cli.config import get_compatible_custom_providers, load_config, load_env
        except ModuleNotFoundError:
            logger.warning("Hermes config loader unavailable; Mem0 requires explicit configuration")
            return None

        config = load_config()
        providers = get_compatible_custom_providers(config)
        provider = next(
            (item for item in providers if str(item.get("name", "")).strip().lower() == "9router"),
            None,
        )
        if provider is None:
            logger.warning("No 9router entry found in Hermes custom_providers")
            return None

        key_env = str(provider.get("key_env") or "").strip()
        env_values = load_env()
        api_key = os.environ.get(key_env) or env_values.get(key_env)
        base_url = str(provider.get("base_url") or "").strip()
        model = str(
            os.environ.get("HERMES_DUAL_MEMORY_LLM_MODEL")
            or provider.get("model")
            or ""
        ).strip()
        if not key_env or not api_key or not base_url or not model:
            logger.warning(
                "9router config is incomplete (key_env=%s, key=%s, base_url=%s, model=%s)",
                key_env or "missing",
                bool(api_key),
                bool(base_url),
                model or "missing",
            )
            return None

        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        embed_model = os.environ.get("HERMES_DUAL_MEMORY_EMBED_MODEL", "nomic-embed-text")
        mem0_home = hermes_home / "hermes-dual-memory"
        return {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "hermes_dual_memory",
                    "path": str(mem0_home / "chroma"),
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": model,
                    "api_key": api_key,
                    "openai_base_url": base_url,
                },
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": embed_model,
                    "ollama_base_url": ollama_url,
                },
            },
            "history_db_path": str(mem0_home / "history.db"),
        }

    @classmethod
    def _create_mem0_client(cls, config: Any = None, hermes_home: Path | None = None) -> Any:
        try:
            from mem0 import Memory
        except ModuleNotFoundError:
            logger.warning("mem0ai is unavailable; System-2 consolidation is disabled")
            return None
        try:
            resolved_config = config
            if resolved_config is None:
                if hermes_home is None:
                    logger.warning("hermes_home is required for default Mem0 configuration")
                    return None
                resolved_config = cls._default_mem0_config(hermes_home)
            if resolved_config is None:
                return None
            return Memory.from_config(resolved_config)
        except Exception:
            logger.exception("Unable to initialize configured Mem0; System-2 consolidation is disabled")
            return None

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

    def _consolidate(self, session_id: str) -> Optional[dict[str, Any]]:
        store = self._store
        if store is None or not session_id:
            return None
        with self._consolidation_run_lock:
            return self._consolidate_locked(store, session_id)

    def _consolidate_locked(self, store: HotSessionStore, session_id: str) -> Optional[dict[str, Any]]:
        rows = store.fetch_turns(session_id, consolidated=False)
        if not rows:
            return None
        if self._mem0 is None or self._llm_call is None:
            logger.error(
                "Cannot consolidate session %s: Mem0 or Hermes auxiliary LLM is unavailable",
                session_id,
            )
            return None
        try:
            report = _consolidation.consolidate_once(
                session_id=session_id,
                rows=rows,
                llm_call=self._llm_call,
                mem0_client=self._mem0,
            )
            store.mark_consolidated(session_id, [int(row["id"]) for row in rows])
            return report
        except Exception:
            logger.exception("System-2 consolidation skipped for session %s", session_id)
            return None

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Start idle consolidation in a daemon thread."""

        del messages
        session_id = self._session_id
        thread = threading.Thread(
            target=self._consolidate,
            args=(session_id,),
            name=f"{self.name}-consolidate-{session_id}",
            daemon=True,
        )
        with self._consolidation_lock:
            self._consolidation_threads = [t for t in self._consolidation_threads if t.is_alive()]
            self._consolidation_threads.append(thread)
        thread.start()

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """Consolidate synchronously so compression retains the new summary."""

        del messages
        report = self._consolidate(self._session_id)
        return report["summary"] if report else ""

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
        with self._consolidation_lock:
            consolidation_threads = list(self._consolidation_threads)
        for thread in consolidation_threads:
            thread.join(timeout=1.0)
        with self._consolidation_lock:
            self._consolidation_threads = [t for t in self._consolidation_threads if t.is_alive()]
        self._store = None


def register(ctx) -> None:
    """Register the memory provider with Hermes discovery."""
    ctx.register_memory_provider(MemoryProvider())
