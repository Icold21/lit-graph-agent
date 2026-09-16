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
    Finds the optimal cutoff point using discrete drop-off and elbow detection.
    Accurately identifies the boundary BEFORE the curve drops into the low-impact tail.
    """
    n = len(scores)
    if n <= min_k:
        return min(n, max_k)

    if scores[0] == scores[-1]:
        return min(n, max_k)

    # Calculate first differences (drop-offs between consecutive papers)
    drops = [scores[i] - scores[i + 1] for i in range(n - 1)]

    # Find the index where the steepest drop occurs
    max_drop_idx = 0
    max_drop = -1.0
    for i, d in enumerate(drops):
        if d > max_drop:
            max_drop = d
            max_drop_idx = i

    # Cutoff preserves all elite papers up to the cliff
    optimal_k = max_drop_idx + 1
    return max(min_k, min(optimal_k, max_k, n))