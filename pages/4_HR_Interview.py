"""HR Interview Simulation page."""

import streamlit as st
import json
from dotenv import load_dotenv
import database as db
import auth_utils as auth
from ai_engine import generate_hr_questions, analyze_hr_response, generate_final_report
from voice_handler import transcribe_audio, analyze_speech_patterns, synthesize_speech, get_browser_stt_component
import streamlit.components.v1 as components
from browser_lock import inject_browser_lock
from webcam_proctor import inject_webcam_proctor
from user_memory import extract_memories_from_conversation, extract_memories_with_ai, get_memory_context_for_ai

load_dotenv()

# Require authentication
auth.require_auth()

st.set_page_config(page_title="IntervueX – HR Interview", page_icon="🤝", layout="wide")

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui_utils import apply_global_css
apply_global_css()

st.markdown("""
<style>
    .interviewer-msg {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-left: 4px solid #818CF8;
        padding: 16px 20px;
        border-radius: 12px;
        margin: 10px 0;
    }
    .candidate-msg {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-left: 4px solid #34D399;
        padding: 16px 20px;
        border-radius: 12px;
        margin: 10px 0;
    }
    .hr-question-card {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #EC4899;
        border-radius: 16px;
        padding: 24px;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("user_id"):
    st.warning("Please sign in from the home page to start an interview.")
    st.stop()

user_id = st.session_state.user_id

# Initialize HR interview state
if "hr_session_id" not in st.session_state:
    st.session_state.hr_session_id = None
if "hr_questions" not in st.session_state:
    st.session_state.hr_questions = []
if "hr_current_idx" not in st.session_state:
    st.session_state.hr_current_idx = 0
if "hr_interview_active" not in st.session_state:
    st.session_state.hr_interview_active = False
if "hr_conversation" not in st.session_state:
    st.session_state.hr_conversation = []
if "hr_responses" not in st.session_state:
    st.session_state.hr_responses = []
if "hr_last_ai_message" not in st.session_state:
    st.session_state.hr_last_ai_message = ""

st.markdown("## 🤝 HR Interview Simulation")

if not st.session_state.hr_interview_active:
    st.markdown("### Configure Your HR Interview")

    resume = db.get_latest_resume(user_id)
    skills = resume.get("skills", []) if resume else []
    experience = resume.get("experience", []) if resume else []

    target_role = st.text_input("Target Role", value="Software Engineer",
                                placeholder="e.g., Senior Backend Developer")

    if skills:
        st.info(f"🎯 Questions will be personalized based on your resume: {', '.join(skills[:6])}")
    else:
        st.warning("📄 Upload your resume for personalized HR questions.")

    st.markdown("---")

    if st.button("🚀 Start HR Interview", use_container_width=True, type="primary"):
        with st.spinner("AI is preparing your personalized HR questions..."):
            session_id = db.create_session(
                user_id=user_id,
                session_type="hr",
                difficulty="medium",
                topic=target_role,
            )

            try:
                memory_ctx = get_memory_context_for_ai(user_id)
                hr_questions = generate_hr_questions(
                    skills=skills,
                    experience=experience,
                    role=target_role,
                    user_memory_context=memory_ctx,
                )
            except Exception as e:
                st.warning(f"AI question generation unavailable ({e}). Using default questions.")
                hr_questions = [
                    {"question": "Tell me about yourself and your background.", "category": "behavioral", "what_to_look_for": "Clear, structured response", "follow_ups": ["What motivated your career choice?"]},
                    {"question": "Describe a challenging project you worked on.", "category": "behavioral", "what_to_look_for": "Problem-solving ability", "follow_ups": ["What was the outcome?"]},
                    {"question": "How do you handle tight deadlines and pressure?", "category": "situational", "what_to_look_for": "Stress management skills", "follow_ups": ["Give a specific example."]},
                    {"question": "Where do you see yourself in 5 years?", "category": "behavioral", "what_to_look_for": "Career vision and ambition", "follow_ups": ["How does this role fit into that plan?"]},
                    {"question": "Why are you interested in this role?", "category": "culture-fit", "what_to_look_for": "Genuine interest and research", "follow_ups": ["What excites you most about this opportunity?"]},
                ]

            st.session_state.hr_session_id = session_id
            st.session_state.hr_questions = hr_questions
            st.session_state.hr_current_idx = 0
            st.session_state.hr_interview_active = True
            st.session_state.hr_conversation = []
            st.session_state.hr_responses = []

            # Save questions to DB
            for i, q in enumerate(hr_questions):
                q_text = q.get("question", "") if isinstance(q, dict) else str(q)
                db.save_question(
                    session_id=session_id,
                    question_number=i + 1,
                    question_text=q_text,
                    question_type="hr",
                    difficulty="medium",
                )

            # Add intro message
            intro = f"Welcome! I'll be conducting your HR interview for the **{target_role}** position. Let's begin with our first question."
            st.session_state.hr_conversation.append({"role": "interviewer", "content": intro})
            st.session_state.hr_last_ai_message = intro
            db.save_chat_message(session_id, "interviewer", intro)

        st.rerun()

else:
    session_id = st.session_state.hr_session_id
    inject_browser_lock(session_id)
    inject_webcam_proctor(session_id)

    questions = st.session_state.hr_questions
    current_idx = st.session_state.hr_current_idx

    # Top bar
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"**Question {current_idx + 1} of {len(questions)}**")
    with col2:
        session = db.get_session(session_id)
        violations = session.get("tab_violations", 0) if session else 0
        if violations > 0:
            st.error(f"⚠️ Violations: {violations}")
        else:
            st.success("✅ Clean")
    with col3:
        if st.button("🛑 End Interview"):
            with st.spinner("Generating report..."):
                try:
                    db_questions = db.get_session_questions(session_id)
                    session_data = db.get_session(session_id)
                    report = generate_final_report(
                        db_questions, "hr",
                        session_data.get("tab_violations", 0) if session_data else 0
                    )
                    db.update_session_scores(
                        session_id=session_id,
                        overall=report.get("overall_score", 0),
                        technical=report.get("technical_score", 0),
                        communication=report.get("communication_score", 0),
                        reasoning=report.get("reasoning_score", 0),
                        problem_solving=report.get("problem_solving_score", 0),
                        feedback=report,
                    )
                except Exception as e:
                    st.warning(f"Could not generate AI report: {e}")
                    db.complete_session(session_id)

            # Extract memories from the full conversation
            try:
                extract_memories_with_ai(user_id, session_id, st.session_state.hr_conversation)
            except Exception:
                pass

            st.session_state.hr_interview_active = False
            st.session_state.view_session_id = session_id
            st.switch_page("pages/5_History.py")

    st.markdown("---")

    if current_idx >= len(questions):
        # Interview complete
        with st.spinner("Generating final report..."):
            try:
                db_questions = db.get_session_questions(session_id)
                session_data = db.get_session(session_id)
                report = generate_final_report(
                    db_questions, "hr",
                    session_data.get("tab_violations", 0) if session_data else 0
                )
                db.update_session_scores(
                    session_id=session_id,
                    overall=report.get("overall_score", 0),
                    technical=report.get("technical_score", 0),
                    communication=report.get("communication_score", 0),
                    reasoning=report.get("reasoning_score", 0),
                    problem_solving=report.get("problem_solving_score", 0),
                    feedback=report,
                )
            except Exception as e:
                st.warning(f"Could not generate AI report: {e}")
                db.complete_session(session_id)

        # Extract memories from the full conversation
        try:
            extract_memories_with_ai(user_id, session_id, st.session_state.hr_conversation)
        except Exception:
            pass

        st.session_state.hr_interview_active = False
        st.session_state.view_session_id = session_id
        st.switch_page("pages/5_History.py")

    current_q = questions[current_idx]
    q_text = current_q.get("question", "") if isinstance(current_q, dict) else str(current_q)
    category = current_q.get("category", "general") if isinstance(current_q, dict) else "general"

    # Display current question
    st.markdown(f"""
    <div class="hr-question-card">
        <span style="background:#EC4899;color:white;padding:2px 10px;border-radius:12px;font-size:0.8rem;">
            {category.upper()}
        </span>
        <h3 style="margin-top:12px;">🤖 {q_text}</h3>
    </div>
    """, unsafe_allow_html=True)

    # Conversation history
    if st.session_state.hr_conversation:
        with st.expander("💬 Conversation History", expanded=False):
            for msg in st.session_state.hr_conversation:
                if msg["role"] == "interviewer":
                    st.markdown(f'<div class="interviewer-msg">🤖 <strong>Interviewer:</strong><br>{msg["content"]}</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="candidate-msg">👤 <strong>You:</strong><br>{msg["content"]}</div>',
                                unsafe_allow_html=True)

    # Optional: play the latest interviewer message via TTS
    last_ai = st.session_state.get("hr_last_ai_message", "")
    if last_ai:
        if st.button("🔊 Listen to interviewer", key="hr_tts_play"):
            with st.spinner("Generating audio..."):
                tts_result = synthesize_speech(last_ai)
                if tts_result.get("error"):
                    st.error(tts_result["error"])
                else:
                    st.audio(tts_result["audio"], format="audio/mp3")

    st.markdown("---")

    # Response area
    st.markdown("### Your Response")

    tab1, tab2, tab3 = st.tabs(["💬 Text Response", "🎙️ Voice Response", "🗣️ Browser Speech-to-Text"])

    with tab1:
        hr_text_response = st.text_area(
            "Type your answer:",
            height=200,
            key=f"hr_text_{current_idx}",
            placeholder="Take your time to structure your response. Use the STAR method for behavioral questions..."
        )

    with tab2:
        st.markdown("Record your verbal response:")
        audio_data = st.audio_input("🎙️ Record", key=f"hr_voice_{current_idx}")

        if audio_data is not None:
            st.audio(audio_data)
            if st.button("📝 Transcribe", key=f"hr_transcribe_{current_idx}"):
                with st.spinner("Transcribing..."):
                    audio_bytes = audio_data.read()
                    result = transcribe_audio(audio_bytes, "audio/wav")
                    if result.get("error"):
                        st.error(result["error"])
                    else:
                        st.session_state[f"hr_voice_transcript_{current_idx}"] = result["transcript"]
                        st.success("Transcribed!")
                        st.markdown(f"**Transcript:** {result['transcript']}")

    with tab3:
        st.markdown("Use your browser's built-in speech recognition (Chrome/Edge recommended):")
        components.html(get_browser_stt_component(), height=200)
        st.markdown("""<p style='font-size:0.85rem;color:#6B7280;'>After speaking, the transcript is saved automatically.
        Copy it to the Text Response tab or it will be included when you submit.</p>""", unsafe_allow_html=True)

    # Submit
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Submit Answer", use_container_width=True, type="primary"):
            voice_transcript = st.session_state.get(f"hr_voice_transcript_{current_idx}", "")
            text_resp = hr_text_response or ""
            combined = f"{text_resp} {voice_transcript}".strip()

            if not combined:
                st.error("Please provide a response before submitting.")
            else:
                # Add to conversation
                st.session_state.hr_conversation.append({
                    "role": "candidate",
                    "content": combined,
                })
                db.save_chat_message(session_id, "candidate", combined)

                # Save recording event for playback
                db.save_recording_event(session_id, "conversation", {
                    "role": "candidate",
                    "content": combined,
                    "question_number": current_idx + 1,
                })

                # Extract memories from candidate's response
                extract_memories_from_conversation(
                    user_id, session_id,
                    [{"role": "candidate", "content": combined}]
                )

                with st.spinner("AI is analyzing your response..."):
                    try:
                        what_to_look_for = current_q.get("what_to_look_for", "") if isinstance(current_q, dict) else ""
                        memory_ctx = get_memory_context_for_ai(user_id)
                        analysis = analyze_hr_response(q_text, combined, what_to_look_for,
                                                      user_memory_context=memory_ctx)

                        # Update DB question
                        db_questions = db.get_session_questions(session_id)
                        if current_idx < len(db_questions):
                            db.update_question_response(
                                question_id=db_questions[current_idx]["id"],
                                candidate_response_text=combined,
                                voice_transcript=voice_transcript,
                                ai_analysis=json.dumps(analysis),
                                communication_score=analysis.get("communication_score", 0) * 10,
                                approach_score=analysis.get("relevance_score", 0) * 10,
                            )

                        st.session_state.hr_responses.append(analysis)

                        # Add interviewer feedback to conversation
                        feedback_msg = analysis.get("feedback", "Thank you for your response.")
                        follow_ups = analysis.get("follow_up_questions", [])
                        if follow_ups:
                            feedback_msg += f"\n\n**Follow-up:** {follow_ups[0]}"

                        st.session_state.hr_conversation.append({
                            "role": "interviewer",
                            "content": feedback_msg,
                        })
                        st.session_state.hr_last_ai_message = feedback_msg
                        db.save_chat_message(session_id, "interviewer", feedback_msg)

                        # Save recording events
                        db.save_recording_event(session_id, "analysis", {
                            "analysis": analysis,
                            "question_number": current_idx + 1,
                        })
                        db.save_recording_event(session_id, "conversation", {
                            "role": "interviewer",
                            "content": feedback_msg,
                        })

                    except Exception as e:
                        st.error(f"AI Analysis Error: {e}")
                        st.session_state.hr_conversation.append({
                            "role": "system",
                            "content": "AI analysis unavailable. Your response has been recorded.",
                        })

                st.rerun()

    with col2:
        if st.button("⏭️ Next Question", use_container_width=True):
            st.session_state.hr_current_idx += 1
            # Add next question to conversation
            if st.session_state.hr_current_idx < len(questions):
                next_q = questions[st.session_state.hr_current_idx]
                next_text = next_q.get("question", "") if isinstance(next_q, dict) else str(next_q)
                st.session_state.hr_conversation.append({
                    "role": "interviewer",
                    "content": f"Let's move on. {next_text}",
                })
            st.rerun()

    # Display latest analysis
    if st.session_state.hr_responses and len(st.session_state.hr_responses) > current_idx:
        analysis = st.session_state.hr_responses[current_idx]
        st.markdown("---")
        st.markdown("### 📊 Response Analysis")

        col1, col2, col3 = st.columns(3)
        with col1:
            score = analysis.get("communication_score", 0)
            color = "#34D399" if score >= 7 else "#FBBF24" if score >= 5 else "#EF4444"
            st.markdown(f"**Communication:** <span style='color:{color};font-size:1.5rem;'>{score}/10</span>", unsafe_allow_html=True)
        with col2:
            score = analysis.get("relevance_score", 0)
            color = "#34D399" if score >= 7 else "#FBBF24" if score >= 5 else "#EF4444"
            st.markdown(f"**Relevance:** <span style='color:{color};font-size:1.5rem;'>{score}/10</span>", unsafe_allow_html=True)
        with col3:
            score = analysis.get("depth_score", 0)
            color = "#34D399" if score >= 7 else "#FBBF24" if score >= 5 else "#EF4444"
            st.markdown(f"**Depth:** <span style='color:{color};font-size:1.5rem;'>{score}/10</span>", unsafe_allow_html=True)

        st.markdown(f"**Feedback:** {analysis.get('feedback', '')}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**✅ Key Points Covered:**")
            for p in analysis.get("key_points_covered", []):
                st.markdown(f"- {p}")
        with col2:
            st.markdown("**📈 Missing Points:**")
            for p in analysis.get("missing_points", []):
                st.markdown(f"- {p}")
