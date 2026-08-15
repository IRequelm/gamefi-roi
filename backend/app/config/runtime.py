"""Runtime version policy."""

from __future__ import annotations

import sys
from dataclasses import dataclass

SUPPORTED_PYTHON_MAJOR = 3
SUPPORTED_PYTHON_MINOR = 12
SUPPORTED_PYTHON = f"{SUPPORTED_PYTHON_MAJOR}.{SUPPORTED_PYTHON_MINOR}"


@dataclass(frozen=True)
class RuntimeStatus:
    version: str
    supported: bool
    requirement: str


def current_runtime_status() -> RuntimeStatus:
    version_info = sys.version_info
    supported = (
        version_info.major == SUPPORTED_PYTHON_MAJOR
        and version_info.minor == SUPPORTED_PYTHON_MINOR
    )
    version = ".".join(str(part) for part in version_info[:3])
    return RuntimeStatus(
        version=version,
        supported=supported,
        requirement=f">={SUPPORTED_PYTHON},<{SUPPORTED_PYTHON_MAJOR}.{SUPPORTED_PYTHON_MINOR + 1}",
    )
