"""AI Engine module using Groq for interview question generation, analysis, and feedback."""

import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Try to get API key from environment or Streamlit secrets
_groq_api_key = os.getenv("GROQ_API_KEY")
if not _groq_api_key:
    try:
        import streamlit as st
        _groq_api_key = st.secrets.get("GROQ_API_KEY")
    except:
        pass

if _groq_api_key:
    client = Groq(api_key=_groq_api_key)
else:
    client = None

MODEL = "llama-3.3-70b-versatile"


def _chat(messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Send a chat completion request with error handling."""
    if client is None:
        raise RuntimeError(
            "Groq API key not configured. Please add GROQ_API_KEY to your .env file. "
            "Get a free key at https://console.groq.com/keys"
        )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            raise RuntimeError(
                "Groq API rate limit exceeded. Please wait a moment and try again, or check your usage at https://console.groq.com"
            )
        if "invalid_api_key" in error_msg.lower() or "401" in error_msg:
            raise RuntimeError(
                "Invalid Groq API key. Please check your GROQ_API_KEY configuration."
            )
        raise RuntimeError(f"Groq API error: {error_msg}")


def extract_resume_skills(resume_text: str) -> dict:
    """Extract skills, experience, education, and summary from resume text."""
    messages = [
        {
            "role": "system",
            "content": """You are an expert resume analyzer. Extract structured information from the resume.
Return a JSON object with these exact keys:
{
    "skills": ["skill1", "skill2", ...],
    "experience": [{"title": "...", "company": "...", "duration": "...", "description": "..."}],
    "education": [{"degree": "...", "institution": "...", "year": "..."}],
    "summary": "Brief professional summary in 2-3 sentences",
    "primary_domain": "e.g., Backend Development, Data Science, Full Stack, etc.",
    "years_of_experience": "estimated total years",
    "strongest_skills": ["top 5 strongest skills based on resume context"]
}
Return ONLY valid JSON, no markdown."""
        },
        {
            "role": "user",
            "content": f"Analyze this resume and extract structured information:\n\n{resume_text}"
        }
    ]
    result = _chat(messages, temperature=0.3, max_tokens=2000)
    try:
        # Clean potential markdown wrapper
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "skills": [],
            "experience": [],
            "education": [],
            "summary": "Unable to parse resume",
            "primary_domain": "Unknown",
            "years_of_experience": "Unknown",
            "strongest_skills": []
        }


def generate_dsa_question(skills: list, difficulty: str = "medium",
                          topic: str = None, previous_questions: list = None,
                          user_memory_context: str = "") -> dict:
    """Generate a DSA interview question personalized to candidate's skills."""
    skill_context = ", ".join(skills) if skills else "general programming"
    prev_context = ""
    if previous_questions:
        prev_context = f"\n\nAvoid these previously asked questions:\n" + "\n".join(
            [f"- {q}" for q in previous_questions[-5:]]
        )

    topic_context = f"\nFocus on the topic: {topic}" if topic else ""

    messages = [
        {
            "role": "system",
            "content": f"""You are an expert technical interviewer conducting a DSA interview.
The candidate has skills in: {skill_context}
Difficulty level: {difficulty}{topic_context}{prev_context}
{user_memory_context}

Generate a coding interview question. Return a JSON object:
{{
    "title": "Problem title",
    "description": "Detailed problem description with examples",
    "examples": [
        {{"input": "...", "output": "...", "explanation": "..."}},
    ],
    "constraints": ["constraint1", "constraint2"],
    "hints": ["hint1", "hint2"],
    "expected_approach": "Brief description of optimal approach",
    "time_complexity": "Expected optimal time complexity",
    "space_complexity": "Expected optimal space complexity",
    "topic_tags": ["Array", "Dynamic Programming", etc.],
    "difficulty": "{difficulty}",
    "starter_code_python": "def solution(...):\\n    # Your code here\\n    pass"
}}
Return ONLY valid JSON."""
        },
        {
            "role": "user",
            "content": "Generate the next interview question."
        }
    ]
    result = _chat(messages, temperature=0.8, max_tokens=1500)
    try:
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "title": "Two Sum",
            "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
            "examples": [{"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "Because nums[0] + nums[1] == 9"}],
            "constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"],
            "hints": ["Think about using a hash map"],
            "expected_approach": "Use a hash map to store complements",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "topic_tags": ["Array", "Hash Table"],
            "difficulty": difficulty,
            "starter_code_python": "def solution(nums, target):\n    # Your code here\n    pass"
        }


def analyze_candidate_response(question: dict, code: str, voice_transcript: str,
                               conversation_history: list = None,
                               user_memory_context: str = "") -> dict:
    """Analyze candidate's code and verbal explanation."""
    conv_context = ""
    if conversation_history:
        conv_context = "\n\nConversation so far:\n" + "\n".join(
            [f"{m['role']}: {m['content']}" for m in conversation_history[-10:]]
        )

    messages = [
        {
            "role": "system",
            "content": f"""You are an expert technical interviewer analyzing a candidate's response.
{user_memory_context}
Question: {question.get('title', '')}: {question.get('description', '')}
Expected approach: {question.get('expected_approach', '')}
Expected time complexity: {question.get('time_complexity', '')}
Expected space complexity: {question.get('space_complexity', '')}
{conv_context}

Candidate's code:
```
{code}
```

Candidate's verbal explanation:
"{voice_transcript}"

Analyze the response thoroughly. Return a JSON object:
{{
    "code_correctness": {{
        "score": 0-10,
        "is_correct": true/false,
        "issues": ["issue1", "issue2"],
        "edge_cases_handled": true/false
    }},
    "approach_analysis": {{
        "score": 0-10,
        "approach_used": "description of approach",
        "is_optimal": true/false,
        "time_complexity_achieved": "O(...)",
        "space_complexity_achieved": "O(...)",
        "reasoning_quality": "excellent/good/fair/poor"
    }},
    "communication_analysis": {{
        "score": 0-10,
        "clarity": "excellent/good/fair/poor",
        "structure": "excellent/good/fair/poor",
        "technical_vocabulary": "excellent/good/fair/poor",
        "explanation_quality": "Brief assessment"
    }},
    "overall_feedback": "Detailed constructive feedback paragraph",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "follow_up_questions": [
        "Follow-up question 1 to probe deeper understanding",
        "Follow-up question 2 about optimization",
        "Follow-up question 3 about edge cases"
    ],
    "suggested_solutions": [
        {{
            "approach": "Approach name",
            "description": "Brief description",
            "code": "Python code for this approach",
            "time_complexity": "O(...)",
            "space_complexity": "O(...)"
        }}
    ]
}}
Return ONLY valid JSON."""
        },
        {
            "role": "user",
            "content": "Analyze the candidate's response now."
        }
    ]
    result = _chat(messages, temperature=0.3, max_tokens=3000)
    try:
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "code_correctness": {"score": 5, "is_correct": False, "issues": ["Unable to analyze"], "edge_cases_handled": False},
            "approach_analysis": {"score": 5, "approach_used": "Unknown", "is_optimal": False, "time_complexity_achieved": "Unknown", "space_complexity_achieved": "Unknown", "reasoning_quality": "fair"},
            "communication_analysis": {"score": 5, "clarity": "fair", "structure": "fair", "technical_vocabulary": "fair", "explanation_quality": "Unable to fully analyze"},
            "overall_feedback": "Unable to fully analyze the response. Please try again.",
            "strengths": [],
            "improvements": [],
            "follow_up_questions": ["Can you explain your approach in more detail?"],
            "suggested_solutions": []
        }


