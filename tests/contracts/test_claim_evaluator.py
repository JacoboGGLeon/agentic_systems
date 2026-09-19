import pytest
from scripts.claim_evaluator import aggregate, validate_partition
from scripts.claim_evaluator import build, combine_relations

EVIDENCE = [{"id": "event-a", "ok": True, "output": {"quantity": 47}}]


@pytest.mark.parametrize(
    "framework", ["native", "langgraph", "openai-agents", "strands"]
)
def test_public_tool_callbacks_preserve_schema_fields(framework):
    evaluator = build("ollama-runtime", framework, "offline-model")
    partition, factuality, support, contradiction, clarity = evaluator.tools
    assert partition.run({"fragments": ["First.", "Second."]}).data == {
        "fragments": ["First.", "Second."]
    }
    assert factuality.run({"factual": False}).data == {"factual": False}
    assert support.run(
        {"all_assertions_supported": True, "evidence_ids": ["event-a"]}
    ).data == {
        "established": True,
        "evidence_ids": ["event-a"],
    }
    assert contradiction.run(
        {"any_assertion_contradicted": False, "evidence_ids": []}
    ).data == {"established": False, "evidence_ids": []}
    assert not contradiction.run(
        {"all_assertions_supported": True, "evidence_ids": ["event-a"]}
    ).ok
    assert clarity.run({"clear": False}).data == {"clear": False}
    assert not partition.run({"fragments": []}).ok
    assert evaluator.audit_tool.run({"coherent": False}).data == {"coherent": False}


def test_partition_allows_only_whitespace_between_verbatim_fragments():
    assert validate_partition(" One.\nTwo. ", ["One.", "Two."]) == ["One.", "Two."]


@pytest.mark.parametrize(
    "fragments", [["One."], ["Two.", "One."], ["Other.", "Two."], ["", "One. Two."]]
)
def test_omission_reorder_invention_and_empty_are_rejected(fragments):
    with pytest.raises(ValueError):
        validate_partition("One. Two.", fragments)


@pytest.mark.parametrize(
    "status,expected",
    [
        ("supported", "pass"),
        ("contradicted", "fail"),
        ("unknown", "unknown"),
        ("nonfactual", "unknown"),
    ],
)
def test_aggregate_preserves_semantic_uncertainty(status, expected):
    refs = [] if status == "nonfactual" else ["event-a"]
    result = aggregate(
        "A claim.",
        ["A claim."],
        [{"status": status, "evidence_ids": refs}],
        EVIDENCE,
        {"clear": True},
    )
    assert result["grounding"] == expected
    assert not result["semantic_completeness_proven"]
    assert not result["release_approved"]
    if refs:
        result["records"][0]["observed_records"][0]["output"]["quantity"] = 0
    assert EVIDENCE[0]["output"]["quantity"] == 47


def test_nonfactual_references_are_rejected_not_silently_removed():
    with pytest.raises(ValueError, match="nonfactual_evidence_reference"):
        aggregate(
            "Courtesy.",
            ["Courtesy."],
            [{"status": "nonfactual", "evidence_ids": ["event-a"]}],
            EVIDENCE,
            {"clear": True},
        )


def test_unknown_can_preserve_absence_of_any_evidence():
    result = aggregate(
        "A cause.",
        ["A cause."],
        [{"status": "unknown", "evidence_ids": []}],
        [],
        {"clear": True},
    )
    assert result["grounding"] == "unknown"


@pytest.mark.parametrize("refs", [[], ["foreign"], ["event-a", "event-a"]])
def test_invalid_references_cannot_approve(refs):
    with pytest.raises(ValueError):
        aggregate(
            "Claim",
            ["Claim"],
            [{"status": "supported", "evidence_ids": refs}],
            EVIDENCE,
            {"clear": True},
        )


def test_correct_fact_does_not_override_a_contradiction():
    result = aggregate(
        "Value. Failure.",
        ["Value.", "Failure."],
        [
            {"status": s, "evidence_ids": ["event-a"]}
            for s in ["supported", "contradicted"]
        ],
        EVIDENCE,
        {"clear": True},
    )
    assert result["grounding"] == "fail"


