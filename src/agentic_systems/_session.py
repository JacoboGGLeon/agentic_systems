"""Process-local leases for borrowed AWS sessions; never serialize credentials."""

from contextlib import contextmanager
import os
import threading


_registry_lock = threading.Lock()
_leases = {}


def validate_session(session, provider, region, api_key, endpoint):
    """Check shape and conflicting options without resolving AWS credentials."""
    if session is None:
        return
    if provider != "bedrock-runtime":
        raise ValueError("session belongs to Bedrock")
    if api_key is not None or endpoint is not None:
        raise ValueError("session cannot be combined with api_key or endpoint")
    if not callable(getattr(session, "client", None)):
        raise ValueError("session must provide the boto3 client interface")
    session_region = getattr(session, "region_name", None)
    if session_region is not None and (not isinstance(session_region, str) or not session_region.strip()):
        raise ValueError("session region_name must be a nonempty string or None")
    if region is not None and session_region is not None and region != session_region:
        raise ValueError("region conflicts with the supplied session")


@contextmanager
def session_scope(session, timeout_s, *, owner_pid=None):
    """Serialize toolkit actor invocations borrowing the same session.

    SDK sessions are not generally thread-safe. A lease covers materialization
    and execution, including SDK-owned worker activity. External concurrent use
    remains the caller's responsibility. Resources belong to the caller and are
    never closed by this lease. Registry references disappear after the last user.
    """
    if session is None:
        yield
        return
    if owner_pid is not None and owner_pid != os.getpid():
        raise RuntimeError("Borrowed AWS sessions cannot cross processes")
    key = id(session)
    with _registry_lock:
        entry = _leases.setdefault(key, {"session": session, "lock": threading.RLock(), "users": 0})
        entry["users"] += 1
    acquired = False
    try:
        acquired = entry["lock"].acquire(timeout=max(0.0, float(timeout_s)))
        if not acquired:
            raise TimeoutError("Timed out waiting for borrowed AWS session")
        yield
    finally:
        if acquired:
            entry["lock"].release()
        with _registry_lock:
            entry["users"] -= 1
            if entry["users"] == 0:
                _leases.pop(key, None)