def generate_interviewer_response(question: dict, conversation_history: list,
                                  analysis: dict = None,
                                  user_memory_context: str = "") -> str:
    """Generate a natural interviewer response based on conversation context."""
    conv_context = "\n".join(
        [f"{m['role']}: {m['content']}" for m in conversation_history[-10:]]
    )

    analysis_context = ""
    if analysis:
        analysis_context = f"""
Current analysis of candidate:
- Code correctness: {analysis.get('code_correctness', {}).get('score', 'N/A')}/10
- Approach: {analysis.get('approach_analysis', {}).get('score', 'N/A')}/10
- Communication: {analysis.get('communication_analysis', {}).get('score', 'N/A')}/10
"""

    messages = [
        {
            "role": "system",
            "content": f"""You are a friendly but thorough technical interviewer conducting a DSA interview.
You should respond naturally, like a real interviewer would.
{user_memory_context}
Current question: {question.get('title', '')}: {question.get('description', '')}
{analysis_context}

Guidelines:
- If the candidate is on the right track, encourage them and ask probing questions
- If they're stuck, give subtle hints without giving away the answer
- Ask about time/space complexity when appropriate
- Probe for edge case handling
- Keep responses concise (2-4 sentences)
- Be professional and encouraging"""
        },
        {
            "role": "user",
            "content": f"Conversation so far:\n{conv_context}\n\nGenerate the interviewer's next response."
        }
    ]
    return _chat(messages, temperature=0.7, max_tokens=300)


