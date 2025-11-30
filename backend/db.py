# db.py
from sqlmodel import SQLModel, create_engine, Session
import os

DB_URL = os.environ.get("DB_URL", "sqlite:///./chat.db")
engine = create_engine(DB_URL, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s
        