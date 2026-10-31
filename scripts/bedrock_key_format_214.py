"""Inspect only public Bedrock key structure; never return credential material."""
import base64
import binascii
from urllib.parse import parse_qs, urlsplit


def inspect_key(value):
    result = {"present": bool(value), "kind": "unknown", "local_format_valid": False}
    if not isinstance(value, str) or value != value.strip():
        return result
    if value.startswith("ABSK"):
        result["kind"] = "long-term"
        encoded = value[4:]
    elif value.startswith("bedrock-api-key-"):
        result["kind"] = "short-term"
        encoded = value[len("bedrock-api-key-"):]
    else:
        return result
    try:
        decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        if result["kind"] == "long-term":
            result["local_format_valid"] = decoded.startswith(b"BedrockAPIKey:") and len(decoded) > len(b"BedrockAPIKey:")
        else:
            text = decoded.decode("utf-8")
            parsed = urlsplit(text if text.startswith("https://") else "https://" + text)
            query = parse_qs(parsed.query)
            result["local_format_valid"] = bool(
                parsed.scheme == "https" and parsed.hostname
                and parsed.hostname.startswith("bedrock")
                and parsed.hostname.endswith(".amazonaws.com")
                and query.get("Action") == ["CallWithBearerToken"]
                and query.get("X-Amz-Signature") and query.get("X-Amz-Credential")
                and query.get("X-Amz-Date") and query.get("X-Amz-Expires")
            )
    except (binascii.Error, UnicodeError, ValueError):
        pass
    return result
