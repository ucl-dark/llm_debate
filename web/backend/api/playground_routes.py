import glob
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException

import web.backend.api.schemas as schemas
from core.file_handler import Method
from web.backend.repositories.debate_repository import (
    CreateDebateInput,
    DebateRepository,
)
from web.backend.repositories.user_repository import UserRepository
from web.backend.services.live_debate import (
    DebateTypes,
    TranscriptConfig,
    create_live_debate_transcript,
    create_live_debate_transcript_from_previous_transcript,
)
from web.backend.services.quality import get_random_question

router = APIRouter()


class GetDebatesResponse(schemas.Model):
    debates: list[schemas.Debate]


@router.get("/debates", response_model=GetDebatesResponse)
def get_debates(user_id: str = Cookie(None)):
    if not user_id:
        raise HTTPException(
            status_code=403, detail="You must be logged in to use the playground."
        )
    debates = DebateRepository.find_playground_debates_for_user(user_id)
    response = [schemas.Debate(**d.__dict__) for d in debates]

    for debate in response:
        # We don't need these and including them will hurt perf
        debate.transcript.rounds = []
        debate.transcript.story = None

    return {"debates": response}


class GetDatasetsResponse(schemas.Model):
    datasets: list[str]


@router.get("/datasets", response_model=GetDatasetsResponse)
def get_datasets():
    datasets = ["QuALITY"]
    return {"datasets": datasets}


class GetDebaterConfigsResponse(schemas.Model):
    debater_configs: list[str]
    consultant_configs: list[str]


@router.get("/debater_configs", response_model=GetDebaterConfigsResponse)
def get_debater_configs():
    debater_dir = Path("./core/config/experiment/debaters")
    consultant_dir = Path("./core/config/experiment/consultants")
    debater_configs = glob.glob(os.path.join(debater_dir, "*.yaml"))
    consultant_configs = glob.glob(os.path.join(consultant_dir, "*.yaml"))
    return {
        "debater_configs": debater_configs,
        "consultant_configs": consultant_configs,
    }


class CreateDebateResponse(schemas.Model):
    id: int


class CreateDebatePayload(schemas.Model):
    debate_type: DebateTypes
    config_path: str
    previous_debate_id: Optional[int]  # An existing debate to use the same question as


@router.post("/debates", response_model=CreateDebateResponse)
async def create_debate(payload: CreateDebatePayload, user_id: str = Cookie(None)):
    user = UserRepository.find_by_id(user_id)
    if not user or not user.admin:
        raise HTTPException(
            status_code=403,
            detail="Must be logged in as an admin to create debates.",
        )
    debate_name = None
    if payload.previous_debate_id:
        previous_debate = DebateRepository.find_by_id(payload.previous_debate_id)
        if not previous_debate:
            raise HTTPException(status_code=404, detail="Previous debate not found")
        debate_name = previous_debate.name
        transcript = create_live_debate_transcript_from_previous_transcript(
            TranscriptConfig(**previous_debate.transcript),
            debate_type=payload.debate_type,
            judge_name=user.full_name,
        )
    else:
        question = await get_random_question()
        debate_name = question.article.title
        transcript = create_live_debate_transcript(
            question, payload.debate_type, user.full_name
        )

    method = Method.debate if payload.debate_type == "debate" else Method.consultancy
    debate_fields = CreateDebateInput(
        name=debate_name,
        method=method,
        allow_judge_interaction=True,
        config_path=payload.config_path,
        transcript=transcript,
        experiment_id=None,
        user_id=user.id,
    )

    debate = DebateRepository.create(debate_fields)
    if not debate:
        raise HTTPException(status_code=500, detail="Unable to create debate.")

    return CreateDebateResponse(id=debate.id)
