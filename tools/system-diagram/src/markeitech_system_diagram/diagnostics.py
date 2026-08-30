from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ManifestError(ValueError):
    """A bounded, non-secret manifest diagnostic."""

    code: str
    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} at {self.location}: {self.message}"
