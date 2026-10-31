"""Process-local audit guard. This is an offline harness, not an OS sandbox."""

import socket
import os
import sys
import threading

_lock = threading.Lock()
_installed = False
_blocked = 0
_blocked_records = []


def enforce_offline():
    global _installed
    with _lock:
        if not _installed:
            sys.addaudithook(_audit)
            _installed = True


def _audit(event, args):
    global _blocked
    if event == "socket.connect":
        # Windows asyncio needs stdlib socketpair for its self-pipe. Permit
        # only that exact stdlib frame connecting its own ephemeral listener.
        # Ordinary loopback connections, including Ollama, remain forbidden.
        frame = sys._getframe(1)
        fallback = getattr(socket, "_fallback_socketpair", None)
        if fallback is not None and frame.f_code is fallback.__code__:
            listener = frame.f_locals.get("lsock")
            if listener is not None and args[0] is frame.f_locals.get("csock"):
                bound = listener.getsockname()[:2]
                if bound[0] in {"127.0.0.1", "::1"} and args[1][:2] == bound:
                    return
    if event in {
        "socket.connect",
        "socket.getaddrinfo",
        "subprocess.Popen",
        "os.system",
    }:
        with _lock:
            _blocked += 1
        frame = sys._getframe(1)
        locations = []
        for _ in range(12):
            if frame is None:
                break
            locations.append(f"{frame.f_code.co_filename}:{frame.f_lineno}:{frame.f_code.co_name}")
            frame = frame.f_back
        # No event arguments: URLs, subprocess args and credentials stay private.
        with _lock:
            _blocked_records.append({"event": event, "test": os.getenv("PYTEST_CURRENT_TEST", "bootstrap"),
                                     "stack": locations})
        print("Offline blocked:", event, "test:", os.getenv("PYTEST_CURRENT_TEST", "bootstrap"),
              "stack:", " <- ".join(locations), file=sys.stderr)
        raise RuntimeError(f"Offline prototype forbids {event}")


def blocked_attempts():
    return _blocked


def blocked_details():
    return list(_blocked_records)
