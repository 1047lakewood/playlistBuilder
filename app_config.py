"""Central configuration loader for Playlist Builder.
Loads ``config.json`` once and provides helper accessors.
The config can be reloaded at runtime via ``reload_config`` (e.g. when
SettingsDialog saves new values).
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, List

_CONFIG_LOCK = threading.Lock()
_CONFIG_DATA: dict | None = None
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def _load_from_disk() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _ensure_loaded() -> None:
    global _CONFIG_DATA
    if _CONFIG_DATA is None:
        with _CONFIG_LOCK:
            if _CONFIG_DATA is None:
                _CONFIG_DATA = _load_from_disk()


def reload_config() -> None:
    """Force reload configuration from disk."""
    global _CONFIG_DATA
    with _CONFIG_LOCK:
        _CONFIG_DATA = _load_from_disk()


def get(path: List[str] | tuple[str, ...], default: Any = None) -> Any:
    """Return value at nested *path* list e.g. ["fonts", "family"]."""
    _ensure_loaded()
    node: Any = _CONFIG_DATA  # type: ignore[arg-type]
    for key in path:
        if not isinstance(node, dict):
            return default
        node = node.get(key, default)
    return node


def set_value(path: List[str] | tuple[str, ...], value: Any) -> None:
    """Update in-memory config; caller must save to disk separately if needed."""
    _ensure_loaded()
    node = _CONFIG_DATA  # type: ignore[assignment]
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def get_config() -> dict:
    _ensure_loaded()
    return _CONFIG_DATA  # type: ignore[return-value]
