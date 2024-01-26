import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import List

import fire
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from core.rollouts.utils import TranscriptConfig
from core.scoring.accuracy import get_accuracy
from web.backend.services.parser import TranscriptParser


def consistent_hash(data):
    return hashlib.md5(str(data).encode()).hexdigest()


# name, exp_dir, match_type
ExperimentDirectory = tuple[str, Path, str]


def main(
    exp_dirs: List[ExperimentDirectory] = None,
    judge_name: str = "gpt-4",
    fig_dir: str = "figures",
    keep_sides_separate: bool = False,
):
    all_data = []
    os.makedirs(fig_dir, exist_ok=True)

    data_id = consistent_hash(tuple(exp_dirs))
    data_path = f"data/quotes_cache_{data_id}.csv"
    if os.path.exists(data_path):
        data_df = pd.read_csv(data_path)
    else:
        for name, exp_dir, match_type in exp_dirs:
            csv_no_swap = Path(exp_dir) / f"debate_sim/{judge_name}/data0_judgement.csv"
            csv_swap = (
                Path(exp_dir) / f"debate_sim/{judge_name}/data0_swap_judgement.csv"
            )
            if not os.path.exists(csv_no_swap):
                csv_no_swap = (
                    Path(exp_dir) / f"debate_sim/{judge_name}-new/data0_judgement.csv"
                )
                csv_swap = (
                    Path(exp_dir)
                    / f"debate_sim/{judge_name}-new/data0_swap_judgement.csv"
                )

            for csv, swap in zip([csv_no_swap, csv_swap], [False, True]):
                df = pd.read_csv(csv)
                _, _, _, _, df = get_accuracy(df, swap=swap)

                for index, row in df.iterrows():
                    transcript = TranscriptConfig(**json.loads(row.transcript))
                    _, quotes_info_strict = TranscriptParser.verify_strict(
                        deepcopy(transcript)
                    )
                    transcript2 = TranscriptParser.add_missing_quote_tags(
                        deepcopy(transcript)
                    )
                    _, quotes_info = TranscriptParser.verify(transcript2)

                    for debater_side in ["correct", "incorrect"]:
                        num_words_arguments = sum(
                            [
                                len(transcript.rounds[i].dict()[debater_side].split())
                                for i in range(len(transcript.rounds))
                            ]
                        )
                        nrm_quotes = [
                            TranscriptParser.normalize_text(q)
                            for q in quotes_info[debater_side]["quotes"]
                        ]
                        if not swap:
                            judge_decision = "A" if row.correct else "B"
                        else:
                            judge_decision = "B" if row.correct else "A"
                        gold_label = "A" if not swap else "B"
                        if match_type == "xp":
                            name_processed = (
                                name.split("_vs_")[0]
                                if debater_side == "correct"
                                else name.split("_vs_")[1]
                            )
                        else:
                            name_processed = name

                        all_data.append(
                            {
                                "question_id": index,
                                "swap": swap,
                                "name": name_processed,
                                "side": debater_side,
                                "debater_name": transcript.names.dict()[debater_side],
                                "debater_letter": transcript.names.dict()[
                                    debater_side
                                ].replace("Debater ", ""),
                                "sim_values_mean": np.mean(
                                    quotes_info[debater_side]["sim_values"]
                                ),
                                "sim_values_sum": sum(
                                    quotes_info[debater_side]["sim_values"]
                                ),
                                "num_quotes": len(quotes_info[debater_side]["quotes"]),
                                "num_words": sum(
                                    [
                                        len(q.split())
                                        for q in quotes_info[debater_side]["quotes"]
                                    ]
                                ),
                                "num_verified": len(
                                    quotes_info_strict[debater_side]["verified_quotes"]
                                ),
                                "num_unverified": len(
                                    quotes_info_strict[debater_side][
                                        "unverified_quotes"
                                    ]
                                ),
                                "num_verified_words": sum(
                                    [
                                        len(q.split())
                                        for q in quotes_info_strict[debater_side][
                                            "verified_quotes"
                                        ]
                                    ]
                                ),
                                "num_unverified_words": sum(
                                    [
                                        len(q.split())
                                        for q in quotes_info_strict[debater_side][
                                            "unverified_quotes"
                                        ]
                                    ]
                                ),
                                "num_fake_quotes": len(
                                    [
                                        q
                                        for q, sim in zip(
                                            quotes_info[debater_side]["quotes"],
                                            quotes_info[debater_side]["sim_values"],
                                        )
                                        if sim == 0 and len(q.split()) > 7
                                    ]
                                ),
                                "num_duplicates": len(nrm_quotes)
                                - len(set(nrm_quotes)),
                                "num_words_arguments": num_words_arguments,
                                "judge_correct": bool(row.correct),
                                "judge_decision": judge_decision,
                                "gold_label": gold_label,
                            }
                        )
        df = pd.DataFrame(all_data)
        df["no_quote_tags"] = (
            df["num_quotes"] - df["num_verified"] - df["num_unverified"]
        )

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        df_summed = df.groupby(["name", "side"])[numeric_cols].sum().reset_index()
        df_mean = df.groupby(["name", "side"])[numeric_cols].mean().reset_index()
        df_mean["sim_values_mean"] = (
            df_summed["sim_values_sum"] / df_summed["num_quotes"]
        )
        df_mean["num_words_per_quote"] = (
            df_summed["num_words"] / df_summed["num_quotes"]
        )
        data_df = df_mean
        data_df.to_csv(data_path, index=False)

    # Convert dictionary to DataFrame
    name_col = "name" if not keep_sides_separate else "name_with_side"
    data_df["name_with_side"] = data_df["name"] + " (" + data_df["side"] + ")"
    data_df.sort_values(["side", name_col], ascending=False, inplace=True)

    # drop columns which aren't numeric
    data_df = data_df[
        [
            name_col,
            "num_quotes",
            "num_verified",
            "num_unverified",
            "no_quote_tags",
            "num_fake_quotes",
            "num_duplicates",
            "sim_values_mean",
            "num_words_per_quote",
            "num_words_arguments",
        ]
    ]
    data_df = data_df.groupby(name_col).mean()
    data_df.reset_index(inplace=True)

    # Calculate the bottom for each stack directly in the DataFrame
    data_df["verified_bottom"] = data_df["num_verified"]
    data_df["unverified_bottom"] = (
        data_df["verified_bottom"] + data_df["num_unverified"]
    )

    # Plotting the data
    fig, ax = plt.subplots(figsize=(10, 7))
    columnwidth = 0.5
    color = sns.color_palette("pastel")

    ax.bar(
        data_df[name_col],
        data_df["num_quotes"],
        label="total",
        color=color[4],
        width=columnwidth,
        edgecolor="black",
        linewidth=1,
    )

    bottom = 0
    for i, column in enumerate(["num_verified", "num_unverified", "no_quote_tags"]):
        ax.bar(
            data_df[name_col],
            data_df[column],
            label=column.replace("num_", "").replace("_", " "),
            color=color[i],
            bottom=bottom,
            width=columnwidth,
            linewidth=1,
            edgecolor="black",
        )
        bottom += data_df[column]

    # Adding labels and title
    ax.set_ylabel("Average Number of Quotes")
    ax.set_title(
        "Average Number of Quotes by Across both Correct and Incorrect Debater For Different Prompts"
    )
    plt.subplots_adjust(bottom=0.2)

    ax.legend(loc="lower right")
    ax.set_ylim([0, data_df["num_quotes"].max() * 1.2])

    # rotate axis labels
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right", rotation_mode="anchor")

    # Display the plot
    plt.savefig(f"{fig_dir}/num_quotes.png", dpi=300, bbox_inches="tight")

    # Data for the additional categories
    categories = [
        "num_fake_quotes",
        "num_duplicates",
        "num_words_per_quote",
        "num_words_arguments",
    ]

    # Create a 2x2 grid of subplots with separate y axes
    fig, axs = plt.subplots(2, 2, figsize=(16, 16))

    # Flatten the axis array for easy iteration
    axs = axs.flatten()

    # Plot each category with its own y-axis
    for i, category in enumerate(categories):
        axs[i].bar(
            data_df[name_col],
            data_df[category],
            color=sns.color_palette("pastel"),
            linewidth=2,
            edgecolor="black",
        )
        axs[i].set_title(category)
        axs[i].set_ylabel("Average Values")
        axs[i].set_ylim(
            [0, data_df[category].max() * 1.2]
        )  # Set y limit with some padding

        # rotate axis labels
        plt.setp(
            axs[i].get_xticklabels(), rotation=20, ha="right", rotation_mode="anchor"
        )

    plt.savefig(f"{fig_dir}/additional_categories.png", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    fire.Fire(main)
