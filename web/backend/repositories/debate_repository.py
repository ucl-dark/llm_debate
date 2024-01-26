from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, insert, select
from sqlalchemy.orm import selectinload

import web.backend.database.models as models
from core.utils import TranscriptConfig
from web.backend.api.schemas import Model
from web.backend.database.connection import SessionLocal
from web.backend.repositories.base_repository import BaseRepository
from web.backend.repositories.experiment_respository import ExperimentRepository


class CreateDebateInput(Model):
    name: str
    max_turns: Optional[int] = None
    min_turns: Optional[int] = None
    method: str
    allow_judge_interaction: bool
    config_path: str
    cross_examiner_config_path: Optional[str] = None
    transcript: TranscriptConfig
    experiment_id: Optional[int]
    user_id: int


class DebateRepository(BaseRepository):
    @staticmethod
    def find_all():
        with SessionLocal() as session:
            return session.scalars(select(models.Debate)).all()

    @staticmethod
    def commit(debate: models.Debate) -> models.Debate:
        if debate.min_turns is not None and not debate.allow_judge_interaction:
            raise ValueError("Can't set min_turns while disallowing judge interaction")
        elif (
            debate.min_turns is not None
            and debate.max_turns is not None
            and debate.min_turns > debate.max_turns
        ):
            raise ValueError("min_turns is higher than max_turns!")
        else:
            return BaseRepository.commit(debate)

    @staticmethod
    def find_by_id(id: int | str):
        with SessionLocal() as session:
            return session.scalar(
                select(models.Debate)
                .options(
                    selectinload(models.Debate.judgement),
                    selectinload(models.Debate.experiment),
                    selectinload(models.Debate.user),
                )
                .where(models.Debate.id == id)
            )

    @staticmethod
    def find_next_experiment_debates_for_user(user_id: int | str):
        debates = DebateRepository.find_experiment_debates_for_user(int(user_id))
        active_debates = [
            d
            for d in debates
            if ExperimentRepository.is_active(d.experiment) and d.judgement is None
        ]

        # sort by experiment id, then by debate id
        ordered_debates = sorted(active_debates, key=lambda d: (d.experiment_id, d.id))
        return ordered_debates

    @staticmethod
    def is_next_debate_available(debate: models.Debate):
        debates = DebateRepository.find_experiment_debates_for_user(int(debate.user_id))
        active_debates = [
            d
            for d in debates
            if ExperimentRepository.is_active(d.experiment)
            and d.judgement is None
            and d.id != debate.id
        ]
        return len(active_debates) > 0

    @staticmethod
    def create_judgement(
        debate_id: int, confidence_correct: int, explanation: Optional[str]
    ):
        # TODO: Make this like other create methods
        with SessionLocal() as session:
            judgement = models.Judgement(
                debate_id=debate_id,
                confidence_correct=confidence_correct,
                explanation=explanation,
                created_at=datetime.now(),
            )
            session.add(judgement)
            session.commit()

    @staticmethod
    def is_complete(debate: models.Debate):
        return debate.judgement is not None

    @staticmethod
    def find_experiment_debates_for_user(user_id: int | str):
        with SessionLocal() as session:
            return session.scalars(
                select(models.Debate)
                .options(
                    selectinload(models.Debate.judgement),
                    selectinload(models.Debate.user),
                    selectinload(models.Debate.experiment),
                )
                .where(
                    and_(
                        models.Debate.user_id == int(user_id),
                        models.Debate.experiment != None,
                    )
                )
            ).all()

    @staticmethod
    def find_debates_for_experiment(experiment_id: int | str):
        with SessionLocal() as session:
            return session.scalars(
                select(models.Debate)
                .options(
                    selectinload(models.Debate.judgement),
                    selectinload(models.Debate.user),
                    selectinload(models.Debate.experiment),
                )
                .where(
                    and_(
                        models.Debate.experiment_id == int(experiment_id),
                    )
                )
            ).all()

    @staticmethod
    def find_completed_debates_for_experiment(experiment_id: int | str):
        with SessionLocal() as session:
            return session.scalars(
                select(models.Debate)
                .options(
                    selectinload(models.Debate.judgement),
                    selectinload(models.Debate.user),
                    selectinload(models.Debate.experiment),
                )
                .where(
                    and_(
                        models.Debate.experiment_id == int(experiment_id),
                        models.Debate.judgement != None,
                    )
                )
            ).all()

    # TODO: Reduce duplication here
    @staticmethod
    def find_completed_experiment_debates_for_user(user_id: int | str):
        with SessionLocal() as session:
            return session.scalars(
                select(models.Debate)
                .options(
                    selectinload(models.Debate.judgement),
                    selectinload(models.Debate.user),
                    selectinload(models.Debate.experiment),
                )
                .where(
                    and_(
                        models.Debate.user_id == int(user_id),
                        models.Debate.experiment != None,
                        models.Debate.judgement != None,
                    )
                )
            ).all()

    @staticmethod
    def find_playground_debates_for_user(user_id: int | str):
        with SessionLocal() as session:
            return session.scalars(
                select(models.Debate)
                .options(
                    selectinload(models.Debate.judgement),
                    selectinload(models.Debate.user),
                )
                .where(
                    and_(
                        models.Debate.user_id == int(user_id),
                        models.Debate.experiment == None,
                    )
                )
            ).all()

    # TODO: Extract out generic create method (this is the same as the exp one)
    @staticmethod
    def create(fields: CreateDebateInput) -> models.Debate | None:
        with SessionLocal() as session:
            if fields.min_turns is not None and not fields.allow_judge_interaction:
                raise ValueError(
                    "Can't set min_turns while disallowing judge interaction"
                )
            elif (
                fields.min_turns is not None
                and fields.max_turns is not None
                and fields.min_turns > fields.max_turns
            ):
                raise ValueError("min_turns is higher than max_turns!")
            stmt = (
                insert(models.Debate).values(**fields.dict()).returning(models.Debate)
            )

            maybe_debate = session.execute(stmt).first()
            if maybe_debate:
                debate = maybe_debate[0]
                session.commit()
                session.refresh(debate)
                return debate
            else:
                return None
