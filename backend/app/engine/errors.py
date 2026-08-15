"""Generic ROI engine errors."""

from __future__ import annotations


class EngineInputError(ValueError):
    """Raised when required generic ROI inputs are missing or invalid."""
