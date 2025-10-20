from graph.graph_query import get_course_prereqs, print_all_course_prereqs

if __name__ == "__main__":
    print("📚 All course prerequisites:")
    print_all_course_prereqs()
    print()

    print("🔍 Prerequisites for CSC321:")
    for prereq in get_course_prereqs("CSC321"):
        print(f"   ↳ {prereq['prereq_code']} - {prereq['prereq_name']}")