from codedjinn.prompts.step_budget import normalize_max_steps


def test_normalize_max_steps_allows_zero() -> None:
    assert normalize_max_steps(0) == 0
    assert normalize_max_steps("0") == 0


def test_normalize_max_steps_clamps_negative_to_zero() -> None:
    assert normalize_max_steps(-1) == 0

