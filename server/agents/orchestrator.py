"""Orchestrator Agent — classifies intent and delegates to specialist agents via tool wrappers."""
from __future__ import annotations

import os
import sys
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
from .prompts import ORCHESTRATOR_PROMPT

load_dotenv()
sys.dont_write_bytecode = True

# ── Tool wrappers with Debug Printing ─────────────────────────────────────

@tool
def sql_agent(query: str) -> str:
    """Delegate to the SQL Agent for any job database queries.
    Use for: job searches, statistics, skill trends, company rankings, listings.
    Do NOT use for course or learning recommendations.
    Pass the user's full request as `query`.
    """
    print("\n" + "="*60)
    print(f"🎯 [ORCHESTRATOR CHOICE] -> Routed to: SQL_AGENT")
    print(f"📝 [PAYLOAD] -> {query!r}")
    print("="*60 + "\n")
    return run_sql_agent(query)


@tool
def resume_agent(query: str) -> str:
    """Delegate to the Resume Agent for resume-related tasks.
    Use for: tailoring a resume to a job, uploading a resume, gap analysis.
    Pass the user's full request (including any job IDs) as `query`.
    """
    print("\n" + "="*60)
    print(f"🎯 [ORCHESTRATOR CHOICE] -> Routed to: RESUME_AGENT")
    print(f"📝 [PAYLOAD] -> {query!r}")
    print("="*60 + "\n")
    return run_resume_agent(query)


@tool
def job_advisor_agent(query: str) -> str:
    """Delegate to the Job Advisor Agent for career coaching and upskilling advice.
    Use for: interview prep, salary negotiation, role fit, application strategy, 
    and ANY requests for course recommendations, tutorials, study plans, or learning paths (e.g., AWS, backend).
    Pass the user's full request verbatim as `query`.
    """
    print("\n" + "="*60)
    print(f"🎯 [ORCHESTRATOR CHOICE] -> Routed to: JOB_ADVISOR_AGENT")
    print(f"📝 [PAYLOAD] -> {query!r}")
    print("="*60 + "\n")
    return run_job_advisor_agent(query)


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
    graph.add_edge("tools", "coordinator")

    return graph.compile()