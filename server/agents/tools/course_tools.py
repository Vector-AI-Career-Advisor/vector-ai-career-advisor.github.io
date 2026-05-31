"""Course Tools — search Udemy & Coursera for curated course recommendations."""
from __future__ import annotations

import json
import logging
import os
import requests
from langchain_core.tools import tool

log = logging.getLogger(__name__)


# Maps general topics to Coursera institutions known for those subjects
INSTITUTION_MAP = {
    "backend": "Meta",
    "backend development": "Meta",
    "frontend": "Meta",
    "web development": "Meta",
    "fullstack": "Meta",
    "full stack": "Meta",
    "react": "Meta",
    "python": "University of Michigan",
    "machine learning": "DeepLearning.AI",
    "deep learning": "DeepLearning.AI",
    "ai": "DeepLearning.AI",
    "artificial intelligence": "DeepLearning.AI",
    "data science": "IBM",
    "data engineering": "IBM",
    "data analysis": "IBM",
    "cloud": "Google",
    "devops": "Google",
    "docker": "Google",
    "kubernetes": "Google",
    "sql": "University of Michigan",
    "database": "University of Michigan",
    "java": "Duke University",
    "android": "Meta",
    "ios": "University of Toronto",
    "swift": "University of Toronto",
    "cybersecurity": "IBM",
    "networking": "Johns Hopkins University",
    "statistics": "Johns Hopkins University",
}


def _get_institution(topic: str) -> str:
    """Pick the best matching Coursera institution for a given topic."""
    topic_lower = topic.lower()
    for key, institution in INSTITUTION_MAP.items():
        if key in topic_lower:
            return institution
    return "Google"  # sensible default


