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


"""
LangChain tool definitions for interacting with the course graph.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from graph.graph_query import (
    get_course_info,
    get_courses_by_semester,
    search_courses,
    get_prerequisites,
    get_available_courses,
    get_dependents,
    get_paths_to,
    list_all_courses,
)


# -----------------------------
# Pydantic inputs
# -----------------------------

class CourseInfoInput(BaseModel):
    course_code: str = Field(..., description="Course code such as 'CSC322' or 'GST100'.")


class CoursesBySemesterInput(BaseModel):
    semester: str = Field(
        ...,
        description="Recommended semester label to filter by (e.g. 'Fall', 'Spring', 'Year 1').",
    )


class SearchCoursesInput(BaseModel):
    text: str = Field(..., description="Free text to search in code, name, or description.")
    limit: int = Field(25, ge=1, le=200, description="Maximum number of results.")


class PrereqsInput(BaseModel):
    course_code: str = Field(..., description="Target course code to inspect prerequisites for.")


class AvailableCoursesInput(BaseModel):
    completed: List[str] = Field(default_factory=list, description="List of completed course codes.")
    exclude: Optional[List[str]] = Field(
        default=None, description="Optional list of course codes to exclude from results."
    )


class DependentsInput(BaseModel):
    course_code: str = Field(..., description="Course code to find dependents for.")


class PathsToInput(BaseModel):
    target_code: str = Field(..., description="Target course code to reach.")
    max_depth: int = Field(4, ge=1, le=8, description="Max relationship depth to explore if edges exist.")


class ListAllCoursesInput(BaseModel):
    limit: int = Field(200, ge=1, le=1000, description="Page size.")
    skip: int = Field(0, ge=0, description="Number of records to skip.")


# -----------------------------
# Wrappers to ensure JSON-string outputs
# -----------------------------

def _wrap_tool_output(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps({"result": repr(value)}, ensure_ascii=False)


# -----------------------------
# Tool functions
# -----------------------------

def _tool_get_course_info(course_code: str) -> str:
    rec = get_course_info(course_code)
    if rec:
        return _wrap_tool_output(rec)
    return _wrap_tool_output({"error": f"No course found for code '{course_code}'."})


def _tool_get_courses_by_semester(semester: str) -> str:
    recs = get_courses_by_semester(semester)
    if recs:
        return _wrap_tool_output(recs)
    return _wrap_tool_output({"error": f"No courses found for semester '{semester}'."})


def _tool_search_courses(text: str, limit: int = 25) -> str:
    recs = search_courses(text, limit=limit)
    return _wrap_tool_output(recs)


def _tool_get_prerequisites(course_code: str) -> str:
    rec = get_prerequisites(course_code)
    return _wrap_tool_output(rec)


def _tool_get_available_courses(completed: List[str], exclude: Optional[List[str]] = None) -> str:
    recs = get_available_courses(completed=completed, exclude=exclude)
    return _wrap_tool_output(recs)


def _tool_get_dependents(course_code: str) -> str:
    recs = get_dependents(course_code)
    return _wrap_tool_output(recs)


def _tool_get_paths_to(target_code: str, max_depth: int = 4) -> str:
    recs = get_paths_to(target_code, max_depth=max_depth)
    return _wrap_tool_output(recs)


def _tool_list_all_courses(limit: int = 200, skip: int = 0) -> str:
    recs = list_all_courses(limit=limit, skip=skip)
    return _wrap_tool_output(recs)


# -----------------------------
# Tool registry
# -----------------------------

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
    StructuredTool.from_function(
        func=_tool_search_courses,
        name="search_courses",
        description="Search courses by code, name, or description.",
        args_schema=SearchCoursesInput,
    ),
    StructuredTool.from_function(
        func=_tool_get_prerequisites,
        name="get_prerequisites",
        description="Return prerequisite lists for a target course.",
        args_schema=PrereqsInput,
    ),
    StructuredTool.from_function(
        func=_tool_get_available_courses,
        name="get_available_courses",
        description="List courses available given a set of completed course codes.",
        args_schema=AvailableCoursesInput,
    ),
    StructuredTool.from_function(
        func=_tool_get_dependents,
        name="get_dependents",
        description="List courses that require the given course as a prerequisite.",
        args_schema=DependentsInput,
    ),
    StructuredTool.from_function(
        func=_tool_get_paths_to,
        name="get_paths_to",
        description="Find prerequisite paths leading to a target course (if edges exist).",
        args_schema=PathsToInput,
    ),
    StructuredTool.from_function(
        func=_tool_list_all_courses,
        name="list_all_courses",
        description="Page through all courses for indexing or dropdowns.",
        args_schema=ListAllCoursesInput,
    ),
]

TOOL_LOOKUP: Dict[str, StructuredTool] = {tool.name: tool for tool in GRAPH_TOOLS}

__all__ = ["GRAPH_TOOLS", "TOOL_LOOKUP"]