"""User Memory module - AI remembers information about users across sessions.

This module extracts key facts from interview conversations and stores them
so the AI interviewer remembers the candidate's background, preferences,
and previously shared information.
"""

import json
import database as db


def extract_memories_from_conversation(user_id: int, session_id: int,
                                        conversation: list) -> list:
    """Extract memorable facts from a conversation using AI.

    Parses the conversation to find personal facts, preferences, skills,
    and other information the user shared during the interview.

    Returns a list of extracted memory dicts.
    """
    extracted = []

    for msg in conversation:
        if msg.get("role") != "candidate":
            continue

        content = msg.get("content", "").strip()
        if not content or len(content) < 10:
            continue

        # Use simple heuristic extraction for common patterns
        # This avoids an extra API call and works for most cases
        facts = _extract_facts_heuristic(content)
        for key, value, category in facts:
            db.save_user_memory(
                user_id=user_id,
                memory_key=key,
                memory_value=value,
                category=category,
                source_session_id=session_id,
            )
            extracted.append({"key": key, "value": value, "category": category})

    return extracted


def extract_memories_with_ai(user_id: int, session_id: int,
                              conversation: list):
    """Extract memories using AI analysis (called after interview ends).

    This uses the Groq API to intelligently extract facts from the
    full conversation. Called once when the interview session ends.
    """
    try:
        from ai_engine import _chat
    except Exception:
        return []

    # Build conversation text
    conv_text = ""
    for msg in conversation:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        conv_text += f"{role}: {content}\n"

    if len(conv_text) < 50:
        return []

    messages = [
        {
            "role": "system",
            "content": """You are analyzing an interview conversation to extract key facts about the candidate.
Extract any personal information, preferences, skills, experiences, or notable details the candidate shared.

Return a JSON array of objects:
[
    {
        "key": "short_descriptive_key (e.g., 'weight', 'favorite_language', 'years_experience')",
        "value": "the actual value or fact",
        "category": "one of: general, preference, skill, personal, interview_style"
    }
]

Rules:
- Only extract FACTS explicitly stated by the candidate
- Do NOT infer or guess information
- Keep keys short and descriptive
- Keep values concise but complete
- If no facts found, return an empty array []

Return ONLY valid JSON."""
        },
        {
            "role": "user",
            "content": f"Extract key facts about the candidate from this interview conversation:\n\n{conv_text[:3000]}"
        }
    ]

    try:
        result = _chat(messages, temperature=0.2, max_tokens=1000)
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]
        facts = json.loads(result)

        extracted = []
        for fact in facts:
            if isinstance(fact, dict) and "key" in fact and "value" in fact:
                category = fact.get("category", "general")
                if category not in ("general", "preference", "skill", "personal", "interview_style"):
                    category = "general"
                db.save_user_memory(
                    user_id=user_id,
                    memory_key=fact["key"],
                    memory_value=fact["value"],
                    category=category,
                    source_session_id=session_id,
                )
                extracted.append(fact)
        return extracted
    except Exception:
        return []


def get_memory_context_for_ai(user_id: int) -> str:
    """Build a context string of user memories to inject into AI prompts.

    Returns a formatted string that can be added to the system prompt
    so the AI remembers everything about the user.
    """
    memories = db.get_user_memories(user_id)
    if not memories:
        return ""

    context = "\n=== REMEMBERED INFORMATION ABOUT THIS CANDIDATE ===\n"
    context += "You have interviewed this candidate before. Here is what you remember:\n"

    categories = {}
    for m in memories:
        cat = m.get("category", "general")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f"- {m['memory_key']}: {m['memory_value']}")

    category_labels = {
        "personal": "Personal Information",
        "skill": "Skills & Technical Background",
        "preference": "Preferences",
        "interview_style": "Interview Style",
        "general": "General Notes",
    }

    for cat, items in categories.items():
        label = category_labels.get(cat, cat.title())
        context += f"\n{label}:\n"
        context += "\n".join(items) + "\n"

    context += "\nIMPORTANT: Use this information naturally. Do NOT ask about things you already know.\n"
    context += "Reference remembered facts when relevant to make the interview feel personalized.\n"
    context += "=== END OF REMEMBERED INFORMATION ===\n"

    return context


def _extract_facts_heuristic(text: str) -> list:
    """Extract facts from text using simple pattern matching.

    Returns list of (key, value, category) tuples.
    """
    facts = []
    text_lower = text.lower()

    # Common patterns for personal info
    import re

    # Weight
    weight_match = re.search(r'(?:my |i )?weigh(?:t is|s?) (\d+\s*(?:kg|lbs?|pounds?|kilos?))', text_lower)
    if weight_match:
        facts.append(("weight", weight_match.group(1).strip(), "personal"))

    # Height
    height_match = re.search(r'(?:my |i am |i\'m )?(?:height is )?(\d+\s*(?:cm|feet|ft|inches|in|\'|"))', text_lower)
    if height_match:
        facts.append(("height", height_match.group(1).strip(), "personal"))

    # Age
    age_match = re.search(r'(?:i am |i\'m |my age is )(\d{1,2})\s*(?:years? old|yrs?)?', text_lower)
    if age_match:
        facts.append(("age", age_match.group(1).strip() + " years old", "personal"))

    # Years of experience
    exp_match = re.search(r'(\d+)\s*(?:\+\s*)?years?\s*(?:of\s*)?(?:experience|exp)', text_lower)
    if exp_match:
        facts.append(("years_of_experience", exp_match.group(1).strip() + " years", "skill"))

    # Favorite/preferred language
    lang_match = re.search(r'(?:my )?(?:favorite|preferred|favourite)\s*(?:programming\s*)?language\s*is\s*(\w+)', text_lower)
    if lang_match:
        facts.append(("favorite_language", lang_match.group(1).strip(), "preference"))

    # College/university
    college_match = re.search(r'(?:i (?:study|studied|go|went) (?:at|to)|i\'m (?:at|from)|my college is|i attend)\s+(.+?)(?:\.|,|$)', text_lower)
    if college_match:
        facts.append(("college", college_match.group(1).strip()[:100], "personal"))

    # Name preference
    name_match = re.search(r'(?:call me|my name is|i\'m called|i go by)\s+(\w+)', text_lower)
    if name_match:
        facts.append(("preferred_name", name_match.group(1).strip(), "personal"))

    # Current role/job
    role_match = re.search(r'(?:i work as|i\'m a|i am a|my role is|my job is|i\'m currently a)\s+(.+?)(?:\.|,|$)', text_lower)
    if role_match:
        facts.append(("current_role", role_match.group(1).strip()[:100], "skill"))

    # Company
    company_match = re.search(r'(?:i work at|i\'m at|i am at|my company is|i work for)\s+(.+?)(?:\.|,|$)', text_lower)
    if company_match:
        facts.append(("current_company", company_match.group(1).strip()[:100], "skill"))

    return facts
