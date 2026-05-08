from datetime import datetime, timezone
from typing import Optional


def compute_health_score(data: dict) -> dict:
    scores = {}

    act = 0
    days = data.get("days_since_last_commit")
    if days is not None:
        if days <= 7:
            act += 20
        elif days <= 30:
            act += 15
        elif days <= 90:
            act += 10
        elif days <= 180:
            act += 5
        else:
            act += 0

    recent = data.get("recent_commit_count", 0)
    if recent >= 20:
        act += 20
    elif recent >= 10:
        act += 15
    elif recent >= 5:
        act += 10
    elif recent >= 1:
        act += 5

    scores["activity"] = min(act, 40)

    com = 0
    stars = data.get("stars", 0)
    if stars >= 1000:
        com += 8
    elif stars >= 100:
        com += 5
    elif stars >= 10:
        com += 2

    forks = data.get("forks", 0)
    if forks >= 200:
        com += 5
    elif forks >= 20:
        com += 3
    elif forks >= 1:
        com += 1

    contributors = data.get("contributors_count", 0)
    if contributors >= 10:
        com += 7
    elif contributors >= 5:
        com += 5
    elif contributors >= 2:
        com += 3
    elif contributors >= 1:
        com += 1

    scores["community"] = min(com, 20)

    maint = 0
    avg_close = data.get("avg_issue_close_days")
    if avg_close is not None:
        if avg_close <= 3:
            maint += 8
        elif avg_close <= 14:
            maint += 5
        elif avg_close <= 30:
            maint += 3
        else:
            maint += 1
    else:
        maint += 3

    if data.get("license") and data["license"] != "None":
        maint += 6

    open_prs = data.get("open_prs_count", 0)
    if open_prs <= 5:
        maint += 6
    elif open_prs <= 20:
        maint += 3

    scores["maintenance"] = min(maint, 20)

    docs = 0
    if data.get("description") and data["description"] != "No description provided.":
        docs += 3
    if data.get("has_wiki"):
        docs += 2
    if data.get("homepage"):
        docs += 2
    if data.get("topics"):
        docs += 3
    scores["docs"] = min(docs, 10)

    ci = 0
    if data.get("has_workflows"):
        ci += 6
    if data.get("total_releases", 0) >= 1:
        ci += 4
    scores["ci"] = min(ci, 10)

    penalty = 0
    if data.get("archived"):
        penalty += 30
    if data.get("disabled"):
        penalty += 30

    total = sum(scores.values()) - penalty
    total = max(0, min(100, total))
    scores["total"] = total

    if data.get("archived") or data.get("disabled"):
        status = "Archived / Inactive"
    elif days is None or days > 365:
        status = "Abandoned"
    elif days > 180:
        status = "Stale"
    elif days > 90:
        status = "Slow"
    elif days > 30:
        status = "Moderately Active"
    else:
        status = "Actively Maintained"

    scores["status"] = status

    return scores


def compute_commit_frequency(commit_dates: list[str]) -> dict:
    if not commit_dates:
        return {}

    from collections import defaultdict
    weekly = defaultdict(int)
    now = datetime.now(timezone.utc)

    for ds in commit_dates:
        try:
            dt = datetime.fromisoformat(ds)
            diff_days = (now - dt).days
            week = diff_days // 7
            if week < 4:
                weekly[f"Week -{week}"] += 1
        except ValueError:
            pass

    return dict(sorted(weekly.items()))
