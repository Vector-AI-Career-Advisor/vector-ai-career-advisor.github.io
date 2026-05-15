"""Main entry point — starts the multi-agent Career Assistant."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from backend.agents.orchestrator import build_orchestrator
from backend.agents.tools.resume_tools import set_current_user, _context

load_dotenv()

def _resolve_user(email: str) -> int | None:
    """Look up a user by email and return their ID, or None if not found."""
    from backend.db.postgres import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def main():
    orchestrator = build_orchestrator()
    history = []


    print("\nCareer Assistant Ready  (3-agent mode)\n")

    # ── Identify the user ─────────────────────────────────────────────────
    while True:
        email = input("Your account email (or press Enter to skip): ").strip()
        if not email:
            print("Running without user session — resume tools will be unavailable.\n")
            break
        user_id = _resolve_user(email)
        if user_id is None:
            print(f"No account found for '{email}'. Try again or press Enter to skip.")
        else:
            set_current_user(user_id)
            print(f"Signed in as {email}.\n")
            break

    print('Type your question, or use:  /upload <path/to/resume.pdf>  |  exit\n')

    while True:
        user_input = input("You: ")
        stripped = user_input.strip()

        if stripped.lower() == "exit":
            break

        # /upload is handled locally — no need to route through the LLM.
        if stripped.lower().startswith("/upload "):
            path = stripped[len("/upload "):]
            user_id = _context.get("user_id")
            if not user_id:
                print("Error: not signed in. Enter your email at startup to use resume features.")
                continue
            # Delegate directly to the resume tool (no agent overhead needed here).
            from backend.agents.tools.resume_tools import upload_resume
            result = upload_resume.invoke({"path": path})
            print(result.get("message") or result.get("error"), "\n")
            continue

        history.append(HumanMessage(content=user_input))
        result = orchestrator.invoke({"messages": history})
        history = result["messages"]
        print("\nAssistant:\n", history[-1].content, "\n")


if __name__ == "__main__":
    main()
