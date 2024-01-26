import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import hydra
import pandas as pd
from omegaconf import DictConfig

from core.create_agents import setup_debate, setup_judge
from core.file_handler import ConsultantType, DebateType, Experiment, Method
from core.llm_api.llm import ModelAPI
from core.load.quality import main as quality_loader
from core.utils import setup_environment

LOGGER = logging.getLogger(__name__)


@hydra.main(version_base=None, config_path="config/", config_name="config")
def main(cfg: DictConfig):
    asyncio.run(async_main(cfg))


async def async_main(cfg: DictConfig):
    setup_environment(
        logger_level=cfg.logging,
        anthropic_tag=cfg.anthropic_tag,
        openai_tag=cfg.openai_tag,
    )
    api_handler = ModelAPI(
        anthropic_num_threads=cfg.anthropic_num_threads,
        openai_fraction_rate_limit=cfg.openai_fraction_rate_limit,
        print_prompt_and_response=cfg.print_prompt_and_response,
        organization=cfg.organization,
    )
    if cfg.method_type == "seq":
        assert (
            cfg.rollout.rollout_type == "quality_seq"
        ), "You didn't set the right rollout config for sequential!"

    if cfg.exp_dir is None:
        date = datetime.now().strftime("%y-%m-%d")
        exp_dir = Path(f"./data/{date}_main")
    else:
        exp_dir = Path(cfg.exp_dir)

    exp_dir.mkdir(parents=True, exist_ok=True)

    experiment = Experiment(
        exp_dir,
        cfg.method,
        cfg.method_type,
        cfg.use_intermediary,
    )
    # Load dataset
    filename = experiment.get_debate_filename(seed=0, swap=False)
    filename.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = filename.parent / f"cache_{filename.stem}"
    if not filename.exists():
        await quality_loader(
            filename,
            split=cfg.split,
            max_tokens=cfg.max_tokens_story,
            limit=cfg.limit,
            sources=cfg.sources,
            difficulty=cfg.difficulty,
            ignore_nyu=cfg.ignore_nyu,
            minimize_story_duplication=cfg.minimize_story_duplication,
            max_answerability=cfg.max_answerability,
            min_untimed_accuracy=cfg.min_untimed_accuracy,
            max_speed_accuracy=cfg.max_speed_accuracy,
            min_context_required=cfg.min_context_required,
            skip_conflicting_labels=cfg.skip_conflicting_labels,
            max_num_from_same_story=cfg.max_num_from_same_story,
        )

    rollout = setup_debate(
        cfg,
        cache_dir,
        api_handler,
    )

    judge = setup_judge(
        cfg,
        cfg.judge,
        api_handler,
    )

    if rollout.config.rollout_type == "quality_seq":
        swap_rollout = cfg.swap
    else:
        swap_rollout = False

    # load data
    df = pd.read_csv(filename)
    row = df.iloc[cfg.index]

    result = await rollout.run(cfg.index, row, swap=swap_rollout)
    row["transcript"] = result["transcript"]

    result = await judge.make_decision(cfg.index, row, swap=cfg.swap)
    judgement = result["judgement"]
    print(judgement)

    if result["complete"]:
        shutil.rmtree(cache_dir)


if __name__ == "__main__":
    main()
