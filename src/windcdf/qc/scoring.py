"""Optional quality scoring logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.models.report import QCReport


def compute_quality_score(report: QCReport) -> float:
    """Compute overall quality score for a dataset.

    Args:
        report: QC report with flags.

    Returns:
        Score between 0.0 (poor) and 1.0 (excellent).
    """
    if report.total_flags == 0:
        return 1.0

    # Simple scoring: penalize based on severity
    severity_weights = {
        "GOOD": 0.0,
        "SUSPECT": 0.1,
        "BAD": 0.5,
        "MISSING": 0.3,
    }

    total_penalty = sum(
        severity_weights.get(f.severity.name, 0.0)
        for f in report.flags
    )

    # Normalize by expected data points (rough estimate)
    # This is a simplified scoring mechanism
    max_penalty = len(report.flags)
    if max_penalty == 0:
        return 1.0

    score = max(0.0, 1.0 - (total_penalty / max_penalty))
    return round(score, 3)


def compute_variable_scores(report: QCReport) -> dict[str, float]:
    """Compute quality score per variable.

    Args:
        report: QC report with flags.

    Returns:
        Dictionary of variable names to scores.
    """
    scores = {}
    for var in report.variables_checked:
        var_flags = report.get_flags_for_variable(var)
        if not var_flags:
            scores[var] = 1.0
        else:
            # Create a mini-report for scoring
            var_report = QCReport(
                filepath=report.filepath,
                variables_checked=[var],
            )
            var_report.flags = var_flags
            scores[var] = compute_quality_score(var_report)

    return scores
