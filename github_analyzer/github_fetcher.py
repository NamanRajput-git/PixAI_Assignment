import os
import requests
from datetime import datetime, timezone
from typing import Optional


GITHUB_API_BASE = "https://api.github.com"


def _get_headers(token: Optional[str] = None) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    tok = token or os.getenv("GITHUB_TOKEN", "")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return headers


def _get(url: str, headers: dict, params: dict = None) -> Optional[dict | list]:
    """Generic GET with basic error handling."""
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise ConnectionError(f"GitHub API error: {e}") from e


def fetch_repo_data(owner: str, repo: str, token: Optional[str] = None) -> dict:
    """
    Fetches comprehensive metrics for a GitHub repository.
    Returns a structured dict ready for analysis.
    """
    h = _get_headers(token)
    base = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"

    info = _get(base, h)
    if info is None:
        raise ValueError(f"Repository '{owner}/{repo}' not found or is private.")

    commits = _get(f"{base}/commits", h, params={"per_page": 30}) or []
    open_issues_data = _get(f"{base}/issues", h, params={"state": "open", "per_page": 100}) or []
    open_prs = _get(f"{base}/pulls", h, params={"state": "open", "per_page": 100}) or []
    closed_issues_data = _get(f"{base}/issues", h, params={"state": "closed", "per_page": 30}) or []
    contributors = _get(f"{base}/contributors", h, params={"per_page": 20}) or []
    releases = _get(f"{base}/releases", h, params={"per_page": 5}) or []
    languages = _get(f"{base}/languages", h) or {}
    topics_data = _get(f"{base}/topics", h) or {}
    workflows = _get(f"{base}/actions/workflows", h) or {}

    commit_dates = []
    for c in commits:
        try:
            date_str = c["commit"]["author"]["date"]
            commit_dates.append(datetime.fromisoformat(date_str.replace("Z", "+00:00")))
        except (KeyError, ValueError):
            pass

    days_since_last_commit = None
    if commit_dates:
        latest = max(commit_dates)
        days_since_last_commit = (datetime.now(timezone.utc) - latest).days

    response_times = []
    for issue in closed_issues_data:
        if issue.get("pull_request"):
            continue
        try:
            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))
            response_times.append((closed - created).days)
        except (KeyError, ValueError, TypeError):
            pass
    avg_issue_close_days = round(sum(response_times) / len(response_times), 1) if response_times else None

    real_open_issues = [i for i in open_issues_data if not i.get("pull_request")]

    return {
        "full_name": info.get("full_name", f"{owner}/{repo}"),
        "description": info.get("description") or "No description provided.",
        "html_url": info.get("html_url", ""),
        "homepage": info.get("homepage") or "",
        "owner": owner,
        "repo": repo,
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "watchers": info.get("watchers_count", 0),
        "network_count": info.get("network_count", 0),
        "language": info.get("language") or "Unknown",
        "languages": languages,
        "size_kb": info.get("size", 0),
        "default_branch": info.get("default_branch", "main"),
        "topics": topics_data.get("names", []),
        "open_issues_count": len(real_open_issues),
        "open_prs_count": len(open_prs),
        "closed_issues_sample": len(closed_issues_data),
        "days_since_last_commit": days_since_last_commit,
        "recent_commit_count": len(commit_dates),
        "recent_commit_dates": [d.isoformat() for d in sorted(commit_dates, reverse=True)[:10]],
        "avg_issue_close_days": avg_issue_close_days,
        "has_wiki": info.get("has_wiki", False),
        "has_pages": info.get("has_pages", False),
        "has_discussions": info.get("has_discussions", False),
        "license": (info.get("license") or {}).get("name") or "None",
        "archived": info.get("archived", False),
        "disabled": info.get("disabled", False),
        "is_fork": info.get("fork", False),
        "contributors_count": len(contributors),
        "top_contributors": [
            {"login": c.get("login", ""), "contributions": c.get("contributions", 0)}
            for c in contributors[:5]
        ],
        "total_releases": len(releases),
        "latest_release": releases[0].get("tag_name") if releases else None,
        "latest_release_date": releases[0].get("published_at") if releases else None,
        "has_workflows": bool((workflows.get("workflows") or [])),
        "created_at": info.get("created_at", ""),
        "updated_at": info.get("updated_at", ""),
        "pushed_at": info.get("pushed_at", ""),
    }