def generate_hr_questions(skills: list, experience: list, role: str = "Software Engineer",
                          user_memory_context: str = "") -> list:
    """Generate HR interview questions personalized to the candidate."""
    skill_context = ", ".join(skills) if skills else "general software development"
    exp_context = json.dumps(experience[:3]) if experience else "entry-level"

    messages = [
        {
            "role": "system",
            "content": f"""You are an HR interviewer preparing questions for a {role} position.
Candidate's skills: {skill_context}
Candidate's experience: {exp_context}
{user_memory_context}

Generate 8 HR interview questions personalized to this candidate. Mix behavioral and situational questions.
Return a JSON array of objects:
[
    {{
        "question": "The question text",
        "category": "behavioral/situational/technical-behavioral/culture-fit",
        "what_to_look_for": "Key points in an ideal answer",
        "follow_ups": ["follow-up 1", "follow-up 2"]
    }}
]
Return ONLY valid JSON."""
        },
        {
            "role": "user",
            "content": "Generate the HR interview questions."
        }
    ]
    result = _chat(messages, temperature=0.7, max_tokens=2000)
    try:
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return [
            {"question": "Tell me about yourself.", "category": "behavioral", "what_to_look_for": "Clear, structured response", "follow_ups": ["What motivated your career choice?"]},
            {"question": "Describe a challenging project you worked on.", "category": "behavioral", "what_to_look_for": "Problem-solving ability", "follow_ups": ["What was the outcome?"]},
        ]


def analyze_hr_response(question: str, response_text: str, what_to_look_for: str,
                        user_memory_context: str = "") -> dict:
    """Analyze candidate's HR interview response."""
    messages = [
        {
            "role": "system",
            "content": f"""You are an expert HR interviewer analyzing a candidate's response.
{user_memory_context}
Question: {question}
Key points to evaluate: {what_to_look_for}

Candidate's response: "{response_text}"

Return a JSON object:
{{
    "communication_score": 0-10,
    "relevance_score": 0-10,
    "depth_score": 0-10,
    "confidence_level": "high/medium/low",
    "key_points_covered": ["point1", "point2"],
    "missing_points": ["point1", "point2"],
    "feedback": "Constructive feedback paragraph",
    "strengths": ["strength1"],
    "improvements": ["improvement1"],
    "follow_up_questions": ["question1", "question2"]
}}
Return ONLY valid JSON."""
        },
        {
            "role": "user",
            "content": "Analyze the candidate's response."
        }
    ]
    result = _chat(messages, temperature=0.3, max_tokens=1000)
    try:
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "communication_score": 5,
            "relevance_score": 5,
            "depth_score": 5,
            "confidence_level": "medium",
            "key_points_covered": [],
            "missing_points": [],
            "feedback": "Unable to fully analyze.",
            "strengths": [],
            "improvements": [],
            "follow_up_questions": []
        }


