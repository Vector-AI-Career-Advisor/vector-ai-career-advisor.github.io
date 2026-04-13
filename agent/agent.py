from datetime import date
import os
import sys
from typing import Annotated, TypedDict

# Ensure the project root is on the path so `db`, `config`, etc. are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tools import TOOLS, set_current_user, _context
from prompts import SYSTEM_PROMPT

load_dotenv()


class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_llm():
    return ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-sonnet-4-6",
        temperature=0,
    )


def build_agent():
    llm = build_llm().bind_tools(TOOLS)

    def assistant(state: State):
        prompt = SYSTEM_PROMPT.format(today=date.today().strftime("%B %d, %Y"))
        messages = [SystemMessage(content=prompt)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    def route(state: State):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(State)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")

    return graph.compile()


def _upload_resume(path: str) -> None:
    """Extract text from a local PDF and store it in the DB for the current user."""
    import io
    import pypdf
    from db import get_connection

    user_id = _context.get("user_id")
    if not user_id:
        print("Error: not signed in. Enter your email at startup to use resume features.")
        return

    path = os.path.expanduser(path.strip())
    if not os.path.isfile(path):
        print(f"Error: file not found: {path}")
        return
    if not path.lower().endswith(".pdf"):
        print("Error: only PDF files are supported.")
        return

    with open(path, "rb") as f:
        reader = pypdf.PdfReader(io.BytesIO(f.read()))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if not text:
        print("Error: could not extract text from PDF.")
        return

    filename = os.path.basename(path)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO resumes (user_id, filename, content)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                    SET filename   = EXCLUDED.filename,
                        content    = EXCLUDED.content,
                        updated_at = NOW()
                """,
                (user_id, filename, text),
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Resume '{filename}' uploaded successfully.")


def _resolve_user(email: str) -> int | None:
    """Look up a user by email and return their ID, or None if not found."""
    import psycopg2
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def main():
    agent = build_agent()
    history = []

    # ── Identify the user ─────────────────────────────────────────────────
    print("\nCareer Assistant Ready\n")
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

    print("Commands: /upload <path/to/resume.pdf>  |  exit\n")

    while True:
        user = input("You: ")
        stripped = user.strip()

        if stripped.lower() == "exit":
            break

        if stripped.lower().startswith("/upload "):
            _upload_resume(stripped[len("/upload "):])
            continue

        history.append(HumanMessage(content=user))
        result = agent.invoke({"messages": history})
        history = result["messages"]
        print("\nAssistant:\n", history[-1].content, "\n")


if __name__ == "__main__":
    main()