import logging
import re
from pathlib import Path

import hydra
import numpy as np
import pandas as pd
from omegaconf import DictConfig

from core.file_handler import Experiment
from core.scoring.accuracy import get_complete_rows

UNKNOWN_THRESHOLD = 20
LOGGER = logging.getLogger(__name__)


def func_conceded(judgement):
    judgement = judgement.strip()
    if judgement == "Y":
        return True
    elif judgement == "N":
        return False
    else:
        return "Unknown"


def get_concessions(df, n_votes=1, verbose=False):
    if not isinstance(df, pd.DataFrame):
        df = pd.read_csv(df, encoding="utf-8")

    full = len(df)
    conceded_columns = []

    for n_vote in range(n_votes):
        n_vote = n_vote if n_vote > 0 else ""
        complete_column = f"complete_concession{n_vote}"
        judge_column = f"answer_concession{n_vote}"
        conceded_column = f"conceded{n_vote}"
        conceded_columns.append(conceded_column)

        df = get_complete_rows(df, complete_column)
        df[conceded_column] = df[judge_column].apply(func_conceded)

        if verbose:
            concessions = (df[conceded_column] == True).sum() / full
            print(f"Concessions {n_vote}: {concessions}")

    df_tmp = df.copy()
    df_tmp["conceded_true_count"] = df_tmp[conceded_columns].apply(
        lambda row: (row == True).sum(), axis=1
    )
    df_tmp["conceded_false_count"] = df_tmp[conceded_columns].apply(
        lambda row: (row == False).sum(), axis=1
    )
    df_tmp["conceded_voted"] = (
        df_tmp["conceded_true_count"] > df_tmp["conceded_false_count"]
    )

    count_unknown = (df_tmp[conceded_columns] == "Unknown").sum().sum()

    concessions = (df_tmp["conceded_voted"] == True).sum() / full

    return concessions, count_unknown, full, df


def score_file(
    filename: Path,
    swap: bool = False,
    method: str = None,
    model: str = None,
    dataset: str = None,
    results_file: Path = None,
    resave_df: bool = False,
    verbose: bool = False,
    n_votes: int = 1,
):
    concessions, count_unknown, total, df = get_concessions(
        filename, n_votes=n_votes, verbose=verbose
    )
    unknown_proportion = 100 * count_unknown / total / n_votes

    print(f"{unknown_proportion} unknown proportion ({count_unknown} out of {total}))")

    results = pd.DataFrame(
        {
            "method": [method],
            "concessions": [concessions],
            "dataset": [dataset],
            "model": [model],
            "swap": [swap],
            "n_votes": [n_votes],
            "unknown_proportion": [unknown_proportion],
            "num_matches": [total],
        }
    )
    if verbose:
        print(results.round(3).to_markdown(index=False))
    if results_file is not None:
        results.to_csv(results_file, mode="a", header=False, index=False)
    if resave_df:
        df.to_csv(filename, index=False)
    return results


@hydra.main(version_base=None, config_path="../config/", config_name="config")
def main(
    cfg: DictConfig,
):
    verbose = cfg.logging == "DEBUG"
    exp_dir = Path(cfg.exp_dir)
    experiment = Experiment(
        exp_dir,
        cfg.method,
        cfg.method_type,
        cfg.use_intermediary,
    )
    filename_judgement = experiment.get_judge_filename(
        cfg.judge_name, seed=cfg.seed, swap=False
    )
    filename_swap_judgement = experiment.get_judge_filename(
        cfg.judge_name, seed=cfg.seed, swap=True
    )
    results_file = exp_dir / "concessions.csv"

    dfs = []
    for filename, swap in zip(
        [filename_judgement, filename_swap_judgement], [False, True]
    ):
        df = score_file(
            filename,
            swap=swap,
            method=cfg.method,
            model=cfg.judge_name,
            dataset=cfg.dataset,
            n_votes=cfg.n_votes,
        )
        dfs.append(df)

    df = pd.concat(dfs)
    df["method"] = str(experiment)
    df["method_type"] = cfg.method
    df["debate_type"] = cfg.method_type if cfg.method == "debate" else None
    df["consultant_type"] = cfg.method_type if cfg.method == "consultancy" else None
    df["use_intermediary"] = cfg.use_intermediary
    df["seed"] = cfg.seed
    df["exp_suffix"] = ""  # for legacy

    if verbose:
        print(df.to_markdown())
    df.to_csv(results_file, mode="a", index=False)


if __name__ == "__main__":
    main()
