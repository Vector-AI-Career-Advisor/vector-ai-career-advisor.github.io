"""Advisor Tools — read-only tools for the Job Advisor Agent.

Thin re-exports of the two DB tools the advisor needs.
Keeping them separate means the advisor's ToolNode only binds
what it should have access to.
"""
from .db_tools import get_job_details, top_skills

ADVISOR_TOOLS = [get_job_details, top_skills]
