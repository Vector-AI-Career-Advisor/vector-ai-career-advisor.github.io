from __future__ import annotations
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage

from core.security import get_current_user
from agents.orchestrator import build_orchestrator, conversation_history
from agents.tools.resume_tools import set_current_user

log = logging.getLogger(__name__)

router = APIRouter()

# ── Orchestrator singleton ─────────────────────────────────────────────────

_orchestrator = None

def _get_agent():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = build_orchestrator()
    return _orchestrator



# ── Schemas ────────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    role: str   # "user" | "agents"
    text: str

class ChatRequest(BaseModel):
    message: str
    history: List[HistoryItem] = []
    job_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    agents_used: List[str] = []


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user_id: str = Depends(get_current_user)):
    set_current_user(int(user_id))
    agent = _get_agent()

    lc_history: list = []
    for item in req.history:
        if item.role == "user":
            lc_history.append(HumanMessage(content=item.text))
        elif item.role == "agents":
            lc_history.append(AIMessage(content=item.text))

    message = req.message
    if req.job_id:
        message = f"[The user currently has job ID '{req.job_id}' open.]\n{message}"

    lc_history.append(HumanMessage(content=message))

    # Expose prior turns (everything except the current message) to sub-agents
    # and the evaluator via a per-request context variable.
    token = conversation_history.set(lc_history[:-1])
    try:
        result = agent.invoke({"messages": lc_history})
        last: BaseMessage = result["messages"][-1]
        reply = last.content if hasattr(last, "content") else str(last)
    except Exception:
        log.exception("Agent invocation failed for user %s", user_id)
        raise HTTPException(status_code=500, detail="Agent failed to process the request")
    finally:
        conversation_history.reset(token)

    agents_used: List[str] = []
    for msg in result["messages"]:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                name = tc.get("name", "")
                if name and name not in agents_used:
                    agents_used.append(name)

    return ChatResponse(reply=reply, agents_used=agents_used)