def _search_udemy(topic: str, goal: str) -> list:
    api_key = os.getenv("RAPIDAPI_KEY_UDEMY")
    if not api_key:
        log.debug("RAPIDAPI_KEY_UDEMY not set — skipping Udemy search")
        return []

    search_query = f"{topic} project" if goal == "project" else f"{topic} course"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-rapidapi-host": "udemy-coupons-and-courses.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }
    payload = {"searchQuery": search_query, "page": 1, "limit": 10}
    try:
        log.debug("Udemy search: %s", search_query)
        r = requests.post(
            "https://udemy-coupons-and-courses.p.rapidapi.com/search.php",
            headers=headers,
            data=payload,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        result = data if isinstance(data, list) else data.get("courses") or data.get("results") or []
        log.info("Udemy returned %d courses for '%s'", len(result), topic)
        return result
    except requests.RequestException as e:
        log.warning("Udemy API error: %s", e)
        return []


def _search_coursera(topic: str, goal: str) -> list:
    api_key = os.getenv("RAPIDAPI_KEY_COURSERA")
    if not api_key:
        log.debug("RAPIDAPI_KEY_COURSERA not set — skipping Coursera search")
        return []

    institution = _get_institution(topic)
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "collection-for-coursera-courses.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }
    params = {
        "page_no": 1,
        "course_institution": institution,
    }
    try:
        log.debug("Coursera search: institution=%s topic=%s", institution, topic)
        r = requests.get(
            "https://collection-for-coursera-courses.p.rapidapi.com/rapidapi/course/get_course.php",
            headers=headers,
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        result = data if isinstance(data, list) else data.get("courses") or data.get("results") or []
        log.info("Coursera returned %d courses for '%s'", len(result), topic)
        return result
    except requests.RequestException as e:
        log.warning("Coursera API error: %s", e)
        return []


def _is_free(course: dict) -> bool:
    price = course.get("price") or course.get("coupon_price") or course.get("cost") or ""
    if isinstance(price, (int, float)):
        return price == 0
    return str(price).lower() in ["free", "0", "$0", "free trial", "audit"]


def _slim(course: dict, platform: str) -> dict:
    """Return only the fields needed to pass to Claude."""
    return {
        "platform": platform,
        "title": course.get("title") or course.get("name") or "Untitled",
        "description": (course.get("description") or course.get("short_description") or "")[:150],
        "rating": course.get("rating") or "",
        "url": course.get("url") or course.get("link") or "",
        "free": _is_free(course),
    }


def _ask_claude(topic: str, goal: str, courses: list[dict]) -> str:
    """Send the raw course list to Claude and ask for a concise recommendation."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        log.warning("ANTHROPIC_API_KEY not set — using fallback course formatter")
        return _fallback_format(topic, goal, courses)

    if not courses:
        log.debug("No courses to send to Claude — using fallback")
        return _fallback_format(topic, goal, courses)

    goal_label = "hands-on project building" if goal == "project" else "conceptual understanding"
    courses_json = json.dumps(courses, ensure_ascii=False, indent=2)

    prompt = f"""You are a career advisor recommending courses for someone who wants to learn **{topic}**.
Their goal: {goal_label}.

Here are the courses fetched from Udemy and Coursera (raw data):
{courses_json}

Write a SHORT, friendly recommendation. Rules:
- Prefer free courses. Mention paid ones only if clearly superior.
- Pick the 1-2 BEST options per category (Coursera free, Udemy free, Udemy paid).
- Skip a category entirely if there are no good results.
- For each course: name, 1-sentence reason why, URL if available.
- End with a 2-3 line personal recommendation (order to take them, project tip).
- NO bullet overload. Keep it concise — max ~200 words total.
- Use markdown headers: **Best free (Coursera)**, **Best free (Udemy)**, **Best paid (Udemy)**, **My recommendation**.
"""

    try:
        log.info("Sending %d courses to Claude for curation (topic=%s)", len(courses), topic)
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        result = resp.json()["content"][0]["text"].strip()
        log.info("Claude curation complete for topic '%s'", topic)
        return result
    except Exception as e:
        log.warning("Claude API error: %s — using fallback", e)
        return _fallback_format(topic, goal, courses)


def _fallback_format(topic: str, goal: str, courses: list[dict]) -> str:
    """Simple formatter used when Claude API is unavailable."""
    free = [c for c in courses if c["free"]][:3]
    paid = [c for c in courses if not c["free"]][:2]
    lines = [f"**Course recommendations for {topic}**\n"]
    if free:
        lines.append("**Free courses**")
        for c in free:
            entry = f"- **{c['title']}** ({c['platform']})"
            if c["url"]:
                entry += f" — {c['url']}"
            lines.append(entry)
    if paid:
        lines.append("\n**Paid courses**")
        for c in paid:
            entry = f"- **{c['title']}** ({c['platform']})"
            if c["rating"]:
                entry += f" ⭐ {c['rating']}"
            lines.append(entry)
    if not free and not paid:
        lines.append("No courses found. Try searching directly on udemy.com or coursera.org.")
    lines.append("\n**Tip:** Build real projects and put them on GitHub — that matters more than certificates.")
    return "\n".join(lines)


@tool
def recommend_courses(topic: str, goal: str) -> str:
    """Search Udemy & Coursera and return AI-curated course recommendations.

    Args:
        topic: The skill or subject (e.g. 'Docker', 'React', 'Data Engineering', 'Backend Development')
        goal: Either 'project' (hands-on portfolio building) or 'knowledge' (conceptual understanding)

    Returns:
        AI-curated course recommendations with direct links and reasoning.
    """
    log.info("recommend_courses called | topic='%s' goal='%s'", topic, goal)

    udemy_raw = _search_udemy(topic, goal)
    coursera_raw = _search_coursera(topic, goal)

    log.info("Course search complete | udemy=%d coursera=%d", len(udemy_raw), len(coursera_raw))

    if not udemy_raw and not coursera_raw:
        log.warning("No courses found for topic='%s'", topic)
        return (
            f"**No courses found for '{topic}'**\n\n"
            f"The course APIs couldn't connect right now. Try directly:\n\n"
            f"1. **Udemy:** udemy.com — search '{topic}'\n"
            f"2. **Coursera:** coursera.org — search '{topic}'\n"
            f"3. **Free:** YouTube channels like Academind, freeCodeCamp, Traversy Media\n\n"
            f"**Pro tip:** Prioritize courses that include real project building for your portfolio."
        )

    courses = (
        [_slim(c, "Coursera") for c in coursera_raw[:6]]
        + [_slim(c, "Udemy") for c in udemy_raw[:6]]
    )

    log.info("Sending %d combined courses to Claude for curation", len(courses))
    return _ask_claude(topic, goal, courses)