def generate_final_report(session_questions: list, session_type: str,
                          tab_violations: int = 0) -> dict:
    """Generate a comprehensive final interview report."""
    questions_summary = []
    for q in session_questions:
        questions_summary.append({
            "question": q.get("question_text", ""),
            "code_score": q.get("code_correctness_score", 0),
            "approach_score": q.get("approach_score", 0),
            "communication_score": q.get("communication_score", 0),
            "analysis": q.get("ai_analysis", ""),
        })

    messages = [
        {
            "role": "system",
            "content": f"""You are generating a final interview assessment report.
Interview type: {session_type}
Tab violations during interview: {tab_violations}

Questions and performance:
{json.dumps(questions_summary, indent=2)}

Generate a comprehensive report. Return JSON:
{{
    "overall_score": 0-100,
    "technical_score": 0-100,
    "communication_score": 0-100,
    "reasoning_score": 0-100,
    "problem_solving_score": 0-100,
    "integrity_note": "Note about tab violations if any",
    "executive_summary": "2-3 sentence overall assessment",
    "detailed_feedback": {{
        "technical_skills": "Paragraph about technical ability",
        "problem_solving": "Paragraph about problem-solving approach",
        "communication": "Paragraph about communication skills",
        "areas_of_strength": ["strength1", "strength2", "strength3"],
        "areas_for_improvement": ["improvement1", "improvement2", "improvement3"],
        "recommended_topics_to_study": ["topic1", "topic2", "topic3"]
    }},
    "interview_readiness": "ready/almost_ready/needs_preparation",
    "recommendation": "Strong recommendation paragraph"
}}
Return ONLY valid JSON."""
        },
        {
            "role": "user",
            "content": "Generate the final report."
        }
    ]
    result = _chat(messages, temperature=0.3, max_tokens=2000)
    try:
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "overall_score": 50,
            "technical_score": 50,
            "communication_score": 50,
            "reasoning_score": 50,
            "problem_solving_score": 50,
            "executive_summary": "Interview completed. Unable to generate detailed report.",
            "detailed_feedback": {
                "technical_skills": "N/A",
                "problem_solving": "N/A",
                "communication": "N/A",
                "areas_of_strength": [],
                "areas_for_improvement": [],
                "recommended_topics_to_study": []
            },
            "interview_readiness": "needs_preparation",
            "recommendation": "Please try the interview again for a more accurate assessment."
        }


# ─────────────────────────────────────────────────────────────────────────────
# Voice AI DSA Agent
# ─────────────────────────────────────────────────────────────────────────────

_VOICE_AGENT_SYSTEM = """You are a senior technical interviewer conducting a live real-time DSA interview via voice.

BEHAVIOR RULES:
1. Start professionally and greet the candidate briefly.
2. Ask ONE DSA problem clearly and concisely.
3. After asking, wait for the candidate explanation. Do NOT immediately evaluate.
4. Let the candidate explain; ask clarifying questions if unclear.
5. Ask at least ONE follow-up that tests deeper understanding.
6. Keep natural short sentences suitable for voice (2-4 sentences per turn).
7. If answer is shallow, prompt: walk me through it step by step, what is the time complexity, can it be optimized?
8. Challenge assumptions when necessary.
9. Guide on errors instead of directly correcting.
10. Simulate realistic pressure but stay professional and encouraging.
Never output JSON during conversation — only during final evaluation.
Never give away the answer directly.
"""

_VOICE_AGENT_EVAL_SYSTEM = """You are a strict DSA interview evaluator.
The conversation below is a completed interview.
Return ONLY the JSON below — no prose, no markdown fences.

{
  "question_asked": "string",
  "follow_up_question": "string",
  "scores": {
    "problem_understanding": 0,
    "logical_reasoning": 0,
    "data_structure_selection": 0,
    "algorithmic_efficiency": 0,
    "optimization_awareness": 0,
    "edge_case_handling": 0,
    "communication_clarity": 0
  },
  "overall_score": 0.0,
  "strengths": ["string"],
  "areas_of_improvement": ["string"],
  "optimization_suggestions": ["string"],
  "final_feedback_summary": "string"
}

Score each dimension 0-10: 0-3 weak, 4-6 basic, 7-8 strong, 9-10 excellent.
overall_score is the weighted average of all 7 scores.
"""


def voice_agent_respond(conversation_history: list, user_message: str,
                        question_context: dict = None, skills: list = None) -> str:
    """Generate the next conversational interviewer turn for the Voice DSA Agent."""
    skill_hint = f"\nCandidate skills: {', '.join(skills)}" if skills else ""
    q_hint = ""
    if question_context:
        q_hint = (
            f"\nCurrent question: {question_context.get('title', '')} — "
            f"{question_context.get('description', '')}\n"
            f"Expected approach: {question_context.get('expected_approach', '')}\n"
            f"Optimal complexity: {question_context.get('time_complexity', '')}"
        )
    messages = [{"role": "system", "content": _VOICE_AGENT_SYSTEM + skill_hint + q_hint}]
    for turn in conversation_history[-20:]:
        role = "assistant" if turn["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})
    return _chat(messages, temperature=0.7, max_tokens=300)


def voice_agent_final_evaluation(conversation_history: list) -> dict:
    """Generate the final 7-dimension JSON evaluation for a Voice DSA Agent session."""
    transcript = "\n".join(
        [f"{t['role'].upper()}: {t['content']}" for t in conversation_history]
    )
    messages = [
        {"role": "system", "content": _VOICE_AGENT_EVAL_SYSTEM},
        {"role": "user", "content": f"Interview transcript:\n\n{transcript}\n\nGenerate evaluation JSON now."}
    ]
    result = _chat(messages, temperature=0.2, max_tokens=1500)
    try:
        if result.strip().startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "question_asked": "Unknown",
            "follow_up_question": "N/A",
            "scores": {
                "problem_understanding": 5, "logical_reasoning": 5,
                "data_structure_selection": 5, "algorithmic_efficiency": 5,
                "optimization_awareness": 5, "edge_case_handling": 5,
                "communication_clarity": 5,
            },
            "overall_score": 5.0,
            "strengths": [],
            "areas_of_improvement": [],
            "optimization_suggestions": [],
            "final_feedback_summary": "Could not parse evaluation. Please try again."
        }


