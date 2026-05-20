"""Job Advisor Agent — conversational career coaching around a specific job posting."""
from __future__ import annotations

import os
from datetime import date
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .tools.advisor_tools import ADVISOR_TOOLS

load_dotenv()

JOB_ADVISOR_PROMPT = """You are an experienced career mentor specialising in tech roles.
When a user asks about a specific job, fetch its details first, then give grounded,
actionable advice. You speak like a trusted friend who knows the industry well.

WHAT YOU DO:
- Interview preparation: likely questions, how to frame experience, red flags to watch for
- Company research prompts: what to look up before applying or interviewing
- Salary negotiation framing: how to approach comp discussions for this role/seniority
- Culture & role fit: help the user assess whether this role suits their goals
- Application strategy: cover letter angle, how to stand out for this specific posting
- Skill gap coaching: if they're missing must-have skills, give a learning roadmap

TOOLS AVAILABLE:
- get_job_details   → fetch the full job posting by ID (always do this first)
- top_skills        → market-wide skill demand for this role type (for benchmarking)

RULES:
1. Always fetch the job posting before giving advice — ground everything in real data.
2. If the user hasn't given a job ID, ask for one or suggest they search first.
3. Never fabricate company details not in the posting.
4. Be encouraging but honest — if a role seems like a poor fit, say so tactfully.
5. Keep advice specific to this posting, not generic career platitudes.

RESPONSE FORMAT:
- Use short sections with clear headers (e.g. **Interview Prep**, **Red Flags**, **Salary**)
- Bullet points for lists of tips
- End with one concrete "next step" the user can take today

Today's date: {today}
"""


class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_job_advisor_agent():
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-haiku-4-5",
        temperature=0,
    ).bind_tools(ADVISOR_TOOLS)

    def assistant(state: State):
        prompt = JOB_ADVISOR_PROMPT.format(today=date.today().strftime("%B %d, %Y"))
        messages = [SystemMessage(content=prompt)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    def route(state: State):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(State)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(ADVISOR_TOOLS))
    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")

    return graph.compile()


_advisor_agent = None


def get_job_advisor_agent():
    global _advisor_agent
    if _advisor_agent is None:
        _advisor_agent = build_job_advisor_agent()
    return _advisor_agent


def run_job_advisor_agent(query: str) -> str:
    """Entry point called by the orchestrator tool wrapper."""
    agent = get_job_advisor_agent()
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    last = result["messages"][-1]
    return last.content if hasattr(last, "content") else str(last)
