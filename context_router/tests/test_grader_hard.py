from context_router.graders.grader_hard import grader_hard


def _block(block_type: str, block_id: int) -> dict:
    return {
        "block_id": block_id,
        "block_type": block_type,
        "attention_score": 0.8,
        "token_count": 200,
        "age": 0,
    }


def _obs(vram: float, oom: bool, blocks: list[dict], done: bool) -> dict:
    return {
        "vram_utilization": vram,
        "incoming_tokens": 150,
        "memory_blocks": blocks,
        "oom_triggered": oom,
        "message": "ok",
        "done": done,
        "reward": 0.0,
    }


PERFECT = [
    _obs(0.25, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False)
] * 50

EMPTY = []

PARTIAL = [
    _obs(0.92, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False),
    _obs(0.70, False, [_block("system_prompt", 0)], False),
    _obs(0.65, False, [_block("system_prompt", 0)], True),
]


def test_perfect_returns_one() -> None:
    assert grader_hard(PERFECT) == 1.0


def test_empty_returns_zero() -> None:
    assert grader_hard(EMPTY) == 0.0


def test_partial_between_zero_and_one() -> None:
    score = grader_hard(PARTIAL)
    assert 0.0 < score < 1.0


def test_returns_float() -> None:
    assert isinstance(grader_hard(PARTIAL), float)


def test_deterministic() -> None:
    assert grader_hard(PARTIAL) == grader_hard(PARTIAL)


def test_clamped() -> None:
    corrupted = [_obs(10.0, True, [], True)]
    score = grader_hard(corrupted)
    assert 0.0 <= score <= 1.0

