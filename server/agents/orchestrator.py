"""Orchestrator Agent — classifies intent and delegates to specialist agents via tool wrappers."""
from __future__ import annotations

import logging
import os
import threading
import sys
from contextvars import ContextVar
from datetime import date
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .sql_agent import run_sql_agent
from .resume_agent import run_resume_agent
from .job_advisor_agent import run_job_advisor_agent
from .evaluator_agent import run_evaluator_agent, EvaluationInput, AgentType
from .prompts import ORCHESTRATOR_PROMPT
from db.postgres import get_connection, insert_evaluation

load_dotenv()
sys.dont_write_bytecode = True

log = logging.getLogger(__name__)

# Stores the conversation history for the current request so tool wrappers
# and the evaluator can access it without threading it through every call.
# Set by router.py before each agent.invoke(); reset in a finally block.
conversation_history: ContextVar[list] = ContextVar("conversation_history", default=[])


# ── Evaluation helpers ────────────────────────────────────────────────────

def _save_evaluation_bg(
    agent_type: AgentType, query: str, response: str, result
) -> None:
    """Persist an EvaluationResult to the DB in a background thread."""
    def _save():
        try:
            conn = get_connection()
            try:
                insert_evaluation(
                    conn,
                    agent_type=agent_type.value,
                    user_message=query,
                    agent_response=response,
                    score=result.score,
                    passed=result.passed,
                    dimensions=result.dimensions,
                    critique=result.critique,
                    suggested_response=result.suggested_response,
                )
            finally:
                conn.close()
        except Exception:
            log.exception("Failed to save evaluation for agent '%s'.", agent_type.value)

    threading.Thread(target=_save, daemon=True).start()


def _build_eval_context(history: list) -> dict:
    """Serialise LangChain messages into a plain dict for the evaluator."""
    if not history:
        return {}
    return {
        "conversation_history": [
            {"role": "user" if isinstance(m, HumanMessage) else "agent", "text": m.content}
            for m in history
            if hasattr(m, "content")
        ]
    }


def _fire_evaluation(agent_type: AgentType, query: str, response: str) -> None:
    """Fire-and-forget: evaluate and save to DB in a background thread."""
    history = conversation_history.get([])
    context = _build_eval_context(history)

    def _run():
        try:
            result = run_evaluator_agent(EvaluationInput(
                agent_type=agent_type,
                user_message=query,
                agent_response=response,
                context=context,
            ))
            _save_evaluation_bg(agent_type, query, response, result)
        except Exception:
            log.exception("[EVALUATOR] Background evaluation failed for '%s'.", agent_type.value)

    threading.Thread(target=_run, daemon=True).start()


# ── Tool wrappers around each specialist agent ────────────────────────────

@tool
def sql_agent(query: str) -> str:
    """Delegate to the SQL Agent for any job database queries.
    Use for: job searches, statistics, skill trends, company rankings, listings.
    Do NOT use for course or learning recommendations.
    Pass the user's full request as `query`.
    """
    history = conversation_history.get([])
    response = run_sql_agent(query, history=history)
    _fire_evaluation(AgentType.SQL, query, response)
    return response


@tool
def resume_agent(query: str) -> str:
    """Delegate to the Resume Agent for resume-related tasks.
    Use for: tailoring a resume to a job, uploading a resume, gap analysis.
    Pass the user's full request (including any job IDs) as `query`.
    """
    history = conversation_history.get([])
    response = run_resume_agent(query, history=history)
    _fire_evaluation(AgentType.RESUME, query, response)
    return response


@tool
def job_advisor_agent(query: str) -> str:
    """Delegate to the Job Advisor Agent for career coaching and upskilling advice.
    Use for: interview prep, salary negotiation, role fit, application strategy,
    and ANY requests for course recommendations, tutorials, study plans, or learning paths.
    Pass the user's full request verbatim as `query`.
    """
    history = conversation_history.get([])
    response = run_job_advisor_agent(query, history=history)
    _fire_evaluation(AgentType.JOB_ADVISOR, query, response)
    return response


ORCHESTRATOR_TOOLS = [sql_agent, resume_agent, job_advisor_agent]


# ── Orchestrator graph ────────────────────────────────────────────────────

class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_orchestrator():
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model=os.getenv("ANTHROPIC_MODEL"),
    ).bind_tools(ORCHESTRATOR_TOOLS)

    def coordinator(state: State):
        prompt = ORCHESTRATOR_PROMPT.format(today=date.today().strftime("%B %d, %Y"))
        messages = [SystemMessage(content=prompt)] + state["messages"]
        try:
            response = llm.invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            print("LLM ERROR:", e)
            raise
        

    def route(state: State):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(State)
    graph.add_node("coordinator", coordinator)
    graph.add_node("tools", ToolNode(ORCHESTRATOR_TOOLS))
    graph.set_entry_point("coordinator")
    graph.add_conditional_edges("coordinator", route, {"tools": "tools", END: END})
    graph.add_edge("tools", END)

    return graph.compile()