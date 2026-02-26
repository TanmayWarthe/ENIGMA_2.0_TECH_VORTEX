"""Interview Session History and Feedback Reports page."""

import streamlit as st
import json
import plotly.graph_objects as go
from dotenv import load_dotenv
import database as db
from user_memory import get_memory_context_for_ai

load_dotenv()

st.set_page_config(page_title="IntervueX – Session History", page_icon="📜", layout="wide")

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui_utils import apply_global_css
apply_global_css()

st.markdown("""
<style>
    .report-card {
        background: #ffffff !important;
        color: #000000 !important;
        border-radius: 16px;
        padding: 24px;
        margin: 15px 0;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    .score-circle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("user_id"):
    st.warning("Please sign in from the home page to view your history.")
    st.stop()

user_id = st.session_state.user_id

st.markdown("## 📜 Interview History & Feedback Reports")
st.markdown("---")

# Check if we should show a specific session
view_session_id = st.session_state.get("view_session_id")

sessions = db.get_user_sessions(user_id)

if not sessions:
    st.info("No interview sessions yet. Start an interview to see your history here!")
    st.stop()

# Session selector
session_options = {}
for s in sessions:
    icon = "💻" if s["session_type"] == "dsa" else "🤝" if s["session_type"] == "hr" else "⚙️"
    status = "✅" if s["status"] == "completed" else "🟡"
    label = f"{icon} {s['session_type'].upper()} - {s['started_at'][:16]} {status} (Score: {s['overall_score']:.0f})"
    session_options[label] = s["id"]

# Find default selection
default_idx = 0
if view_session_id:
    for i, (label, sid) in enumerate(session_options.items()):
        if sid == view_session_id:
            default_idx = i
            break

selected_label = st.selectbox(
    "Select a session to view:",
    options=list(session_options.keys()),
    index=default_idx,
)
selected_session_id = session_options[selected_label]

# Load session data
session = db.get_session(selected_session_id)
questions = db.get_session_questions(selected_session_id)
chat_messages = db.get_chat_messages(selected_session_id)
violations = db.get_tab_violations(selected_session_id)

if not session:
    st.error("Session not found.")
    st.stop()

feedback = session.get("feedback", {})

# Session Overview
st.markdown("### 📋 Session Overview")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    score = session["overall_score"]
    color = "#34D399" if score >= 70 else "#FBBF24" if score >= 50 else "#EF4444"
    st.markdown(f"""
    <div style="text-align:center;">
        <div class="score-circle" style="background:{color};margin:auto;">{score:.0f}</div>
        <p style="color:#9CA3AF;margin-top:8px;">Overall</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    score = session["technical_score"]
    color = "#34D399" if score >= 70 else "#FBBF24" if score >= 50 else "#EF4444"
    st.markdown(f"""
    <div style="text-align:center;">
        <div class="score-circle" style="background:{color};margin:auto;">{score:.0f}</div>
        <p style="color:#9CA3AF;margin-top:8px;">Technical</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    score = session["communication_score"]
    color = "#34D399" if score >= 70 else "#FBBF24" if score >= 50 else "#EF4444"
    st.markdown(f"""
    <div style="text-align:center;">
        <div class="score-circle" style="background:{color};margin:auto;">{score:.0f}</div>
        <p style="color:#9CA3AF;margin-top:8px;">Communication</p>
    </div>
    """, unsafe_allow_html=True)
with col4:
    score = session["reasoning_score"]
    color = "#34D399" if score >= 70 else "#FBBF24" if score >= 50 else "#EF4444"
    st.markdown(f"""
    <div style="text-align:center;">
        <div class="score-circle" style="background:{color};margin:auto;">{score:.0f}</div>
        <p style="color:#9CA3AF;margin-top:8px;">Reasoning</p>
    </div>
    """, unsafe_allow_html=True)
with col5:
    score = session["problem_solving_score"]
    color = "#34D399" if score >= 70 else "#FBBF24" if score >= 50 else "#EF4444"
    st.markdown(f"""
    <div style="text-align:center;">
        <div class="score-circle" style="background:{color};margin:auto;">{score:.0f}</div>
        <p style="color:#9CA3AF;margin-top:8px;">Problem Solving</p>
    </div>
    """, unsafe_allow_html=True)

# Session details
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"**Type:** {session['session_type'].upper()}")
with col2:
    st.markdown(f"**Difficulty:** {session.get('difficulty', 'N/A').title()}")
with col3:
    st.markdown(f"**Status:** {'Completed ✅' if session['status'] == 'completed' else 'In Progress 🟡'}")
with col4:
    v_count = session.get("tab_violations", 0)
    v_color = "#EF4444" if v_count > 0 else "#34D399"
    st.markdown(f"**Tab Violations:** <span style='color:{v_color};font-weight:700;'>{v_count}</span>", unsafe_allow_html=True)

# Radar chart for this session
st.markdown("---")
st.markdown("### 🕸️ Performance Radar")

fig_radar = go.Figure()
categories = ["Technical", "Communication", "Reasoning", "Problem Solving", "Overall"]
values = [
    session["technical_score"],
    session["communication_score"],
    session["reasoning_score"],
    session["problem_solving_score"],
    session["overall_score"],
]
fig_radar.add_trace(go.Scatterpolar(
    r=values + [values[0]],
    theta=categories + [categories[0]],
    fill="toself",
    line=dict(color="#818CF8", width=2),
    fillcolor="rgba(129, 140, 248, 0.2)",
))
fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100]), bgcolor="rgba(0,0,0,0)"),
    paper_bgcolor="rgba(0,0,0,0)",
    height=400,
)
st.plotly_chart(fig_radar, use_container_width=True)

# Executive Summary
if feedback:
    st.markdown("---")
    st.markdown("### 📝 Detailed Feedback Report")

    exec_summary = feedback.get("executive_summary", "")
    if exec_summary:
        st.info(f"**Executive Summary:** {exec_summary}")

    readiness = feedback.get("interview_readiness", "")
    if readiness:
        readiness_colors = {
            "ready": "#34D399",
            "almost_ready": "#FBBF24",
            "needs_preparation": "#EF4444",
        }
        r_color = readiness_colors.get(readiness, "#9CA3AF")
        st.markdown(f"**Interview Readiness:** <span style='color:{r_color};font-weight:700;font-size:1.2rem;'>{readiness.replace('_', ' ').title()}</span>", unsafe_allow_html=True)

    detailed = feedback.get("detailed_feedback", {})
    if detailed:
        col1, col2 = st.columns(2)
        with col1:
            if detailed.get("technical_skills"):
                st.markdown("**🔧 Technical Skills**")
                st.markdown(detailed["technical_skills"])

            if detailed.get("problem_solving"):
                st.markdown("**🧩 Problem Solving**")
                st.markdown(detailed["problem_solving"])

        with col2:
            if detailed.get("communication"):
                st.markdown("**💬 Communication**")
                st.markdown(detailed["communication"])

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**✅ Areas of Strength**")
            for s in detailed.get("areas_of_strength", []):
                st.markdown(f"- {s}")
        with col2:
            st.markdown("**📈 Areas for Improvement**")
            for i in detailed.get("areas_for_improvement", []):
                st.markdown(f"- {i}")
        with col3:
            st.markdown("**📚 Recommended Topics to Study**")
            for t in detailed.get("recommended_topics_to_study", []):
                st.markdown(f"- {t}")

    recommendation = feedback.get("recommendation", "")
    if recommendation:
        st.markdown("---")
        st.markdown(f"**🎯 Recommendation:** {recommendation}")

    integrity = feedback.get("integrity_note", "")
    if integrity:
        st.markdown(f"**🔒 Integrity Note:** {integrity}")

# Questions breakdown
if questions:
    st.markdown("---")
    st.markdown("### 📝 Question-by-Question Breakdown")

    for q in questions:
        with st.expander(f"Q{q['question_number']}: {q['question_text'][:100]}..."):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Code Score", f"{q['code_correctness_score']:.0f}/100")
            with col2:
                st.metric("Approach Score", f"{q['approach_score']:.0f}/100")
            with col3:
                st.metric("Communication", f"{q['communication_score']:.0f}/100")

            if q.get("candidate_code"):
                st.markdown("**Your Code:**")
                st.code(q["candidate_code"], language="python")

            if q.get("candidate_response_text"):
                st.markdown(f"**Your Explanation:** {q['candidate_response_text']}")

            if q.get("voice_transcript"):
                st.markdown(f"**Voice Transcript:** {q['voice_transcript']}")

            if q.get("ai_analysis"):
                try:
                    analysis = json.loads(q["ai_analysis"])
                    st.markdown(f"**AI Feedback:** {analysis.get('overall_feedback', '')}")

                    # Follow-ups
                    follow_ups = q.get("follow_up_questions", [])
                    if follow_ups:
                        st.markdown("**Follow-up Questions:**")
                        for fu in follow_ups:
                            st.markdown(f"- {fu}")

                    # Solutions
                    solutions = q.get("suggested_solutions", [])
                    if solutions:
                        st.markdown("**Suggested Solutions:**")
                        for sol in solutions:
                            if isinstance(sol, dict):
                                st.markdown(f"**{sol.get('approach', '')}:** {sol.get('description', '')}")
                                if sol.get("code"):
                                    st.code(sol["code"], language="python")
                except (json.JSONDecodeError, TypeError):
                    pass

# Chat log
if chat_messages:
    st.markdown("---")
    st.markdown("### 💬 Full Conversation Log")
    with st.expander("View full conversation"):
        for msg in chat_messages:
            role_icon = "🤖" if msg["role"] == "interviewer" else "👤" if msg["role"] == "candidate" else "ℹ️"
            role_label = msg["role"].title()
            st.markdown(f"**{role_icon} {role_label}** ({msg['timestamp'][:19]})")
            st.markdown(msg["content"])
            st.markdown("---")

# Tab violations
if violations:
    st.markdown("---")
    st.markdown("### ⚠️ Tab Violation Log")
    for v in violations:
        st.warning(f"**{v['violation_type']}** at {v['violation_time']}: {v.get('details', 'Tab switch detected')}")

# Webcam Proctoring Violations
proctor_violations = db.get_proctoring_violations(selected_session_id)
if proctor_violations:
    st.markdown("---")
    st.markdown("### 📹 Webcam Proctoring Violations")
    violation_type_icons = {
        "no_face": "👻",
        "multiple_faces": "👥",
        "looking_away": "👀",
        "other": "⚠️",
    }
    for pv in proctor_violations:
        icon = violation_type_icons.get(pv["violation_type"], "⚠️")
        label = pv["violation_type"].replace("_", " ").title()
        st.warning(f"{icon} **{label}** at {pv['violation_time'][:19]} — {pv.get('detail', '')}")

# Interview Recording Playback
recording_events = db.get_recording_events(selected_session_id)
if recording_events:
    st.markdown("---")
    st.markdown("### 🎬 Interview Recording Playback")
    st.markdown("Replay the interview timeline: conversations, code snapshots, and AI analysis.")

    # Group events into a timeline
    with st.expander("▶️ Play Interview Timeline", expanded=False):
        for idx, event in enumerate(recording_events):
            data = event["event_data"]
            etype = event["event_type"]
            ts = event["timestamp"][:19] if event.get("timestamp") else ""

            if etype == "conversation":
                role = data.get("role", "unknown")
                content = data.get("content", "")
                if role == "interviewer":
                    st.markdown(f"""
                    <div style="background:#EEF2FF;border-left:4px solid #818CF8;padding:12px;border-radius:8px;margin:8px 0;">
                        <small style="color:#6B7280;">{ts}</small><br>
                        <strong>🤖 Interviewer:</strong> {content[:500]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:#F0FDF4;border-left:4px solid #34D399;padding:12px;border-radius:8px;margin:8px 0;">
                        <small style="color:#6B7280;">{ts}</small><br>
                        <strong>👤 Candidate:</strong> {content[:500]}
                    </div>
                    """, unsafe_allow_html=True)

            elif etype == "code_snapshot":
                code_text = data.get("code", "")
                q_num = data.get("question_number", "?")
                explanation = data.get("explanation", "")
                st.markdown(f"""
                <div style="background:#FFF7ED;border-left:4px solid #F59E0B;padding:12px;border-radius:8px;margin:8px 0;">
                    <small style="color:#6B7280;">{ts}</small><br>
                    <strong>💻 Code Snapshot (Q{q_num})</strong>
                </div>
                """, unsafe_allow_html=True)
                if code_text:
                    st.code(code_text, language="python")
                if explanation:
                    st.markdown(f"*Explanation:* {explanation[:300]}")

            elif etype == "analysis":
                analysis = data.get("analysis", {})
                q_num = data.get("question_number", "?")
                if isinstance(analysis, dict):
                    score = analysis.get("overall_score", analysis.get("relevance_score", "N/A"))
                    feedback = analysis.get("overall_feedback", analysis.get("feedback", ""))
                    st.markdown(f"""
                    <div style="background:#FDF2F8;border-left:4px solid #EC4899;padding:12px;border-radius:8px;margin:8px 0;">
                        <small style="color:#6B7280;">{ts}</small><br>
                        <strong>📊 AI Analysis (Q{q_num})</strong> — Score: {score}<br>
                        {feedback[:300]}
                    </div>
                    """, unsafe_allow_html=True)

    st.info(f"📝 Total recording events: {len(recording_events)}")

# User Memory Section
st.markdown("---")
st.markdown("### 🧠 AI Memory (What the AI Remembers About You)")
st.markdown("The AI interviewer remembers facts you share across sessions to personalize your experience.")

user_memories = db.get_user_memories(user_id)
if user_memories:
    category_icons = {
        "personal": "👤",
        "skill": "💻",
        "preference": "⭐",
        "interview_style": "🎯",
        "general": "📝",
    }

    # Group by category
    mem_by_cat = {}
    for m in user_memories:
        cat = m.get("category", "general")
        if cat not in mem_by_cat:
            mem_by_cat[cat] = []
        mem_by_cat[cat].append(m)

    for cat, items in mem_by_cat.items():
        icon = category_icons.get(cat, "📝")
        st.markdown(f"**{icon} {cat.replace('_', ' ').title()}**")
        for item in items:
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                st.markdown(f"`{item['memory_key']}`")
            with col2:
                st.markdown(item["memory_value"])
            with col3:
                if st.button("🗑️", key=f"del_mem_{item['id']}",
                             help="Delete this memory"):
                    db.delete_user_memory(user_id, item["memory_key"])
                    st.rerun()
else:
    st.info("No memories yet. The AI will start remembering facts you share during interviews.")
