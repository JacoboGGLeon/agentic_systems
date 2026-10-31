"""Local preflight must recognize both documented key types without disclosure."""
import base64
import json
import pytest
from bedrock_key_format_214 import inspect_key


def short_key():
    payload = b"bedrock.amazonaws.com/?Action=CallWithBearerToken&X-Amz-Signature=FAKE&X-Amz-Credential=FAKE&X-Amz-Date=20260101T000000Z&X-Amz-Expires=3600"
    return "bedrock-api-key-" + base64.b64encode(payload).decode()


def test_short_term_key_is_a_supported_format():
    key = short_key()
    assert inspect_key(key) == {"present": True, "kind": "short-term", "local_format_valid": True}
    assert key not in json.dumps(inspect_key(key))


def test_long_term_key_is_a_supported_format():
    key = "ABSK" + base64.b64encode(b"BedrockAPIKey:FAKE:FAKE").decode()
    assert inspect_key(key)["local_format_valid"]
    assert key not in json.dumps(inspect_key(key))


@pytest.mark.parametrize("key", ["", "FAKE-IAM-ACCESS-KEY", "Bearer " + short_key(), "bedrock-api-key-%%%", "ABSK%%%", " " + short_key()])
def test_bad_format_is_rejected_without_returning_input(key):
    assert inspect_key(key)["local_format_valid"] is False
