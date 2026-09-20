import copy

import pytest

from scripts.two_phase_semantic_application import (
    compact_judge_payload,
    literal_contract,
    run_case,
    validate_literal_answer,
)


@pytest.mark.parametrize(
    "operands,value,text,length",
    [
        ([2, 3], 6, "6", 1),
        ([17, 19], 323, "323", 3),
        ([-12, 10], -120, "-120", 4),
        ([0, 999], 0, "0", 1),
        ([111, 111], 12321, "12321", 5),
    ],
)
def test_literal_requirements_are_derived_not_memorized(operands, value, text, length):
    contract = literal_contract(operands)
    assert (
        contract["expected_value"],
        contract["expected_text"],
        contract["expected_length"],
    ) == (value, text, length)
    validate_literal_answer(f"Quiet stars\n{text}\nNumbers sing", contract)
    with pytest.raises(ValueError, match="literal_middle_value_mismatch"):
        validate_literal_answer(f"Quiet stars\n{value + 1}\nNumbers sing", contract)


@pytest.mark.parametrize("operands", [[True, 3], [2.0, 3], [2], [1, 2, 3]])
def test_rejects_ambiguous_case_data(operands):
    with pytest.raises(ValueError, match="two_integer_operands_required"):
        literal_contract(operands)


@pytest.mark.parametrize(
    "answer,reason",
    [
        ("Quiet stars\n323 \nNumbers sing", "literal_middle_value_mismatch"),
        ("Quiet stars\n3\nNumbers sing", "literal_middle_value_mismatch"),
        ("Quiet stars\n323\nNumbers sing\n", "literal_line_count_mismatch"),
    ],
)
def test_near_negatives_fail_for_the_correct_reason(answer, reason):
    contract = literal_contract([17, 19])
    validate_literal_answer("Quiet stars\n323\nNumbers sing", contract)
    with pytest.raises(ValueError, match=reason):
        validate_literal_answer(answer, contract)


def test_success_flag_cannot_hide_tampering_before_judgment():
    original = run_case("python-runtime", "native", "python-runtime")
    assert (
        compact_judge_payload(original)["evaluation_contract"]["expected_length"] == 3
    )
    changed = copy.deepcopy(original)
    changed["answer"] = "Quiet stars\n3\nNumbers sing"
    with pytest.raises(ValueError, match="literal_middle_value_mismatch"):
        compact_judge_payload(changed)
    changed = copy.deepcopy(original)
    changed["selection"]["payload_json"] = '{"product": 3}'
    with pytest.raises(ValueError, match="selected_evidence_value_mismatch"):
        compact_judge_payload(changed)
