import math
from datetime import datetime
from typing import List

from ..models import Paper


def compute_scientific_metrics(paper: Paper, current_year: int | None = None) -> float:
    """
    Calculates objective bibliometric metrics:
    1. Citation Velocity (Annual Rate)
    2. Influential Citation Ratio
    3. Log-scaled Normalized Scientific Impact Score
    """
    if current_year is None:
        current_year = datetime.now().year

    age = max(1, current_year - (paper.year or current_year))

    # 1. Velocity (Citations per year)
    paper.citation_velocity = round(paper.citation_count / age, 2)

    # 2. Ratio of high-impact citations
    paper.influential_ratio = round(
        (paper.influential_citation_count + 1) / (paper.citation_count + 1), 3
    )

    # 3. Composite Objective Score: Velocity (40%) + Log Volume (35%) + Impact Quality (25%)
    log_volume = math.log10(paper.citation_count + 1)
    score = (
        (min(paper.citation_velocity, 100.0) * 0.40) +
        (log_volume * 4.0) +
        (paper.influential_ratio * 10.0 * 0.25)
    )

    paper.objective_scientific_score = round(score, 3)
    return paper.objective_scientific_score


def find_elbow_cutoff(scores: List[float], min_k: int = 3, max_k: int = 8) -> int:
    """
    Finds the optimal cutoff using an elbow/knee heuristic based on the change
    of consecutive score drops (a discrete Kneedle-style second derivative).

    The knee is the point where a steep head transitions into a flat tail.  We
    compute first differences (drops between ranked papers), then their change
    (curvature).  The largest positive curvature marks the boundary right
    before the low-impact tail.

    ``min_k`` / ``max_k`` are hard bounds; the result always satisfies them.
    """
    n = len(scores)
    if n == 0:
        return 0

    max_k = max(1, min(max_k, n))
    min_k = max(1, min(min_k, max_k))
    if n <= min_k:
        return max_k

    # Scores are expected in descending order; the elbow is meaningless otherwise.
    ordered = sorted(scores, reverse=True)
    if ordered[0] == ordered[-1]:
        return max_k

    drops = [ordered[i] - ordered[i + 1] for i in range(n - 1)]
    curvature = [drops[i] - drops[i + 1] for i in range(len(drops) - 1)]

    if curvature:
        # A large positive curvature at i means the drop after rank i+1 is much
        # steeper than the next one, so the head ends after i+1 papers.
        knee_index = max(range(len(curvature)), key=lambda i: (curvature[i], -i))
        optimal_k = knee_index + 1
    else:
        optimal_k = min_k

    return max(min_k, min(optimal_k, max_k))
