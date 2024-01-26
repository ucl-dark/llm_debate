import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from web.backend.database.utils import get_database_url

echo = bool(int(os.getenv("SQLALCHEMY_ECHO", "1")))
engine = create_engine(get_database_url(), echo=echo)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
