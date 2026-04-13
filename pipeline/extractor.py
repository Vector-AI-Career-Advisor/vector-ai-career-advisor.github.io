"""
LLM-based job description extraction using Claude Haiku.
"""
from __future__ import annotations
import json
import logging
import time
import re
import anthropic
from config import (
    EXTRACTION_PROMPT,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    VALID_ROLES,
    VALID_SENIORITY,
)

log = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── Public API ────────────────────────────────────────────────────────────────

def extract_with_claude(title: str, description: str) -> dict:
    """
    Send a job title + description to Claude Haiku and return a structured extraction.
    Retries up to 3 times on transient errors.
    """
    if not description or description == "N/A":
        return _empty_extraction()

    for attempt in range(3):
        try:
            response = _client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=2000,
                temperature=0,
                system=[
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user", "content": f"Job Title: {title}\n\nJob Description:\n{description[:5000]}\n\nJSON:"},
                ],
            )
            raw = response.content[0].text.strip()
            return _parse_and_validate(raw, title)

        except json.JSONDecodeError as e:
            log.warning("Claude JSON parse error (attempt %d/3): %s", attempt + 1, e)
            if attempt == 2:
                return _empty_extraction()
            time.sleep(2)

        except anthropic.RateLimitError as e:
            wait = (2 ** attempt) * 20
            log.warning("Claude rate limit — waiting %.0fs (attempt %d/3): %s", wait, attempt + 1, e)
            if attempt == 2:
                return _empty_extraction()
            time.sleep(wait)

        except anthropic.APIConnectionError as e:
            log.warning("Claude connection error (attempt %d/3): %s", attempt + 1, e)
            if attempt == 2:
                return _empty_extraction()
            time.sleep(5)

        except Exception as e:
            log.warning("Claude unexpected error (attempt %d/3): %s", attempt + 1, e)
            if attempt == 2:
                return _empty_extraction()
            time.sleep(2)

    return _empty_extraction()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_and_validate(raw: str, title: str) -> dict:
    """Strip markdown fences, extract JSON, validate and return."""
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    data = json.loads(raw)
    return _validate(data, title)


def _empty_extraction() -> dict:
    return {
        "role":            "Other",
        "seniority":       "Not specified",
        "description":     None,
        "yearsexperience": None,
        "skills_must":     [],
        "skills_nice":     [],
        "past_experience": [],
    }


def _validate(data: dict, title: str) -> dict:
    """Validate and normalise a raw Claude extraction dict."""
    empty  = _empty_extraction()
    result = {}

    for key, default in empty.items():
        # LLM sometimes returns "experience" instead of "yearsexperience"
        llm_key = "experience" if key == "yearsexperience" else key
        val     = data.get(llm_key, data.get(key, default))

        if key in {"skills_must", "skills_nice", "past_experience"}:
            result[key] = [str(v) for v in val if v] if isinstance(val, list) else []

        elif key == "yearsexperience":
            try:
                result[key] = int(val) if val is not None else None
            except (ValueError, TypeError):
                result[key] = None

        elif key == "role":
            result[key] = str(val).strip() if val in VALID_ROLES else _infer_role(title)

        elif key == "seniority":
            result[key] = str(val).strip() if val in VALID_SENIORITY else "Not specified"

        else:
            result[key] = str(val).strip() if val else None

    # Overwrite seniority from years of experience when not a leadership role
    _apply_seniority_heuristic(result)

    return result


def _apply_seniority_heuristic(result: dict) -> None:
    """
    Override seniority based on years of experience for non-leadership roles.
    """
    leadership = {"Lead", "Staff", "Principal", "Manager", "Director", "VP"}
    yrs = result.get("yearsexperience")

    if yrs is None or result.get("seniority") in leadership:
        return

    if yrs <= 3:
        new = "Junior"
    elif yrs <= 5:
        new = "Mid"
    else:
        new = "Senior"

    if new != result.get("seniority"):
        log.debug(
            "Seniority override: '%s' → '%s' (yearsexperience=%d)",
            result.get("seniority"), new, yrs,
        )
    result["seniority"] = new


def _infer_role(title: str) -> str:
    """Keyword-based role fallback when the LLM returns an unrecognised value."""
    t = title.lower()
    checks = [
        (["frontend", "front-end", "front end", "ui developer", "react developer",
          "angular developer", "vue developer", "web developer"],        "Frontend"),
        (["backend", "back-end", "back end", "server-side", "node developer"],   "Backend"),
        (["fullstack", "full-stack", "full stack"],                               "Fullstack"),
        (["machine learning", "deep learning", "nlp", "computer vision",
          "llm", "ai engineer", "ml engineer", "artificial intelligence"],        "AI / ML"),
        (["data scientist"],                                                       "Data Scientist"),
        (["data engineer", "etl", "pipeline engineer"],                           "Data Engineer"),
        (["data analyst", "bi developer", "business intelligence"],               "Data Analyst"),
        (["devops", "cloud engineer", "sre", "site reliability",
          "platform engineer", "infrastructure engineer"],                        "DevOps / Cloud"),
        (["mobile", "android", "ios", "flutter", "react native"],                 "Mobile"),
        (["qa ", "quality engineer", "automation engineer",
          "test engineer", "sdet"],                                               "QA / Automation"),
        (["security", "cyber", "infosec", "penetration", "appsec"],              "Security"),
        (["embedded", "firmware"],                                                 "Embedded / Firmware"),
        (["solutions architect", "solution architect", "system architect"],       "Solutions Architect"),
        (["team lead", "tech lead", "engineering manager"],                       "Team Lead"),
        (["software engineer", "software developer", "programmer",
          "developer", "engineer"],                                               "Software Development"),
    ]

    for keywords, role in checks:
        if any(k in t for k in keywords):
            return role

    # Special case: product manager (needs AND logic)
    if ("product" in t and "manager" in t) or any(
        k in t for k in ["product lead", "vp product", "head of product", "product owner"]
    ):
        return "Product Manager"

    return "Other"
