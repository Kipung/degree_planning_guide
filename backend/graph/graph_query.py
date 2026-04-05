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
    """Return a single course using the current seeded graph schema."""
    code = _normalize_course_code(course_code)
    query = """
    MATCH (c:Course {code: $code})
    RETURN c.code AS code,
           c.name AS name,
           c.description AS description,
           c.units_min AS units_min,
           c.requires AS requires,
           c.offered AS offered
    """
    recs = graph.run(query, code=code).data()
    if not recs:
        return None
    c = recs[0]
    units = c.get("units_min")
    try:
        units = int(units) if units is not None else None
    except Exception:
        units = None
    return {
        "code": c.get("code"),
        "name": c.get("name"),
        "description": c.get("description"),
        "units": units,
        "requires": c.get("requires") or [],
        "requires_any": [],
        "coreq": [],
        "offered": c.get("offered") or [],
    }


def get_course_detail(course_code: str) -> Optional[Dict]:
    """Alias for get_course_info since edges may not exist; keeps API stable."""
    return get_course_info(course_code)


def get_courses_by_semester(semester: str) -> List[Dict]:
    """List courses by offered term when available."""
    query = """
    MATCH (c:Course)
    WHERE any(term IN coalesce(c.offered, []) WHERE toLower(term) CONTAINS toLower($semester))
    RETURN c.code AS code,
           c.name AS name,
           toInteger(c.units_min) AS units
    ORDER BY code
    """
    return graph.run(query, semester=semester).data()


def list_all_courses(limit: int = 200, skip: int = 0) -> List[Dict]:
    query = """
    MATCH (c:Course)
    RETURN c.code AS code,
           c.name AS name,
           toInteger(c.units_min) AS units
    ORDER BY code SKIP $skip LIMIT $limit
    """
    return graph.run(query, limit=limit, skip=skip).data()


def search_courses(text: str, limit: int = 25) -> List[Dict]:
    q = (text or "").lower().strip()
    query = """
    MATCH (c:Course)
    WHERE toLower(c.code) CONTAINS $q
       OR toLower(c.name) CONTAINS $q
       OR toLower(coalesce(c.description, "")) CONTAINS $q
    RETURN c.code AS code,
           c.name AS name,
           toInteger(c.units_min) AS units
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
    """Fetch minimal fields for dependency computations using seeded properties."""
    query = """
    MATCH (c:Course)
    RETURN c.code AS code,
           c.name AS name,
           c.requires AS requires,
           toInteger(c.units_min) AS units
    """
    rows = graph.run(query).data()
    out = []
    for r in rows:
        out.append({
            "code": r.get("code"),
            "name": r.get("name"),
            "units": r.get("units"),
            "requires": r.get("requires") or [],
            "requires_any": [],
            "coreq": [],
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
    MATCH p = (s:Course)-[:REQUIRES*1..$max_depth]->(t:Course {code: $target})
    WITH nodes(p) AS ns
    RETURN [x IN ns | x.code] AS nodes, size(ns) - 1 AS length
    ORDER BY length ASC LIMIT 25
    """
    try:
        return graph.run(query, target=target, max_depth=max_depth).data()
    except Exception:
        return []


def course_exists(course_code: str) -> bool:
    code = _normalize_course_code(course_code)
    q = """
    MATCH (c:Course {code: $code}) RETURN count(c) AS n
    """
    rec = graph.run(q, code=code).data()
    return bool(rec and rec[0].get("n", 0) > 0)
