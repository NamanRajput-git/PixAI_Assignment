import os
import json
from typing import Optional
from openai import OpenAI


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"


def _build_prompt(data: dict, scores: dict) -> str:

    days = data.get("days_since_last_commit", "unknown")
    langs = ", ".join(data.get("languages", {}).keys()) or data.get("language", "Unknown")
    topics = ", ".join(data.get("topics", [])) or "none"

    return f"""You are a senior open-source engineer analyzing a GitHub repository's health.

## Repository: {data['full_name']}
Description: {data['description']}
Language(s): {langs}
Topics: {topics}
License: {data.get('license', 'None')}
Archived: {data.get('archived', False)}

## Activity Metrics
- Stars: {data['stars']:,} | Forks: {data['forks']:,} | Watchers: {data['watchers']:,}
- Last commit: {days} days ago
- Commits in last 30 fetched: {data['recent_commit_count']}
- Contributors: {data['contributors_count']}
- Open Issues: {data['open_issues_count']} | Open PRs: {data['open_prs_count']}
- Avg issue close time: {data.get('avg_issue_close_days', 'N/A')} days
- Total releases: {data['total_releases']}
- Latest release: {data.get('latest_release', 'None')} ({data.get('latest_release_date', 'N/A')})
- Has CI/CD workflows: {data.get('has_workflows', False)}
- Has Wiki: {data.get('has_wiki', False)} | Has Homepage: {bool(data.get('homepage', ''))}

## Computed Health Scores (out of max)
- Activity: {scores['activity']}/40
- Community: {scores['community']}/20
- Maintenance: {scores['maintenance']}/20
- Documentation: {scores['docs']}/10
- CI/CD: {scores['ci']}/10
- **Overall: {scores['total']}/100**
- Status: {scores['status']}

## Your Task
Write a concise repository health report with these sections:
1. **Summary** (2-3 sentences: what this repo is, its overall health verdict)
2. **Strengths** (bullet points, max 4)
3. **Weaknesses / Red Flags** (bullet points, max 4)
4. **Recommendations** (bullet points, max 4 — actionable advice for maintainers)
5. **Final Verdict** (one sentence with a clear Active/Stale/Abandoned judgment and why)

Be direct and specific. Use concrete numbers from the metrics above.
"""


def get_llm_analysis(
    data: dict,
    scores: dict,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    key = api_key or os.getenv("NVIDIA_API_KEY", "")

    if not key:
        return _fallback_summary(data, scores)

    try:
        client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=key)
        prompt = _build_prompt(data, scores)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"LLM analysis unavailable: {str(e)}\n\n{_fallback_summary(data, scores)}"


def _fallback_summary(data: dict, scores: dict) -> str:
    days = data.get("days_since_last_commit", 9999)
    status = scores.get("status", "Unknown")
    total = scores.get("total", 0)

    lines = [
        f"## Auto-generated Summary (no LLM key provided)\n",
        f"**{data['full_name']}** scored **{total}/100** overall.",
        f"Status: **{status}**",
        "",
        f"- Last commit was **{days} days ago**.",
        f"- The repo has **{data['stars']:,} stars** and **{data['forks']:,} forks**.",
        f"- License: {data.get('license', 'None')}",
        f"- Top language: {data.get('language', 'Unknown')}",
    ]
    return "\n".join(lines)
