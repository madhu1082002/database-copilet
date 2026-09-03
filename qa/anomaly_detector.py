"""Flag anomalous AI output patterns (proposal §10.3)."""

from __future__ import annotations

NO_DATA_PHRASES = (
    "no failure records",
    "no immediate optimization",
    "no data",
    "data is missing",
    "not available from the clusters api",
    "all recent runs may have succeeded",
)


def is_no_data_response(text: str) -> bool:
    if not text:
        return True
    lower = text.lower()
    return any(phrase in lower for phrase in NO_DATA_PHRASES)


def detect_output_anomaly(
    recent_responses: list[str],
    threshold: float = 0.9,
    min_samples: int = 5,
) -> dict:
    """
    If 90%+ of recent answers are 'no data available' style replies, flag an anomaly.
    """
    if not recent_responses:
        return {"anomaly": False, "reason": None, "no_data_rate": 0.0, "sample_size": 0}

    no_data = sum(1 for text in recent_responses if is_no_data_response(text))
    rate = no_data / len(recent_responses)
    flagged = rate >= threshold and len(recent_responses) >= min_samples
    return {
        "anomaly": flagged,
        "reason": "high_no_data_rate" if flagged else None,
        "no_data_rate": round(rate, 3),
        "sample_size": len(recent_responses),
    }
