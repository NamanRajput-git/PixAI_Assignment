import os
import re
from dotenv import load_dotenv
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from github_analyzer.github_fetcher import fetch_repo_data
from github_analyzer.metrics import compute_health_score, compute_commit_frequency
from github_analyzer.llm_analyzer import get_llm_analysis

load_dotenv()

st.set_page_config(
    page_title="GitHub Health Checker",
    page_icon=":mag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main { background-color: #0d1117; }

.metric-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.5rem;
}

.score-ring {
    text-align: center;
    padding: 1.5rem;
    background: linear-gradient(135deg, #161b22, #1c2128);
    border: 1px solid #30363d;
    border-radius: 16px;
}

.status-badge {
    display: inline-block;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.85rem;
}

.section-header {
    color: #58a6ff;
    font-weight: 600;
    font-size: 1.1rem;
    border-bottom: 1px solid #30363d;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}

.repo-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e6edf3;
}

.repo-desc {
    color: #8b949e;
    font-size: 0.95rem;
    margin-top: 0.3rem;
}

.stButton > button {
    background: linear-gradient(135deg, #238636, #2ea043);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.5rem 2rem;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2ea043, #3fb950);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(46,160,67,0.3);
}

.llm-report {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    color: #e6edf3;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)


def parse_repo_url(url_or_slug: str):
    """Accepts 'owner/repo' or full GitHub URLs."""
    url_or_slug = url_or_slug.strip().rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+)/([^/\s]+?)(?:\.git)?$", url_or_slug)
    if match:
        return match.group(1), match.group(2)
    parts = url_or_slug.split("/")
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def gauge_chart(score: int) -> go.Figure:
    color = "#3fb950" if score >= 70 else "#d29922" if score >= 40 else "#f85149"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 36, "color": "#e6edf3"}, "suffix": "/100"},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#1c2128",
            "bordercolor": "#30363d",
            "steps": [
                {"range": [0, 40], "color": "#1c2128"},
                {"range": [40, 70], "color": "#1c2128"},
                {"range": [70, 100], "color": "#1c2128"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        margin=dict(t=20, b=10, l=10, r=10),
        height=220,
        font={"color": "#e6edf3"},
    )
    return fig


def radar_chart(scores: dict) -> go.Figure:
    categories = ["Activity", "Community", "Maintenance", "Docs", "CI/CD"]
    values = [
        scores["activity"] / 40 * 100,
        scores["community"] / 20 * 100,
        scores["maintenance"] / 20 * 100,
        scores["docs"] / 10 * 100,
        scores["ci"] / 10 * 100,
    ]
    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(88,166,255,0.15)",
        line=dict(color="#58a6ff", width=2),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#1c2128",
            radialaxis=dict(visible=True, range=[0, 100], tickcolor="#8b949e", gridcolor="#30363d", color="#8b949e"),
            angularaxis=dict(tickcolor="#8b949e", gridcolor="#30363d", color="#8b949e"),
        ),
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        margin=dict(t=10, b=10, l=10, r=10),
        height=280,
        showlegend=False,
    )
    return fig


def lang_bar(languages: dict) -> go.Figure:
    if not languages:
        return None
    total = sum(languages.values())
    labels = list(languages.keys())
    pcts = [v / total * 100 for v in languages.values()]
    colors = px.colors.qualitative.Bold

    fig = go.Figure(go.Bar(
        x=pcts, y=labels, orientation="h",
        marker_color=colors[:len(labels)],
        text=[f"{p:.1f}%" for p in pcts],
        textposition="auto",
    ))
    fig.update_layout(
        paper_bgcolor="#161b22",
        plot_bgcolor="#1c2128",
        font={"color": "#e6edf3"},
        margin=dict(t=5, b=5, l=10, r=10),
        height=max(100, len(labels) * 40),
        xaxis=dict(title="%", color="#8b949e", gridcolor="#30363d"),
        yaxis=dict(color="#e6edf3"),
    )
    return fig


with st.sidebar:
    st.markdown("## GitHub Health Checker")
    st.markdown("Analyze any public repository's health using GitHub APIs + NVIDIA LLM.")
    st.divider()

    repo_input = st.text_input(
        "Repository",
        placeholder="owner/repo  or  https://github.com/owner/repo",
        help="Enter a GitHub repository slug or full URL.",
    )

    github_token = os.getenv("GITHUB_TOKEN", "")
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")

    st.markdown("#### LLM Model")
    model_choice = st.selectbox(
        "Model",
        options=[
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "mistralai/mistral-7b-instruct-v0.3",
            "google/gemma-2-9b-it",
        ],
        index=0,
    )

    analyze_btn = st.button("Analyze Repository", use_container_width=True)

    st.divider()
    st.markdown(
        "<small style='color:#8b949e'>Built with Streamlit · GitHub API · NVIDIA NIM</small>",
        unsafe_allow_html=True,
    )


