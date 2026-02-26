"""SQLite database module for Interview Simulation System."""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "interview_system.db")


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize all database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            raw_text TEXT,
            skills_json TEXT DEFAULT '[]',
            experience_json TEXT DEFAULT '[]',
            education_json TEXT DEFAULT '[]',
            summary TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_type TEXT NOT NULL CHECK(session_type IN ('dsa', 'hr', 'technical')),
            status TEXT DEFAULT 'in_progress' CHECK(status IN ('in_progress', 'completed', 'abandoned')),
            difficulty TEXT DEFAULT 'medium' CHECK(difficulty IN ('easy', 'medium', 'hard')),
            topic TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            overall_score REAL DEFAULT 0,
            technical_score REAL DEFAULT 0,
            communication_score REAL DEFAULT 0,
            reasoning_score REAL DEFAULT 0,
            problem_solving_score REAL DEFAULT 0,
            feedback_json TEXT DEFAULT '{}',
            tab_violations INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS interview_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT DEFAULT 'coding',
            difficulty TEXT DEFAULT 'medium',
            candidate_response_text TEXT,
            candidate_code TEXT,
            voice_transcript TEXT,
            ai_analysis TEXT,
            code_correctness_score REAL DEFAULT 0,
            approach_score REAL DEFAULT 0,
            communication_score REAL DEFAULT 0,
            follow_up_questions_json TEXT DEFAULT '[]',
            suggested_solutions_json TEXT DEFAULT '[]',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS tab_violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            violation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            violation_type TEXT DEFAULT 'tab_switch',
            details TEXT,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('interviewer', 'candidate', 'system')),
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'text' CHECK(message_type IN ('text', 'code', 'audio_transcript')),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS interview_recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            event_type TEXT NOT NULL CHECK(event_type IN ('code_snapshot', 'conversation', 'audio_clip', 'analysis', 'question_start')),
            event_data TEXT NOT NULL DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
        );

        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            memory_key TEXT NOT NULL,
            memory_value TEXT NOT NULL,
            category TEXT DEFAULT 'general' CHECK(category IN ('general', 'preference', 'skill', 'personal', 'interview_style')),
            source_session_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (source_session_id) REFERENCES interview_sessions(id),
            UNIQUE(user_id, memory_key)
        );

        CREATE TABLE IF NOT EXISTS proctoring_violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            violation_type TEXT NOT NULL CHECK(violation_type IN ('no_face', 'multiple_faces', 'looking_away', 'other')),
            detail TEXT,
            violation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
        );
    """)

    conn.commit()
    conn.close()


# ---- User Operations ----

def create_user(name: str, email: str) -> int:
    """Create a new user and return their ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    if cursor.lastrowid == 0:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = cursor.fetchone()["id"]
    else:
        user_id = cursor.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---- Resume Operations ----

def save_resume(user_id: int, filename: str, raw_text: str, skills: list,
                experience: list, education: list, summary: str) -> int:
    """Save a parsed resume."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resumes (user_id, filename, raw_text, skills_json, experience_json, education_json, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, filename, raw_text, json.dumps(skills), json.dumps(experience),
          json.dumps(education), summary))
    conn.commit()
    resume_id = cursor.lastrowid
    conn.close()
    return resume_id


def get_latest_resume(user_id: int) -> Optional[dict]:
    """Get the latest resume for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["skills"] = json.loads(result["skills_json"])
        result["experience"] = json.loads(result["experience_json"])
        result["education"] = json.loads(result["education_json"])
        return result
    return None


# ---- Interview Session Operations ----

def create_session(user_id: int, session_type: str, difficulty: str = "medium",
                   topic: str = None) -> int:
    """Create a new interview session."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interview_sessions (user_id, session_type, difficulty, topic)
        VALUES (?, ?, ?, ?)
    """, (user_id, session_type, difficulty, topic))
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id


