import pytest
from models import CacheObservation
from graders.grader_easy import grader_easy

def _make_obs(vram=0.5, incoming=10, oom=False):
    return CacheObservation(
        vram_utilization=vram,
        incoming_tokens=incoming,
        memory_blocks=[],
        oom_triggered=oom,
        message="ok"
    )

def test_grader_easy_type():
    obs = [_make_obs()]
    score = grader_easy(obs)
    assert isinstance(score, float), "Grader must return float"

def test_grader_easy_empty():
    score = grader_easy([])
    assert isinstance(score, float), "Grader must handle empty trajectory securely"
    assert 0.0 <= score <= 1.0, "Empty score must be clamped"

def test_grader_easy_clamped():
    obs = [_make_obs()]
    score = grader_easy(obs)
    assert 0.0 <= score <= 1.0, "Score must be bounded [0.0, 1.0]"

def test_grader_easy_deterministic():
    obs = [_make_obs()]
    score1 = grader_easy(obs)
    score2 = grader_easy(obs)
    assert score1 == score2, "Grader must return deterministic score for same trajectory"

def test_grader_easy_perfect():
    obs = [_make_obs(vram=0.1, incoming=10, oom=False)]
    score = grader_easy(obs)
    assert score >= 0.0, "Perfect simulation trajectory runs without exception"

def test_grader_easy_partial():
    obs = [_make_obs(vram=0.9, incoming=50, oom=True)]
    score = grader_easy(obs)
    assert score >= 0.0, "Partial simulation trajectory runs without exception"
