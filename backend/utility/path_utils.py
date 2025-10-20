"""
Cross-platform filesystem path helpers for the backend.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def project_root() -> Path:
    """Return the repository root directory."""
    return Path(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
        )
    )


@lru_cache(maxsize=1)
def backend_dir() -> Path:
    """Return the backend directory."""
    return project_root() / "backend"


@lru_cache(maxsize=1)
def graph_dir() -> Path:
    """Return the graph module directory."""
    return backend_dir() / "graph"


@lru_cache(maxsize=1)
def models_dir() -> Path:
    """Return the directory containing bundled models."""
    return backend_dir() / "models"


@lru_cache(maxsize=1)
def course_data_path() -> Path:
    """Return the absolute path to the canonical course data JSON."""
    return graph_dir() / "course_data.json"


__all__ = [
    "project_root",
    "backend_dir",
    "graph_dir",
    "models_dir",
    "course_data_path",
]

