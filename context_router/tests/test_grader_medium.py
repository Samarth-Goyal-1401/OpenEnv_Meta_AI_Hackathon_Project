import pytest
from models import CacheObservation
from graders.grader_medium import grader_medium

def _make_obs(vram=0.5, incoming=10, oom=False):
    return CacheObservation(
        vram_utilization=vram,
        incoming_tokens=incoming,
        memory_blocks=[],
        oom_triggered=oom,
        message="ok"
    )

def test_grader_medium_type():
    obs = [_make_obs()]
    score = grader_medium(obs)
    assert isinstance(score, float), "Grader must return float"

def test_grader_medium_empty():
    score = grader_medium([])
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0

def test_grader_medium_clamped():
    obs = [_make_obs()]
    score = grader_medium(obs)
    assert 0.0 <= score <= 1.0

def test_grader_medium_deterministic():
    obs = [_make_obs()]
    assert grader_medium(obs) == grader_medium(obs)

def test_grader_medium_perfect():
    score = grader_medium([_make_obs(vram=0.1)])
    assert score >= 0.0

def test_grader_medium_partial():
    score = grader_medium([_make_obs(vram=0.9, oom=True)])
    assert score >= 0.0
