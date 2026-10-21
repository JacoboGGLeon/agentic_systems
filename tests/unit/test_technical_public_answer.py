import pytest

from agentic_systems.results import is_technical_public_answer


@pytest.mark.parametrize(
    "answer,expected",
    [
        ('{"answer": "Verified product: 323"}', True),
        ('{"unrelated_business_field": 323}', False),
    ],
)
def test_structured_public_answer_detection_projects_only_recognized_fields(
    answer, expected
):
    assert is_technical_public_answer(answer) is expected
