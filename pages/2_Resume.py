"""Resume Upload and Management page."""

import streamlit as st
import json
from dotenv import load_dotenv
import database as db
import auth_utils as auth
from resume_parser import parse_resume

load_dotenv()

# Require authentication
auth.require_auth()

st.set_page_config(page_title="IntervueX – Resume", page_icon="📄", layout="wide")

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui_utils import apply_global_css
apply_global_css()

if not st.session_state.get("user_id"):
    st.warning("Please sign in from the home page to manage your resume.")
    st.stop()

user_id = st.session_state.user_id

st.markdown("## 📄 Resume Management")
st.markdown("Upload your resume to get personalized interview questions based on your skills and experience.")
st.markdown("---")

# File uploader
uploaded_file = st.file_uploader(
    "Upload your resume (PDF or TXT)",
    type=["pdf", "txt"],
    help="We'll extract your skills, experience, and education to personalize your interview experience."
)

if uploaded_file is not None:
    if st.button("🔍 Analyze Resume", use_container_width=True, type="primary"):
        with st.spinner("Analyzing your resume with AI..."):
            try:
                file_bytes = uploaded_file.read()
                result = parse_resume(file_bytes, uploaded_file.name)

                # Save to database
                db.save_resume(
                    user_id=user_id,
                    filename=uploaded_file.name,
                    raw_text=result.get("raw_text", ""),
                    skills=result.get("skills", []),
                    experience=result.get("experience", []),
                    education=result.get("education", []),
                    summary=result.get("summary", "")
                )

                st.success("Resume analyzed and saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error analyzing resume: {e}")
                st.info("Please ensure your GROQ_API_KEY is set correctly in the .env file for AI-based resume analysis.")

st.markdown("---")

# Display current resume info
resume = db.get_latest_resume(user_id)
if resume:
    st.markdown("### 📋 Current Resume Analysis")

    # Summary
    st.markdown("#### Professional Summary")
    st.info(resume.get("summary", "No summary available"))

    col1, col2 = st.columns(2)

    with col1:
        # Skills
        st.markdown("#### 🛠️ Extracted Skills")
        skills = resume.get("skills", [])
        if skills:
            # Display as tags
            skills_html = " ".join(
                [f'<span style="background:#4F46E5;color:white;padding:4px 12px;border-radius:20px;'
                 f'margin:2px;display:inline-block;font-size:0.85rem;">{skill}</span>'
                 for skill in skills]
            )
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.write("No skills detected")

        st.markdown("")

        # Education
        st.markdown("#### 🎓 Education")
        education = resume.get("education", [])
        if education:
            for edu in education:
                if isinstance(edu, dict):
                    st.markdown(f"**{edu.get('degree', 'N/A')}**")
                    st.markdown(f"_{edu.get('institution', 'N/A')}_ | {edu.get('year', 'N/A')}")
                    st.markdown("---")
                else:
                    st.markdown(f"- {edu}")
        else:
            st.write("No education info detected")

    with col2:
        # Experience
        st.markdown("#### 💼 Experience")
        experience = resume.get("experience", [])
        if experience:
            for exp in experience:
                if isinstance(exp, dict):
                    st.markdown(f"**{exp.get('title', 'N/A')}** at _{exp.get('company', 'N/A')}_")
                    st.markdown(f"Duration: {exp.get('duration', 'N/A')}")
                    if exp.get("description"):
                        st.markdown(f"> {exp['description'][:200]}...")
                    st.markdown("---")
                else:
                    st.markdown(f"- {exp}")
        else:
            st.write("No experience info detected")

    # Raw text preview
    with st.expander("📝 Raw Extracted Text"):
        st.text_area("", value=resume.get("raw_text", ""), height=300, disabled=True)

    st.markdown("---")
    st.markdown("#### 📊 Resume Stats")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Skills Found", len(resume.get("skills", [])))
    with col2:
        st.metric("Experience Entries", len(resume.get("experience", [])))
    with col3:
        st.metric("Education Entries", len(resume.get("education", [])))

else:
    st.info("👆 Upload your resume above to get started with personalized interview questions!")

    st.markdown("### Why upload your resume?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **🎯 Personalized Questions**
        
        Get interview questions tailored to your actual skills and experience level.
        """)
    with col2:
        st.markdown("""
        **📈 Targeted Practice**
        
        Focus on areas relevant to your career goals and current skill gaps.
        """)
    with col3:
        st.markdown("""
        **🔍 Skill Gap Analysis**
        
        Identify areas where you need more preparation based on your background.
        """)
