import itertools
from functools import partial
from pathlib import Path
from typing import List

import typer
from hydra import compose, initialize
from hydra.core.global_hydra import GlobalHydra
from omegaconf import OmegaConf
from tenacity import RetryError

from core.debate import main as debate_main
from core.judge import main as judge_main
from core.scoring.accuracy import main as score_main
from core.swiss_tournament import save_results, swiss_tournament

DebaterConfig = tuple[str, Path, dict]
JudgeConfig = tuple[str, str, Path]


def make_exp_dir(exp_dir: Path):
    exp_dir = Path.home() / f"results/{exp_dir}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    return exp_dir


def run_match(
    debater1,
    debater2,
    judges,
    tournament_dir,
    limit=150,
    num_steps=3,
    seed=0,
    logger_level="info",
    org="NYU",
    num_threads=80,
    max_num_from_same_story=1,
    dataset_split=["dev", "train"],
):
    name1, debater_config1, kwargs1 = debater1
    name2, debater_config2, kwargs2 = debater2

    match_dir = tournament_dir / f"{name1}_{name2}"

    print(f"Start Match:\n{name1} vs {name2}")
    match_dir.mkdir(parents=True, exist_ok=True)

    # add text file which states name of debaters
    with open(match_dir / "debaters.txt", "w") as f:
        f.write(f"{name1}\n{name2}")

    conf1 = OmegaConf.load(debater_config1)
    conf2 = OmegaConf.load(debater_config2)

    GlobalHydra.instance().clear()

    results = match_dir / "results.csv"
    match_done = results.exists() and results.stat().st_size > 0

    with initialize(version_base=None, config_path="config", job_name="debate_app"):
        cfg = compose(config_name="config")
        debate_cfg = compose(config_name="experiment/debate")
        cfg = OmegaConf.merge(cfg, debate_cfg)

        # add debater configs to match
        OmegaConf.update(cfg, "correct_debater", conf1, force_add=True)
        OmegaConf.update(cfg, "incorrect_debater", conf2, force_add=True)

        for k, v in kwargs1.items():
            conf_extra = OmegaConf.load(v)
            OmegaConf.update(cfg, f"correct_{k}", conf_extra, force_add=True)
        for k, v in kwargs2.items():
            conf_extra = OmegaConf.load(v)
            OmegaConf.update(cfg, f"incorrect_{k}", conf_extra, force_add=True)

        cfg.correct_preference.language_model.model = conf1.preference_model
        cfg.incorrect_preference.language_model.model = conf2.preference_model

        if "critic" in kwargs1:
            cfg.correct_critic.language_model.model = conf1.language_model.model
            cfg.correct_critique_pm.language_model.model = conf1.preference_model
        if "critic" in kwargs2:
            cfg.incorrect_critic.language_model.model = conf2.language_model.model
            cfg.incorrect_critique_pm.language_model.model = conf2.preference_model

        if "claude-v1.3" in [
            cfg.correct_preference.language_model.model,
            cfg.incorrect_preference.language_model.model,
        ]:
            num_threads = 30

        debate_cfg_overrides = [
            f"exp_dir={match_dir}",
            f"method_type=sim",
            f"limit={limit}",
            f"rollout.num_steps={num_steps}",
            f"logging={logger_level}",
            f"seed={seed}",
            f"organization={org}",
            f"anthropic_num_threads={num_threads}",
            f"max_num_from_same_story={max_num_from_same_story}",
            f"split={dataset_split}",
        ]

        for kv in debate_cfg_overrides:
            k, v = kv.split("=")[0], kv.split("=")[1]
            OmegaConf.update(cfg, k, v)

        if not match_done:
            debate_main(cfg)

    print(f"Finished debater:\n{name1} vs {name2}")

    for judge_name, judge_model, judge_config in judges:
        print(f"Start judge:\n{name1} vs {name2}")
        with initialize(
            version_base=None,
            config_path="config",
            job_name="judge_app",
        ):
            cfg = compose(config_name="config")
            debate_cfg = compose(config_name="experiment/debate")
            cfg = OmegaConf.merge(cfg, debate_cfg)
            judge_cfg_overrides = [
                "method=debate",
                "method_type=sim",
                f"limit={limit}",
                f"exp_dir={match_dir}",
                f"logging={logger_level}",
                f"seed={seed}",
                f"organization={org}",
                f"judge_name={judge_name}",
                f"anthropic_num_threads={num_threads}",
            ]

            for kv in judge_cfg_overrides:
                k, v = kv.split("=")[0], kv.split("=")[1]
                OmegaConf.update(cfg, k, v)

            OmegaConf.update(cfg, "judge", OmegaConf.load(judge_config), force_add=True)
            cfg.judge.language_model.model = judge_model
            if not match_done:
                judge_main(cfg)

        with initialize(version_base=None, config_path="config", job_name="score_app"):
            score_cfg_overrides = [
                "method=debate",
                "method_type=sim",
                f"limit={limit}",
                "use_intermediary=False",
                f"exp_dir={match_dir}",
                f"seed={seed}",
                f"judge_name={judge_name}",
            ]
            cfg = compose(config_name="config", overrides=score_cfg_overrides)
            wins_correct, wins_incorrect = score_main(cfg)
        return wins_correct, wins_incorrect


