from graph.neo4j_connect import graph



def get_course_info(course_code: str):
    course_code = course_code.upper().strip()

    # normalize common phrases
    if course_code in ["FIRST YEAR EXPERIENCE", "FYE"]:
        course_code = "GST100"

    query = """
    MATCH (c:Course {code: $course_code})
    RETURN c.code AS code, c.name AS name, c.units AS units,
           c.recommended_semester AS recommended_semester,
           c.requires AS requires, c.requires_any AS requires_any,
           c.coreq AS coreq, c.satisfies AS satisfies
    """
    result = graph.run(query, course_code=course_code).data()
    return result[0] if result else None

# graph_query.py
def get_courses_by_semester(semester: str):
    query = """
    MATCH (c:Course)
    WHERE c.recommended_semester = $semester
    RETURN c.code AS code, c.name AS name, c.units AS units
    """
    return graph.run(query, semester=semester).data()