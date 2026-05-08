# GitHub Repository Health Checker

A **Streamlit web app** that analyzes any public GitHub repository's health using the **GitHub REST API** for real-time data and **NVIDIA NIM (free LLM endpoints)** for AI-powered insights.

---

## Features

| Feature | Details |
|---|---|
|  **Health Score** | Overall 0–100 score across 5 weighted dimensions |
|  **Activity Analysis** | Commit recency, frequency, last-push date |
|  **Community Metrics** | Stars, forks, watchers, contributors |
|  **Maintenance Signals** | Issue response time, open PRs, license presence |
|  **Documentation Check** | Wiki, homepage, topics, description quality |
|  **CI/CD Detection** | GitHub Actions workflows, releases |
|  **LLM Report** | AI-generated summary, strengths, weaknesses & recommendations via NVIDIA NIM |
|  **Visual Charts** | Gauge, radar, language bar, commit frequency bar |

---

## Setup

### 1. Clone / download the project

```bash
git clone <this-repo>
cd PixAI_Assignment
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxx
```

> Both keys are **optional** but highly recommended:
> - **GitHub Token** — raises rate limit from 60 → 5,000 req/hr. Get one at [github.com/settings/tokens](https://github.com/settings/tokens) (no scopes needed for public repos).
> - **NVIDIA API Key** — enables AI analysis. Get a free key at [build.nvidia.com](https://build.nvidia.com).

Alternatively, you can paste API keys directly in the sidebar of the running app — no `.env` file required.

### 5. Run the app

```bash
streamlit run app.py
```

The app opens at **http://localhost:8501** in your browser.

---

## Usage

1. Enter a repository in the sidebar — any of these formats work:
   - `owner/repo` (e.g., `facebook/react`)
   - `https://github.com/owner/repo`
2. Optionally paste your API keys in the sidebar fields.
3. Click ** Analyze Repository**.
4. Review the health report, charts, and AI analysis.

---

## Project Structure

```
PixAI_Assignment/
├── app.py                      # Streamlit entry-point
├── requirements.txt
├── .env.example                # Template for API keys
├── .env                        # Your actual keys (git-ignored)
└── github_analyzer/
    ├── __init__.py
    ├── github_fetcher.py       # GitHub REST API calls & data parsing
    ├── metrics.py              # Health scoring engine (pure Python)
    └── llm_analyzer.py         # NVIDIA NIM LLM integration
```

---

## Health Score Dimensions

| Dimension | Max Points | What's Measured |
|---|---|---|
| Activity | 40 | Days since last commit, commit count in recent 30 |
| Community | 20 | Stars, forks, number of contributors |
| Maintenance | 20 | Avg issue close time, open PRs, license |
| Documentation | 10 | Description, wiki, homepage, topics |
| CI/CD | 10 | GitHub Actions workflows, releases |

**Status labels** (based on days since last commit):

| Status | Days Since Last Commit |
|---|---|
| 🟢 Actively Maintained | ≤ 30 days |
| 🟢 Moderately Active | 31–90 days |
| 🟡 Slow | 91–180 days |
| 🟠 Stale | 181–365 days |
| 🔴 Abandoned | > 365 days |
| 🔴 Archived / Inactive | Archived flag set |

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Optional | GitHub PAT for higher API rate limits |
| `NVIDIA_API_KEY` | Optional | NVIDIA NIM key for LLM analysis |

---

## Notes

- Only **public repositories** are supported without additional OAuth scopes.
- The app works without any API keys (uses GitHub unauthenticated calls up to 60 req/hr and skips LLM analysis).
- LLM fallback: if no NVIDIA key is provided, a rule-based summary is shown instead.
