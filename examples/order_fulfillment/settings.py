"""Credential-free configuration of the deterministic reference example."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    provider: str = "python-runtime"
    live: str = "0"

    def __post_init__(self):
        if self.provider != "python-runtime" or self.live != "0":
            raise ValueError(
                "This deterministic example uses Python; live acceptance has a separate budgeted harness"
            )


def load_settings(path):
    values = {}
    allowed = {"AGENTIC_PROVIDER", "AGENTIC_LIVE"}
    if Path(path).is_file():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() in allowed:
                values[key.strip()] = value.strip()
    values.update({key: os.environ[key] for key in allowed if key in os.environ})
    return Settings(
        values.get("AGENTIC_PROVIDER", "python-runtime"),
        values.get("AGENTIC_LIVE", "0"),
    )
