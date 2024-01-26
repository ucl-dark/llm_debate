from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict

from core.file_handler import Method
from core.rollouts.utils import TranscriptConfig


class Model(BaseModel):
    # This is for v2
    # model_config = ConfigDict(from_attributes=True)
    class Config:
        orm_mode = True


class Question(Model):
    id: int
    question_text: str
    correct_answer: str
    incorrect_answer: str


class ModelJudgement(Model):
    judgement_text: str
    judge_name: str


class HumanJudgement(Model):
    id: int
    created_at: datetime
    confidence_correct: float
    explanation: Optional[str]


class File(Model):
    id: int
    path: str
    path_hash: Union[str, None] = None
    created_at: datetime
    imported_at: datetime


class Row(Model):
    id: int
    row_number: int


class Experiment(Model):
    id: int
    name: str
    public_name: Optional[str]
    give_judge_feedback: bool
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]


class User(Model):
    id: int
    user_name: str
    full_name: Optional[str]
    admin: bool


class Debate(Model):
    id: int
    name: str
    max_turns: Optional[int]
    min_turns: Optional[int]
    method: Method
    allow_judge_interaction: bool
    config_path: str
    user: User
    transcript: TranscriptConfig
    judgement: Optional[HumanJudgement]
    experiment: Optional[Experiment]
