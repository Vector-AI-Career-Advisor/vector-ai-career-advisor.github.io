from __future__ import annotations
import sys
import os
import importlib.util

# ── Path & sys.modules fix ─────────────────────────────────────────────────
#
# Problem: backend/db/ (no __init__.py) is a namespace package that gets
# registered as sys.modules['db'] when auth/jobs/resumes routers are imported.
# agent/tools.py does `from db import get_connection` which then fails because
# the backend's db namespace has no get_connection.
#
# Fix: after ensuring PROJECT_ROOT is on sys.path, explicitly load the root
# db package (which has __init__.py + get_connection) into sys.modules['db'].
# Existing backend modules already hold direct references to the functions they
# imported from db.database, so overriding sys.modules['db'] doesn't break them.

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_root_db_dir  = os.path.join(_PROJECT_ROOT, 'db')
_root_db_init = os.path.join(_root_db_dir, '__init__.py')

if not hasattr(sys.modules.get('db'), 'get_connection'):
    _spec = importlib.util.spec_from_file_location(
        'db', _root_db_init,
        submodule_search_locations=[_root_db_dir],
    )
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules['db'] = _mod
    _spec.loader.exec_module(_mod)

# ── Agent imports (module-level so they only run once) ─────────────────────
from datetime import date
from typing import Annotated, List, Optional, TypedDict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from core.security import get_current_user
from agent.tools import TOOLS, set_current_user   # safe now that db is fixed
from agent.prompts import SYSTEM_PROMPT

router = APIRouter()

# ── Agent singleton ────────────────────────────────────────────────────────

class _State(TypedDict):
    messages: Annotated[list, add_messages]

_agent = None

def _get_agent():
    global _agent
    if _agent is not None:
        return _agent

    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-sonnet-4-6",
        temperature=0,
    ).bind_tools(TOOLS)

    def assistant(state: _State):
        prompt = SYSTEM_PROMPT.format(today=date.today().strftime("%B %d, %Y"))
        msgs = [SystemMessage(content=prompt)] + state["messages"]
        return {"messages": [llm.invoke(msgs)]}

    def route(state: _State):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(_State)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")

    _agent = graph.compile()
    return _agent


# ── Schemas ────────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    role: str   # "user" | "agent"
    text: str

class ChatRequest(BaseModel):
    message: str
    history: List[HistoryItem] = []
    job_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user_id: str = Depends(get_current_user)):
    set_current_user(int(user_id))
    agent = _get_agent()

    lc_history: list = []
    for item in req.history:
        if item.role == "user":
            lc_history.append(HumanMessage(content=item.text))
        elif item.role == "agent":
            lc_history.append(AIMessage(content=item.text))

    message = req.message
    if req.job_id:
        message = f"[The user currently has job ID '{req.job_id}' open.]\n{message}"

    lc_history.append(HumanMessage(content=message))

    result = agent.invoke({"messages": lc_history})
    reply  = result["messages"][-1].content

    return ChatResponse(reply=reply)
