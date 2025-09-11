from sqlalchemy.ext.declarative import declarative_base

from src.util import util_env as key
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(key.require("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()