def get_session(session_id: int) -> Optional[dict]:
    """Get a session by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["feedback"] = json.loads(result.get("feedback_json", "{}") or "{}")
        return result
    return None


def update_session_scores(session_id: int, overall: float, technical: float,
                          communication: float, reasoning: float,
                          problem_solving: float, feedback: dict):
    """Update session scores and feedback."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE interview_sessions
        SET overall_score = ?, technical_score = ?, communication_score = ?,
            reasoning_score = ?, problem_solving_score = ?, feedback_json = ?,
            status = 'completed', ended_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (overall, technical, communication, reasoning, problem_solving,
          json.dumps(feedback), session_id))
    conn.commit()
    conn.close()


def complete_session(session_id: int):
    """Mark a session as completed."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE interview_sessions SET status = 'completed', ended_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (session_id,))
    conn.commit()
    conn.close()


def get_user_sessions(user_id: int, limit: int = 50) -> list:
    """Get all sessions for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM interview_sessions WHERE user_id = ?
        ORDER BY started_at DESC LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def increment_tab_violations(session_id: int, violation_type: str = "tab_switch",
                             details: str = ""):
    """Record a tab violation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tab_violations (session_id, violation_type, details)
        VALUES (?, ?, ?)
    """, (session_id, violation_type, details))
    cursor.execute("""
        UPDATE interview_sessions SET tab_violations = tab_violations + 1
        WHERE id = ?
    """, (session_id,))
    conn.commit()
    conn.close()


def get_tab_violations(session_id: int) -> list:
    """Get all tab violations for a session."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tab_violations WHERE session_id = ? ORDER BY violation_time
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Question Operations ----

def save_question(session_id: int, question_number: int, question_text: str,
                  question_type: str = "coding", difficulty: str = "medium") -> int:
    """Save an interview question."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interview_questions
        (session_id, question_number, question_text, question_type, difficulty)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, question_number, question_text, question_type, difficulty))
    conn.commit()
    qid = cursor.lastrowid
    conn.close()
    return qid


def update_question_response(question_id: int, candidate_response_text: str = None,
                             candidate_code: str = None, voice_transcript: str = None,
                             ai_analysis: str = None, code_correctness_score: float = 0,
                             approach_score: float = 0, communication_score: float = 0,
                             follow_up_questions: list = None,
                             suggested_solutions: list = None):
    """Update a question with candidate's response and AI analysis."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE interview_questions
        SET candidate_response_text = ?, candidate_code = ?, voice_transcript = ?,
            ai_analysis = ?, code_correctness_score = ?, approach_score = ?,
            communication_score = ?, follow_up_questions_json = ?,
            suggested_solutions_json = ?
        WHERE id = ?
    """, (candidate_response_text, candidate_code, voice_transcript,
          ai_analysis, code_correctness_score, approach_score, communication_score,
          json.dumps(follow_up_questions or []),
          json.dumps(suggested_solutions or []),
          question_id))
    conn.commit()
    conn.close()


def get_session_questions(session_id: int) -> list:
    """Get all questions for a session."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM interview_questions WHERE session_id = ?
        ORDER BY question_number
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["follow_up_questions"] = json.loads(d.get("follow_up_questions_json", "[]") or "[]")
        d["suggested_solutions"] = json.loads(d.get("suggested_solutions_json", "[]") or "[]")
        results.append(d)
    return results


# ---- Chat Message Operations ----

def save_chat_message(session_id: int, role: str, content: str,
                      message_type: str = "text") -> int:
    """Save a chat message."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_messages (session_id, role, content, message_type)
        VALUES (?, ?, ?, ?)
    """, (session_id, role, content, message_type))
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id


def get_chat_messages(session_id: int) -> list:
    """Get all chat messages for a session."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM chat_messages WHERE session_id = ?
        ORDER BY timestamp
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Analytics Operations ----

