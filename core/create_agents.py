import logging
from pathlib import Path
from typing import Optional

from omegaconf import DictConfig

from core.agents.debater_base import DebaterBase, DebaterConfig
from core.agents.debater_quality import DebaterQuality
from core.agents.judge_base import JudgeBase, JudgeConfig
from core.agents.judge_quality import JudgeQuality
from core.file_handler import Method
from core.llm_api.llm import ModelAPI
from core.rollouts.quality_seq import QualitySeqRollout
from core.rollouts.quality_sim import QualitySimRollout
from core.rollouts.rollout_base import RolloutBase, RolloutConfig

DEBATER_CLASSES = {
    "quality": DebaterQuality,
}
LOGGER = logging.getLogger(__name__)


def create_debater(
    method: Method,
    config: DebaterConfig,
    correct: bool,
    api_handler: ModelAPI,
) -> DebaterBase:
    debater_class = DEBATER_CLASSES.get(config.debater_type)
    if not debater_class:
        raise ValueError(f"Unknown debater type: {config.debater_type}")
    return debater_class(method, config, correct, api_handler)


JUDGE_CLASSES = {
    "quality": JudgeQuality,
}


def create_judge(
    method: Method,
    config: JudgeConfig,
    rollout_config: RolloutConfig,
    api_handler: ModelAPI,
) -> JudgeBase:
    judge_class = JUDGE_CLASSES.get(config.judge_type)
    if not judge_class:
        raise ValueError(f"Unknown judge type: {config.judge_type}")
    return judge_class(method, config, rollout_config, api_handler)


# setup rollout
ROLLOUT_CLASSES = {
    "quality_sim": QualitySimRollout,
    "quality_seq": QualitySeqRollout,
}


def create_rollout(
    method: Method,
    config: RolloutConfig,
    cache_dir: Path,
    correct_debater: Optional[DebaterBase],
    incorrect_debater: Optional[DebaterBase],
    cross_examiner: Optional[JudgeBase],
    correct_judge_BoN: Optional[JudgeBase],
    incorrect_judge_BoN: Optional[JudgeBase],
    correct_judge_critic: Optional[JudgeBase],
    incorrect_judge_critic: Optional[JudgeBase],
    correct_judge_critique_pm: Optional[JudgeBase],
    incorrect_judge_critique_pm: Optional[JudgeBase],
) -> RolloutBase:
    rollout_class = ROLLOUT_CLASSES.get(config.rollout_type)
    if not rollout_class:
        raise ValueError(f"Unknown rollout type: {config.rollout_type}")
    return rollout_class(
        method,
        config,
        cache_dir,
        correct_debater,
        incorrect_debater,
        cross_examiner,
        correct_judge_BoN,
        incorrect_judge_BoN,
        correct_judge_critic,
        incorrect_judge_critic,
        correct_judge_critique_pm,
        incorrect_judge_critique_pm,
    )


def setup_debate(
    cfg: dict,
    cache_dir: Path,
    api_handler: ModelAPI,
) -> RolloutBase:
    assert cfg.rollout.name1 != cfg.rollout.name2

    correct_judge_BoN = (
        create_judge(cfg.method, cfg.correct_preference, cfg.rollout, api_handler)
        if cfg.correct_debater.BoN > 1
        else None
    )
    incorrect_judge_BoN = (
        create_judge(cfg.method, cfg.incorrect_preference, cfg.rollout, api_handler)
        if cfg.incorrect_debater.BoN > 1
        else None
    )
    correct_judge_critic = (
        create_judge(cfg.method, cfg.correct_critic, cfg.rollout, api_handler)
        if cfg.correct_debater.cBoN > 0
        else None
    )
    incorrect_judge_critic = (
        create_judge(cfg.method, cfg.incorrect_critic, cfg.rollout, api_handler)
        if cfg.incorrect_debater.cBoN > 0
        else None
    )
    correct_judge_critique_pm = (
        create_judge(cfg.method, cfg.correct_critique_pm, cfg.rollout, api_handler)
        if cfg.correct_debater.cBoN > 0
        else None
    )
    incorrect_judge_critique_pm = (
        create_judge(cfg.method, cfg.incorrect_critique_pm, cfg.rollout, api_handler)
        if cfg.incorrect_debater.cBoN > 0
        else None
    )

    if cfg.method == "debate" or cfg.method == "baseline":
        correct_debater = create_debater(
            cfg.method,
            cfg.correct_debater,
            correct=True,
            api_handler=api_handler,
        )
        incorrect_debater = create_debater(
            cfg.method, cfg.incorrect_debater, correct=False, api_handler=api_handler
        )

    if cfg.method == "consultancy":
        if cfg.method_type == "correct":
            correct_debater = create_debater(
                cfg.method,
                cfg.correct_debater,
                correct=True,
                api_handler=api_handler,
            )
            incorrect_debater = None

        elif cfg.method_type == "incorrect":
            correct_debater = None
            incorrect_debater = create_debater(
                cfg.method,
                cfg.incorrect_debater,
                correct=False,
                api_handler=api_handler,
            )
        else:
            raise ValueError(f"Unknown method type: {cfg.method_type}")

    if cfg.use_intermediary:
        cross_examiner = create_judge(
            cfg.method,
            cfg.cross_examiner,
            cfg.rollout,
            api_handler,
        )
    else:
        cross_examiner = None

    rollout = create_rollout(
        cfg.method,
        cfg.rollout,
        cache_dir,
        correct_debater,
        incorrect_debater,
        cross_examiner,
        correct_judge_BoN,
        incorrect_judge_BoN,
        correct_judge_critic,
        incorrect_judge_critic,
        correct_judge_critique_pm,
        incorrect_judge_critique_pm,
    )
    if correct_debater:
        LOGGER.info(cfg.correct_debater.language_model)
    if incorrect_debater:
        LOGGER.info(cfg.incorrect_debater.language_model)
    if cross_examiner:
        LOGGER.info(cfg.cross_examiner.language_model)
    return rollout


def setup_judge(
    cfg: DictConfig,
    judge_cfg: DictConfig,
    api_handler: ModelAPI,
):
    judge = create_judge(cfg.method, judge_cfg, cfg.rollout, api_handler)
    return judge
