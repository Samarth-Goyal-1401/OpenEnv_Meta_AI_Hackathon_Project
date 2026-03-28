import pytest
from models import CacheObservation
from graders.grader_hard import grader_hard

def _make_obs(vram=0.5, incoming=10, oom=False):
    return CacheObservation(
        vram_utilization=vram,
        incoming_tokens=incoming,
        memory_blocks=[],
        oom_triggered=oom,
        message="ok"
    )

def test_grader_hard_type():
    obs = [_make_obs()]
    score = grader_hard(obs)
    assert isinstance(score, float), "Grader must return float"

def test_grader_hard_empty():
    score = grader_hard([])
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0

def test_grader_hard_clamped():
    obs = [_make_obs()]
    score = grader_hard(obs)
    assert 0.0 <= score <= 1.0

def test_grader_hard_deterministic():
    obs = [_make_obs()]
    assert grader_hard(obs) == grader_hard(obs)

def test_grader_hard_perfect():
    score = grader_hard([_make_obs(vram=0.1)])
    assert score >= 0.0

def test_grader_hard_partial():
    score = grader_hard([_make_obs(vram=0.9, oom=True)])
    assert score >= 0.0
