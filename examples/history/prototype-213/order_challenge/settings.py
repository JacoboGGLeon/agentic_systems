"""Credential-free configuration. Inference remains disabled in this revision."""
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    backend: str = "native"
    provider: str = "python-runtime"
    live: str = "0"

    def __post_init__(self):
        if self.backend not in {"native", "langgraph"}:
            raise ValueError("backend must be native or langgraph")
        if self.provider != "python-runtime" or self.live != "0":
            raise ValueError("This offline candidate permits only python-runtime with AGENTIC_LIVE=0")


def load_settings(path):
    allowed = {"AGENTIC_BACKEND", "AGENTIC_PROVIDER", "AGENTIC_LIVE"}
    values = {}
    if Path(path).is_file():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() in allowed:
                values[key.strip()] = value.strip()
    values.update({key: os.environ[key] for key in allowed if key in os.environ})
    return Settings(values.get("AGENTIC_BACKEND", "native"),
                    values.get("AGENTIC_PROVIDER", "python-runtime"),
                    values.get("AGENTIC_LIVE", "0"))
