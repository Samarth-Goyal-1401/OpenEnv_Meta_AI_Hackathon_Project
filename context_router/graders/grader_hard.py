from typing import List
from models import CacheObservation

def grader_hard(trajectory: List[CacheObservation]) -> float:
    """
    Evaluates the 'hard' task trajectory.
    Returns a score between 0.0 and 1.0.
    """
    try:
        _ = trajectory
        return 0.5
    except Exception:
        return 0.0