# ---------------------------------------------------------------------------
# Voice AI DSA Agent
# ---------------------------------------------------------------------------

_VOICE_AGENT_SYSTEM = (
    "You are a senior technical interviewer conducting a live real-time DSA "
    "interview via voice.\n\n"
    "BEHAVIOR RULES:\n"
    "1. Start professionally and greet the candidate briefly.\n"
    "2. Ask ONE DSA problem clearly and concisely.\n"
    "3. After asking, wait — do NOT immediately evaluate.\n"
    "4. Let the candidate explain; ask clarifying questions if unclear.\n"
    "5. Ask at least ONE follow-up testing deeper understanding.\n"
    "6. Keep natural, short sentences (2-4 per turn) suitable for voice.\n"
    "7. If shallow: 'Walk me through step-by-step?' / 'Time & space complexity?' "
    "/ 'Can this be optimized?'\n"
    "8. Challenge assumptions when necessary.\n"
    "9. Guide on errors instead of correcting directly.\n"
    "10. Simulate pressure but stay professional and encouraging.\n"
    "NEVER output JSON during the conversation. NEVER give away the answer."
)

_VOICE_AGENT_EVAL_SYSTEM = (
    "You are a strict DSA interview evaluator. "
    "Return ONLY the following JSON — no prose, no markdown fences.\n\n"
    '{"question_asked":"string","follow_up_question":"string",'
    '"scores":{"problem_understanding":0,"logical_reasoning":0,'
    '"data_structure_selection":0,"algorithmic_efficiency":0,'
    '"optimization_awareness":0,"edge_case_handling":0,'
    '"communication_clarity":0},"overall_score":0.0,'
    '"strengths":["string"],"areas_of_improvement":["string"],'
    '"optimization_suggestions":["string"],"final_feedback_summary":"string"}\n\n'
    "Score each dimension 0-10: 0-3 weak | 4-6 basic | 7-8 strong | 9-10 excellent. "
    "overall_score is the weighted average of all 7 scores."
)


