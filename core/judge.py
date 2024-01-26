import asyncio
import logging
import random
from enum import StrEnum
from pathlib import Path
from shutil import copyfile

import hydra
import pandas as pd
from omegaconf import DictConfig

from core.agents.judge_base import JudgeBase
from core.create_agents import setup_judge
from core.file_handler import Experiment
from core.llm_api.llm import ModelAPI
from core.utils import (
    async_function_with_retry,
    delete_old_prompt_files,
    setup_environment,
)

LOGGER = logging.getLogger(__name__)


class JudgeType(StrEnum):
    default = "judge"
    concession = "concession"


async def run_judge(
    judge: JudgeBase,
    filename: Path,
    anthropic_num_threads: int = 5,
    round_limit: int = None,
    limit: int = None,
    swap: bool = False,
    n_vote: int = 0,
    judge_type: JudgeType = JudgeType.default,
):
    # load data
    full_df = pd.read_csv(filename)
    if limit is not None:
        full_df = full_df.head(int(limit))
    assert full_df[
        "complete"
    ].all(), "Not all values in the column 'complete' are True, rerun debate"

    # majority voting setup
    n_vote_str = n_vote if n_vote > 0 else ""
    complete_column = f"complete_{judge_type}{n_vote_str}"
    judge_column = f"answer_{judge_type}{n_vote_str}"
    if complete_column not in full_df.columns:
        full_df[complete_column] = False
        full_df[judge_column] = ""
    # filter out rows that have already been completed
    df = full_df[full_df[complete_column] == False]

    LOGGER.info(f"Using column {complete_column}")
    LOGGER.info(f"Using file {filename}")
    LOGGER.info(f"Processing {len(df)} rows")
    if round_limit is not None:
        LOGGER.info(f"Using round limit {round_limit}")

    async def bounded_run(sem, index, row, swap, round_limit):
        async with sem:
            return await judge.make_decision(index, row, swap, round_limit)

    sem = asyncio.Semaphore(int(anthropic_num_threads))
    tasks = [
        bounded_run(sem, index, row, swap, round_limit) for index, row in df.iterrows()
    ]
    results = await asyncio.gather(*tasks)

    correct = sum([bool(result["complete"]) for result in results])
    LOGGER.info(f"Processed {len(results)} rows. {correct} were complete.")

    df.update(
        pd.DataFrame(
            {
                judge_column: [result["judgement"] for result in results],
                complete_column: [result["complete"] for result in results],
            },
            index=df.index,
        )
    )
    # some judgments apply swap to the transcript so return a new one
    if results and "transcript" in results[0]:
        df.update(
            pd.DataFrame(
                {
                    "transcript": [result["transcript"] for result in results],
                },
                index=df.index,
            )
        )
    full_df.update(df)

    full_df.to_csv(filename, index=False)
    if full_df[complete_column].eq(True).all():
        return True
    else:
        return False


@hydra.main(version_base=None, config_path="config/", config_name="config")
def main(cfg: DictConfig):
    complete = asyncio.run(async_main(cfg))
    return complete


async def async_main(cfg: DictConfig):
    setup_environment(
        logger_level=cfg.logging,
        anthropic_tag=cfg.anthropic_tag,
        openai_tag=cfg.openai_tag,
    )
    random.seed(cfg.seed)

    delete_old_prompt_files()
    api_handler = ModelAPI(
        anthropic_num_threads=cfg.anthropic_num_threads,
        openai_fraction_rate_limit=cfg.openai_fraction_rate_limit,
        print_prompt_and_response=cfg.print_prompt_and_response,
        organization=cfg.organization,
    )

    exp_dir = Path(cfg.exp_dir)
    exp_dir.mkdir(parents=True, exist_ok=True)

    experiment = Experiment(
        exp_dir,
        cfg.method,
        cfg.method_type,
        cfg.use_intermediary,
    )
    if cfg.judge_type == JudgeType.concession:
        cfg.judge = cfg.concession_judge

    judge = setup_judge(
        cfg,
        cfg.judge,
        api_handler,
    )
    if cfg.judge_name is None:
        cfg.judge_name = judge.config.language_model.model
        LOGGER.info(f"Judge name not specified, using {cfg.judge_name}")

    # using exp_suffix to easily run differing number of rounds with judge
    exp_suffix = f"_{cfg.round_limit}rounds" if cfg.round_limit is not None else ""

    # Run swap = False
    filename = experiment.get_debate_filename(seed=cfg.seed, swap=False)
    filename_judgement = experiment.get_judge_filename(
        cfg.judge_name, seed=cfg.seed, swap=False, exp_suffix=exp_suffix
    )

    assert filename.exists(), f"{filename} does not exist"
    filename_judgement.parent.mkdir(exist_ok=True, parents=True)
    if not filename_judgement.exists():
        copyfile(filename, filename_judgement)

    complete = await async_function_with_retry(
        run_judge,
        judge,
        filename_judgement,
        anthropic_num_threads=cfg.anthropic_num_threads,
        round_limit=cfg.round_limit,
        limit=cfg.limit,
        swap=False,
        n_vote=cfg.judge.n_vote,
        judge_type=cfg.judge_type,
    )

    # Run swap = True
    filename_swap = experiment.get_debate_filename(seed=cfg.seed, swap=True)
    filename_swap_judgement = experiment.get_judge_filename(
        cfg.judge_name, seed=cfg.seed, swap=True, exp_suffix=exp_suffix
    )
    if not filename_swap_judgement.exists():
        if cfg.method_type == "seq" or (
            cfg.method == "debate" and cfg.use_intermediary
        ):
            assert (
                filename_swap.exists()
            ), f"{filename_swap} does not exist and is required for sequential (or intermediary debate)"
            copyfile(filename_swap, filename_swap_judgement)
        else:
            # If debate is seq, we insist that a swapped debate file exists. In other cases, we should still prefer using a swapped debate file if it's available.
            if filename_swap.exists():
                copyfile(filename_swap, filename_swap_judgement)
            else:
                copyfile(filename, filename_swap_judgement)

    complete_swap = await async_function_with_retry(
        run_judge,
        judge,
        filename_swap_judgement,
        anthropic_num_threads=cfg.anthropic_num_threads,
        round_limit=cfg.round_limit,
        limit=cfg.limit,
        swap=True,
        n_vote=cfg.judge.n_vote,
        judge_type=cfg.judge_type,
    )
    return complete and complete_swap


if __name__ == "__main__":
    main()
