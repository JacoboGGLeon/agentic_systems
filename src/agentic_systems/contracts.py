"""Contracts, policies and validation results for Agentic Systems 1.0."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


CompletionMode = Literal[
    "default",
    "when_contract_satisfied",
    "when_required_tools_satisfied",
    "always_finalize",
]
FailurePolicy = Literal["allow", "no_unresolved", "fail_fast"]
ToolExpectationValue = list[str] | tuple[str, ...] | set[str] | dict[str, Any] | None


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    severity: Literal["error", "warning"] = "error"
    path: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)

    def add(
        self,
        code: str,
        message: str,
        *,
        severity: Literal["error", "warning"] = "error",
        path: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                severity=severity,
                path=path,
                meta=meta or {},
            )
        )
        if severity == "error":
            self.ok = False

    def raise_if_failed(self) -> "ValidationResult":
        if self.ok:
            return self
        detail = "; ".join(f"{issue.code}: {issue.message}" for issue in self.issues)
        raise ValueError(f"Validation failed: {detail}")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AgentContract(BaseModel):
    """Declarative behavioral contract for an Agent run.

    Contract fields express failure semantics, expected output subsets, and
    expected Tool evidence without aliases.
    """

    model_config = ConfigDict(extra="forbid")

    must_call: list[str] = Field(default_factory=list)
    must_not_call: list[str] = Field(default_factory=list)
    tool_expectation: dict[str, Any] | None = None
    completion: CompletionMode = "default"
    failure_policy: FailurePolicy = "no_unresolved"
    require_no_unresolved_tool_failures: bool = True
    expected_output: dict[str, Any] | None = None
    expected_tool_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("completion", mode="before")
    @classmethod
    def normalize_completion(cls, value: Any) -> Any:
        if value in {None, "default"}:
            return "default"
        aliases = {
            "when_contract_satisfied": "when_required_tools_satisfied",
            "required_tools_ok": "when_required_tools_satisfied",
        }
        return aliases.get(value, value)

    @field_validator("failure_policy", mode="before")
    @classmethod
    def normalize_failure_policy(cls, value: Any) -> Any:
        if value in {None, True}:
            return "no_unresolved"
        if value is False:
            return "allow"
        return value

    def model_post_init(self, __context: Any) -> None:
        if (
            not self.require_no_unresolved_tool_failures
            and self.failure_policy == "no_unresolved"
        ):
            self.failure_policy = "allow"
        if self.require_no_unresolved_tool_failures and self.failure_policy == "allow":
            self.require_no_unresolved_tool_failures = False

    @classmethod
    def coerce(cls, value: "AgentContract | dict[str, Any] | None") -> "AgentContract":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        return cls.model_validate(value)

    def check(
        self,
        *,
        policy: "RunPolicy | dict[str, Any] | None" = None,
        available_tools: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> ValidationResult:
        """Validate this contract before a run.

        Runtime validation still happens on ``RunResult.validate(...)``.  This
        method catches static contradictions earlier: impossible tool budgets,
        references to tools that are not registered, or conflicting allow/deny
        rules.  It returns ``ValidationResult`` instead of raising so notebooks
        can display the issues cleanly.
        """

        return validate_contract_policy(self, policy, available_tools=available_tools)


def normalize_tool_expectation(value: ToolExpectationValue = None) -> dict[str, Any]:
    """Normalize user-facing tool expectations.

    Supported forms:
    - lab.expect.exactly("a") -> {"exactly": ["a"]}.
    - lab.expect.any_of("a", "b") -> {"any_of": ["a", "b"], "allowed": ["a", "b"]}.
    - lab.expect.all_of("a", "b") -> {"all_of": ["a", "b"], "allowed": ["a", "b"]}.
    - ["a", "b"] means {"all_of": ["a", "b"]} for backwards compatibility.
    - {"any_of": [...]}, {"all_of": [...]}, {"exactly": [...]}, {"allowed": [...]}.
    - {"min_count": 1, "allowed": [...]} for flexible cases.
    """

    if value is None:
        return {}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {"all_of": _clean_tool_names(value)}
    if not isinstance(value, dict):
        raise TypeError("tool expectation must be a list/tuple/set, dict, or None")
    expectation = dict(value)
    for key in ("any_of", "all_of", "exactly", "allowed"):
        if key in expectation and expectation[key] is not None:
            expectation[key] = _clean_tool_names(expectation[key])
    if "min_count" in expectation and expectation["min_count"] is not None:
        expectation["min_count"] = int(expectation["min_count"])
    return expectation


def validate_tool_expectation(
    actual_tools: list[str] | tuple[str, ...], expectation: ToolExpectationValue = None
) -> dict[str, Any]:
    """Validate actual tool names against a flexible expectation schema."""

    expected = normalize_tool_expectation(expectation)
    actual = [str(name) for name in actual_tools if str(name)]
    actual_set = set(actual)
    issues: list[dict[str, Any]] = []

    allowed = expected.get("allowed")
    if allowed:
        extra = [name for name in actual if name not in set(allowed)]
    elif expected.get("exactly"):
        allowed = list(expected["exactly"])
        extra = [name for name in actual if name not in set(allowed)]
    else:
        extra = []
    if extra:
        issues.append(
            {
                "code": "unexpected_tool",
                "message": "Unexpected tool call(s).",
                "tools": extra,
            }
        )

    missing: list[str] = []
    all_of = expected.get("all_of") or []
    for name in all_of:
        if name not in actual_set:
            missing.append(name)
    if missing:
        issues.append(
            {
                "code": "missing_required_tool",
                "message": "Required tool call(s) missing.",
                "tools": missing,
            }
        )

    any_of = expected.get("any_of") or []
    if any_of and not any(name in actual_set for name in any_of):
        issues.append(
            {
                "code": "missing_any_tool",
                "message": "At least one expected tool must be called.",
                "tools": list(any_of),
            }
        )

    exactly = expected.get("exactly") or []
    exactly_missing = [name for name in exactly if name not in actual_set]
    if exactly_missing:
        issues.append(
            {
                "code": "missing_exact_tool",
                "message": "Exact tool set is incomplete.",
                "tools": exactly_missing,
            }
        )

    min_count = expected.get("min_count")
    if min_count is not None:
        pool = set(
            expected.get("allowed")
            or expected.get("any_of")
            or expected.get("all_of")
            or actual
        )
        matching_count = sum(1 for name in actual if name in pool)
        if matching_count < int(min_count):
            issues.append(
                {
                    "code": "tool_min_count_not_met",
                    "message": "Minimum expected tool count was not met.",
                    "expected": int(min_count),
                    "actual": matching_count,
                }
            )
    else:
        matching_count = sum(
            1 for name in actual if not allowed or name in set(allowed)
        )

    if not expected:
        rule = "unspecified"
    elif expected.get("exactly"):
        rule = "exactly"
    elif expected.get("all_of") and expected.get("allowed"):
        rule = "all_of_allowed"
    elif expected.get("all_of"):
        rule = "all_of"
    elif expected.get("any_of"):
        rule = "any_of"
    elif expected.get("allowed"):
        rule = "allowed"
    elif expected.get("min_count") is not None:
        rule = "min_count"
    else:
        rule = "custom"

    return {
        "ok": not issues,
        "rule": rule,
        "expectation": expected,
        "actual": actual,
        "missing": missing,
        "extra": extra,
        "matching_count": matching_count,
        "issues": issues,
    }


def _clean_tool_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    return [str(item) for item in list(value or []) if str(item)]


class RunPolicy(BaseModel):
    """Execution policy resolved from defaults + mode + per-run overrides."""

    model_config = ConfigDict(extra="forbid")

    max_turns: int = 8
    max_tool_calls: int | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    tool_choice: str = "auto"
    repair: bool = True
    max_repairs: int = 2
    finalize: Literal["never", "on_max_turns", "after_required_tools"] = "on_max_turns"
    trace: Literal["compact", "full"] = "compact"
    strict: bool = True

    @field_validator("max_turns")
    @classmethod
    def validate_positive_max_turns(cls, value: int) -> int:
        if int(value) < 1:
            raise ValueError("max_turns must be >= 1")
        return int(value)

    @field_validator("max_tool_calls")
    @classmethod
    def validate_optional_tool_limit(cls, value: int | None) -> int | None:
        if value is not None and int(value) < 0:
            raise ValueError("max_tool_calls must be >= 0 when provided")
        return int(value) if value is not None else None

    @field_validator("max_tokens")
    @classmethod
    def validate_optional_token_limit(cls, value: int | None) -> int | None:
        if value is not None and int(value) < 1:
            raise ValueError("max_tokens must be >= 1 when provided")
        return int(value) if value is not None else None

    @classmethod
    def validate_optional_positive_ints(cls, value: int | None) -> int | None:
        """Retain the 2.0 validation helper while field validators specialize bounds."""

        if value is not None and int(value) < 1:
            raise ValueError("value must be >= 1 when provided")
        return int(value) if value is not None else None

    @field_validator("max_repairs")
    @classmethod
    def validate_non_negative_repairs(cls, value: int) -> int:
        if int(value) < 0:
            raise ValueError("max_repairs must be >= 0")
        return int(value)

    @field_validator("temperature")
    @classmethod
    def validate_temperature_range(cls, value: float | None) -> float | None:
        if value is None:
            return None
        number = float(value)
        if number < 0 or number > 2:
            raise ValueError("temperature must be between 0 and 2")
        return number

    @field_validator("tool_choice")
    @classmethod
    def validate_tool_choice(cls, value: str) -> str:
        clean = str(value or "").strip()
        if not clean:
            raise ValueError("tool_choice must be non-empty")
        return clean

    @classmethod
    def coerce(cls, value: "RunPolicy | dict[str, Any] | None") -> "RunPolicy":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        return cls.model_validate(value)

    @classmethod
    def for_mode(cls, mode: str = "default") -> "RunPolicy":
        presets: dict[str, dict[str, Any]] = {
            "default": {},
            "fast": {
                "max_turns": 4,
                "max_tokens": 500,
                "repair": False,
                "trace": "compact",
            },
            "audit": {"max_turns": 10, "repair": True, "trace": "full", "strict": True},
            "debug": {
                "max_turns": 10,
                "repair": True,
                "trace": "full",
                "strict": False,
            },
            "eval": {
                "max_turns": 8,
                "temperature": 0.0,
                "repair": True,
                "trace": "compact",
            },
            "prod": {
                "max_turns": 8,
                "repair": True,
                "max_repairs": 1,
                "trace": "compact",
                "strict": True,
            },
        }
        if mode not in presets:
            raise ValueError(
                f"Unknown run mode '{mode}'. Use one of: {sorted(presets)}"
            )
        return cls(**presets[mode])

    def merge(self, overrides: "RunPolicy | dict[str, Any] | None") -> "RunPolicy":
        if overrides is None:
            return self
        if isinstance(overrides, RunPolicy):
            data = overrides.model_dump(exclude_unset=True)
        else:
            data = dict(overrides)
        base = self.model_dump()
        base.update({key: value for key, value in data.items() if value is not None})
        return RunPolicy(**base)

    def check(
        self,
        *,
        contract: AgentContract | dict[str, Any] | None = None,
        available_tools: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> ValidationResult:
        """Validate this policy against an optional declarative contract."""

        return validate_contract_policy(contract, self, available_tools=available_tools)


def resolve_policy(
    *,
    mode: str,
    agent_policy: RunPolicy | dict[str, Any] | None = None,
    run_config: RunPolicy | dict[str, Any] | None = None,
) -> RunPolicy:
    return RunPolicy.for_mode(mode).merge(agent_policy).merge(run_config)


class ContractPolicySpec(BaseModel):
    """Named, notebook-friendly bundle of an ``AgentContract`` and ``RunPolicy``.

    The object is intentionally small.  It does not introduce a new execution
    layer; it only makes contract + policy intent reusable and inspectable.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    contract: AgentContract = Field(default_factory=AgentContract)
    policy: RunPolicy = Field(default_factory=RunPolicy)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        clean = str(value or "").strip()
        if not clean:
            raise ValueError("ContractPolicySpec.name must be non-empty")
        return clean

    @classmethod
    def coerce(
        cls, value: "ContractPolicySpec | dict[str, Any]"
    ) -> "ContractPolicySpec":
        if isinstance(value, cls):
            return value
        return cls.model_validate(value)

    def check(
        self,
        *,
        available_tools: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> ValidationResult:
        return validate_contract_policy(
            self.contract, self.policy, available_tools=available_tools
        )

    def raise_if_failed(
        self,
        *,
        available_tools: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> "ContractPolicySpec":
        self.check(available_tools=available_tools).raise_if_failed()
        return self

    def agent_kwargs(self) -> dict[str, Any]:
        """Return kwargs accepted by ``lab.agent(...)`` / ``system.agent(...)``."""

        return {"contract": self.contract, "policy": self.policy}

    def describe(self) -> dict[str, Any]:
        """Return a compact JSON-like description for notebooks and logs."""

        validation = self.check()
        return {
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
            "contract": self.contract.model_dump(mode="json"),
            "policy": self.policy.model_dump(mode="json"),
            "validation": validation.to_dict(),
            "metadata": dict(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def validate_contract_policy(
    contract: AgentContract | dict[str, Any] | None = None,
    policy: RunPolicy | dict[str, Any] | None = None,
    *,
    available_tools: list[str] | tuple[str, ...] | set[str] | None = None,
) -> ValidationResult:
    """Validate declarative contract and policy consistency before execution.

    ``RunResult.validate(...)`` answers "did this run satisfy the contract?".
    This function answers "is the declared contract/policy internally possible?".
    """

    contract_obj = AgentContract.coerce(contract)
    policy_obj = RunPolicy.coerce(policy)
    result = ValidationResult(ok=True)
    available = (
        {str(name) for name in available_tools or [] if str(name)}
        if available_tools is not None
        else None
    )

    must_call = _clean_tool_names(contract_obj.must_call)
    must_not_call = _clean_tool_names(contract_obj.must_not_call)
    must_call_set = set(must_call)
    must_not_call_set = set(must_not_call)
    overlap = sorted(must_call_set & must_not_call_set)
    if overlap:
        result.add(
            "contract_tool_conflict",
            "A tool cannot be required and forbidden at the same time.",
            path="contract.must_call",
            meta={"tools": overlap},
        )

    for field_name, names in (
        ("must_call", must_call),
        ("must_not_call", must_not_call),
    ):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            result.add(
                "duplicate_contract_tool",
                f"Duplicate tool name(s) in contract.{field_name}.",
                severity="warning",
                path=f"contract.{field_name}",
                meta={"tools": duplicates},
            )

    expectation = normalize_tool_expectation(contract_obj.tool_expectation)
    expected_names = _tool_names_from_expectation(expectation)
    referenced_names = sorted(must_call_set | must_not_call_set | expected_names)
    if available is not None:
        unknown = [name for name in referenced_names if name not in available]
        if unknown:
            result.add(
                "contract_references_unknown_tool",
                "Contract references tool(s) that are not available.",
                path="contract.tools",
                meta={"tools": unknown, "available_tools": sorted(available)},
            )

    allowed = set(expectation.get("allowed") or expectation.get("exactly") or [])
    if allowed:
        required_outside_allowed = sorted(
            name for name in must_call_set if name not in allowed
        )
        if required_outside_allowed:
            result.add(
                "required_tool_not_allowed",
                "Contract requires tool(s) that the tool expectation does not allow.",
                path="contract.tool_expectation.allowed",
                meta={"tools": required_outside_allowed, "allowed": sorted(allowed)},
            )

        forbidden_inside_exact = sorted(
            name
            for name in must_not_call_set
            if name in set(expectation.get("exactly") or [])
        )
        if forbidden_inside_exact:
            result.add(
                "forbidden_tool_in_exact_expectation",
                "Contract forbids tool(s) that the exact expectation requires.",
                path="contract.tool_expectation.exactly",
                meta={"tools": forbidden_inside_exact},
            )

    required_min = _minimum_required_tool_calls(contract_obj, expectation)
    if (
        policy_obj.max_tool_calls is not None
        and required_min > policy_obj.max_tool_calls
    ):
        result.add(
            "policy_tool_budget_too_small",
            "RunPolicy.max_tool_calls is smaller than the contract's minimum required tool calls.",
            path="policy.max_tool_calls",
            meta={
                "minimum_required": required_min,
                "max_tool_calls": policy_obj.max_tool_calls,
            },
        )

    has_required_tools = (
        required_min > 0 or bool(must_call_set) or bool(expectation.get("any_of"))
    )
    if (
        contract_obj.completion == "when_required_tools_satisfied"
        and not has_required_tools
    ):
        result.add(
            "completion_without_required_tools",
            "Contract completion waits for required tools, but no required tool rule is declared.",
            severity="warning",
            path="contract.completion",
        )
    if policy_obj.finalize == "after_required_tools" and not has_required_tools:
        result.add(
            "finalize_without_required_tools",
            "Policy finalizes after required tools, but no required tool rule is declared.",
            severity="warning",
            path="policy.finalize",
        )
    if policy_obj.repair is False and contract_obj.failure_policy in {
        "no_unresolved",
        "fail_fast",
    }:
        result.add(
            "strict_failure_without_repair",
            "Failure policy requires no unresolved tool failures while repair is disabled.",
            severity="warning",
            path="policy.repair",
        )

    return result


def _tool_names_from_expectation(expectation: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("any_of", "all_of", "exactly", "allowed"):
        names.update(_clean_tool_names(expectation.get(key) or []))
    return names


def _minimum_required_tool_calls(
    contract: AgentContract, expectation: dict[str, Any]
) -> int:
    candidates = [len(set(_clean_tool_names(contract.must_call)))]
    if expectation.get("all_of"):
        candidates.append(len(set(_clean_tool_names(expectation["all_of"]))))
    if expectation.get("exactly"):
        candidates.append(len(set(_clean_tool_names(expectation["exactly"]))))
    if expectation.get("min_count") is not None:
        candidates.append(int(expectation["min_count"]))
    if expectation.get("any_of"):
        candidates.append(1)
    return max(candidates or [0])
