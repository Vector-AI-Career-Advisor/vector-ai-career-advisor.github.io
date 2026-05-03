"""SQL Agent — handles all structured DB queries and job searches."""
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

from .tools.db_tools import DB_TOOLS
from .prompts import SQL_AGENT_PROMPT

load_dotenv()

class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_sql_agent():
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-haiku-4-5",
        temperature=0,
    ).bind_tools(DB_TOOLS)

    def assistant(state: State):
        prompt = SQL_AGENT_PROMPT.format(today=date.today().strftime("%B %d, %Y"))
        messages = [SystemMessage(content=prompt)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    def route(state: State):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(State)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(DB_TOOLS))
    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")

    return graph.compile()


# Singleton — built once and reused by the orchestrator tool wrapper.
_sql_agent = None


def get_sql_agent():
    global _sql_agent
    if _sql_agent is None:
        _sql_agent = build_sql_agent()
    return _sql_agent


def run_sql_agent(query: str) -> str:
    """Entry point called by the orchestrator tool wrapper."""
    agent = get_sql_agent()
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    last = result["messages"][-1]
    return last.content if hasattr(last, "content") else str(last)
