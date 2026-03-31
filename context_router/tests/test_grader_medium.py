from context_router.graders.grader_medium import grader_medium


def _block(block_type: str, attention: float, block_id: int) -> dict:
    return {
        "block_id": block_id,
        "block_type": block_type,
        "attention_score": attention,
        "token_count": 128,
        "age": 0,
    }


PERFECT = [
    {
        "vram_utilization": 0.85,
        "incoming_tokens": 120,
        "memory_blocks": [
            _block("system_prompt", 1.0, 1),
            _block("code_snippet", 0.9, 2),
        ],
        "oom_triggered": False,
        "message": "start",
        "done": False,
        "reward": 0.0,
    },
    {
        "vram_utilization": 0.30,
        "incoming_tokens": 90,
        "memory_blocks": [
            _block("system_prompt", 1.0, 1),
            _block("code_snippet", 0.85, 2),
        ],
        "oom_triggered": False,
        "message": "target reached",
        "done": True,
        "reward": 0.0,
    },
]

EMPTY = []

PARTIAL = [
    {
        "vram_utilization": 0.92,
        "incoming_tokens": 200,
        "memory_blocks": [
            _block("system_prompt", 1.0, 1),
            _block("code_snippet", 0.9, 2),
            _block("user_query", 0.7, 3),
        ],
        "oom_triggered": False,
        "message": "start",
        "done": False,
        "reward": 0.0,
    },
    {
        "vram_utilization": 0.55,
        "incoming_tokens": 180,
        "memory_blocks": [_block("system_prompt", 1.0, 1), _block("user_query", 0.7, 3)],
        "oom_triggered": False,
        "message": "partial progress",
        "done": True,
        "reward": 0.0,
    },
]


def test_perfect_returns_one() -> None:
    assert grader_medium(PERFECT) == 1.0


def test_empty_returns_zero() -> None:
    assert grader_medium(EMPTY) == 0.0


def test_partial_between_zero_and_one() -> None:
    score = grader_medium(PARTIAL)
    assert 0.0 < score < 1.0


def test_returns_float() -> None:
    assert isinstance(grader_medium(PARTIAL), float)


def test_deterministic() -> None:
    assert grader_medium(PARTIAL) == grader_medium(PARTIAL)


def test_clamped() -> None:
    corrupted = [{"vram_utilization": 99.0, "oom_triggered": True, "memory_blocks": []}]
    score = grader_medium(corrupted)
    assert 0.0 <= score <= 1.0


def test_better_trajectory_beats_worse() -> None:
    worse = [
        {
            "vram_utilization": 0.90,
            "incoming_tokens": 150,
            "memory_blocks": [_block("system_prompt", 1.0, 1), _block("small_talk", 0.1, 4)],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.70,
            "incoming_tokens": 150,
            "memory_blocks": [_block("small_talk", 0.1, 4)],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    better = [
        {
            "vram_utilization": 0.90,
            "incoming_tokens": 150,
            "memory_blocks": [
                _block("system_prompt", 1.0, 1),
                _block("code_snippet", 0.9, 2),
            ],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.35,
            "incoming_tokens": 150,
            "memory_blocks": [
                _block("system_prompt", 1.0, 1),
                _block("code_snippet", 0.85, 2),
            ],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    worse_score = grader_medium(worse)
    better_score = grader_medium(better)
    assert better_score > worse_score


def test_oom_penalty_consistency() -> None:
    no_oom = [
        {
            "vram_utilization": 0.50,
            "oom_triggered": False,
            "memory_blocks": [_block("system_prompt", 1.0, 1)],
            "done": True,
        },
    ]
    with_oom = [
        {
            "vram_utilization": 0.50,
            "oom_triggered": True,
            "memory_blocks": [_block("system_prompt", 1.0, 1)],
            "done": True,
        },
    ]
    score_no_oom = grader_medium(no_oom)
    score_with_oom = grader_medium(with_oom)
    assert score_with_oom < score_no_oom


def test_stress_consistency() -> None:
    trajectory = [
        {
            "vram_utilization": 0.85,
            "incoming_tokens": 100,
            "memory_blocks": [_block("system_prompt", 1.0, 1)],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.60,
            "incoming_tokens": 80,
            "memory_blocks": [_block("system_prompt", 1.0, 1)],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.42,
            "incoming_tokens": 60,
            "memory_blocks": [_block("system_prompt", 1.0, 1)],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    scores = [grader_medium(trajectory) for _ in range(10)]
    assert len(set(scores)) == 1, f"Inconsistent scores: {scores}"


def test_replacement_block_does_not_get_full_credit() -> None:
    original = [
        {
            "vram_utilization": 0.90,
            "incoming_tokens": 140,
            "memory_blocks": [
                _block("system_prompt", 1.0, 1),
                _block("code_snippet", 0.95, 2),
                _block("user_query", 0.70, 3),
            ],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.35,
            "incoming_tokens": 100,
            "memory_blocks": [
                _block("system_prompt", 1.0, 1),
                _block("code_snippet", 0.95, 2),
                _block("user_query", 0.70, 3),
            ],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    replaced = [
        original[0],
        {
            "vram_utilization": 0.35,
            "incoming_tokens": 100,
            "memory_blocks": [
                _block("system_prompt", 1.0, 99),
                _block("code_snippet", 0.95, 100),
                _block("user_query", 0.70, 101),
            ],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    assert grader_medium(replaced) < grader_medium(original)