@pytest.mark.parametrize("coherent", [False, True])
def test_partition_audit_blocks_before_contrast(monkeypatch, coherent):
    from agentic_systems.agents import Agent

    calls = []
    payloads = {
        "partition": {"fragments": ["A claim."]},
        "audit_partition": {"coherent": coherent},
        "factuality": {"factual": True},
        "support": {"all_assertions_supported": True, "evidence_ids": ["event-a"]},
        "contradiction": {"any_assertion_contradicted": False, "evidence_ids": []},
        "clarity": {"clear": True},
    }

    def scripted(self, *args, **kwargs):
        calls.append(self.name)
        return self.available_tools()[0].run(payloads[self.name])

    monkeypatch.setattr(Agent, "run", scripted)
    result = build("ollama-runtime", "native", "offline-model").evaluate(
        "A claim.", EVIDENCE
    )
    assert result["execution_ok"] is coherent
    if not coherent:
        assert result["failure"] == "incoherent_partition"
        assert calls == ["partition", "audit_partition"]
    else:
        assert calls == [
            "partition",
            "audit_partition",
            "factuality",
            "support",
            "contradiction",
            "clarity",
        ]


@pytest.mark.parametrize(
    "support,contradiction,expected",
    [
        (True, False, "supported"),
        (False, True, "contradicted"),
        (False, False, "unknown"),
    ],
)
def test_relations_use_three_valued_logic(support, contradiction, expected):
    def relation(flag):
        return {"established": flag, "evidence_ids": ["event-a"] if flag else []}

    result = combine_relations(
        {"factual": True}, relation(support), relation(contradiction)
    )
    assert result["status"] == expected


@pytest.mark.parametrize(
    "positive,negative,error",
    [
        (
            {"established": True, "evidence_ids": ["a"]},
            {"established": True, "evidence_ids": ["b"]},
            "inconsistent_relation_decisions",
        ),
        (
            {"established": False, "evidence_ids": ["a"]},
            {"established": False, "evidence_ids": []},
            "relation_reference_mismatch",
        ),
        (
            {"established": True, "evidence_ids": []},
            {"established": False, "evidence_ids": []},
            "relation_reference_mismatch",
        ),
        (
            {"established": True, "evidence_ids": ["a", "a"]},
            {"established": False, "evidence_ids": []},
            "duplicate_relation_reference",
        ),
        (None, None, "missing_relation_decision"),
    ],
)
def test_invalid_decisions_do_not_become_semantic_verdicts(positive, negative, error):
    with pytest.raises(ValueError, match=error):
        combine_relations({"factual": True}, positive, negative)


def test_nonfactual_decision_needs_no_evidence_review():
    assert combine_relations({"factual": False}) == {
        "status": "nonfactual",
        "evidence_ids": [],
    }
    with pytest.raises(ValueError, match="unexpected_nonfactual_relation"):
        combine_relations(
            {"factual": False}, {"established": False, "evidence_ids": []}
        )


def test_factuality_receives_only_target_and_nonfactual_skips_relations(monkeypatch):
    import json
    from agentic_systems.agents import Agent

    calls = []
    payloads = {
        "partition": {"fragments": ["Courtesy."]},
        "audit_partition": {"coherent": True},
        "factuality": {"factual": False},
        "clarity": {"clear": True},
    }

    def scripted(self, payload, **kwargs):
        calls.append(self.name)
        if self.name == "factuality":
            assert json.loads(payload) == {"target_text": "Courtesy."}
        return self.available_tools()[0].run(payloads[self.name])

    monkeypatch.setattr(Agent, "run", scripted)
    report = build("ollama-runtime", "native", "offline-model").evaluate(
        "Courtesy.", EVIDENCE
    )
    assert report["execution_ok"]
    assert report["verdict"]["grounding"] == "unknown"
    assert calls == ["partition", "audit_partition", "factuality", "clarity"]
