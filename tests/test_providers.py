import pytest

from lit_graph.llm.providers import UniversalLLMProvider


@pytest.mark.parametrize(
    "raw, expected_type",
    [
        ('{"a": 1}', dict),
        ('```json\n{"a": 1}\n```', dict),
        ('<think>reasoning</think>{"a": 1}', dict),
        ('prefix text {"a": 1} suffix', dict),
        ('[{"a": 1}]', list),
        ('not json at all', dict),
    ],
)
def test_json_sanitizer_handles_reasoning_models(raw, expected_type):
    parsed = UniversalLLMProvider._sanitize_and_parse_json(raw)
    assert isinstance(parsed, expected_type)


def test_empty_json_returns_an_empty_dict():
    assert UniversalLLMProvider._sanitize_and_parse_json("") == {}