def get_user_analytics(user_id: int) -> dict:
    """Get analytics data for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    # Total sessions
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
               AVG(CASE WHEN status = 'completed' THEN overall_score END) as avg_overall,
               AVG(CASE WHEN status = 'completed' THEN technical_score END) as avg_technical,
               AVG(CASE WHEN status = 'completed' THEN communication_score END) as avg_communication,
               AVG(CASE WHEN status = 'completed' THEN reasoning_score END) as avg_reasoning,
               AVG(CASE WHEN status = 'completed' THEN problem_solving_score END) as avg_problem_solving,
               SUM(tab_violations) as total_violations
        FROM interview_sessions WHERE user_id = ?
    """, (user_id,))
    stats = dict(cursor.fetchone())

    # Sessions by type
    cursor.execute("""
        SELECT session_type, COUNT(*) as count,
               AVG(CASE WHEN status = 'completed' THEN overall_score END) as avg_score
        FROM interview_sessions WHERE user_id = ?
        GROUP BY session_type
    """, (user_id,))
    by_type = [dict(r) for r in cursor.fetchall()]

    # Score trend over time
    cursor.execute("""
        SELECT id, session_type, overall_score, technical_score,
               communication_score, started_at
        FROM interview_sessions
        WHERE user_id = ? AND status = 'completed'
        ORDER BY started_at
    """, (user_id,))
    trend = [dict(r) for r in cursor.fetchall()]

    # Sessions by difficulty
    cursor.execute("""
        SELECT difficulty, COUNT(*) as count,
               AVG(CASE WHEN status = 'completed' THEN overall_score END) as avg_score
        FROM interview_sessions WHERE user_id = ?
        GROUP BY difficulty
    """, (user_id,))
    by_difficulty = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "stats": stats,
        "by_type": by_type,
        "trend": trend,
        "by_difficulty": by_difficulty,
    }


# ---- Interview Recording Operations ----

def save_recording_event(session_id: int, event_type: str, event_data: dict) -> int:
    """Save an interview recording event (code snapshot, conversation, etc.)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interview_recordings (session_id, event_type, event_data)
        VALUES (?, ?, ?)
    """, (session_id, event_type, json.dumps(event_data)))
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id


def get_recording_events(session_id: int) -> list:
    """Get all recording events for a session in chronological order."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM interview_recordings WHERE session_id = ?
        ORDER BY timestamp ASC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["event_data"] = json.loads(d.get("event_data", "{}") or "{}")
        results.append(d)
    return results


# ---- User Memory Operations ----

def save_user_memory(user_id: int, memory_key: str, memory_value: str,
                     category: str = "general", source_session_id: int = None):
    """Save or update a user memory entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_memory (user_id, memory_key, memory_value, category, source_session_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, memory_key)
        DO UPDATE SET memory_value = excluded.memory_value,
                     updated_at = CURRENT_TIMESTAMP,
                     source_session_id = excluded.source_session_id
    """, (user_id, memory_key, memory_value, category, source_session_id))
    conn.commit()
    conn.close()


def get_user_memories(user_id: int, category: str = None) -> list:
    """Get all memories for a user, optionally filtered by category."""
    conn = get_connection()
    cursor = conn.cursor()
    if category:
        cursor.execute("""
            SELECT * FROM user_memory WHERE user_id = ? AND category = ?
            ORDER BY updated_at DESC
        """, (user_id, category))
    else:
        cursor.execute("""
            SELECT * FROM user_memory WHERE user_id = ? ORDER BY updated_at DESC
        """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user_memory(user_id: int, memory_key: str):
    """Delete a specific user memory."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM user_memory WHERE user_id = ? AND memory_key = ?
    """, (user_id, memory_key))
    conn.commit()
    conn.close()


def get_user_memory_summary(user_id: int) -> str:
    """Get a formatted summary of all user memories for AI context injection."""
    memories = get_user_memories(user_id)
    if not memories:
        return ""
    lines = []
    for m in memories:
        lines.append(f"- {m['memory_key']}: {m['memory_value']}")
    return "\n".join(lines)


# ---- Proctoring Violation Operations ----

def save_proctoring_violation(session_id: int, violation_type: str, detail: str = "") -> int:
    """Save a webcam proctoring violation."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO proctoring_violations (session_id, violation_type, detail)
        VALUES (?, ?, ?)
    """, (session_id, violation_type, detail))
    conn.commit()
    vid = cursor.lastrowid
    conn.close()
    return vid


def get_proctoring_violations(session_id: int) -> list:
    """Get all proctoring violations for a session."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM proctoring_violations WHERE session_id = ?
        ORDER BY violation_time
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize the database on import
init_db()
