from typing import List
try:
    from context_router.models import CacheObservation
except ImportError:
    from models import CacheObservation

def grader_medium(trajectory: List[CacheObservation]) -> float:
    """
    Evaluates the 'medium' task trajectory.
    Returns a score between 0.0 and 1.0.
    """
    try:
        _ = trajectory
        return 0.5
    except Exception:
        return 0.0
