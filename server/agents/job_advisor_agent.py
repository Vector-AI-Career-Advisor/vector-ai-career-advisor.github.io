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
from .prompts import JOB_ADVISOR_PROMPT

load_dotenv()


class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_job_advisor_agent():
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model=os.getenv("ANTHROPIC_MODEL"),
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
