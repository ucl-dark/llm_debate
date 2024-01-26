from typing import List

import typer

import web.backend.database.models as models
from core.utils import typer_async
from web.backend.database.connection import SessionLocal
from web.backend.repositories.user_repository import UserRepository
from web.backend.services.live_debate import create_live_debate_transcript
from web.backend.services.quality import get_random_question
from web.backend.utils import create_debate_name


async def create_debate(debate_type: str, user, experiment):
    question = await get_random_question()
    transcript = create_live_debate_transcript(question, debate_type, user.full_name)
    debate_name = create_debate_name(question.article.title)
    new_debate = models.Debate(
        user_id=user.id,
        transcript=transcript.dict(),
        experiment=experiment,
        name=debate_name,
    )
    return new_debate


@typer_async
async def main(user_ids: List[int]):
    session = SessionLocal()
    with session:

        async def create_debates(user, experiment):
            for _ in range(2):
                debate = await create_debate("debate", user, experiment)
                session.add(debate)
            for _ in range(4):
                debate = await create_debate("consultancy", user, experiment)
                session.add(debate)

        for user_id in user_ids:
            user = UserRepository.find_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            exp1 = models.Experiment(
                debater_config="standard",
                consultant_config="standard",
                max_turns=None,
                interactive_judge=False,
                judge_feedback=False,
            )
            session.add(exp1)
            await create_debates(user, exp1)

            exp2 = models.Experiment(
                debater_config="interactive",
                consultant_config="interactive",
                max_turns=2,
                interactive_judge=True,
                judge_feedback=True,
            )
            session.add(exp2)
            await create_debates(user, exp2)

            session.commit()


if __name__ == "__main__":
    typer.run(main)
