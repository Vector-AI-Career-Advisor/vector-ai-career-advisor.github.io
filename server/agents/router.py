from __future__ import annotations
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from core.security import get_current_user
from agents.orchestrator import build_orchestrator
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

    try:
        result = agent.invoke({"messages": lc_history})
        reply = result["messages"][-1].content
    except Exception:
        log.exception("Agent invocation failed for user %s", user_id)
        raise HTTPException(status_code=500, detail="Agent failed to process the request")

    return ChatResponse(reply=reply)
