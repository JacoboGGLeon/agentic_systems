"""Scan tracked and generated release files for credential material."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    re.compile(rb"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"(?<![A-Z0-9])(AKIA|ASIA)[0-9A-Z]{16}"),
    re.compile(rb"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9_]{30,}"),
)
PLACEHOLDERS = (b"example", b"placeholder", b"redacted", b"your_", b"test-")


def _tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / item.decode() for item in output.split(b"\0") if item]


def _local_secret_values() -> tuple[bytes, ...]:
    dotenv = ROOT / ".env"
    if not dotenv.exists():
        return ()
    values: list[bytes] = []
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not any(
            word in key.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD")
        ):
            continue
        normalized = value.strip().strip('"').strip("'").encode()
        if len(normalized) >= 12:
            values.append(normalized)
    return tuple(values)


def main() -> int:
    secrets = _local_secret_values()
    violations: list[str] = []
    for path in _tracked_files():
        if path.name == ".env":
            violations.append(f"{path.relative_to(ROOT)}: tracked .env is forbidden")
            continue
        if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
            continue
        payload = path.read_bytes()
        lowered = payload.lower()
        pattern_match = any(pattern.search(payload) for pattern in PATTERNS)
        placeholder = any(marker in lowered for marker in PLACEHOLDERS)
        local_match = any(secret in payload for secret in secrets)
        if local_match or (pattern_match and not placeholder):
            violations.append(f"{path.relative_to(ROOT)}: possible credential material")
    if violations:
        print("Secret gate failed (values are intentionally not displayed):")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Secret gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
