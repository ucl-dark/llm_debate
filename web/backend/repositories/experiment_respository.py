import random
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, func, insert, select
from sqlalchemy.orm import selectinload

import web.backend.database.models as models
from web.backend.api.schemas import Model
from web.backend.database.connection import SessionLocal
from web.backend.repositories.base_repository import BaseRepository
from web.backend.repositories.user_repository import UserRepository


class CreateExperimentInput(Model):
    name: str
    public_name: Optional[str]
    give_judge_feedback: Optional[bool]
    starts_at: Optional[date]
    ends_at: Optional[date]


class ExperimentRepository(BaseRepository):
    @staticmethod
    def find_all():
        with SessionLocal() as session:
            return session.scalars(select(models.Experiment)).all()

    @staticmethod
    def find_by_id(id: int | str):
        with SessionLocal() as session:
            return session.scalar(
                select(models.Experiment).where(models.Experiment.id == int(id))
            )

    @staticmethod
    def find_by_name(name: str):
        with SessionLocal() as session:
            return session.scalar(
                select(models.Experiment).where(models.Experiment.name == name)
            )

    @staticmethod
    def is_active(experiment: models.Experiment):
        ends_at = experiment.ends_at
        starts_at = experiment.starts_at
        return (ends_at is None or ends_at > datetime.utcnow()) and (
            starts_at is None or starts_at < datetime.utcnow()
        )

    @staticmethod
    def create(fields: CreateExperimentInput) -> models.Experiment | None:
        with SessionLocal() as session:
            stmt = (
                insert(models.Experiment)
                .values(**fields.dict())
                .returning(models.Experiment)
            )

            maybe_experiment = session.execute(stmt).first()
            if maybe_experiment:
                experiment = maybe_experiment[0]
                session.commit()
                session.refresh(experiment)
                return experiment
            else:
                return None

    @staticmethod
    def delete(id: int):
        with SessionLocal() as session:
            experiment = ExperimentRepository.find_by_id(id)
            session.delete(experiment)
            session.commit()
