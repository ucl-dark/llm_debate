import json
import traceback
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException

import web.backend.api.schemas as schemas
import web.backend.database.models as models
from web.backend.repositories.debate_repository import DebateRepository
from web.backend.repositories.user_repository import UserRepository
from web.backend.services.live_debate import TranscriptConfig, new_turn
from web.backend.services.parser import TranscriptParser

router = APIRouter()


class GetDebateResponse(schemas.Debate):
    raw_transcript: str
    debates_remaining: Optional[int]
    next_debate_id: Optional[int]


def construct_debate_response(
    debate: models.Debate,
    debates_remaining: Optional[int] = None,
    next_debate_id: Optional[int] = None,
):
    response = GetDebateResponse(
        **debate.__dict__,
        raw_transcript=json.dumps(debate.transcript),
        debates_remaining=debates_remaining,
        next_debate_id=next_debate_id,
    )

    transcript = TranscriptConfig(**debate.transcript)
    if transcript.story is not None:
        transcript, _ = TranscriptParser.verify_strict(transcript)
    if debate.user:
        transcript.names.judge = debate.user.full_name
    response.transcript = transcript
    response.judgement = (
        schemas.HumanJudgement(**debate.judgement.__dict__)
        if debate.judgement
        else None
    )
    response.experiment = (
        schemas.Experiment(**debate.experiment.__dict__) if debate.experiment else None
    )

    return response


# TODO: Move thhis to experiment routes? It is exp specific
@router.get("/next", response_model=GetDebateResponse | None)
def get_next_debate(user_id: str = Cookie(None)):
    next_debates = DebateRepository.find_next_experiment_debates_for_user(user_id)
    if len(next_debates) == 0:
        return None

    return construct_debate_response(
        next_debates[0], debates_remaining=len(next_debates)
    )


@router.get("/{debate_id}", response_model=GetDebateResponse)
def get_debate(debate_id, user_id: str = Cookie(None)):
    debate = DebateRepository.find_by_id(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    if debate.experiment_id:
        user = UserRepository.find_by_id(user_id)
        if not user or (not int(user_id) == debate.user_id and not user.admin):
            raise HTTPException(
                status_code=403, detail="Cannot view other users debates"
            )

    next_debates = []
    next_debate_id = None
    if user_id:
        next_debates = DebateRepository.find_next_experiment_debates_for_user(user_id)
        if len(next_debates) > 0:
            next_debate_id = next_debates[0].id

    return construct_debate_response(
        debate, debates_remaining=len(next_debates), next_debate_id=next_debate_id
    )


class CreateTurnPayload(schemas.Model):
    judge_message: Optional[str]


@router.post("/{debate_id}/turn", response_model=GetDebateResponse)
async def create_turn(
    debate_id, payload: CreateTurnPayload, user_id: str = Cookie(None)
):
    debate = DebateRepository.find_by_id(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    if not int(user_id) == debate.user_id:
        raise HTTPException(
            status_code=403, detail="Cannot continue another user's debate"
        )

    try:
        new_transcript = await new_turn(debate, payload.judge_message)
        # TODO: Surely there is some way I could add a default error handler instead?
    except BaseException as e:
        stack_trace = traceback.format_exc()
        print(stack_trace)
        print(e)
        raise HTTPException(status_code=500, detail=f"Error generating argument")
    debate.transcript = new_transcript.dict()
    debate = DebateRepository.commit(debate)
    response = construct_debate_response(debate)

    return response


class CreateJudgementPayload(schemas.Model):
    confidence_correct: int
    explanation: Optional[str] = None


@router.post("/{debate_id}/judgements")
def create_judgement(
    debate_id, payload: CreateJudgementPayload, user_id: str = Cookie(None)
):
    debate = DebateRepository.find_by_id(debate_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    if not int(user_id) == debate.user_id:
        raise HTTPException(
            status_code=403, detail="Cannot judge another user's debate"
        )
    if DebateRepository.is_complete(debate):
        raise HTTPException(status_code=400, detail="Debate has already been judged.")

    DebateRepository.create_judgement(
        debate_id=debate.id,
        confidence_correct=payload.confidence_correct,
        explanation=payload.explanation,
    )
