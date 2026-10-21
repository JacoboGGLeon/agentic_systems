"""Persistent, process-locked inference reservations for release acceptance.

Transport hooks deliberately live until process exit, including timed-out workers.
Only request metadata is persisted; prompts, responses and credentials are omitted.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_UP
import json
import os
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit


class BudgetExceeded(RuntimeError):
    pass


class ReleaseBudget:
    def __init__(self, path: Path, routes: dict[str, dict], phase: str):
        self.path = path
        self.routes = routes
        self.phase = phase
        self.lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def locked(self):
        # Separate OS lock survives atomic ledger replacement and serializes processes.
        with self.lock, self.path.with_suffix(".lock").open("a+b") as stream:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def reserve(self, url, body, *, bearer: bool = False):
        endpoint = urlsplit(str(url))
        raw = body.encode() if isinstance(body, str) else body
        if not isinstance(raw, bytes) or len(raw) > 65536:
            raise ValueError("Release inference must be JSON text bounded to 64 KiB")
        payload = json.loads(raw)
        route = None
        for provider, spec in self.routes.items():
            base = urlsplit(spec["endpoint"])
            if (endpoint.scheme, endpoint.netloc) != (base.scheme, base.netloc):
                continue
            if provider == "bedrock-runtime":
                if not bearer:
                    raise ValueError(
                        "Release profile requires Bedrock bearer authentication"
                    )
                if unquote(endpoint.path) not in {
                    f"/model/{spec['model']}/converse",
                    f"/model/{spec['model']}/converse-stream",
                }:
                    continue
                limit = payload.get("inferenceConfig", {}).get("maxTokens")
            else:
                if (
                    endpoint.path
                    not in {
                        base.path.rstrip("/") + "/chat/completions",
                        base.path.rstrip("/") + "/responses",
                    }
                    or payload.get("model") != spec["model"]
                ):
                    continue
                limit = payload.get(
                    "max_output_tokens",
                    payload.get("max_completion_tokens", payload.get("max_tokens")),
                )
            route = provider, spec
            break
        if route is None:
            raise ValueError(
                "Inference endpoint, operation or model is outside frozen routes"
            )
        if type(limit) is not int or not 1 <= limit <= 4096 or payload.get("n", 1) != 1:
            raise ValueError("Inference output must be bounded to 4096 tokens, n=1")
        # Each UTF-8 byte is reserved as an input token plus framing; reserve full
        # output including reasoning. No caching discounts or refunds are assumed.
        provider, spec = route
        reserve = (
            Decimal("1.25")
            * (
                Decimal(len(raw) + 4096) * Decimal(str(spec["input_usd_per_million"]))
                + Decimal(limit) * Decimal(str(spec["output_usd_per_million"]))
            )
            / Decimal(1_000_000)
        ).quantize(Decimal("0.000001"), rounding=ROUND_UP)
        with self.locked():
            if self.path.exists():
                ledger = json.loads(self.path.read_text(encoding="utf-8"))
                if ledger["routes"] != self.routes or ledger["limits"] != {
                    "usd": 10,
                    "requests": 1000,
                }:
                    raise ValueError("Frozen budget identity changed")
            else:
                ledger = {
                    "schema_version": "agentic_systems.release-budget.v1",
                    "limits": {"usd": 10, "requests": 1000},
                    "routes": self.routes,
                    "attempts": [],
                }
            rows = ledger["attempts"]
            total = sum((Decimal(str(r["reserved_usd"])) for r in rows), Decimal(0))
            if len(rows) >= 1000 or total + reserve > Decimal(10):
                raise BudgetExceeded(
                    "Authorized USD 10 / 1000 inference allocation exhausted"
                )
            rows.append(
                {
                    "attempt": len(rows) + 1,
                    "phase": self.phase,
                    "provider": provider,
                    "request_bytes": len(raw),
                    "max_output_tokens": limit,
                    "reserved_usd": str(reserve),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            temporary = self.path.with_suffix(".pending")
            temporary.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, self.path)

    def install(self):
        import httpx
        from botocore.httpsession import URLLib3Session

        sync_send = httpx.Client._send_single_request
        async_send = httpx.AsyncClient._send_single_request
        boto_send = URLLib3Session.send

        def sync(client, request):
            self.reserve(request.url, request.read())
            return sync_send(client, request)

        async def asynchronous(client, request):
            self.reserve(request.url, await request.aread())
            return await async_send(client, request)

        def boto(client, request):
            auth = request.headers.get("Authorization", b"")
            if isinstance(auth, str):
                auth = auth.encode()
            self.reserve(
                request.url, request.body, bearer=auth.lower().startswith(b"bearer ")
            )
            return boto_send(client, request)

        httpx.Client._send_single_request = sync
        httpx.AsyncClient._send_single_request = asynchronous
        URLLib3Session.send = boto