def voice_agent_respond(conversation_history: list, user_message: str,
                        question_context: dict = None, skills: list = None) -> str:
    """Generate the next conversational interviewer turn for the Voice DSA Agent."""
    skill_hint = ("\nCandidate skills: " + ", ".join(skills)) if skills else ""
    q_hint = ""
    if question_context:
        q_hint = (
            "\nCurrent question: "
            + question_context.get("title", "") + " — "
            + question_context.get("description", "") + "\n"
            "Expected approach: " + question_context.get("expected_approach", "") + "\n"
            "Optimal complexity: " + question_context.get("time_complexity", "")
        )
    messages = [{"role": "system", "content": _VOICE_AGENT_SYSTEM + skill_hint + q_hint}]
    for turn in conversation_history[-20:]:
        role = "assistant" if turn["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})
    return _chat(messages, temperature=0.7, max_tokens=300)


def voice_agent_final_evaluation(conversation_history: list) -> dict:
    """Generate the final 7-dimension JSON evaluation for a Voice DSA Agent session."""
    transcript = "\n".join(
        t["role"].upper() + ": " + t["content"] for t in conversation_history
    )
    messages = [
        {"role": "system", "content": _VOICE_AGENT_EVAL_SYSTEM},
        {"role": "user", "content": "Interview transcript:\n\n" + transcript
         + "\n\nGenerate evaluation JSON now."}
    ]
    result = _chat(messages, temperature=0.2, max_tokens=1500)
    try:
        if result.strip().startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except Exception:
        return {
            "question_asked": "Unknown",
            "follow_up_question": "N/A",
            "scores": {k: 5 for k in [
                "problem_understanding", "logical_reasoning",
                "data_structure_selection", "algorithmic_efficiency",
                "optimization_awareness", "edge_case_handling",
                "communication_clarity",
            ]},
            "overall_score": 5.0,
            "strengths": [],
            "areas_of_improvement": [],
            "optimization_suggestions": [],
            "final_feedback_summary": "Could not parse evaluation. Please try again.",
        }


# ---------------------------------------------------------------------------
# Voice AI DSA Agent
# ---------------------------------------------------------------------------

_VOICE_AGENT_SYSTEM = (
    "You are a senior technical interviewer conducting a live real-time DSA "
    "interview via voice.\n\n"
    "BEHAVIOR RULES:\n"
    "1. Start professionally and greet the candidate briefly.\n"
    "2. Ask ONE DSA problem clearly and concisely.\n"
    "3. After asking, wait — do NOT immediately evaluate.\n"
    "4. Let the candidate explain; ask clarifying questions if unclear.\n"
    "5. Ask at least ONE follow-up testing deeper understanding.\n"
    "6. Keep natural, short sentences (2-4 per turn) suitable for voice.\n"
    "7. If shallow: 'Walk me through step-by-step?' / 'Time & space complexity?' "
    "/ 'Can this be optimized?'\n"
    "8. Challenge assumptions when necessary.\n"
    "9. Guide on errors instead of correcting directly.\n"
    "10. Simulate pressure but stay professional and encouraging.\n"
    "NEVER output JSON during the conversation. NEVER give away the answer."
)

_VOICE_AGENT_EVAL_SYSTEM = (
    "You are a strict DSA interview evaluator. "
    "Return ONLY the following JSON — no prose, no markdown fences.\n\n"
    '{"question_asked":"string","follow_up_question":"string",'
    '"scores":{"problem_understanding":0,"logical_reasoning":0,'
    '"data_structure_selection":0,"algorithmic_efficiency":0,'
    '"optimization_awareness":0,"edge_case_handling":0,'
    '"communication_clarity":0},"overall_score":0.0,'
    '"strengths":["string"],"areas_of_improvement":["string"],'
    '"optimization_suggestions":["string"],"final_feedback_summary":"string"}\n\n'
    "Score each dimension 0-10: 0-3 weak | 4-6 basic | 7-8 strong | 9-10 excellent. "
    "overall_score is the weighted average of all 7 scores."
)


def voice_agent_respond(conversation_history: list, user_message: str,
                        question_context: dict = None, skills: list = None) -> str:
    """Generate the next conversational interviewer turn for the Voice DSA Agent."""
    skill_hint = ("\nCandidate skills: " + ", ".join(skills)) if skills else ""
    q_hint = ""
    if question_context:
        q_hint = (
            "\nCurrent question: "
            + question_context.get("title", "") + " — "
            + question_context.get("description", "") + "\n"
            "Expected approach: " + question_context.get("expected_approach", "") + "\n"
            "Optimal complexity: " + question_context.get("time_complexity", "")
        )
    messages = [{"role": "system", "content": _VOICE_AGENT_SYSTEM + skill_hint + q_hint}]
    for turn in conversation_history[-20:]:
        role = "assistant" if turn["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})
    return _chat(messages, temperature=0.7, max_tokens=300)


def voice_agent_final_evaluation(conversation_history: list) -> dict:
    """Generate the final 7-dimension JSON evaluation for a Voice DSA Agent session."""
    transcript = "\n".join(
        t["role"].upper() + ": " + t["content"] for t in conversation_history
    )
    messages = [
        {"role": "system", "content": _VOICE_AGENT_EVAL_SYSTEM},
        {"role": "user", "content": "Interview transcript:\n\n" + transcript
         + "\n\nGenerate evaluation JSON now."}
    ]
    result = _chat(messages, temperature=0.2, max_tokens=1500)
    try:
        if result.strip().startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(result)
    except Exception:
        return {
            "question_asked": "Unknown",
            "follow_up_question": "N/A",
            "scores": {k: 5 for k in [
                "problem_understanding", "logical_reasoning",
                "data_structure_selection", "algorithmic_efficiency",
                "optimization_awareness", "edge_case_handling",
                "communication_clarity",
            ]},
            "overall_score": 5.0,
            "strengths": [],
            "areas_of_improvement": [],
            "optimization_suggestions": [],
            "final_feedback_summary": "Could not parse evaluation. Please try again.",
        }
