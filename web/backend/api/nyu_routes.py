from typing import List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from core.agents.debater_base import DebaterConfig, TranscriptConfig
from core.create_agents import create_debater
from core.llm_api.llm import ModelAPI
from core.rollouts.utils import Answers, DebaterNames, RolloutConfig, Round
from core.utils import delete_old_prompt_files, load_yaml

router = APIRouter()


class DebateRequestTurn(BaseModel):
    role: str
    index: Optional[int]
    text: str
    probabilities: Optional[List[float]]


class DebateRequestInput(BaseModel):
    storyId: str
    storyTitle: str
    story: str
    question: str
    answers: List[str]
    correctAnswerIndex: Literal[0, 1]
    debaterIndex: int
    turns: List[DebateRequestTurn]
    charLimitOpt: int
    quoteCharLimitOpt: int
    turnType: str


round_types = {
    "simultaneous": "sim",
    "single debater": "sim",
    "sequential": "seq",
}


def get_turn_role(input: DebateRequestInput, turn: DebateRequestTurn):
    if turn.role.lower() == "judge":
        return "judge"
    elif turn.role.lower() == "debater":
        return "correct" if turn.index == input.correctAnswerIndex else "incorrect"
    else:
        raise ValueError(f"Unknown role - {turn.role}")


def is_round_finished(round: dict[str, str], input: DebateRequestInput):
    if input.turnType in ["single debater"]:
        return round.get("correct") or round.get("incorrect")
    else:
        # Sequential rounds contain both correct and incorrect in 2-sided debate
        return round.get("correct") and round.get("incorrect")


def get_turn_content(turn: DebateRequestTurn):
    if len(turn.text.strip()) == 0:
        return None
    return turn.text.strip()


def nyu_input_to_transcript_config(
    input: DebateRequestInput, rollout_config: RolloutConfig
) -> TranscriptConfig:
    correct_idx = input.correctAnswerIndex
    incorrect_idx = 1 - input.correctAnswerIndex
    swap = correct_idx == 1
    transcript = TranscriptConfig(
        index=0,
        story=input.story,
        story_title=input.storyTitle,
        question=input.question,
        answers=Answers(
            correct=input.answers[correct_idx], incorrect=input.answers[incorrect_idx]
        ),
        names=DebaterNames(
            correct=(rollout_config.name1 if not swap else rollout_config.name2),
            incorrect=(rollout_config.name2 if not swap else rollout_config.name1),
        ),
        swap=swap,
        rollout_type=rollout_config.rollout_type,
        rounds=[],
    )
    current_round = {}
    for turn in input.turns:
        role = get_turn_role(input, turn)
        current_round[role] = get_turn_content(turn)
        if is_round_finished(current_round, input):
            # TODO: Fix, this is type of new round, not original
            current_round["type"] = round_types[input.turnType]
            transcript.rounds.append(Round(**current_round))
            current_round = {}

    if bool(current_round):
        # we're on a partially completed round
        if (
            current_round.get("correct")
            or current_round.get("incorrect")
            or current_round.get("judge")
        ):
            transcript.rounds.append(Round(**current_round))

    return transcript


# Used by the NYU frontend
@router.post("/debate")
async def debate(input: DebateRequestInput):
    rollout_config = RolloutConfig(
        **load_yaml("./core/config/quality/rollout_nyu.yaml")
    )
    debater_config_path = "./core/config/quality/debater_debate.yaml"
    consultant_config_path = "./core/config/quality/debater_consultant.yaml"
    debater_config = DebaterConfig(
        **load_yaml(
            consultant_config_path
            if input.turnType == "single debater"
            else debater_config_path
        )
    )
    # Change 'None' indexes to 0 (the initial judge index is None)
    input.turns = [
        DebateRequestTurn(
            role=turn.role, text=turn.text, index=turn.index or 0, probabilities=None
        )
        for turn in input.turns
    ]
    api_handler = ModelAPI(
        anthropic_num_threads=9,
        openai_fraction_rate_limit=0.9,
    )
    is_argument_for_correct_answer = input.debaterIndex == input.correctAnswerIndex
    transcript = nyu_input_to_transcript_config(input, rollout_config)
    debater = create_debater(
        debater_config, is_argument_for_correct_answer, api_handler
    )
    response = await debater.take_turn(transcript)

    return response
