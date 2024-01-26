import datetime
from typing import List, Literal

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedColumn,
    mapped_column,
    relationship,
)

from core.file_handler import Method


class Base(DeclarativeBase):
    pass


class File(Base):
    __tablename__ = "file"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(Text(), nullable=False, index=True)
    import_complete: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    imported_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    rows: Mapped[List["Row"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )


class Row(Base):
    __tablename__ = "row"
    id: Mapped[int] = mapped_column(primary_key=True)
    row_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    transcript: Mapped[str] = mapped_column(Text(), nullable=True)
    judgement_text: Mapped[str] = mapped_column(Text(), nullable=True)

    file_id: Mapped[int] = mapped_column(
        ForeignKey("file.id", ondelete="CASCADE"),
        index=True,
    )
    file: Mapped["File"] = relationship(back_populates="rows")

    question_id: Mapped[int] = mapped_column(
        ForeignKey("question.id", ondelete="CASCADE"), index=True
    )
    question: Mapped["Question"] = relationship(back_populates="rows")


class Question(Base):
    __tablename__ = "question"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_text: Mapped[str] = mapped_column(Text(), nullable=False, index=True)
    correct_answer: Mapped[str] = mapped_column(Text(), nullable=False, index=True)
    incorrect_answer: Mapped[str] = mapped_column(Text(), nullable=False, index=True)

    rows: Mapped[List["Row"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Debate(Base):
    __tablename__ = "debate"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    max_turns: Mapped[int] = mapped_column(Integer(), nullable=True)
    min_turns: Mapped[int] = mapped_column(Integer(), nullable=True)
    method: Mapped[Method] = mapped_column(Text(), nullable=False)
    allow_judge_interaction: Mapped[bool] = mapped_column(Boolean(), default=True)
    config_path: Mapped[str] = mapped_column(Text())
    cross_examiner_config_path: Mapped[str] = mapped_column(Text(), nullable=True)
    transcript = Column(JSON, nullable=False, default={})
    judgement: Mapped["Judgement"] = relationship(back_populates="debate")

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiment.id", ondelete="CASCADE"), index=True, nullable=True
    )
    experiment: Mapped["Experiment"] = relationship(back_populates="debates")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="debates")


class Judgement(Base):
    __tablename__ = "judgement"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seconds_spent: Mapped[int] = mapped_column(Integer(), nullable=True)
    debate_id: Mapped[int] = mapped_column(
        ForeignKey("debate.id", ondelete="CASCADE"), index=True
    )
    debate: Mapped["Debate"] = relationship(back_populates="judgement")
    confidence_correct: Mapped[float] = mapped_column(Float(), nullable=False)
    explanation: Mapped[str] = mapped_column(Text(), nullable=True)


class Experiment(Base):
    __tablename__ = "experiment"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        Text(), nullable=False
    )  # only user visible if public name not defined
    public_name: Mapped[str] = mapped_column(Text(), nullable=True)
    debates: Mapped[List["Debate"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    give_judge_feedback: Mapped[bool] = mapped_column(Boolean(), default=False)
    # We'll assume UTC for these
    starts_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    ends_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False), nullable=True
    )


class User(Base):
    __tablename__ = "users"  # user is a reserved keyword in psql
    id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(Text(), nullable=True)
    debates: Mapped[List["Debate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    admin: Mapped[bool] = mapped_column(Boolean(), default=False)


class UserGroup(Base):
    __tablename__ = "user_group"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text(), nullable=True)
    # being quite lazy using an id array instead of a join table, but this is simpler and we won't have many users or need to edit groups often
    user_ids = Column(ARRAY(Integer()))
