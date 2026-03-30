from context_router.graders.grader_easy import grader_easy


PERFECT = [
    {
        "vram_utilization": 0.80,
        "incoming_tokens": 120,
        "memory_blocks": [],
        "oom_triggered": False,
        "message": "start",
        "done": False,
        "reward": 0.0,
    },
    {
        "vram_utilization": 0.30,
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


def test_perfect_returns_one() -> None:
    assert grader_easy(PERFECT) == 1.0


def test_empty_returns_zero() -> None:
    assert grader_easy(EMPTY) == 0.0


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

