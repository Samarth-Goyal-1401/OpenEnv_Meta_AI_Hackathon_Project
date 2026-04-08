from context_router.graders.grader_easy import grader_easy


PERFECT = [
    {
        "vram_utilization": 1.00,
        "incoming_tokens": 120,
        "memory_blocks": [],
        "oom_triggered": False,
        "message": "start",
        "done": False,
        "reward": 0.0,
    }
] * 49 + [
    {
        "vram_utilization": 0.00,
        "incoming_tokens": 80,
        "memory_blocks": [],
        "oom_triggered": False,
        "message": "target reached",
        "done": True,
        "reward": 0.0,
    },
]

EMPTY = []

PARTIAL = [
    {
        "vram_utilization": 0.90,
        "incoming_tokens": 140,
        "memory_blocks": [],
        "oom_triggered": False,
        "message": "start",
        "done": False,
        "reward": 0.0,
    },
    {
        "vram_utilization": 0.62,
        "incoming_tokens": 110,
        "memory_blocks": [],
        "oom_triggered": False,
        "message": "improved but above target",
        "done": True,
        "reward": 0.0,
    },
]


def test_perfect_returns_high() -> None:
    assert grader_easy(PERFECT) >= 0.98


def test_empty_returns_baseline() -> None:
    assert grader_easy(EMPTY) == 0.01


def test_partial_between_zero_and_one() -> None:
    score = grader_easy(PARTIAL)
    assert 0.0 < score < 1.0


def test_returns_float() -> None:
    assert isinstance(grader_easy(PARTIAL), float)


def test_deterministic() -> None:
    assert grader_easy(PARTIAL) == grader_easy(PARTIAL)


def test_clamped() -> None:
    corrupted = [{"vram_utilization": -5.0, "oom_triggered": False}]
    score = grader_easy(corrupted)
    assert 0.0 <= score <= 1.0


def test_better_trajectory_beats_worse() -> None:
    worse = [
        {
            "vram_utilization": 0.95,
            "incoming_tokens": 100,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.80,
            "incoming_tokens": 100,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    better = [
        {
            "vram_utilization": 0.95,
            "incoming_tokens": 100,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.40,
            "incoming_tokens": 100,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    worse_score = grader_easy(worse)
    better_score = grader_easy(better)
    assert better_score > worse_score


def test_oom_penalty_consistency() -> None:
    no_oom = [
        {
            "vram_utilization": 0.80,
            "oom_triggered": False,
            "memory_blocks": [],
            "done": True,
        },
    ]
    with_oom = [
        {
            "vram_utilization": 0.80,
            "oom_triggered": True,
            "memory_blocks": [],
            "done": True,
        },
    ]
    score_no_oom = grader_easy(no_oom)
    score_with_oom = grader_easy(with_oom)
    assert score_with_oom < score_no_oom


def test_stress_consistency() -> None:
    trajectory = [
        {
            "vram_utilization": 0.85,
            "incoming_tokens": 100,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.60,
            "incoming_tokens": 80,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": "",
            "done": False,
            "reward": 0.0,
        },
        {
            "vram_utilization": 0.45,
            "incoming_tokens": 60,
            "memory_blocks": [],
            "oom_triggered": False,
            "message": "",
            "done": True,
            "reward": 0.0,
        },
    ]
    scores = [grader_easy(trajectory) for _ in range(10)]
    assert len(set(scores)) == 1, f"Inconsistent scores: {scores}"
