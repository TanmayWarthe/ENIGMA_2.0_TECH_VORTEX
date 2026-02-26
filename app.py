"""Main Streamlit application for AI Interview Simulation System."""

import streamlit as st
from dotenv import load_dotenv
import database as db
import os

from ui_utils import apply_global_css

load_dotenv()

# Initialize database
db.init_db()

st.set_page_config(
    page_title="IntervueX – AI Interview Coach",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Make the entire app use the Outfit font natively */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }
    
    .main-header {
        font-size: 4.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4F46E5, #7C3AED, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        letter-spacing: -0.03em;
    }
    .sub-header {
        font-size: 1.15rem;
        color: var(--text-color);
        opacity: 0.75;
        margin-bottom: 2.5rem;
        font-weight: 400;
        line-height: 1.6;
    }
    .feature-card {
        background: #ffffff !important;
        color: #000000 !important;
        border-radius: 20px;
        padding: 28px;
        margin: 12px 0;
        border: 1px solid rgba(128, 128, 128, 0.15);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .feature-card:hover {
        border-color: #4F46E5;
        transform: translateY(-5px);
        box-shadow: 0 12px 25px rgba(79, 70, 229, 0.15);
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 18px;
        background: var(--background-color);
        width: 64px;
        height: 64px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 16px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }
    .feature-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #000000;
        margin-bottom: 10px;
        letter-spacing: -0.01em;
    }
    .feature-desc {
        font-size: 0.95rem;
        color: #000000;
        opacity: 0.8;
        line-height: 1.6;
    }
    .stat-card {
        background: #ffffff !important;
        color: #000000 !important;
        border-radius: 18px;
        padding: 24px;
        text-align: center;
        border: 1px solid rgba(128, 128, 128, 0.15);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        margin-bottom: 1rem;
        transition: transform 0.2s;
        min-height: 260px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .stat-card:hover {
        transform: translateY(-3px);
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: 800;
        color: #4F46E5;
        letter-spacing: -0.03em;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #000000;
        opacity: 0.8;
        font-weight: 600;
        margin-top: 6px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.1);
    }
    /* Sleek Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(128, 128, 128, 0.25);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(128, 128, 128, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
# Session state initialization
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='collapsedControl'] { display: none !important; }</style>", unsafe_allow_html=True)
    
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    left_col, right_col = st.columns([1.2, 1], gap="large")

    with left_col:
        if st.session_state.auth_mode == "login":
            st.markdown('<p class="main-header" style="font-size: 3rem; margin-top: 2rem;">Master Your Next Tech Interview</p>', unsafe_allow_html=True)
            st.markdown('<p class="sub-header">AI-powered interview simulation with voice feedback, real-time code analysis, and personalized coaching to help you ace your dream job.</p>', unsafe_allow_html=True)

            st.markdown("""
            <div class="feature-card" style="padding: 20px;">
                <h4 style="margin:0; color:#4F46E5;">&lt;/&gt; Live Coding Sessions</h4>
                <p style="margin:0; font-size: 0.9em; opacity: 0.8;">Practice with real interview questions and get instant feedback.</p>
            </div>
            <div class="feature-card" style="padding: 20px;">
                <h4 style="margin:0; color:#EC4899;">✨ AI Voice Interviewer</h4>
                <p style="margin:0; font-size: 0.9em; opacity: 0.8;">Natural conversation with intelligent follow-up questions.</p>
            </div>
            <div class="feature-card" style="padding: 20px;">
                <h4 style="margin:0; color:#10B981;">⚡ Performance Analytics</h4>
                <p style="margin:0; font-size: 0.9em; opacity: 0.8;">Track progress and identify areas for improvement.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<p class="main-header" style="font-size: 3rem; margin-top: 2rem;">Launch Your Career With Confidence</p>', unsafe_allow_html=True)
            st.markdown('<p class="sub-header">Join thousands of developers who have mastered their interview skills with our AI-powered platform.</p>', unsafe_allow_html=True)
            
            st.markdown("""
            <div class="feature-card" style="padding: 15px; border-left: 5px solid #10B981;">
                <h4 style="margin:0;">✅ Free Forever Plan</h4>
                <p style="margin:0; font-size: 0.9em; opacity: 0.8;">Unlimited practice sessions, no credit card required.</p>
            </div>
            <div class="feature-card" style="padding: 15px; border-left: 5px solid #4F46E5;">
                <h4 style="margin:0;">🎯 AI-Personalized Questions</h4>
                <p style="margin:0; font-size: 0.9em; opacity: 0.8;">Questions tailored to your resume and skill level.</p>
            </div>
            <div class="feature-card" style="padding: 15px; border-left: 5px solid #EC4899;">
                <h4 style="margin:0;">📈 Detailed Analytics</h4>
                <p style="margin:0; font-size: 0.9em; opacity: 0.8;">Track your progress with comprehensive insights.</p>
            </div>
            """, unsafe_allow_html=True)

    with right_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container():
            st.markdown("""
            <style>
                div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
                    background-color: white;
                    padding: 2rem;
                    border-radius: 1rem;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    border: 1px solid rgba(0,0,0,0.05);
                }
            </style>
            """, unsafe_allow_html=True)
            if st.session_state.auth_mode == "login":
                st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>Welcome Back</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; opacity: 0.7; margin-bottom: 2rem;'>Sign in to continue your interview preparation journey</p>", unsafe_allow_html=True)
                
                email = st.text_input("Email Address", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                
                if st.button("Sign In", use_container_width=True, type="primary"):
                    if email:
                        user = db.get_user_by_email(email)
                        if user:
                            st.session_state.user_id = user["id"]
                            st.session_state.user_name = user["name"]
                            st.session_state.user_email = user["email"]
                            st.rerun()
                        else:
                            st.error("User not found.")
                    else:
                        st.error("Please enter email.")
                
                st.markdown("<p style='text-align: center; font-size: 0.8rem; opacity: 0.6; margin: 1rem 0;'>NEW TO INTERVUEX?</p>", unsafe_allow_html=True)
                if st.button("Create Free Account", use_container_width=True):
                    st.session_state.auth_mode = "register"
                    st.rerun()
            
            else:
                st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>Create Account</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; opacity: 0.7; margin-bottom: 2rem;'>Start practicing in less than 60 seconds</p>", unsafe_allow_html=True)
                
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email Address", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                
                if st.button("Create Free Account", use_container_width=True, type="primary"):
                    if name and email:
                        user_id = db.create_user(name, email)
                        st.session_state.user_id = user_id
                        st.session_state.user_name = name
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error("Please fill all fields.")
                        
                st.markdown("<p style='text-align: center; font-size: 0.8rem; opacity: 0.6; margin: 1rem 0;'>ALREADY HAVE AN ACCOUNT?</p>", unsafe_allow_html=True)
                if st.button("Sign In Instead", use_container_width=True):
                    st.session_state.auth_mode = "login"
                    st.rerun()

    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("### 🎯 IntervueX")
    st.markdown("---")
    
    st.markdown(f"**Welcome, {st.session_state.user_name}!**")
    st.markdown(f"📧 {st.session_state.user_email}")

    # Check if resume is uploaded
    resume = db.get_latest_resume(st.session_state.user_id)
    if resume:
        st.success(f"📄 Resume: {resume['filename']}")
        skills = resume.get("skills", [])
        if skills:
            st.markdown("**Skills detected:**")
            st.markdown(", ".join(skills[:10]))
    else:
        st.warning("📄 No resume uploaded yet")

    st.markdown("---")

    # Quick stats
    analytics = db.get_user_analytics(st.session_state.user_id)
    stats = analytics["stats"]
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sessions", stats.get("total", 0))
    with col2:
        avg_score = stats.get("avg_overall", 0)
        st.metric("Avg Score", f"{avg_score:.0f}" if avg_score else "N/A")

    st.markdown("---")
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.user_email = None
        st.rerun()

# Main content
if st.session_state.user_id is not None:
    # Dashboard for logged in users
    st.markdown('<p class="main-header" style="font-size: 30px">Welcome Back!</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">IntervueX is your ultimate AI-powered interview practice platform, offering real-time voice interactions, resume-based personalizations, and deep performance analytics.</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Ready for your next interview practice session, {st.session_state.user_name}?</p>', unsafe_allow_html=True)

    # Quick action buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="stat-card">
            <div class="feature-icon">💻</div>
            <div class="feature-title">DSA Interview</div>
            <div class="feature-desc">Practice coding problems with AI interviewer</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start DSA Interview", use_container_width=True, key="home_dsa"):
            st.switch_page("pages/3_DSA_Interview.py")

    with col2:
        st.markdown("""
        <div class="stat-card">
            <div class="feature-icon">🤝</div>
            <div class="feature-title">HR Interview</div>
            <div class="feature-desc">Practice behavioral questions</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start HR Interview", use_container_width=True, key="home_hr"):
            st.switch_page("pages/4_HR_Interview.py")

    with col3:
        st.markdown("""
        <div class="stat-card">
            <div class="feature-icon">📄</div>
            <div class="feature-title">My Resume</div>
            <div class="feature-desc">Upload and manage your resume</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Manage Resume", use_container_width=True, key="home_resume"):
            st.switch_page("pages/2_Resume.py")

    with col4:
        st.markdown("""
        <div class="stat-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Analytics</div>
            <div class="feature-desc">View your performance trends</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Dashboard", use_container_width=True, key="home_dash"):
            st.switch_page("pages/1_Dashboard.py")

    # Recent sessions
    st.markdown("---")
    st.markdown("### 📋 Recent IntervueX Sessions")

    sessions = db.get_user_sessions(st.session_state.user_id, limit=5)
    if sessions:
        for session in sessions:
            session_type_icons = {"dsa": "💻", "hr": "🤝", "technical": "⚙️"}
            icon = session_type_icons.get(session["session_type"], "📝")
            status_color = "🟢" if session["status"] == "completed" else "🟡"

            with st.expander(
                f"{icon} {session['session_type'].upper()} Interview - "
                f"{session['started_at'][:16]} {status_color}"
            ):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Overall", f"{session['overall_score']:.0f}/100")
                with col2:
                    st.metric("Technical", f"{session['technical_score']:.0f}/100")
                with col3:
                    st.metric("Communication", f"{session['communication_score']:.0f}/100")
                with col4:
                    st.metric("Violations", session["tab_violations"])

                if st.button("View Details", key=f"view_{session['id']}"):
                    st.session_state.view_session_id = session["id"]
                    st.switch_page("pages/5_History.py")
        else:
            st.info("No interview sessions yet. Start your first interview to see your progress here!")
