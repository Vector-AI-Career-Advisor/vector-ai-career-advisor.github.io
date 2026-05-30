"""Evaluator Agent — judges the accuracy and quality of other agents' responses."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from .prompts import EVALUATOR_PROMPT, AGENT_RUBRICS

load_dotenv()


# ── Domain types ──────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    JOB_ADVISOR = "job_advisor"
    RESUME = "resume"
    SQL = "sql"
    ORCHESTRATOR = "orchestrator"


@dataclass
class EvaluationInput:
    agent_type: AgentType
    user_message: str       # what the user asked
    agent_response: str     # what the agent replied
    context: dict           # e.g. resume content, job data — whatever the agent had access to


@dataclass
class EvaluationResult:
    score: int              # 0–100
    passed: bool            # score >= 70
    dimensions: dict        # {accuracy, relevance, completeness, tone, groundedness} → {score, reason}
    critique: str           # what the agent did wrong or could improve
    suggested_response: str # better version of the response, or "N/A"
    agent_type: AgentType
    latency_ms: int | None = None


# ── Graph ─────────────────────────────────────────────────────────────────────

class State(TypedDict):
    messages: Annotated[list, add_messages]


def build_evaluator_agent():
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model=os.getenv("EVALUATION_MODEL"),
        temperature=0,
    )

    def evaluator(state: State):
        # The rubric for the target agent is embedded in the first HumanMessage
        # by run_evaluator_agent before the graph is invoked; pull agent_type out
        # of it so we can append the right rubric to the system prompt.
        first_msg = state["messages"][0].content if state["messages"] else ""
        agent_key = ""
        for line in first_msg.splitlines():
            if line.startswith("Agent:"):
                agent_key = line.split(":", 1)[1].strip()
                break

        rubric = AGENT_RUBRICS.get(agent_key, "")
        base = EVALUATOR_PROMPT.format(today=date.today().strftime("%B %d, %Y"))
        prompt = f"{base}\nAgent-specific rubric: {rubric}" if rubric else base
        messages = [SystemMessage(content=prompt)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    graph = StateGraph(State)
    graph.add_node("evaluator", evaluator)
    graph.set_entry_point("evaluator")
    graph.add_edge("evaluator", END)

    return graph.compile()


_evaluator_agent = None


def get_evaluator_agent():
    global _evaluator_agent
    if _evaluator_agent is None:
        _evaluator_agent = build_evaluator_agent()
    return _evaluator_agent


def run_evaluator_agent(evaluation_input: EvaluationInput) -> EvaluationResult:
    """Evaluate an agent's response and return a structured EvaluationResult."""
    query = (
        f"Agent: {evaluation_input.agent_type.value}\n"
        f"User message: {evaluation_input.user_message}\n"
        f"Agent response: {evaluation_input.agent_response}\n"
    )
    if evaluation_input.context:
        query += f"Context available to agent: {json.dumps(evaluation_input.context)}\n"

    agent = get_evaluator_agent()
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    raw = result["messages"][-1].content.strip()

    # Strip markdown code fences if the model added them despite instructions
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    return EvaluationResult(
        score=data["score"],
        passed=data["passed"],
        dimensions=data["dimensions"],
        critique=data["critique"],
        suggested_response=data.get("suggested_response", ""),
        agent_type=evaluation_input.agent_type,
    )
