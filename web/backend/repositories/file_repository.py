from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

import web.backend.database.models as models
from web.backend.database.connection import SessionLocal
from web.backend.repositories.base_repository import BaseRepository
from web.backend.utils import create_path_hash


class FileRepository(BaseRepository):
    @staticmethod
    def find_all():
        with SessionLocal() as session:
            row_counts = (
                select(models.Row.file_id, func.count("*").label("count"))
                .group_by(models.Row.file_id)
                .alias()
            )

            files_query = (
                select(models.File, row_counts.c.count)
                .outerjoin(row_counts, models.File.id == row_counts.c.file_id)
                .order_by(models.File.path)
            )

            return session.execute(files_query).all()

    @staticmethod
    def find_by_path_hash(hash: str, include_rows: bool = False):
        with SessionLocal() as session:
            files = session.query(models.File).all()
            for file in files:
                file_hash = create_path_hash(file.path)
                if file_hash.startswith(hash):
                    query = select(models.File).where(models.File.id == file.id)

                    if include_rows:
                        query = query.options(
                            selectinload(models.File.rows).selectinload(
                                models.Row.question
                            )
                        )

                    found_file = session.scalar(query)
                    return found_file

            return None

    @staticmethod
    def find_random(include_rows: bool = False):
        with SessionLocal() as session:
            query = select(models.File).order_by(func.random()).limit(1)

            if include_rows:
                query = query.options(
                    selectinload(models.File.rows).selectinload(models.Row.question)
                )

            return session.scalar(query)

    @staticmethod
    def find_row_for_file(file_id: int, row_number: int):
        with SessionLocal() as session:
            return session.scalar(
                select(models.Row)
                .where(
                    models.Row.file_id == file_id, models.Row.row_number == row_number
                )
                .options(
                    selectinload(models.Row.file), selectinload(models.Row.question)
                )
            )
