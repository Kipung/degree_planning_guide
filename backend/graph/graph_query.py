from typing import List, Dict, Optional, Tuple
from graph.neo4j_connect import graph


# -----------------------------
# Normalization helpers
# -----------------------------

def _normalize_course_code(raw: str) -> str:
    """Normalize user inputs like names or aliases to canonical course codes."""
    code = (raw or "").upper().strip()
    if code in {"FIRST YEAR EXPERIENCE", "FYE"}:
        return "GST100"
    return code


# -----------------------------
# JSON-schema aware helpers
# -----------------------------

def _split_prereq_rules(prereq_data: Optional[List[Dict]]) -> Tuple[List[str], List[str], List[str]]:
    """Parse JSON-style prerequisite rule blocks into requires/requires_any/coreq lists.

    The JSON uses a structure like:
      {
        "type": "Prerequisite",
        "rule": "Complete ALL of the following Courses:",
        "courses": ["GRK313"]
      }
    We do a simple keyword parse on rule to classify.
    """
    requires: List[str] = []
    requires_any: List[str] = []
    coreq: List[str] = []
    for r in (prereq_data or []):
        rule = (r.get("rule") or "").lower()
        courses = [
            _normalize_course_code(c) for c in (r.get("courses") or [])
        ]
        if "coreq" in rule or "co-req" in rule or "co requisite" in rule:
            coreq += courses
        elif "at least" in rule or "atleast" in rule or "one of" in rule:
            requires_any += courses
        else:  # default to ALL
            requires += courses
    # de-dup while preserving order
    def _dedup(xs: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                out.append(x); seen.add(x)
        return out
    return _dedup(requires), _dedup(requires_any), _dedup(coreq)


# -----------------------------
# Core lookups compatible with current JSON-backed graph
# -----------------------------

def get_course_info(course_code: str) -> Optional[Dict]:
    """Return a single course mapped from JSON property names to standard fields.

    The underlying node properties follow the JSON schema: course_code, course_name,
    course_description, credit_hours_min, prerequisites, etc. We map them to a
    stable interface for the agent: code, name, description, units, requires,
    requires_any, coreq, recommended_semester, satisfies.
    """
    code = _normalize_course_code(course_code)
    query = """
    MATCH (c:Course {course_code: $code})
    RETURN c.course_code AS course_code,
           c.course_name AS course_name,
           c.course_description AS course_description,
           c.credit_hours_min AS credit_hours_min,
           c.prerequisites AS prerequisites,
           c.recommended_semester AS recommended_semester,
           c.satisfies AS satisfies
    """
    recs = graph.run(query, code=code).data()
    if not recs:
        return None
    c = recs[0]
    req, req_any, coreq = _split_prereq_rules(c.get("prerequisites"))
    # Normalize units to int when possible
    units = c.get("credit_hours_min")
    try:
        units = int(units) if units is not None else None
    except Exception:
        units = None
    return {
        "code": c.get("course_code"),
        "name": c.get("course_name"),
        "description": c.get("course_description"),
        "units": units,
        "requires": req,
        "requires_any": req_any,
        "coreq": coreq,
        "recommended_semester": c.get("recommended_semester"),
        "satisfies": c.get("satisfies"),
    }


def get_course_detail(course_code: str) -> Optional[Dict]:
    """Alias for get_course_info since edges may not exist; keeps API stable."""
    return get_course_info(course_code)


def get_courses_by_semester(semester: str) -> List[Dict]:
    """List courses by JSON's optional recommended_semester field if present."""
    query = """
    MATCH (c:Course)
    WHERE c.recommended_semester = $semester
    RETURN c.course_code AS code,
           c.course_name AS name,
           toInteger(c.credit_hours_min) AS units
    ORDER BY code
    """
    return graph.run(query, semester=semester).data()


def list_all_courses(limit: int = 200, skip: int = 0) -> List[Dict]:
    query = """
    MATCH (c:Course)
    RETURN c.course_code AS code,
           c.course_name AS name,
           toInteger(c.credit_hours_min) AS units
    ORDER BY code SKIP $skip LIMIT $limit
    """
    return graph.run(query, limit=limit, skip=skip).data()


def search_courses(text: str, limit: int = 25) -> List[Dict]:
    q = (text or "").lower().strip()
    query = """
    MATCH (c:Course)
    WHERE toLower(c.course_code) CONTAINS $q
       OR toLower(c.course_name) CONTAINS $q
       OR toLower(coalesce(c.course_description, "")) CONTAINS $q
    RETURN c.course_code AS code,
           c.course_name AS name,
           toInteger(c.credit_hours_min) AS units
    ORDER BY code LIMIT $limit
    """
    return graph.run(query, q=q, limit=limit).data()


def get_prerequisites(course_code: str) -> Dict[str, List[str]]:
    info = get_course_info(course_code)
    if not info:
        return {"requires": [], "requires_any": [], "coreq": []}
    return {
        "requires": info.get("requires") or [],
        "requires_any": info.get("requires_any") or [],
        "coreq": info.get("coreq") or [],
    }


def _all_courses_with_prereqs() -> List[Dict]:
    """Fetch minimal fields for dependency computations using JSON properties."""
    query = """
    MATCH (c:Course)
    RETURN c.course_code AS course_code,
           c.course_name AS course_name,
           c.prerequisites AS prerequisites,
           toInteger(c.credit_hours_min) AS units
    """
    rows = graph.run(query).data()
    out = []
    for r in rows:
        req, req_any, coreq = _split_prereq_rules(r.get("prerequisites"))
        out.append({
            "code": r.get("course_code"),
            "name": r.get("course_name"),
            "units": r.get("units"),
            "requires": req,
            "requires_any": req_any,
            "coreq": coreq,
        })
    return out


def get_dependents(course_code: str) -> List[Dict]:
    """Compute dependents by scanning JSON-style prerequisites client-side."""
    code = _normalize_course_code(course_code)
    courses = _all_courses_with_prereqs()
    out: List[Dict] = []
    for c in courses:
        if code in (c["requires"] or []) or code in (c["requires_any"] or []):
            out.append({"code": c["code"], "name": c["name"], "units": c["units"]})
    return sorted(out, key=lambda x: x["code"])


def get_available_courses(completed: List[str], exclude: Optional[List[str]] = None) -> List[Dict]:
    """Courses whose prerequisites are satisfied by `completed`.

    Uses JSON-style prerequisites parsed on the fly.
    """
    completed_norm = {_normalize_course_code(c) for c in (completed or [])}
    exclude_norm = {_normalize_course_code(c) for c in (exclude or [])}
    courses = _all_courses_with_prereqs()

    def ok(c: Dict) -> bool:
        req = set(c.get("requires") or [])
        req_any = set(c.get("requires_any") or [])
        # All-of requirements
        if not req.issubset(completed_norm):
            return False
        # Any-of requirement, if present
        if req_any and not (req_any & completed_norm):
            return False
        return True

    out = []
    for c in courses:
        code = c["code"]
        if code in exclude_norm:
            continue
        if code in completed_norm:
            continue
        if ok(c):
            out.append({
                "code": code,
                "name": c["name"],
                "units": c["units"],
                # recommended_semester not guaranteed in JSON, omit here
            })
    return sorted(out, key=lambda x: x["code"])


def get_blocked_courses(incomplete: List[str]) -> List[Dict]:
    """Courses blocked by missing prerequisites in `incomplete`.

    This identifies courses for which a required ALL-of prereq is missing or an
    ANY-of group has no overlap with the incomplete set.
    """
    missing = {_normalize_course_code(c) for c in (incomplete or [])}
    courses = _all_courses_with_prereqs()
    out: List[Dict] = []
    for c in courses:
        req = set(c.get("requires") or [])
        req_any = set(c.get("requires_any") or [])
        # Blocked if at least one ALL-of prereq is in missing
        blocked_all = bool(req & missing)
        # Blocked if there is an ANY-of group and none of them are satisfied
        blocked_any = bool(req_any) and not bool(req_any & missing)
        if blocked_all or blocked_any:
            out.append({"code": c["code"], "name": c["name"], "units": c["units"]})
    return sorted(out, key=lambda x: x["code"])


def get_paths_to(target_code: str, max_depth: int = 4) -> List[Dict]:
    """If edge relationships exist, return prerequisite paths. Otherwise empty.
    """
    target = _normalize_course_code(target_code)
    query = """
    MATCH p = (s:Course)-[:REQUIRES|REQUIRES_ANY*1..$max_depth]->(t:Course {course_code: $target})
    WITH nodes(p) AS ns
    RETURN [x IN ns | coalesce(x.course_code, x.code)] AS nodes, size(ns) - 1 AS length
    ORDER BY length ASC LIMIT 25
    """
    try:
        return graph.run(query, target=target, max_depth=max_depth).data()
    except Exception:
        return []


def course_exists(course_code: str) -> bool:
    code = _normalize_course_code(course_code)
    q = """
    MATCH (c:Course {course_code: $code}) RETURN count(c) AS n
    """
    rec = graph.run(q, code=code).data()
    return bool(rec and rec[0].get("n", 0) > 0)