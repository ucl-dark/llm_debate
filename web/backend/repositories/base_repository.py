from typing import TypeVar

from web.backend.database.connection import SessionLocal
from web.backend.database.models import Base

T = TypeVar("T", bound=Base)


class BaseRepository:
    @staticmethod
    def commit(resource: T) -> T:
        with SessionLocal() as session:
            session.add(resource)
            session.commit()
            session.refresh(resource)
            return resource