st.markdown("# GitHub Repository Health Checker")
st.markdown(
    "Enter a repository on the left and click **Analyze** to get a comprehensive health report powered by real-time GitHub data and AI insights.",
    help=None,
)

if analyze_btn and repo_input:
    owner, repo = parse_repo_url(repo_input)
    if not owner or not repo:
        st.error("Invalid repository format. Use `owner/repo` or a full GitHub URL.")
        st.stop()

    with st.spinner(f"Fetching data for **{owner}/{repo}**..."):
        try:
            data = fetch_repo_data(owner, repo, token=github_token or None)
        except (ValueError, ConnectionError) as e:
            st.error(str(e))
            st.stop()

    with st.spinner("Computing health scores..."):
        scores = compute_health_score(data)
        freq = compute_commit_frequency(data.get("recent_commit_dates", []))

    with st.spinner("Running LLM analysis..."):
        analysis = get_llm_analysis(data, scores, api_key=nvidia_key or None, model=model_choice)

    st.markdown(f"""
    <div style='margin-bottom:1.5rem;'>
      <div class='repo-title'>
        <a href='{data["html_url"]}' target='_blank' style='color:#58a6ff;text-decoration:none;'>
          {data["full_name"]}
        </a>
      </div>
      <div class='repo-desc'>{data["description"]}</div>
    </div>
    """, unsafe_allow_html=True)

    col_g, col_r, col_info = st.columns([1.2, 1.2, 2.5])

    with col_g:
        st.markdown("<div class='section-header'>Overall Score</div>", unsafe_allow_html=True)
        st.plotly_chart(gauge_chart(scores["total"]), use_container_width=True)

    with col_r:
        st.markdown("<div class='section-header'>Score Breakdown</div>", unsafe_allow_html=True)
        st.plotly_chart(radar_chart(scores), use_container_width=True)

    with col_info:
        st.markdown("<div class='section-header'>Key Metrics</div>", unsafe_allow_html=True)
        days = data.get("days_since_last_commit", "N/A")
        cols = st.columns(2)
        with cols[0]:
            st.metric("Stars", f"{data['stars']:,}")
            st.metric("Forks", f"{data['forks']:,}")
            st.metric("Contributors", data["contributors_count"])
            st.metric("Open Issues", data["open_issues_count"])
        with cols[1]:
            st.metric("Last Commit", f"{days}d ago" if isinstance(days, int) else "N/A")
            st.metric("Releases", data["total_releases"])
            st.metric("Open PRs", data["open_prs_count"])
            st.metric("License", data["license"])

        status_colors = {
            "Actively Maintained": "#3fb950",
            "Moderately Active": "#58a6ff",
            "Slow": "#d29922",
            "Stale": "#f0883e",
            "Abandoned": "#f85149",
            "Archived / Inactive": "#6e40c9",
        }
        c = status_colors.get(scores["status"], "#8b949e")
        st.markdown(
            f"<div style='margin-top:0.5rem;'>"
            f"<span style='background:{c}22;color:{c};border:1px solid {c}66;"
            f"padding:0.3rem 1rem;border-radius:20px;font-weight:600;font-size:0.95rem;'>"
            f"{scores['status']}</span></div>",
            unsafe_allow_html=True,
        )

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("<div class='section-header'>Languages</div>", unsafe_allow_html=True)
        fig_lang = lang_bar(data.get("languages", {}))
        if fig_lang:
            st.plotly_chart(fig_lang, use_container_width=True)
        else:
            st.info("No language data available.")

        st.markdown("<div class='section-header'>Topics</div>", unsafe_allow_html=True)
        if data.get("topics"):
            badges = " ".join(
                f"<span style='background:#1f3a5f;color:#58a6ff;padding:0.2rem 0.6rem;"
                f"border-radius:12px;font-size:0.8rem;margin:2px;display:inline-block;'>{t}</span>"
                for t in data["topics"]
            )
            st.markdown(badges, unsafe_allow_html=True)
        else:
            st.info("No topics set.")

    with col_b:
        st.markdown("<div class='section-header'>Recent Commit Activity</div>", unsafe_allow_html=True)
        if freq:
            fig_freq = go.Figure(go.Bar(
                x=list(freq.keys()),
                y=list(freq.values()),
                marker_color="#58a6ff",
            ))
            fig_freq.update_layout(
                paper_bgcolor="#161b22",
                plot_bgcolor="#1c2128",
                font={"color": "#e6edf3"},
                margin=dict(t=5, b=5, l=10, r=10),
                height=160,
                xaxis=dict(color="#8b949e", gridcolor="#30363d"),
                yaxis=dict(color="#8b949e", gridcolor="#30363d", title="Commits"),
            )
            st.plotly_chart(fig_freq, use_container_width=True)
        else:
            st.info("No recent commit data.")

        st.markdown("<div class='section-header'>Top Contributors</div>", unsafe_allow_html=True)
        for c in data.get("top_contributors", []):
            pct_bar = min(c["contributions"] / max(data["top_contributors"][0]["contributions"], 1) * 100, 100)
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;'>"
                f"<span style='color:#e6edf3;min-width:120px;font-size:0.85rem;'>@{c['login']}</span>"
                f"<div style='flex:1;background:#1c2128;border-radius:4px;height:8px;'>"
                f"<div style='width:{pct_bar:.0f}%;background:#58a6ff;border-radius:4px;height:8px;'></div></div>"
                f"<span style='color:#8b949e;font-size:0.8rem;min-width:40px;text-align:right;'>{c['contributions']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    st.markdown("<div class='section-header'>Health Score Breakdown</div>", unsafe_allow_html=True)
    score_cols = st.columns(5)
    score_defs = [
        ("Activity", scores["activity"], 40, "Commit frequency & recency"),
        ("Community", scores["community"], 20, "Stars, forks, contributors"),
        ("Maintenance", scores["maintenance"], 20, "Issue response & license"),
        ("Docs", scores["docs"], 10, "Wiki, homepage, topics"),
        ("CI/CD", scores["ci"], 10, "Workflows & releases"),
    ]
    for col, (label, val, max_val, tip) in zip(score_cols, score_defs):
        with col:
            pct = val / max_val * 100
            color = "#3fb950" if pct >= 70 else "#d29922" if pct >= 40 else "#f85149"
            st.markdown(
                f"<div class='metric-card' title='{tip}'>"
                f"<div style='color:#8b949e;font-size:0.75rem;'>{label}</div>"
                f"<div style='color:{color};font-size:1.4rem;font-weight:700;'>{val}<span style='color:#8b949e;font-size:0.9rem;'>/{max_val}</span></div>"
                f"<div style='background:#0d1117;border-radius:4px;height:6px;margin-top:0.4rem;'>"
                f"<div style='width:{pct:.0f}%;background:{color};border-radius:4px;height:6px;'></div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with st.expander("Additional Repository Info", expanded=False):
        info_cols = st.columns(3)
        with info_cols[0]:
            st.markdown("**Repository Details**")
            st.write(f"Default branch: `{data['default_branch']}`")
            st.write(f"Size: {data['size_kb']:,} KB")
            st.write(f"Is fork: {'Yes' if data['is_fork'] else 'No'}")
            st.write(f"Archived: {'Yes' if data['archived'] else 'No'}")
        with info_cols[1]:
            st.markdown("**Dates**")
            st.write(f"Created: {data['created_at'][:10]}")
            st.write(f"Last updated: {data['updated_at'][:10]}")
            st.write(f"Last push: {data['pushed_at'][:10]}")
        with info_cols[2]:
            st.markdown("**Features**")
            st.write(f"Wiki: {'Yes' if data['has_wiki'] else 'No'}")
            st.write(f"Pages: {'Yes' if data['has_pages'] else 'No'}")
            st.write(f"Discussions: {'Yes' if data['has_discussions'] else 'No'}")
            st.write(f"CI Workflows: {'Yes' if data['has_workflows'] else 'No'}")
            if data.get("homepage"):
                st.write(f"[Homepage]({data['homepage']})")

    st.divider()

    st.markdown("<div class='section-header'>AI Health Analysis (NVIDIA NIM)</div>", unsafe_allow_html=True)
    if nvidia_key:
        st.markdown(f"<small style='color:#8b949e'>Model: `{model_choice}`</small>", unsafe_allow_html=True)
    st.markdown(f"<div class='llm-report'>{analysis}</div>", unsafe_allow_html=True)

elif analyze_btn and not repo_input:
    st.warning("Please enter a repository name or URL first.")

else:
    st.markdown("""
    <div style='text-align:center;padding:4rem 2rem;'>
      <h2 style='color:#e6edf3;'>Ready to analyze any public GitHub repository</h2>
      <p style='color:#8b949e;max-width:500px;margin:auto;'>
        Enter a repository on the left sidebar and click <b>Analyze Repository</b> to get
        a detailed health report with metrics, scores, and AI-powered insights.
      </p>
      <div style='margin-top:2rem;display:flex;justify-content:center;gap:1rem;flex-wrap:wrap;'>
        <code style='background:#161b22;border:1px solid #30363d;padding:0.4rem 0.8rem;border-radius:8px;color:#58a6ff;'>facebook/react</code>
        <code style='background:#161b22;border:1px solid #30363d;padding:0.4rem 0.8rem;border-radius:8px;color:#58a6ff;'>openai/openai-python</code>
        <code style='background:#161b22;border:1px solid #30363d;padding:0.4rem 0.8rem;border-radius:8px;color:#58a6ff;'>tensorflow/tensorflow</code>
      </div>
    </div>
    """, unsafe_allow_html=True)
