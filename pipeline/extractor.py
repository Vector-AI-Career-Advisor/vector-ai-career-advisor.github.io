"""
LLM-based job description extraction using Groq.

Key improvements over v1:
- Smart description pre-processing: strips boilerplate/HTML noise before
  sending to Groq, preserving ALL semantically meaningful content so field
  quality is not degraded.
- Token-aware truncation: estimates token count and only truncates when
  truly necessary, keeping as much of the description as possible.
- Retry-After header parsing: honours the exact cooldown Groq signals
  instead of using arbitrary exponential back-off that burns retries too
  fast or waits longer than needed.
- Token-bucket rate limiter per key: tracks requests-per-minute AND
  tokens-per-minute so we stay under both limits simultaneously.
- Groq client reuse: one client instance per key (not recreated every call).
- Logo field removed entirely.
- Cleaner separation between rate-limit flavours (RPM vs TPD).
"""

from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from groq import APIConnectionError, Groq, RateLimitError
from config import (
    EXTRACTION_PROMPT,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    VALID_ROLES,
    VALID_SENIORITY,
)

log = logging.getLogger(__name__)

# ── Groq client pool ──────────────────────────────────────────────────────────

_GROQ_KEYS: list[str] = [k for k in [GROQ_API_KEY_EXTRACT, GROQ_API_KEY_CHAT] if k]

if not _GROQ_KEYS:
    raise RuntimeError(
        "No Groq API keys configured. Set GROQ_API_KEY_EXTRACT or GROQ_API_KEY_CHAT."
    )

log.info("Loaded %d Groq key(s).", len(_GROQ_KEYS))

# One persistent client per key — avoids re-initialising TLS on every call.
_clients: list[Groq] = [Groq(api_key=k) for k in _GROQ_KEYS]


# ── Token-bucket rate limiter (per key) ───────────────────────────────────────
#
# Groq free-tier limits (llama-3 family): ~30 RPM, ~14 400 TPM per key.
# We target 25 RPM / 12 000 TPM to leave a comfortable safety margin.
# Adjust these constants if you upgrade your Groq plan.

_RPM_LIMIT   = 25          # requests per minute per key
_TPM_LIMIT   = 12_000      # tokens per minute per key
_WINDOW      = 60.0        # sliding window in seconds

# Rolling log of (timestamp, tokens_used) per key, protected by per-key lock.
_key_locks:    list[threading.Lock]       = [threading.Lock() for _ in _GROQ_KEYS]
_key_requests: list[list[float]]          = [[] for _ in _GROQ_KEYS]  # timestamps
_key_tokens:   list[list[tuple[float, int]]] = [[] for _ in _GROQ_KEYS]  # (ts, n_tokens)


def _prune_window(key_idx: int) -> None:
    """Drop entries older than the sliding window. Must be called under lock."""
    cutoff = time.time() - _WINDOW
    _key_requests[key_idx] = [t for t in _key_requests[key_idx] if t > cutoff]
    _key_tokens[key_idx]   = [(t, n) for t, n in _key_tokens[key_idx] if t > cutoff]


def _wait_for_capacity(key_idx: int, estimated_tokens: int) -> None:
    """
    Block until this key has both request-slot and token-budget available.
    Must be called under the key's lock.
    """
    while True:
        _prune_window(key_idx)
        n_req    = len(_key_requests[key_idx])
        n_tokens = sum(n for _, n in _key_tokens[key_idx])

        if n_req < _RPM_LIMIT and (n_tokens + estimated_tokens) < _TPM_LIMIT:
            break

        # Figure out how long until the oldest entry expires.
        oldest_req = _key_requests[key_idx][0]   if _key_requests[key_idx]   else time.time()
        oldest_tok = _key_tokens[key_idx][0][0]   if _key_tokens[key_idx]    else time.time()
        sleep_until = min(oldest_req, oldest_tok) + _WINDOW
        wait = max(0.2, sleep_until - time.time())
        log.debug(
            "Key %d at capacity (req=%d/%d tok=%d/%d) — sleeping %.1fs",
            key_idx + 1, n_req, _RPM_LIMIT, n_tokens, _TPM_LIMIT, wait,
        )
        time.sleep(wait)


