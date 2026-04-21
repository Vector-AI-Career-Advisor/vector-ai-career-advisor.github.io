"""
LLM-based job description extraction using Groq.
"""

from __future__ import annotations
import json
import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import APIConnectionError, Groq, RateLimitError
from config import (
    EXTRACTION_PROMPT,
    GROQ_API_KEY_CHAT,
    GROQ_API_KEY_EXTRACT,
    GROQ_MODEL,
    VALID_ROLES,
    VALID_SENIORITY,
)

log = logging.getLogger(__name__)

# ── Groq client state ─────────────────────────────────────────────────────────

_GROQ_KEYS = [k for k in [GROQ_API_KEY_EXTRACT, GROQ_API_KEY_CHAT] if k]

if not _GROQ_KEYS:
    raise RuntimeError("No Groq API keys configured. Set GROQ_API_KEY_EXTRACT or GROQ_API_KEY_CHAT.")

log.info("Loaded %d Groq key(s).", len(_GROQ_KEYS))

# Per-key throttle state: each key gets its own lock + last-request timestamp.
# This allows true parallel extraction — one worker per key — without key contention.
_MIN_GAP_SECONDS = 3.0
_key_locks: list[threading.Lock] = [threading.Lock() for _ in _GROQ_KEYS]
_key_last_used: list[float]      = [0.0] * len(_GROQ_KEYS)


def _throttle_key(key_idx: int) -> None:
    """Sleep as needed to keep this key under the per-minute rate limit."""
    wait = _MIN_GAP_SECONDS - (time.time() - _key_last_used[key_idx])
    if wait > 0:
        time.sleep(wait)
    _key_last_used[key_idx] = time.time()


def _get_client(key_idx: int) -> Groq:
    return Groq(api_key=_GROQ_KEYS[key_idx])


# ── Public API ────────────────────────────────────────────────────────────────

def extract_with_groq(title: str, description: str, key_idx: int = 0) -> dict:
    """
    Send a job title + description to Groq and return a structured extraction.
    Retries up to 3 times on transient errors. Uses the key at `key_idx`,
    falling back to the next key on rate-limit errors.
    """
    if not description or description == "N/A":
        return _empty_extraction()

    current_key = key_idx % len(_GROQ_KEYS)

    for attempt in range(3):
        with _key_locks[current_key]:
            _throttle_key(current_key)
            client = _get_client(current_key)
            try:
                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": EXTRACTION_PROMPT},
                        {"role": "user",   "content": f"Job Title: {title}\n\nJob Description:\n{description[:5000]}\n\nJSON:"},
                    ],
                    temperature=0,
                    max_tokens=2000,
                )
                raw = response.choices[0].message.content.strip()
                return _parse_and_validate(raw, title)

            except json.JSONDecodeError as e:
                log.warning("Groq JSON parse error (attempt %d/3): %s", attempt + 1, e)
                if attempt == 2:
                    return _empty_extraction()
                time.sleep(2)

            except RateLimitError as e:
                err = str(e)
                if "tokens per day" in err or "TPD" in err:
                    log.warning("Groq daily token limit reached on key %d — skipping job.", current_key)
                    return _empty_extraction()

                # Rotate to next key
                current_key = (current_key + 1) % len(_GROQ_KEYS)
                wait = (2 ** attempt) * 20 + random.uniform(0, 10)
                log.warning(
                    "Groq rate limit — rotated to key %d/%d, waiting %.0fs (attempt %d/3).",
                    current_key + 1, len(_GROQ_KEYS), wait, attempt + 1,
                )
                time.sleep(wait)

            except APIConnectionError as e:
                log.warning("Groq connection error (attempt %d/3): %s", attempt + 1, e)
                if attempt == 2:
                    return _empty_extraction()
                time.sleep(5)

            except Exception as e:
                log.warning("Groq unexpected error (attempt %d/3): %s", attempt + 1, e)
                if attempt == 2:
                    return _empty_extraction()
                time.sleep(2)

    return _empty_extraction()