def main(
    tournament_dir: Path,
    debaters: List[DebaterConfig],
    judges: List[JudgeConfig],
    match_up_type: str,
    limit: int = 150,
    num_steps: int = 3,
    seed: int = 0,
    logger_level: str = "info",
    org: str = "NYU",
    num_threads: int = 80,
    max_num_from_same_story: int = 1,
    dataset_split: list = ["dev", "train"],
):
    """
    A method for running a tournament between multiple configs of debaters and judges
    """

    # generate debating pairings
    if match_up_type == "round-robin":
        debate_pairs = itertools.permutations(debaters, 2)
        dir_name = "xp"
    elif match_up_type == "first-vs-rest":
        dir_name = "fvr"
        debate_pairs1 = [(debaters[0], debater) for debater in debaters[1:]]
        debate_pairs2 = [(debater, debaters[0]) for debater in debaters[1:]]
        debate_pairs = debate_pairs1 + debate_pairs2
    elif match_up_type == "self-play":
        debate_pairs = [(debate_config, debate_config) for debate_config in debaters]
        dir_name = "sp"
    elif match_up_type == "swiss-tournament":
        dir_name = "st"
    else:
        raise ValueError(f"play_type {match_up_type} not supported")

    tournament_dir = make_exp_dir(Path(tournament_dir) / dir_name)

    if match_up_type in ["round-robin", "self-play", "first-vs-rest"]:
        for debater1, debater2 in debate_pairs:
            try:
                run_match(
                    debater1,
                    debater2,
                    judges,
                    tournament_dir,
                    limit,
                    num_steps,
                    seed,
                    logger_level,
                    org,
                    num_threads,
                    max_num_from_same_story,
                    dataset_split,
                )
            except RetryError as e:
                print(
                    f"Error occurred on debate {debater1[0]} vs {debater2[0]}. Error message: {e}."
                )
                continue
    elif match_up_type == "swiss-tournament":
        # Ensure these debaters are sorted by seed
        debaters = {debater[0]: debater for debater in debaters}
        run_function = partial(
            run_match,
            judges=judges,
            tournament_dir=tournament_dir,
            limit=limit,
            num_steps=num_steps,
            seed=seed,
            logger_level=logger_level,
            org=org,
            num_threads=num_threads,
            max_num_from_same_story=max_num_from_same_story,
            dataset_split=dataset_split,
        )
        final_ranking, scores, results = swiss_tournament(
            debaters, run_function, tournament_dir=tournament_dir
        )
        save_results(debaters, tournament_dir, final_ranking, scores, results)


if __name__ == "__main__":
    typer.run(main)