def _record_usage(key_idx: int, tokens_used: int) -> None:
    """Log a completed request. Must be called under the key's lock."""
    now = time.time()
    _key_requests[key_idx].append(now)
    _key_tokens[key_idx].append((now, tokens_used))


# ── Description pre-processing ────────────────────────────────────────────────
#
# LinkedIn descriptions arrive with repeated boilerplate, bullet-point noise,
# and sometimes HTML artefacts. Stripping these reduces token spend without
# losing any structured information the LLM needs.

# Max chars we send to Groq.  At ~4 chars/token this is ~2 500 tokens of
# input — well within limits while preserving the full semantic content of
# even very long job ads.
_MAX_CHARS = 10_000

_BOILERPLATE_PATTERNS = [
    # Equal-opportunity / legal boilerplate
    r"(equal\s+opportunity|eeo|affirmative\s+action).{0,300}",
    # "About LinkedIn" / platform ads
    r"linkedin is committed.{0,200}",
    # Generic benefit lists that add zero extraction value
    r"(we offer|our benefits include|what we offer)[:\s].{0,400}",
]
_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS), re.DOTALL | re.IGNORECASE)

# Rough token estimator: 1 token ≈ 4 chars for English/mixed text.
def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _preprocess_description(raw: str) -> str:
    """
    Clean and intelligently truncate a raw LinkedIn description.

    Strategy:
    1. Strip obvious HTML artefacts and excess whitespace.
    2. Remove legal/boilerplate paragraphs.
    3. If still over _MAX_CHARS, keep the first 70 % and last 30 % so
       we get the requirements section (usually mid-document) AND the
       closing details, while discarding the repetitive middle filler.
    """
    # Remove HTML tags that occasionally leak through Selenium
    text = re.sub(r"<[^>]+>", " ", raw)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip boilerplate
    text = _BOILERPLATE_RE.sub("", text)
    # Collapse runs of spaces
    text = re.sub(r" {2,}", " ", text).strip()

    if len(text) <= _MAX_CHARS:
        return text

    # Smart truncation: preserve beginning (intro + role overview) and
    # the end (requirements / qualifications are often listed last).
    head = int(_MAX_CHARS * 0.70)
    tail = _MAX_CHARS - head
    return text[:head] + "\n\n[...]\n\n" + text[-tail:]


# ── Public extraction API ─────────────────────────────────────────────────────

