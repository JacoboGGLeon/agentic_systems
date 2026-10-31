"""Optional ADA diagnostics; no credential resolution, service calls or repair."""

import argparse
import json
import os

__version__ = "2.1.4"
__all__ = ["diagnose"]
_AWS_KEYS = (
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN", "AWS_PROFILE", "AWS_BEARER_TOKEN_BEDROCK",
)


def diagnose(*, session=None):
    """Return safe presence flags without consulting STS or metadata services.

    A static pair without a token may be a valid long-lived credential. This
    inspection reports ambiguity and suggests verification; it never declares
    keys invalid, resolves credentials, or removes environment variables.
    """
    present = {key: bool(os.environ.get(key, "").strip()) for key in _AWS_KEYS}
    pair_without_token = present["AWS_ACCESS_KEY_ID"] and present["AWS_SECRET_ACCESS_KEY"] and not present["AWS_SESSION_TOKEN"]
    return {
        "version": __version__, "scope": "configuration-only",
        "session_supplied": session is not None,
        "session_region": getattr(session, "region_name", None) if session is not None else None,
        "environment_present": present,
        "static_pair_without_session_token": pair_without_token,
        "hint": "Verify the intended credential provider; a static pair may be valid." if pair_without_token else None,
        "session_authentication": "explicit-iam" if session is not None else "not-resolved",
        "environment_mutated": False, "services_checked": False,
        "credentials_resolved": False, "ada_validated": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="agentic-systems-ada", description=__doc__)
    parser.add_argument("command", choices=("doctor",))
    parser.parse_args(argv)
    print(json.dumps(diagnose()))
    return 0
