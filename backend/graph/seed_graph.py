"""
Seed Neo4j from the canonical 8-field course JSON.

Expected per course:
- course_code, course_name, course_description,
- credit_hours_min, credit_hours_max, lab_hours,
- offered, prerequisites

Fields may be scalars, lists, or nested dicts. We normalize and keep all courses.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utility.backend_log import logger
from graph.neo4j_connect import graph  # py2neo Graph

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "course_data.json"


# ----------------------------
# Normalizers
# ----------------------------
def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            for delim in ["-", "–", " to "]:
                if delim in s:
                    left = s.split(delim, 1)[0].strip()
                    try:
                        return float(left)
                    except Exception:
                        pass
    return None


def _to_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return []
        parts = [p.strip() for p in s.replace("/", ",").replace("&", ",").split(",")]
        return [p for p in parts if p]
    return [x]


def _derive_code(obj: Dict[str, Any], idx: int) -> str:
    for k in ["course_code", "code", "id", "course_id"]:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip().upper()
    name = obj.get("course_name") or obj.get("name")
    if isinstance(name, str) and name.strip():
        base = "".join(ch for ch in name.title() if ch.isalnum())[:12]
        if base:
            return f"X_{base}_{idx}"
    return f"X_UNK_{idx}"


def _extract_codes_from_prereq_item(item: Any) -> List[str]:
    out: List[str] = []
    if item is None:
        return out
    if isinstance(item, str):
        out += re.findall(r"[A-Z]{2,4}\\d{2,4}", item.upper())
        return out
    if isinstance(item, dict):
        courses = item.get("courses")
        if isinstance(courses, list):
            for c in courses:
                if isinstance(c, str) and c.strip():
                    out.append(c.strip().upper())
        for k, v in item.items():
            if k == "courses":
                continue
            out.extend(_extract_codes_from_prereq_item(v))
        return list(dict.fromkeys(out))
    if isinstance(item, list):
        for sub in item:
            out.extend(_extract_codes_from_prereq_item(sub))
        return list(dict.fromkeys(out))
    return out


def _parse_prereq_codes(prerequisites: Any) -> List[str]:
    return list(dict.fromkeys(_extract_codes_from_prereq_item(prerequisites)))


# ----------------------------
# Seeding core
# ----------------------------
def _ensure_constraints() -> None:
    graph.run(
        "CREATE CONSTRAINT course_code_unique IF NOT EXISTS FOR (c:Course) REQUIRE c.code IS UNIQUE"
    )


def _chunked(seq: List[Dict[str, Any]], n: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _prepare(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    nodes: List[Dict[str, Any]] = []
    rels: List[Dict[str, str]] = []

    for idx, obj in enumerate(records):
        code = _derive_code(obj, idx)
        name = (obj.get("course_name") or obj.get("name") or "").strip() or None
        desc = (obj.get("course_description") or obj.get("description") or "").strip() or None
        units_min = _to_float(obj.get("credit_hours_min"))
        units_max = _to_float(obj.get("credit_hours_max"))
        lab_hours = _to_float(obj.get("lab_hours"))
        offered = _to_list(obj.get("offered"))
        req_codes = _parse_prereq_codes(obj.get("prerequisites"))

        nodes.append(
            {
                "code": code,
                "name": name,
                "description": desc,
                "units_min": units_min,
                "units_max": units_max,
                "lab_hours": lab_hours,
                "offered": offered,
                "requires": req_codes,
            }
        )
        for tgt in req_codes:
            if tgt and tgt != code:
                rels.append({"src": code, "dst": tgt})

    return nodes, rels


def seed_graph_from_json(path: Optional[Path] = None, batch_size: int = 500) -> None:
    json_path = Path(path) if path else DATA_PATH
    logger.debug("📄 Loading courses JSON: %s", json_path)
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Top-level JSON must be a list of course objects")

    _ensure_constraints()
    nodes, rels = _prepare(data)
    logger.info("Prepared %d Course nodes and %d REQUIRES rels", len(nodes), len(rels))

    # Upsert nodes
    for chunk in _chunked(nodes, batch_size):
        graph.run(
            """
            UNWIND $rows AS row
            MERGE (c:Course {code: row.code})
            SET c.name      = coalesce(row.name, c.name),
                c.units_min = row.units_min,
                c.units_max = row.units_max,
                c.lab_hours = row.lab_hours,
                c.offered   = row.offered,
                c.requires  = row.requires,
                // keep the longest non-empty description
                c.description =
                  CASE
                    WHEN c.description IS NULL THEN row.description
                    WHEN row.description IS NULL THEN c.description
                    WHEN size(row.description) > size(c.description) THEN row.description
                    ELSE c.description
                  END
            """,
            rows=chunk,
        )

    # Relationships
    for chunk in _chunked(rels, max(1, batch_size * 2)):
        graph.run(
            """
            UNWIND $rels AS rel
            MATCH (src:Course {code: rel.src})
            MERGE (dst:Course {code: rel.dst})
            MERGE (src)-[:REQUIRES]->(dst)
            """,
            rels=chunk,
        )

    counts = graph.run(
        """
        CALL { MATCH (c:Course) RETURN count(c) AS courses }
        CALL { MATCH (:Course)-[r:REQUIRES]->(:Course) RETURN count(r) AS edges }
        RETURN courses, edges
        """
    ).data()[0]
    logger.info("✅ Seed complete. Courses=%s, REQUIRES=%s", counts["courses"], counts["edges"])


if __name__ == "__main__":
    seed_graph_from_json()