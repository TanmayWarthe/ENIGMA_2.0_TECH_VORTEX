"""Performance Analytics Dashboard page."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dotenv import load_dotenv
import database as db
import auth_utils as auth

load_dotenv()

st.set_page_config(page_title="IntervueX – Dashboard", page_icon="📊", layout="wide")

# Require authentication
auth.require_auth()

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui_utils import apply_global_css
apply_global_css()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }
    .metric-card {
        background: #ffffff !important;
        color: #000000 !important;
        border-radius: 18px;
        padding: 24px;
        text-align: center;
        border: 1px solid rgba(128, 128, 128, 0.15);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        margin: 5px 0;
        transition: transform 0.2s;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .metric-card:hover {
        transform: translateY(-3px);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #4F46E5;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #000000;
        opacity: 0.8;
        font-weight: 600;
        margin-top: 4px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("user_id"):
    st.warning("Please sign in from the home page to view your dashboard.")
    st.stop()

user_id = st.session_state.user_id
st.markdown("## 📊 Performance Analytics Dashboard")
st.markdown("---")

analytics = db.get_user_analytics(user_id)
stats = analytics["stats"]

# Top-level metrics
col1, col2, col3, col4, col5, col6 = st.columns(6)

total = stats.get("total", 0) or 0
completed = stats.get("completed", 0) or 0
avg_overall = stats.get("avg_overall", 0) or 0
avg_tech = stats.get("avg_technical", 0) or 0
avg_comm = stats.get("avg_communication", 0) or 0
total_violations = stats.get("total_violations", 0) or 0

with col1:
    st.markdown(f"""<div class="metric-card"><div class="metric-value">{total}</div>
    <div class="metric-label">Total Sessions</div></div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="metric-card"><div class="metric-value">{completed}</div>
    <div class="metric-label">Completed</div></div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div class="metric-card"><div class="metric-value">{avg_overall:.0f}</div>
    <div class="metric-label">Avg Overall Score</div></div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""<div class="metric-card"><div class="metric-value">{avg_tech:.0f}</div>
    <div class="metric-label">Avg Technical</div></div>""", unsafe_allow_html=True)
with col5:
    st.markdown(f"""<div class="metric-card"><div class="metric-value">{avg_comm:.0f}</div>
    <div class="metric-label">Avg Communication</div></div>""", unsafe_allow_html=True)
with col6:
    st.markdown(f"""<div class="metric-card"><div class="metric-value">{total_violations}</div>
    <div class="metric-label">Tab Violations</div></div>""", unsafe_allow_html=True)

st.markdown("---")

if not analytics["trend"]:
    st.info("Complete some interview sessions to see your performance analytics here!")
    st.stop()

# Score Trend Chart
st.markdown("### 📈 Score Trend Over Time")
trend_data = analytics["trend"]
if trend_data:
    df_trend = pd.DataFrame(trend_data)
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=list(range(1, len(df_trend) + 1)),
        y=df_trend["overall_score"],
        mode="lines+markers",
        name="Overall",
        line=dict(color="#818CF8", width=3),
        marker=dict(size=8)
    ))
    fig_trend.add_trace(go.Scatter(
        x=list(range(1, len(df_trend) + 1)),
        y=df_trend["technical_score"],
        mode="lines+markers",
        name="Technical",
        line=dict(color="#34D399", width=2),
        marker=dict(size=6)
    ))
    fig_trend.add_trace(go.Scatter(
        x=list(range(1, len(df_trend) + 1)),
        y=df_trend["communication_score"],
        mode="lines+markers",
        name="Communication",
        line=dict(color="#F472B6", width=2),
        marker=dict(size=6)
    ))
    fig_trend.update_layout(
        xaxis_title="Session #",
        yaxis_title="Score",
        yaxis=dict(range=[0, 100]),
        # template automatically handled by streamlit
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# Charts Row
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📊 Sessions by Type")
    by_type = analytics["by_type"]
    if by_type:
        df_type = pd.DataFrame(by_type)
        fig_type = px.bar(
            df_type, x="session_type", y="count",
            color="session_type",
            color_discrete_map={"dsa": "#818CF8", "hr": "#F472B6", "technical": "#34D399"},
            # template automatically handled by streamlit
        )
        fig_type.update_layout(
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
        )
        st.plotly_chart(fig_type, use_container_width=True)

with col2:
    st.markdown("### 🎯 Average Score by Type")
    if by_type:
        df_type_score = pd.DataFrame(by_type)
        fig_score = px.bar(
            df_type_score, x="session_type", y="avg_score",
            color="session_type",
            color_discrete_map={"dsa": "#818CF8", "hr": "#F472B6", "technical": "#34D399"},
            # template automatically handled by streamlit
        )
        fig_score.update_layout(
            showlegend=False,
            yaxis=dict(range=[0, 100]),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
        )
        st.plotly_chart(fig_score, use_container_width=True)

# Difficulty breakdown
st.markdown("### 🏋️ Performance by Difficulty")
by_diff = analytics["by_difficulty"]
if by_diff:
    df_diff = pd.DataFrame(by_diff)
    fig_diff = px.bar(
        df_diff, x="difficulty", y="avg_score",
        color="difficulty",
        color_discrete_map={"easy": "#34D399", "medium": "#FBBF24", "hard": "#EF4444"},
        # template automatically handled by streamlit
        text="count",
    )
    fig_diff.update_layout(
        yaxis=dict(range=[0, 100]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=350,
    )
    fig_diff.update_traces(texttemplate="%{text} sessions", textposition="outside")
    st.plotly_chart(fig_diff, use_container_width=True)

# Skill radar chart (if we have enough data)
st.markdown("### 🕸️ Skills Radar")
avg_reasoning = stats.get("avg_reasoning", 0) or 0
avg_ps = stats.get("avg_problem_solving", 0) or 0

categories = ["Technical", "Communication", "Reasoning", "Problem Solving", "Overall"]
values = [avg_tech, avg_comm, avg_reasoning, avg_ps, avg_overall]

fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(
    r=values + [values[0]],
    theta=categories + [categories[0]],
    fill="toself",
    line=dict(color="#818CF8", width=2),
    fillcolor="rgba(129, 140, 248, 0.2)",
))
fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 100]),
        bgcolor="rgba(0,0,0,0)",
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    height=450,
)
st.plotly_chart(fig_radar, use_container_width=True)
