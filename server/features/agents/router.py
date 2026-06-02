from __future__ import annotations
import asyncio
import json
import logging
import threading
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from server.core.security import get_current_user
from server.core.logging import set_session_user, clear_session_user
from server.agents.orchestrator import build_orchestrator, conversation_history
from server.agents.resume.resume_tools import set_current_user
from server.agents.eval.evaluator_agent import run_evaluator_agent, EvaluationInput
from server.db.postgres import get_connection, insert_evaluation

# Use the "agents" namespace so this module's logs flow into the session log file.
log = logging.getLogger("agents.router")

router = APIRouter()


# ── Evaluation ────────────────────────────────────────────────────────────

def _fire_orchestrator_evaluation(user_message: str, final_reply: str, agents_used: List[str]) -> None:
    """Evaluate the orchestrator's full response in a background thread.
    ContextVar is copied at thread start so the session log is inherited."""
    def _run():
        try:
            result = run_evaluator_agent(EvaluationInput(
                user_message=user_message,
                final_response=final_reply,
                agents_used=agents_used,
            ))
            conn = get_connection()
            try:
                insert_evaluation(
                    conn,
                    agent_type="orchestrator",
                    user_message=user_message,
                    agent_response=final_reply,
                    score=result.score,
                    passed=result.passed,
                    dimensions=result.dimensions,
                    critique=result.critique,
                    suggested_response=result.suggested_response,
                )
            finally:
                conn.close()
        except Exception:
            log.exception("[EVALUATOR] Orchestrator evaluation failed")

    threading.Thread(target=_run, daemon=True).start()


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


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(req: ChatRequest, user_id: str = Depends(get_current_user)):
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

    async def generate():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def run_agent():
            """
            Runs the entire agent.stream() in one dedicated thread.
            conversation_history.set() and .reset() both happen here,
            so the token is always in the same Context — no ValueError.
            Results are pushed to the asyncio queue via call_soon_threadsafe.
            """
            set_session_user(int(user_id))
            agents_used: List[str] = []
            final_reply = ""
            try:
                token = conversation_history.set(lc_history[:-1])
            except Exception:
                log.exception("Failed to initialise conversation context for user %s", user_id)
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    f"data: {json.dumps({'type': 'error', 'detail': 'Agent failed to process the request'})}\n\n",
                )
                loop.call_soon_threadsafe(queue.put_nowait, None)
                return
            try:
                for chunk in agent.stream({"messages": lc_history}, stream_mode="updates"):
                    if "coordinator" not in chunk:
                        continue
                    for msg in chunk["coordinator"].get("messages", []):
                        if not isinstance(msg, AIMessage):
                            continue
                        if getattr(msg, "tool_calls", None):
                            new_agents = [
                                tc["name"] for tc in msg.tool_calls
                                if tc.get("name") and tc["name"] not in agents_used
                            ]
                            if new_agents:
                                agents_used.extend(new_agents)
                                loop.call_soon_threadsafe(
                                    queue.put_nowait,
                                    f"data: {json.dumps({'type': 'planning', 'agents': agents_used})}\n\n",
                                )
                        elif msg.content:
                            final_reply = msg.content

                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    f"data: {json.dumps({'type': 'reply', 'reply': final_reply, 'agents_used': agents_used})}\n\n",
                )
                if final_reply:
                    _fire_orchestrator_evaluation(req.message, final_reply, agents_used)
            except Exception:
                log.exception("Agent streaming failed for user %s", user_id)
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    f"data: {json.dumps({'type': 'error', 'detail': 'Agent failed to process the request'})}\n\n",
                )
            finally:
                conversation_history.reset(token)
                clear_session_user()
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        threading.Thread(target=run_agent, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return StreamingResponse(generate(), media_type="text/event-stream")
