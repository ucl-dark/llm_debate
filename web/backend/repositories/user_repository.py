import json
from typing import List, Set, Tuple

from sqlalchemy import and_, select

import web.backend.database.models as models
from core.utils import TranscriptConfig
from web.backend.database.connection import SessionLocal
from web.backend.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    @staticmethod
    def find_by_id(id: int | str):
        with SessionLocal() as session:
            return session.scalar(select(models.User).where(models.User.id == int(id)))

    @staticmethod
    def find_by_ids(ids: List[int]):
        with SessionLocal() as session:
            users = session.query(models.User).filter(models.User.id.in_(ids)).all()
            assert len(users) == len(ids), f"Could not find all user ids {ids}"
            return users

    @staticmethod
    def find_by_names(names: List[str]):
        with SessionLocal() as session:
            users = (
                session.query(models.User)
                .filter(models.User.user_name.in_(names))
                .all()
            )
            assert len(users) == len(names), f"Could not find all user names {names}"
            return users

    @staticmethod
    def find_by_name(name: str):
        with SessionLocal() as session:
            return session.scalar(
                select(models.User).where(models.User.user_name == name)
            )

    @staticmethod
    def find_group_by_name(name: str):
        with SessionLocal() as session:
            return session.scalar(
                select(models.UserGroup).where(models.UserGroup.name == name)
            )

    @staticmethod
    def find_users_by_group_name(group_name: str):
        group = UserRepository.find_group_by_name(group_name)
        assert group, "Could not find group"
        users = UserRepository.find_by_ids(group.user_ids)
        return users

    @staticmethod
    def find_questions_from_user_group(group: models.UserGroup):
        with SessionLocal() as session:
            debates = session.scalars(select(models.Debate))
            debates = [
                d
                for d in debates
                if d.experiment_id != None and d.user_id in group.user_ids
            ]
            previous_questions: Set[Tuple[str, str, int]] = set()
            for debate in debates:
                transcript = TranscriptConfig(**debate.transcript)
                if transcript.story_title and len(transcript.story_title) > 0:
                    previous_questions.add(
                        (transcript.question, transcript.story_title, debate.id)
                    )

            questions = list(previous_questions)
            # sort by id so we go from earliest seen to latest
            questions = sorted(questions, key=lambda x: x[2])
            seen = set()
            deduped = []
            for q, s, id in questions:
                key = f"{s} - {q}"
                if key not in seen:
                    seen.add(key)
                    deduped.append((q, s, id))
            return deduped
