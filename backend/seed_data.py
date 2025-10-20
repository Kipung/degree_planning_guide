from db import SessionLocal
from models import Student, Course

session = SessionLocal()

students = [
    Student(name="Alice Kim", major="Computer Science"),
    Student(name="Bob Lee", major="Mechanical Engineering")
]

courses = [
    Course(code="CS101", name="Intro to Programming", prerequisites=""),
    Course(code="CS201", name="Data Structures", prerequisites="CS101")
]

session.add_all(students + courses)
session.commit()
session.close()

print("✅ Seed data inserted!")