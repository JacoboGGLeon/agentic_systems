"""Configuration for the external Accountability OTC skill."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AccountabilitySettings:
    """Runtime configuration for the OTC accountability skill.

    Values are environment-driven so the same notebooks run unchanged across
    SageMaker/ADA sandboxes and local smoke tests.
    """

    database: str = os.getenv("OTC_DATABASE", "mx_master")
    table: str = os.getenv("OTC_TABLE", "t_mrdc_mthly_invty_otc")
    workgroup: str = os.getenv("OTC_WORKGROUP", "sandbox")
    region: str = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    model_id: str = os.getenv("OTC_MODEL_ID", "qwen.qwen3-32b-v1:0")
    max_limit: int = int(os.getenv("OTC_MAX_LIMIT", "500"))

    @property
    def table_ref(self) -> str:
        return f'"{self.database}"."{self.table}"'

    @property
    def allowed_table_names(self) -> tuple[str, ...]:
        return (
            f"{self.database}.{self.table}".lower(),
            f'"{self.database}"."{self.table}"'.lower(),
        )
