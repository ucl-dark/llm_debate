from fastapi import APIRouter, Cookie, HTTPException

import web.backend.api.schemas as schemas
from web.backend.repositories.debate_repository import DebateRepository

router = APIRouter()


class GetDebatesResponse(schemas.Model):
    debates: list[schemas.Debate]


@router.get("/completed_debates", response_model=GetDebatesResponse)
def get_completed_debates(user_id: str = Cookie(None)):
    if not user_id:
        raise HTTPException(
            status_code=403, detail="You must be logged in to view your debates."
        )

    debates = DebateRepository.find_completed_experiment_debates_for_user(user_id)
    # Only show last N debates to prevent shenanigans
    sorted_debates = sorted(debates, key=lambda d: d.id, reverse=True)
    response = [schemas.Debate(**d.__dict__) for d in sorted_debates[:50]]

    for debate in response:
        # We don't need these and including them will hurt perf
        debate.transcript.rounds = []
        debate.transcript.story = None

    return {"debates": response}