def extract_with_groq(
    title: str,
    description: str,
    key_idx: int = 0,
) -> dict:
    """
    Send a job title + description to Groq and return a structured extraction.

    - Preprocesses the description to reduce token usage without quality loss.
    - Uses per-key token-bucket rate limiting.
    - Parses Retry-After headers when available.
    - Retries up to 3 times with key rotation on RPM errors.
    """
    if not description or description == "N/A":
        return _empty_extraction()

    processed   = _preprocess_description(description)
    est_tokens  = _estimate_tokens(EXTRACTION_PROMPT) + _estimate_tokens(processed) + 50
    current_key = key_idx % len(_GROQ_KEYS)

    for attempt in range(3):
        with _key_locks[current_key]:
            _wait_for_capacity(current_key, est_tokens)
            client = _clients[current_key]

            try:
                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": EXTRACTION_PROMPT},
                        {
                            "role": "user",
                            "content": (
                                f"Job Title: {title}\n\n"
                                f"Job Description:\n{processed}\n\n"
                                "JSON:"
                            ),
                        },
                    ],
                    temperature=0,
                    max_tokens=1500,
                )
                tokens_used = getattr(response.usage, "total_tokens", est_tokens)
                _record_usage(current_key, tokens_used)

                raw = response.choices[0].message.content.strip()
                return _parse_and_validate(raw, title)

            except json.JSONDecodeError as e:
                log.warning("Groq JSON parse error (attempt %d/3): %s", attempt + 1, e)
                if attempt == 2:
                    return _empty_extraction()
                time.sleep(2)

            except RateLimitError as e:
                err_str = str(e)

                # Daily token limit — no point retrying on any key for this job
                if "tokens per day" in err_str or "TPD" in err_str:
                    log.warning(
                        "Groq daily token limit on key %d — skipping job.", current_key + 1
                    )
                    return _empty_extraction()

                # Parse Retry-After if Groq provided it (beats guessing)
                retry_after = _parse_retry_after(e)
                if retry_after:
                    log.warning(
                        "Groq RPM hit on key %d — Retry-After=%ds (attempt %d/3).",
                        current_key + 1, retry_after, attempt + 1,
                    )
                    time.sleep(retry_after + random.uniform(0.5, 2.0))
                else:
                    # Rotate key before sleeping
                    current_key = (current_key + 1) % len(_GROQ_KEYS)
                    wait = (2 ** attempt) * 10 + random.uniform(0, 5)
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
    """
    if not stubs:
        return []

    valid_stubs, skipped_count = _filter_valid_stubs(stubs)
    if not valid_stubs:
        return []

    n_workers = len(_GROQ_KEYS)
    results: list[Optional[dict]] = [None] * len(valid_stubs)

    def _worker(idx: int, stub: dict) -> tuple[int, dict]:
        key_idx = idx % n_workers
        log.info(
            "[%d/%d] Extracting: %s | %s (key %d)",
            idx + 1, len(valid_stubs), stub["title"], stub["company"], key_idx + 1,
        )
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
        log.info(
            "  ✓ %s | %s | exp: %s",
            job["role"], job["seniority"],
            f"{job['yearsexperience']}yr" if job["yearsexperience"] else "?",
        )
        jobs.append(job)

    log.info(
        "Extraction complete — %d/%d jobs processed (%d skipped).",
        len(jobs), len(stubs), skipped_count,
    )
    return jobs


# ── Internal helpers ──────────────────────────────────────────────────────────

def _filter_valid_stubs(stubs: list[dict]) -> tuple[list[dict], int]:
    valid, skipped = [], 0
    for stub in stubs:
        desc = stub.get("raw_description", "")
        if not desc or desc == "N/A":
            log.warning(
                "Skipping '%s' @ '%s' — no description.", stub["title"], stub["company"]
            )
            skipped += 1
        else:
            valid.append(stub)
    if skipped:
        log.info("Skipped %d stub(s) with missing descriptions.", skipped)
    return valid, skipped


def _parse_retry_after(exc: RateLimitError) -> Optional[int]:
    """
    Try to extract a Retry-After value (seconds) from the Groq error response.
    Returns None if not present.
    """
    # Groq SDK exposes the raw response on some versions
    try:
        headers = exc.response.headers  # type: ignore[attr-defined]
        val = headers.get("retry-after") or headers.get("Retry-After")
        if val:
            return int(float(val))
    except Exception:
        pass

    # Fallback: parse from the error message string
    match = re.search(r"retry.{0,10}?(\d+)\s*s", str(exc), re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


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

    _apply_seniority_heuristic(result)
    return result


def _apply_seniority_heuristic(result: dict) -> None:
    """
    Override seniority based on years of experience ONLY when the LLM
    returned 'Not specified'. Explicit LLM values are always preserved.
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

    log.debug(
        "Seniority heuristic: 'Not specified' → '%s' (yearsexperience=%d)", new, yrs
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

    if ("product" in t and "manager" in t) or any(
        k in t for k in ["product lead", "vp product", "head of product", "product owner"]
    ):
        return "Product Manager"

    return "Other"
