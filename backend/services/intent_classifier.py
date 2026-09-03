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
        r"\b(performance|compute|save money|jobs consume)\b",
        r"\bdownsize\b",
    ],
}


def classify_intent_details(query: str, category_hint: str | None = None) -> tuple[str, float]:
    if category_hint and category_hint in CATEGORIES:
        return category_hint, 1.0

    query_lower = query.lower()
    scores = {cat: 0 for cat in CATEGORIES}

    for cat, patterns in CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                scores[cat] += 1

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "pipeline_status", 0.4

    total = sum(scores.values())
    confidence = scores[best] / total
    tied = sum(1 for value in scores.values() if value == scores[best])
    if tied > 1:
        confidence *= 0.7
    return best, round(min(confidence, 1.0), 2)


def classify_intent(query: str, category_hint: str | None = None) -> str:
    intent, _confidence = classify_intent_details(query, category_hint)
    return intent
