from __future__ import annotations

import os
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError


class _IdentityMixin:
    def whoami(self, *, mask: bool = False) -> Dict[str, Any]:
        """Return AWS identity metadata or bearer-token authentication mode.

        Set ``mask=True`` when the notebook output may be copied to docs, tickets,
        or commits. Set ``mask=False`` when debugging IAM/role assumptions.
        """

        auth_mode = getattr(self, "auth_mode", None) or (
            "bedrock-api-key"
            if os.getenv("AWS_BEARER_TOKEN_BEDROCK")
            else "aws-credential-chain"
        )
        if auth_mode == "bedrock-api-key":
            result = {
                "account": None,
                "arn": None,
                "user_id": None,
                "region": self.region_name,
                "model_id": self.model_id,
                "auth_mode": auth_mode,
                "identity_available": False,
                "note": "Bearer tokens authenticate Bedrock calls but cannot call STS GetCallerIdentity.",
            }
            return self.redact_aws_identity(result) if mask else result

        identity = self.sts.get_caller_identity()
        result = {
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
            "region": self.region_name,
            "model_id": self.model_id,
            "auth_mode": auth_mode,
            "identity_available": True,
        }
        return self.redact_aws_identity(result) if mask else result

    @staticmethod
    def _mask_middle(value: Any, *, keep_start: int = 6, keep_end: int = 4) -> Any:
        """Mask long identifiers while preserving enough shape for debugging."""

        if value is None:
            return value

        text = str(value)
        if len(text) <= keep_start + keep_end:
            return "*" * len(text)

        return f"{text[:keep_start]}...{text[-keep_end:]}"

    @classmethod
    def redact_aws_identity(cls, identity: Dict[str, Any]) -> Dict[str, Any]:
        """Return a safe-to-share version of AWS identity metadata."""

        redacted = dict(identity)

        account = redacted.get("account")
        if account:
            account_text = str(account)
            redacted["account"] = (
                f"{account_text[:6]}******" if len(account_text) >= 6 else "***"
            )

        user_id = redacted.get("user_id")
        if user_id:
            redacted["user_id"] = cls._mask_middle(user_id)

        arn = redacted.get("arn")
        if arn:
            arn_text = str(arn)
            account_raw = str(identity.get("account") or "")
            if account_raw:
                arn_text = arn_text.replace(account_raw, "****")
            # Keep role family visible but avoid leaking the full role/session path.
            parts = arn_text.split("/")
            if len(parts) >= 3:
                arn_text = "/".join(parts[:2] + [cls._mask_middle(parts[-1])])
            redacted["arn"] = arn_text

        redacted["redacted"] = True
        return redacted

    def model_availability(
        self,
        model_id: Optional[str] = None,
        *,
        full_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Best-effort Bedrock model metadata check.

        Important:
        - This is not a real inference smoke test.
        - Some AWS roles can invoke a model but cannot call Bedrock management APIs.
        - We intentionally avoid get_foundation_model_availability because many
          boto3/botocore Bedrock clients do not expose that method.
        - The strongest runtime check is still a real bedrock-runtime.converse call.
        - Return value is JSON-safe; boto3 may include datetime objects.

        Parameters:
        - full_metadata=True returns the full JSON-safe boto3 metadata payload.
        - full_metadata=False returns a compact, documentation-safe summary.
        """

        selected_model = model_id or self.model_id

        def availability_payload(raw: Any) -> Any:
            safe = self._make_jsonable(raw)
            if full_metadata:
                return safe
            return self._summarize_model_metadata(safe)

        get_error: Optional[Dict[str, Any]] = None

        # Preferred metadata check: exact model lookup.
        if hasattr(self.bedrock, "get_foundation_model"):
            try:
                out = self.bedrock.get_foundation_model(modelIdentifier=selected_model)
                return {
                    "model_id": selected_model,
                    "ok": True,
                    "check": "get_foundation_model",
                    "full_metadata": full_metadata,
                    "availability": availability_payload(out),
                    "note": (
                        "Metadata check succeeded. A real Converse call is still "
                        "the strongest runtime/invoke validation."
                    ),
                }
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                message = exc.response.get("Error", {}).get("Message", str(exc))

                if code in {
                    "AccessDeniedException",
                    "UnauthorizedOperation",
                    "AccessDenied",
                }:
                    return {
                        "model_id": selected_model,
                        "ok": None,
                        "check": "get_foundation_model",
                        "full_metadata": full_metadata,
                        "availability": "unknown_due_to_iam",
                        "error_code": code,
                        "message": (
                            "IAM denied Bedrock model metadata check. "
                            "Inference may still work if bedrock-runtime:Converse "
                            "is allowed."
                        ),
                        "raw_message": message,
                    }

                get_error = {
                    "error_code": code,
                    "message": message,
                }
        else:
            get_error = {
                "error_code": "MethodNotAvailable",
                "message": (
                    "This boto3/botocore Bedrock client has no "
                    "get_foundation_model method."
                ),
            }

        # Fallback metadata check: list models in region and look for a match.
        if hasattr(self.bedrock, "list_foundation_models"):
            try:
                out = self.bedrock.list_foundation_models()
                summaries = out.get("modelSummaries", [])

                matches = []
                for model in summaries:
                    candidates = {
                        model.get("modelId"),
                        model.get("foundationModelId"),
                        model.get("modelArn"),
                    }
                    if selected_model in candidates:
                        matches.append(model)

                safe_matches = self._make_jsonable(matches)
                if not full_metadata:
                    safe_matches = [
                        self._summarize_model_metadata(match) for match in safe_matches
                    ]

                return {
                    "model_id": selected_model,
                    "ok": bool(matches),
                    "check": "list_foundation_models",
                    "full_metadata": full_metadata,
                    "matched": safe_matches,
                    "model_count": len(summaries),
                    "previous_get_foundation_model_error": get_error,
                    "note": (
                        "list_foundation_models validates metadata visibility in "
                        "this region, not runtime invoke entitlement. Use "
                        "run_direct for the real Converse smoke test."
                    ),
                }
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                message = exc.response.get("Error", {}).get("Message", str(exc))

                return {
                    "model_id": selected_model,
                    "ok": None,
                    "check": "list_foundation_models",
                    "full_metadata": full_metadata,
                    "availability": "unknown_due_to_error",
                    "error_code": code,
                    "message": message,
                    "previous_get_foundation_model_error": get_error,
                }

        return {
            "model_id": selected_model,
            "ok": None,
            "check": "none",
            "full_metadata": full_metadata,
            "availability": "unknown_due_to_client_capability",
            "message": (
                "This boto3/botocore Bedrock client exposes neither "
                "get_foundation_model nor list_foundation_models."
            ),
            "previous_get_foundation_model_error": get_error,
        }

    # ---------------------------------------------------------------------
    # Tool registry
    # ---------------------------------------------------------------------
