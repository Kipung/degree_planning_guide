"""
LangChain tool definitions for interacting with the course graph.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from graph.graph_query import get_course_info, get_courses_by_semester


class CourseInfoInput(BaseModel):
    course_code: str = Field(..., description="Course code such as 'CIS110' or 'GST100'.")


class CoursesBySemesterInput(BaseModel):
    semester: str = Field(
        ...,
        description="Recommended semester label to filter by (e.g. 'Fall', 'Spring', 'Year 1').",
    )


def _wrap_tool_output(value: Any) -> str:
    """
    Ensure the tool output is a JSON-serializable string for the LLM.
    """
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps({"result": repr(value)}, ensure_ascii=False)


def _tool_get_course_info(course_code: str) -> str:
    record = get_course_info(course_code)
    if record:
        return _wrap_tool_output(record)
    return _wrap_tool_output({"error": f"No course found for code '{course_code}'."})


def _tool_get_courses_by_semester(semester: str) -> str:
    records = get_courses_by_semester(semester)
    if records:
        return _wrap_tool_output(records)
    return _wrap_tool_output({"error": f"No courses found for semester '{semester}'."})


GRAPH_TOOLS: List[StructuredTool] = [
    StructuredTool.from_function(
        func=_tool_get_course_info,
        name="get_course_info",
        description="Retrieve detailed information for a course code.",
        args_schema=CourseInfoInput,
    ),
    StructuredTool.from_function(
        func=_tool_get_courses_by_semester,
        name="get_courses_by_semester",
        description="List courses that are recommended for a given semester label.",
        args_schema=CoursesBySemesterInput,
    ),
]

TOOL_LOOKUP: Dict[str, StructuredTool] = {tool.name: tool for tool in GRAPH_TOOLS}

__all__ = ["GRAPH_TOOLS", "TOOL_LOOKUP"]

