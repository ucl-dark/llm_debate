import os
from pathlib import Path

import fire

from core.tournament import main as tournament_main

CONFIG_DIR = os.path.dirname(os.path.realpath(__file__)) + "/tournament_players"

DEBATE_CONFIGS_FILES = [
    (
        "gpt3.5_Bo1",
        Path(f"{CONFIG_DIR}/gpt_3_5_Bo1.yaml"),
        {},
    ),
    (
        "gpt3.5_Bo2",
        Path(f"{CONFIG_DIR}/gpt_3_5_Bo2.yaml"),
        {},
    ),
    (
        "gpt3.5_Bo4",
        Path(f"{CONFIG_DIR}/gpt_3_5_Bo4.yaml"),
        {},
    ),
    (
        "gpt3.5_Bo8",
        Path(f"{CONFIG_DIR}/gpt_3_5_Bo8.yaml"),
        {},
    ),
    (
        "gpt3.5_Bo16",
        Path(f"{CONFIG_DIR}/gpt_3_5_Bo16.yaml"),
        {},
    ),
    (
        "claude1.3_Bo1",
        Path(f"{CONFIG_DIR}/claude_1_3_Bo1.yaml"),
        {},
    ),
    (
        "claude2.1_Bo1",
        Path(f"{CONFIG_DIR}/claude_2_1_Bo1.yaml"),
        {},
    ),
    (
        "claude2.1_Co2",
        Path(f"{CONFIG_DIR}/claude_2_1_Co2.yaml"),
        {
            "critic": Path("core/config/experiment/critic/debate/critic_story.yaml"),
            "critique_pm": Path(
                "core/config/experiment/critic/debate/critique_pm_story.yaml"
            ),
        },
    ),
    (
        "claude2.1_Co16",
        Path(f"{CONFIG_DIR}/claude_2_1_Co16.yaml"),
        {
            "critic": Path(
                "core/config/experiment/critic/debate/critic_story_higher_temp.yaml"
            ),
            "critique_pm": Path(
                "core/config/experiment/critic/debate/critique_pm_story.yaml"
            ),
        },
    ),
    (
        "claude2.1_Bo4",
        Path(f"{CONFIG_DIR}/claude_2_1_Bo4.yaml"),
        {},
    ),
    (
        "claude2.1_Bo8",
        Path(f"{CONFIG_DIR}/claude_2_1_Bo8.yaml"),
        {},
    ),
    (
        "claude2.1_Bo16",
        Path(f"{CONFIG_DIR}/claude_2_1_Bo16.yaml"),
        {},
    ),
    (
        "claude2.1_Bo4_Co8",
        Path(f"{CONFIG_DIR}/claude_2_1_Bo4_Co8.yaml"),
        {
            "critic": Path(
                "core/config/experiment/critic/debate/critic_story_higher_temp.yaml"
            ),
            "critique_pm": Path(
                "core/config/experiment/critic/debate/critique_pm_story.yaml"
            ),
        },
    ),
    (
        "gpt4t_Bo1",
        Path(f"{CONFIG_DIR}/gpt_4_t_Bo1.yaml"),
        {},
    ),
    (
        "gpt4t_Bo4",
        Path(f"{CONFIG_DIR}/gpt_4_t_Bo4.yaml"),
        {},
    ),
    (
        "gpt4t_Co16",
        Path(f"{CONFIG_DIR}/gpt_4_t_Co16.yaml"),
        {
            "critic": Path(
                "core/config/experiment/critic/debate/critic_story_higher_temp.yaml"
            ),
            "critique_pm": Path(
                "core/config/experiment/critic/debate/critique_pm_story.yaml"
            ),
        },
    ),
    (
        "gpt4t_Bo4_Co8",
        Path(f"{CONFIG_DIR}/gpt_4_t_Bo4_Co8.yaml"),
        {
            "critic": Path(
                "core/config/experiment/critic/debate/critic_story_higher_temp.yaml"
            ),
            "critique_pm": Path(
                "core/config/experiment/critic/debate/critique_pm_story.yaml"
            ),
        },
    ),
    (
        "gpt4t_Bo8",
        Path(f"{CONFIG_DIR}/gpt_4_t_Bo8.yaml"),
        {},
    ),
    (
        "gpt4t_Bo16",
        Path(f"{CONFIG_DIR}/gpt_4_t_Bo16.yaml"),
        {},
    ),
    (
        "gpt4t_Bo32",
        Path(f"{CONFIG_DIR}/gpt_4_t_Bo32.yaml"),
        {},
    ),
]


JUDGE_CONFIG_FILES = [
    (
        "gpt-4-1106-preview",
        "gpt-4-1106-preview",
        Path("./core/config/experiment/judge/debate/default.yaml"),
    ),
]


def main(
    tournament_dir: Path,
    method: str,
    anthropic_num_threads: int = 1,
):
    if method == "sp":
        match_up_type = "self-play"
        # T_l dataset
        max_num_from_same_story = 5
        dataset_split = "train"
        limit = 400
    elif method == "st":
        match_up_type = "swiss-tournament"
        # D_l dataset
        max_num_from_same_story = 5
        dataset_split = "dev"
        limit = 291
    else:
        raise ValueError(f"method {method} not supported")

    print(f"Running {match_up_type}")

    # reverse list so strongest player first
    debaters = DEBATE_CONFIGS_FILES[::-1]

    tournament_main(
        tournament_dir=tournament_dir,
        debaters=debaters,
        judges=JUDGE_CONFIG_FILES,
        match_up_type=match_up_type,
        org="DEFAULT_ORG",
        limit=limit,
        num_threads=anthropic_num_threads,
        max_num_from_same_story=max_num_from_same_story,
        dataset_split=dataset_split,
    )


if __name__ == "__main__":
    fire.Fire(main)
