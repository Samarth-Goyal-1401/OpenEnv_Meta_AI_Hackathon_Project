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


def test_better_trajectory_beats_worse() -> None:
    worse_trajectory = [
        _obs(
            0.92, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False
        ),
        _obs(0.85, False, [_block("system_prompt", 0)], False),
        _obs(0.80, False, [], True),
    ]
    better_trajectory = [
        _obs(
            0.92, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False
        ),
        _obs(
            0.70, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False
        ),
        _obs(
            0.50, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False
        ),
        _obs(
            0.25, False, [_block("system_prompt", 0), _block("code_snippet", 1)], True
        ),
    ]
    worse_score = grader_hard(worse_trajectory)
    better_score = grader_hard(better_trajectory)
    assert better_score > worse_score


def test_oom_penalty_consistency() -> None:
    no_oom = [_obs(0.50, False, [_block("system_prompt", 0)], True)]
    with_oom = [_obs(0.50, True, [_block("system_prompt", 0)], True)]
    score_no_oom = grader_hard(no_oom)
    score_with_oom = grader_hard(with_oom)
    assert score_with_oom < score_no_oom


def test_stress_consistency() -> None:
    trajectory = [
        _obs(
            0.85, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False
        ),
        _obs(
            0.60, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False
        ),
        _obs(
            0.45, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False
        ),
        _obs(
            0.30, False, [_block("system_prompt", 0), _block("code_snippet", 1)], True
        ),
    ]
    scores = [grader_hard(trajectory) for _ in range(10)]
    assert len(set(scores)) == 1, f"Inconsistent scores: {scores}"


def test_replacement_critical_blocks_score_lower() -> None:
    original = [
        _obs(
            0.85,
            False,
            [
                _block("system_prompt", 0),
                _block("code_snippet", 1),
                _block("rag_context", 2),
            ],
            False,
        ),
        _obs(
            0.32,
            False,
            [
                _block("system_prompt", 0),
                _block("code_snippet", 1),
                _block("rag_context", 2),
            ],
            True,
        ),
    ]
    replaced = [
        original[0],
        _obs(
            0.32,
            False,
            [
                _block("system_prompt", 10),
                _block("code_snippet", 11),
                _block("rag_context", 12),
            ],
            True,
        ),
    ]
    assert grader_hard(replaced) < grader_hard(original)


def test_late_retention_collapse_is_penalized() -> None:
    stable = [
        _obs(0.85, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False),
        _obs(0.60, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False),
        _obs(0.38, False, [_block("system_prompt", 0), _block("code_snippet", 1)], True),
    ]
    collapses_late = [
        _obs(0.85, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False),
        _obs(0.60, False, [_block("system_prompt", 0), _block("code_snippet", 1)], False),
        _obs(0.38, False, [_block("system_prompt", 0)], True),
    ]
    assert grader_hard(collapses_late) < grader_hard(stable)
