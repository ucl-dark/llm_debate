import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import web.backend.database.models as models
from core.agents.debater_base import DebaterConfig
from core.agents.debater_quality import DebaterQuality
from core.agents.judge_base import JudgeConfig
from core.agents.judge_quality import JudgeQuality
from core.file_handler import Method
from core.llm_api.llm import ModelAPI
from core.load.quality import (
    QuestionWithArticle,
    best_distractor_for_question,
    correct_answer_for_question,
)
from core.rollouts.quality_sim import QualitySimRollout
from core.rollouts.utils import (
    Answers,
    DebaterNames,
    RolloutConfig,
    StubCacheManager,
    TranscriptConfig,
)
from core.utils import load_yaml, setup_environment

LOGGER = logging.getLogger(__name__)

LIVE_DEBATE_TYPES = ["Interactive"]


DebateTypes = Literal[
    "debate", "consultancy", "correct_consultancy", "incorrect_consultancy"
]


def names_from_debate_type(
    debate_type: DebateTypes, rollout_config: RolloutConfig, swap: bool
):
    names = {}
    match debate_type:
        case "debate":
            names["correct"] = (
                rollout_config.name1 if not swap else rollout_config.name2
            )
            names["incorrect"] = (
                rollout_config.name2 if not swap else rollout_config.name1
            )
        case "correct_consultancy":
            names["correct"] = rollout_config.consultant_name
        case "incorrect_consultancy":
            names["incorrect"] = rollout_config.consultant_name
        case "consultancy":
            consultant = random.choice(["correct", "incorrect"])
            names[consultant] = rollout_config.consultant_name

    return names


def create_live_debate_transcript(
    question: QuestionWithArticle, debate_type: DebateTypes, judge_name: Optional[str]
):
    swap = random.choice([True, False])
    rollout_config = create_rollout_config()
    names = names_from_debate_type(debate_type, rollout_config, swap)
    story = question.article.article
    question.article.article = "<TRUNCATED>"

    transcript = TranscriptConfig(
        index=0,
        story=story,
        story_title=question.article.title,
        question=question.question,
        question_set_id=question.set_unique_id,
        answers=Answers(
            correct=correct_answer_for_question(question),
            incorrect=best_distractor_for_question(question),
        ),
        names=DebaterNames(**names, judge=judge_name),
        swap=swap,
        rollout_type=rollout_config.rollout_type,
        extra={"quality_question": question},
    )

    return transcript


def create_live_debate_transcript_from_previous_transcript(
    transcript: TranscriptConfig, debate_type: DebateTypes, judge_name: Optional[str]
):
    swap = random.choice([True, False])
    rollout_config = create_rollout_config()
    names = names_from_debate_type(debate_type, rollout_config, swap)
    transcript.names = DebaterNames(**names, judge=judge_name)
    transcript.rounds = []
    transcript.responses = []
    transcript.swap = swap
    transcript.rollout_type = rollout_config.rollout_type

    return transcript


def create_rollout_config():
    root = "./core/config/experiment"
    rollout_config_path = f"{root}/rollout/live.yaml"
    rollout_config = RolloutConfig(**load_yaml(rollout_config_path))

    return rollout_config


def create_rollout(debate: models.Debate):
    api_handler = ModelAPI(organization="DEFAULT_ORG")
    transcript = TranscriptConfig(**debate.transcript)
    rollout_config = create_rollout_config()
    correct_debater, incorrect_debater, cross_examiner = [None, None, None]
    print(f"debater config: {debate.config_path}")
    debater_config = DebaterConfig(**load_yaml(debate.config_path))

    if transcript.names.correct:
        correct_debater = DebaterQuality(
            debate.method, debater_config, True, api_handler
        )

    if transcript.names.incorrect:
        incorrect_debater = DebaterQuality(
            debate.method, debater_config, False, api_handler
        )

    if debate.cross_examiner_config_path:
        cross_examiner_config = JudgeConfig(
            **load_yaml(debate.cross_examiner_config_path)
        )
        cross_examiner = JudgeQuality(
            debate.method, cross_examiner_config, rollout_config, api_handler
        )

    bon_pm = None
    if debater_config.bon_pm_config:
        judge_config = JudgeConfig(**load_yaml(debater_config.bon_pm_config))
        bon_pm = JudgeQuality(debate.method, judge_config, rollout_config, api_handler)

    critic = None
    if debater_config.critic_config:
        judge_config = JudgeConfig(**load_yaml(debater_config.critic_config))
        critic = JudgeQuality(debate.method, judge_config, rollout_config, api_handler)

    critique_pm = None
    if debater_config.critique_pm_config:
        judge_config = JudgeConfig(**load_yaml(debater_config.critique_pm_config))
        critique_pm = JudgeQuality(
            debate.method, judge_config, rollout_config, api_handler
        )

    rollout = QualitySimRollout(
        debate.method,
        rollout_config,
        Path(""),
        correct_debater,
        incorrect_debater,
        cross_examiner,
        bon_pm,
        bon_pm,
        critic,
        critic,
        critique_pm,
        critique_pm,
    )

    return rollout


async def new_turn(debate: models.Debate, judge_message: Optional[str]):
    start = datetime.now()
    setup_environment()
    rollout = create_rollout(debate)
    transcript = TranscriptConfig(**debate.transcript)

    cache_manager = StubCacheManager()
    current_step = len(transcript.rounds)
    new_transcript = await rollout.debate_turn(
        transcript, current_step, cache_manager, judge_message
    )
    duration = datetime.now() - start
    if "round_times" in new_transcript.extra:
        new_transcript.extra["round_times"][
            f"{len(new_transcript.rounds)}"
        ] = duration.seconds
    else:
        new_transcript.extra["round_times"] = {
            f"{len(new_transcript.rounds)}": duration.seconds
        }

    return new_transcript
