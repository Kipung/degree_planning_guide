# models.py
from db import engine   # ✅ not 'from backend.db'
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    major = Column(String)

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    code = Column(String)
    name = Column(String)
    prerequisites = Column(String)  # comma-separated