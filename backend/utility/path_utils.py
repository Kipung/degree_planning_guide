"""
Cross-platform filesystem path helpers for the backend.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def project_root() -> Path:
    """Return the repository root directory.

    When running inside Docker we only copy the backend package, so the repo
    root is effectively the backend directory itself. Detect that scenario and
    fall back gracefully.
    """
    here = Path(os.path.abspath(os.path.dirname(__file__)))
    # two levels up when running from the full repo on the host machine
    host_candidate = here.parent.parent
    if (host_candidate / "backend").exists():
        return host_candidate
    # inside the container the backend folder is the project root
    return here.parent


@lru_cache(maxsize=1)
def backend_dir() -> Path:
    """Return the backend directory."""
    root = project_root()
    backend_path = root / "backend"
    return backend_path if backend_path.exists() else root


@lru_cache(maxsize=1)
def graph_dir() -> Path:
    """Return the graph module directory."""
    return backend_dir() / "graph"


@lru_cache(maxsize=1)
def course_data_path() -> Path:
    """Return the absolute path to the canonical course data JSON."""
    return graph_dir() / "course_data.json"


__all__ = [
    "project_root",
    "backend_dir",
    "graph_dir",
    "course_data_path",
]
