from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DB_URL = os.getenv("DB_URL", "postgresql://postgres:password@db:5432/postgres")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)