def extract_all_parallel(stubs: list[dict]) -> list[dict]:
    """
    Run Groq extraction in parallel — one worker per API key.
    Returns fully structured job dicts in the same order as `stubs`.
    Stubs with no description are skipped before hitting the API.
    """
    if not stubs:
        return []

    # Pre-filter: skip stubs with no usable description
    valid_stubs   = []
    skipped_count = 0
    for stub in stubs:
        desc = stub.get("raw_description", "")
        if not desc or desc == "N/A":
            log.warning("Skipping '%s' @ '%s' — no description fetched.", stub["title"], stub["company"])
            skipped_count += 1
        else:
            valid_stubs.append(stub)

    if skipped_count:
        log.info("Skipped %d stub(s) with missing descriptions.", skipped_count)

    n_workers = len(_GROQ_KEYS)
    results   = [None] * len(valid_stubs)

    def _worker(idx: int, stub: dict) -> tuple[int, dict]:
        key_idx = idx % n_workers
        log.info("[%d/%d] Extracting: %s | %s (key %d)", idx + 1, len(valid_stubs),
                 stub["title"], stub["company"], key_idx + 1)
        extracted = extract_with_groq(stub["title"], stub["raw_description"], key_idx=key_idx)
        return idx, extracted

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_worker, i, stub): i for i, stub in enumerate(valid_stubs)}
        for future in as_completed(futures):
            try:
                idx, extracted = future.result()
                results[idx] = extracted
            except Exception as e:
                i = futures[future]
                log.error("Extraction worker failed for stub %d: %s", i, e)
                results[i] = _empty_extraction()

    jobs = []
    for stub, extracted in zip(valid_stubs, results):
        if extracted is None:
            extracted = _empty_extraction()
        job = {
            "id":              stub["id"],
            "title":           stub["title"],
            "company":         stub["company"],
            "location":        stub["location"],
            "url":             stub["url"],
            "role":            extracted["role"],
            "seniority":       extracted["seniority"],
            "description":     extracted["description"],
            "skills_must":     extracted["skills_must"],
            "skills_nice":     extracted["skills_nice"],
            "yearsexperience": extracted["yearsexperience"],
            "past_experience": extracted["past_experience"],
            "posted_at":       stub.get("posted_at"),
            "keyword":         stub["keyword"],
            "source":          "linkedin",
        }
        log.info("  ✓ %s | %s | exp: %s", job["role"], job["seniority"],
                 f"{job['yearsexperience']}yr" if job["yearsexperience"] else "?")
        jobs.append(job)

    log.info("Extraction complete — %d/%d jobs processed (%d skipped).",
             len(jobs), len(stubs), skipped_count)
    return jobs


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
    """Validate and normalise a raw Groq extraction dict."""
    empty  = _empty_extraction()
    result = {}

    for key, default in empty.items():
        # Groq sometimes returns "experience" instead of "yearsexperience"
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

    # Only apply heuristic when the LLM couldn't determine seniority
    _apply_seniority_heuristic(result)

    return result


def _apply_seniority_heuristic(result: dict) -> None:
    """
    Override seniority based on years of experience ONLY when the LLM
    returned 'Not specified'. Explicit LLM values (including leadership
    titles) are always preserved.
    """
    if result.get("seniority") != "Not specified":
        return

    yrs = result.get("yearsexperience")
    if yrs is None:
        return

    if yrs <= 3:
        new = "Junior"
    elif yrs <= 5:
        new = "Mid"
    else:
        new = "Senior"

    log.debug("Seniority heuristic: 'Not specified' → '%s' (yearsexperience=%d)", new, yrs)
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

    if ("product" in t and "manager" in t) or any(
        k in t for k in ["product lead", "vp product", "head of product", "product owner"]
    ):
        return "Product Manager"

    return "Other"