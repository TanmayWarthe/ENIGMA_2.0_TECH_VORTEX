"""DSA Interview Simulation page with voice AI agent."""

import streamlit as st
import json
from datetime import datetime
from dotenv import load_dotenv
import database as db
from ai_engine import (
    generate_dsa_question,
    analyze_candidate_response,
    generate_interviewer_response,
    generate_final_report,
)
from voice_handler import transcribe_audio, analyze_speech_patterns, synthesize_speech, get_browser_stt_component
import streamlit.components.v1 as components
from browser_lock import inject_browser_lock
from webcam_proctor import inject_webcam_proctor
from user_memory import extract_memories_from_conversation, extract_memories_with_ai, get_memory_context_for_ai

load_dotenv()

st.set_page_config(page_title="IntervueX – DSA Interview", page_icon="💻", layout="wide")

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui_utils import apply_global_css
apply_global_css()

# Custom CSS for interview page
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
    .system-msg {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-left: 4px solid #F472B6;
        padding: 12px 16px;
        border-radius: 12px;
        margin: 8px 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .question-card {
        background: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #4F46E5;
        border-radius: 16px;
        padding: 24px;
        margin: 15px 0;
    }
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

if not st.session_state.get("user_id"):
    st.warning("Please sign in from the home page to start an interview.")
    st.stop()

user_id = st.session_state.user_id

# Initialize interview session state
if "dsa_session_id" not in st.session_state:
    st.session_state.dsa_session_id = None
if "dsa_current_question" not in st.session_state:
    st.session_state.dsa_current_question = None
if "dsa_question_number" not in st.session_state:
    st.session_state.dsa_question_number = 0
if "dsa_conversation" not in st.session_state:
    st.session_state.dsa_conversation = []
if "dsa_questions_asked" not in st.session_state:
    st.session_state.dsa_questions_asked = []
if "dsa_current_analysis" not in st.session_state:
    st.session_state.dsa_current_analysis = None
if "dsa_interview_active" not in st.session_state:
    st.session_state.dsa_interview_active = False
if "dsa_question_db_id" not in st.session_state:
    st.session_state.dsa_question_db_id = None
if "dsa_total_questions" not in st.session_state:
    st.session_state.dsa_total_questions = 3
if "dsa_last_ai_message" not in st.session_state:
    st.session_state.dsa_last_ai_message = ""

st.markdown("## 💻 DSA Interview Simulation")

if not st.session_state.dsa_interview_active:
    # Interview setup
    st.markdown("### Configure Your Interview")

    resume = db.get_latest_resume(user_id)
    skills = resume.get("skills", []) if resume else []

    col1, col2 = st.columns(2)
    with col1:
        difficulty = st.select_slider(
            "Difficulty Level",
            options=["easy", "medium", "hard"],
            value="medium"
        )
        num_questions = st.slider("Number of Questions", 1, 5, 3)

    with col2:
        topic_options = [
            "Random / Mixed",
            "Arrays & Strings",
            "Linked Lists",
            "Trees & Graphs",
            "Dynamic Programming",
            "Sorting & Searching",
            "Stack & Queue",
            "Hash Tables",
            "Recursion & Backtracking",
            "Greedy Algorithms",
        ]
        topic = st.selectbox("Focus Topic", topic_options)
        if topic == "Random / Mixed":
            topic = None

        enable_voice = st.checkbox("Enable Voice Recording", value=True,
                                   help="Record your verbal explanation via microphone")

    if skills:
        st.info(f"🎯 Questions will be personalized to your skills: {', '.join(skills[:8])}")
    else:
        st.warning("📄 Upload your resume for personalized questions, or continue with general questions.")

    st.markdown("---")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🚀 Start Interview", use_container_width=True, type="primary"):
            # Create session
            session_id = db.create_session(
                user_id=user_id,
                session_type="dsa",
                difficulty=difficulty,
                topic=topic,
            )
            st.session_state.dsa_session_id = session_id
            st.session_state.dsa_interview_active = True
            st.session_state.dsa_question_number = 0
            st.session_state.dsa_conversation = []
            st.session_state.dsa_questions_asked = []
            st.session_state.dsa_total_questions = num_questions
            st.session_state.dsa_enable_voice = enable_voice
            st.rerun()

else:
    # Active interview
    session_id = st.session_state.dsa_session_id

    # Inject browser lock and webcam proctoring
    inject_browser_lock(session_id)
    inject_webcam_proctor(session_id)

    # Top bar with session info
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"**Session #{session_id}** | Question {st.session_state.dsa_question_number + 1} of {st.session_state.dsa_total_questions}")
    with col2:
        session = db.get_session(session_id)
        st.markdown(f"**Difficulty:** {session['difficulty'].title() if session else 'N/A'}")
    with col3:
        violations = session.get("tab_violations", 0) if session else 0
        if violations > 0:
            st.error(f"⚠️ Violations: {violations}")
        else:
            st.success("✅ No violations")
    with col4:
        if st.button("🛑 End Interview", type="secondary"):
            st.session_state.dsa_ending = True

    st.markdown("---")

    # Handle end interview
    if st.session_state.get("dsa_ending"):
        st.warning("Are you sure you want to end the interview?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, End Interview", type="primary"):
                # Generate final report
                with st.spinner("Generating final report..."):
                    try:
                        questions = db.get_session_questions(session_id)
                        session_data = db.get_session(session_id)
                        report = generate_final_report(
                            questions,
                            "dsa",
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
                    extract_memories_with_ai(user_id, session_id, st.session_state.dsa_conversation)
                except Exception:
                    pass  # Memory extraction is best-effort

                # Reset state
                st.session_state.dsa_interview_active = False
                st.session_state.dsa_ending = False
                st.session_state.view_session_id = session_id
                st.switch_page("pages/5_History.py")
        with col2:
            if st.button("No, Continue"):
                st.session_state.dsa_ending = False
                st.rerun()
        st.stop()

    # Generate new question if needed
    if st.session_state.dsa_current_question is None:
        if st.session_state.dsa_question_number >= st.session_state.dsa_total_questions:
            # All questions done, generate report
            with st.spinner("Generating final interview report..."):
                try:
                    questions = db.get_session_questions(session_id)
                    session_data = db.get_session(session_id)
                    report = generate_final_report(
                        questions,
                        "dsa",
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
                extract_memories_with_ai(user_id, session_id, st.session_state.dsa_conversation)
            except Exception:
                pass

            st.session_state.dsa_interview_active = False
            st.session_state.view_session_id = session_id
            st.switch_page("pages/5_History.py")

        with st.spinner("AI Interviewer is preparing the next question..."):
            resume = db.get_latest_resume(user_id)
            skills = resume.get("skills", []) if resume else []
            session_data = db.get_session(session_id)

            try:
                # Get user memory context for personalized AI
                memory_ctx = get_memory_context_for_ai(user_id)

                question = generate_dsa_question(
                    skills=skills,
                    difficulty=session_data.get("difficulty", "medium") if session_data else "medium",
                    topic=session_data.get("topic") if session_data else None,
                    previous_questions=st.session_state.dsa_questions_asked,
                    user_memory_context=memory_ctx,
                )
            except Exception as e:
                st.warning(f"AI question generation unavailable ({e}). Using fallback question.")
                question = {
                    "title": "Two Sum",
                    "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume each input has exactly one solution.",
                    "examples": [{"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "nums[0] + nums[1] == 9"}],
                    "constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"],
                    "hints": ["Use a hash map to store complements"],
                    "expected_approach": "Hash map for O(n) lookup",
                    "time_complexity": "O(n)", "space_complexity": "O(n)",
                    "topic_tags": ["Array", "Hash Table"],
                    "difficulty": session_data.get("difficulty", "medium") if session_data else "medium",
                    "starter_code_python": "def twoSum(nums: list[int], target: int) -> list[int]:\n    # Your code here\n    pass"
                }

            st.session_state.dsa_current_question = question
            st.session_state.dsa_questions_asked.append(question.get("title", ""))

            # Save question to DB
            qid = db.save_question(
                session_id=session_id,
                question_number=st.session_state.dsa_question_number + 1,
                question_text=f"{question.get('title', '')}: {question.get('description', '')}",
                question_type="coding",
                difficulty=question.get("difficulty", "medium"),
            )
            st.session_state.dsa_question_db_id = qid

            # Add to conversation
            intro_msg = f"**Question {st.session_state.dsa_question_number + 1}: {question.get('title', '')}**\n\n{question.get('description', '')}"
            st.session_state.dsa_conversation.append({
                "role": "interviewer",
                "content": intro_msg
            })
            db.save_chat_message(session_id, "interviewer", intro_msg)

            st.rerun()

    question = st.session_state.dsa_current_question

    # Display question
    st.markdown(f"""
    <div class="question-card">
        <h3>📝 {question.get('title', 'Problem')}</h3>
        <p>{question.get('description', '')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Examples
    examples = question.get("examples", [])
    if examples:
        with st.expander("📋 Examples", expanded=True):
            for i, ex in enumerate(examples):
                st.markdown(f"**Example {i + 1}:**")
                st.code(f"Input: {ex.get('input', '')}\nOutput: {ex.get('output', '')}")
                if ex.get("explanation"):
                    st.markdown(f"_Explanation: {ex['explanation']}_")

    # Constraints
    constraints = question.get("constraints", [])
    if constraints:
        with st.expander("⚙️ Constraints"):
            for c in constraints:
                st.markdown(f"- {c}")

    # Hints (collapsible)
    hints = question.get("hints", [])
    if hints:
        with st.expander("💡 Hints (try solving without these first!)"):
            for i, h in enumerate(hints):
                st.markdown(f"**Hint {i + 1}:** {h}")

    st.markdown("---")

    # Conversation history
    st.markdown("### 💬 Interview Conversation")
    for msg in st.session_state.dsa_conversation:
        if msg["role"] == "interviewer":
            st.markdown(f'<div class="interviewer-msg">🤖 <strong>Interviewer:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True)
        elif msg["role"] == "candidate":
            st.markdown(f'<div class="candidate-msg">👤 <strong>You:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="system-msg">ℹ️ {msg["content"]}</div>',
                        unsafe_allow_html=True)

    # Optional: play the latest interviewer message via TTS
    last_ai = st.session_state.get("dsa_last_ai_message", "")
    if last_ai:
        if st.button("🔊 Listen to last interviewer message"):
            with st.spinner("Generating audio..."):
                tts_result = synthesize_speech(last_ai)
                if tts_result.get("error"):
                    st.error(tts_result["error"])
                else:
                    st.audio(tts_result["audio"], format="audio/mp3")

    st.markdown("---")

    # Response section
    st.markdown("### ✍️ Your Response")

    tab1, tab2, tab3, tab4 = st.tabs(["💻 Code Editor", "🎙️ Voice Explanation", "🗣️ Browser Speech-to-Text", "💬 Text Response"])

    with tab1:
        starter_code = question.get("starter_code_python", "def solution():\n    # Your code here\n    pass")
        code_response = st.text_area(
            "Write your solution here:",
            value=starter_code,
            height=300,
            key="code_editor",
        )

    with tab2:
        if st.session_state.get("dsa_enable_voice", True):
            st.markdown("Record your verbal explanation of your approach:")
            audio_data = st.audio_input("🎙️ Record your explanation", key="voice_input")

            if audio_data is not None:
                st.audio(audio_data)
                if st.button("📝 Transcribe Audio", key="transcribe_btn"):
                    with st.spinner("Transcribing with Deepgram..."):
                        audio_bytes = audio_data.read()
                        result = transcribe_audio(audio_bytes, "audio/wav")

                        if result.get("error"):
                            st.error(f"Transcription error: {result['error']}")
                        else:
                            st.session_state.dsa_voice_transcript = result.get("transcript", "")
                            speech_analysis = analyze_speech_patterns(result.get("words", []))
                            st.session_state.dsa_speech_analysis = speech_analysis

                            st.success("Transcription complete!")
                            st.markdown(f"**Transcript:** {result['transcript']}")

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Speaking Pace", f"{speech_analysis['speaking_pace_wpm']} WPM")
                            with col2:
                                st.metric("Filler Words", speech_analysis["filler_word_count"])
                            with col3:
                                st.metric("Pauses", speech_analysis["pause_count"])

                if st.session_state.get("dsa_voice_transcript"):
                    st.info(f"Current transcript: {st.session_state.dsa_voice_transcript}")
        else:
            st.info("Voice recording is disabled for this session.")

    with tab3:
        st.markdown("Use your browser's built-in speech recognition (Chrome/Edge recommended):")
        components.html(get_browser_stt_component(), height=200)
        st.markdown("""<p style='font-size:0.85rem;color:#6B7280;'>After speaking, the transcript is saved automatically.
        Copy it to the Text Response tab or it will be included when you submit.</p>""", unsafe_allow_html=True)

    with tab4:
        text_response = st.text_area(
            "Type your explanation here (alternative to voice):",
            height=150,
            key="text_response",
            placeholder="Explain your approach, time complexity, and any trade-offs..."
        )

    st.markdown("---")

    # Submit response
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        if st.button("📤 Submit Response & Get Feedback", use_container_width=True, type="primary"):
            voice_transcript = st.session_state.get("dsa_voice_transcript", "")
            text_resp = st.session_state.get("text_response", "")
            code = st.session_state.get("code_editor", "")

            # Combine voice and text responses
            combined_explanation = ""
            if voice_transcript:
                combined_explanation += f"[Voice]: {voice_transcript}\n"
            if text_resp:
                combined_explanation += f"[Text]: {text_resp}"

            if not combined_explanation.strip() and not code.strip():
                st.error("Please provide at least a code solution or an explanation.")
            else:
                # Add candidate response to conversation
                candidate_msg = ""
                if code.strip():
                    candidate_msg += f"**Code:**\n```python\n{code}\n```\n"
                if combined_explanation.strip():
                    candidate_msg += f"\n**Explanation:** {combined_explanation}"

                st.session_state.dsa_conversation.append({
                    "role": "candidate",
                    "content": candidate_msg,
                })
                db.save_chat_message(session_id, "candidate", candidate_msg)

                # Save recording event for playback
                db.save_recording_event(session_id, "code_snapshot", {
                    "code": code,
                    "question_number": st.session_state.dsa_question_number + 1,
                    "explanation": combined_explanation,
                })
                db.save_recording_event(session_id, "conversation", {
                    "role": "candidate",
                    "content": candidate_msg,
                })

                # Extract memories from candidate's response
                extract_memories_from_conversation(
                    user_id, session_id,
                    [{"role": "candidate", "content": combined_explanation}]
                )

                with st.spinner("AI is analyzing your response..."):
                    try:
                        memory_ctx = get_memory_context_for_ai(user_id)
                        analysis = analyze_candidate_response(
                            question=question,
                            code=code,
                            voice_transcript=combined_explanation,
                            conversation_history=st.session_state.dsa_conversation,
                            user_memory_context=memory_ctx,
                        )
                        st.session_state.dsa_current_analysis = analysis

                        # Update question in DB
                        code_score = analysis.get("code_correctness", {}).get("score", 0) * 10
                        approach_score = analysis.get("approach_analysis", {}).get("score", 0) * 10
                        comm_score = analysis.get("communication_analysis", {}).get("score", 0) * 10

                        db.update_question_response(
                            question_id=st.session_state.dsa_question_db_id,
                            candidate_response_text=combined_explanation,
                            candidate_code=code,
                            voice_transcript=voice_transcript,
                            ai_analysis=json.dumps(analysis),
                            code_correctness_score=code_score,
                            approach_score=approach_score,
                            communication_score=comm_score,
                            follow_up_questions=analysis.get("follow_up_questions", []),
                            suggested_solutions=analysis.get("suggested_solutions", []),
                        )

                        # Generate interviewer response
                        interviewer_response = generate_interviewer_response(
                            question=question,
                            conversation_history=st.session_state.dsa_conversation,
                            analysis=analysis,
                            user_memory_context=memory_ctx,
                        )

                        st.session_state.dsa_conversation.append({
                            "role": "interviewer",
                            "content": interviewer_response,
                        })
                        st.session_state.dsa_last_ai_message = interviewer_response
                        db.save_chat_message(session_id, "interviewer", interviewer_response)

                        # Save recording events
                        db.save_recording_event(session_id, "analysis", {
                            "analysis": analysis,
                            "question_number": st.session_state.dsa_question_number + 1,
                        })
                        db.save_recording_event(session_id, "conversation", {
                            "role": "interviewer",
                            "content": interviewer_response,
                        })

                    except Exception as e:
                        st.error(f"AI Analysis Error: {e}")
                        st.session_state.dsa_conversation.append({
                            "role": "system",
                            "content": f"AI analysis unavailable. Your response has been recorded.",
                        })
                        db.update_question_response(
                            question_id=st.session_state.dsa_question_db_id,
                            candidate_response_text=combined_explanation,
                            candidate_code=code,
                            voice_transcript=voice_transcript,
                        )

                # Clear voice transcript for next response
                st.session_state.dsa_voice_transcript = ""
                st.rerun()

    with col2:
        if st.button("⏭️ Next Question", use_container_width=True):
            st.session_state.dsa_question_number += 1
            st.session_state.dsa_current_question = None
            st.session_state.dsa_current_analysis = None
            st.session_state.dsa_voice_transcript = ""
            st.rerun()

    with col3:
        if st.button("💡 Get Hint", use_container_width=True):
            if hints:
                hint_idx = min(
                    st.session_state.get("dsa_hint_idx", 0),
                    len(hints) - 1
                )
                hint_msg = f"💡 **Hint:** {hints[hint_idx]}"
                st.session_state.dsa_conversation.append({
                    "role": "interviewer",
                    "content": hint_msg,
                })
                st.session_state.dsa_hint_idx = hint_idx + 1
                st.rerun()

    # Display analysis if available
    analysis = st.session_state.get("dsa_current_analysis")
    if analysis:
        st.markdown("---")
        st.markdown("### 📊 AI Analysis of Your Response")

        col1, col2, col3 = st.columns(3)
        with col1:
            code_score = analysis.get("code_correctness", {}).get("score", 0)
            color = "#34D399" if code_score >= 7 else "#FBBF24" if code_score >= 5 else "#EF4444"
            st.markdown(f"**Code Correctness:** <span style='color:{color};font-size:1.5rem;font-weight:700;'>{code_score}/10</span>", unsafe_allow_html=True)
        with col2:
            approach_score = analysis.get("approach_analysis", {}).get("score", 0)
            color = "#34D399" if approach_score >= 7 else "#FBBF24" if approach_score >= 5 else "#EF4444"
            st.markdown(f"**Approach Quality:** <span style='color:{color};font-size:1.5rem;font-weight:700;'>{approach_score}/10</span>", unsafe_allow_html=True)
        with col3:
            comm_score = analysis.get("communication_analysis", {}).get("score", 0)
            color = "#34D399" if comm_score >= 7 else "#FBBF24" if comm_score >= 5 else "#EF4444"
            st.markdown(f"**Communication:** <span style='color:{color};font-size:1.5rem;font-weight:700;'>{comm_score}/10</span>", unsafe_allow_html=True)

        # Detailed feedback
        st.markdown(f"**Overall Feedback:** {analysis.get('overall_feedback', '')}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**✅ Strengths:**")
            for s in analysis.get("strengths", []):
                st.markdown(f"- {s}")
        with col2:
            st.markdown("**📈 Areas for Improvement:**")
            for i in analysis.get("improvements", []):
                st.markdown(f"- {i}")

        # Follow-up questions
        follow_ups = analysis.get("follow_up_questions", [])
        if follow_ups:
            with st.expander("🔄 Follow-up Questions"):
                for i, fq in enumerate(follow_ups):
                    st.markdown(f"{i + 1}. {fq}")

        # Suggested solutions
        solutions = analysis.get("suggested_solutions", [])
        if solutions:
            with st.expander("💡 Suggested Solutions"):
                for sol in solutions:
                    if isinstance(sol, dict):
                        st.markdown(f"**{sol.get('approach', 'Alternative Approach')}**")
                        st.markdown(sol.get("description", ""))
                        if sol.get("code"):
                            st.code(sol["code"], language="python")
                        st.markdown(f"_Time: {sol.get('time_complexity', 'N/A')} | Space: {sol.get('space_complexity', 'N/A')}_")
                        st.markdown("---")
