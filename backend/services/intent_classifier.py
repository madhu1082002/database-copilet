import re

CATEGORIES = {
    "pipeline_status": [
        r"\b(status|run|ran|today|last night|yesterday|successful|failed|show me)\b",
        r"\bwhich pipelines?\b",
        r"\bdid .+ (run|complete|finish)\b",
    ],
    "failure_diagnosis": [
        r"\b(why|what caused|root cause|error|fail|failure|diagnos)\b",
        r"\bshow error\b",
        r"\bwhat went wrong\b",
    ],
    "optimization": [
        r"\b(cost|reduce|optimize|optimization|savings|underutiliz)\b",
        r"\b(cluster|resource|cpu|memory|oversized|high resource)\b",
        r"\bperformance\b",
        r"\bcompute\b",
    ],
}


def classify_intent(query: str, category_hint: str | None = None) -> str:
    if category_hint and category_hint in CATEGORIES:
        return category_hint

    query_lower = query.lower()
    scores = {cat: 0 for cat in CATEGORIES}

    for cat, patterns in CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                scores[cat] += 1

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "pipeline_status"
    return best
