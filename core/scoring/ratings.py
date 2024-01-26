import os
from pathlib import Path

import fire
import pandas as pd

from core.scoring.trueskill import get_elo_ratings, get_trueskill_ratings


def find_match_dirs(exp_dir: str):
    exp_dir = Path(exp_dir)
    return [x for x in exp_dir.iterdir() if x.is_dir()]


def clean_df(df):
    df = df[df.iloc[:, 0] != df.columns[0]]

    df.loc[:, "accuracy"] = df["accuracy"].astype(float)

    if "num_matches" not in df.columns:
        df.loc[:, "num_matches"] = int(150)

    df.loc[:, "num_matches"] = df["num_matches"].astype(int)
    return df


def main(tournament_dir: Path = None, judge_name: str = None, dir_name: str = "xp"):
    playoffs = []

    # TODO: support different playtypes
    xp_dir = Path(tournament_dir) / dir_name

    for match_dir in find_match_dirs(xp_dir):
        player_info = match_dir / "debaters.txt"
        results = match_dir / "results.csv"

        if not os.path.exists(results) or not os.path.exists(player_info):
            print(f"skipping {match_dir}")
            continue

        with open(player_info) as f:
            debaters = f.read().splitlines()
        debater1, debater2 = debaters

        debater1 = debater1.replace("normal", "claude")
        debater2 = debater2.replace("normal", "claude")

        debater1 = debater1.replace("fs", "Fs")
        debater2 = debater2.replace("fs", "Fs")

        if debater1 == "claude":
            debater1 = "claude_BoN1"
        if debater2 == "claude":
            debater2 = "claude_BoN1"

        if debater1 == "claude_BoN8_td3":
            debater1 = "claude_BoN8_gpt4b"
        if debater2 == "claude_BoN8_td3":
            debater2 = "claude_BoN8_gpt4b"

        df = pd.read_csv(results)
        df = clean_df(df)

        df.drop_duplicates(inplace=True, keep="last")

        if judge_name is not None:
            df = df[(df["model"] == judge_name)]
            assert len(df) > 0, f"no matches found for judge {judge_name}"
        win_rate = df.groupby("seed")["accuracy"].mean()
        num_matches = df.groupby("seed")["num_matches"].sum()

        win_rate = win_rate.mean()
        num_matches = num_matches.sum()

        playoffs.append((debater1, debater2, win_rate, num_matches))

    # aggregate matches in playoffs
    debaters = set([x[0] for x in playoffs] + [x[1] for x in playoffs])
    new_playoffs = []
    for debater1 in debaters:
        # get debater1
        debater1_matches = [x for x in playoffs if debater1 == x[0]]
        opponents = list(set([x[1] for x in debater1_matches]))
        for debater2 in opponents:
            if debater1 == debater2:  # skip self-play
                continue
            debater1_debater2_matches = [
                x for x in debater1_matches if debater2 == x[1]
            ]

            # aggregate win rate and num_matches
            _win_rate = sum([x[2] for x in debater1_debater2_matches]) / len(
                debater1_debater2_matches
            )
            _num_matches = sum([x[3] for x in debater1_debater2_matches])
            new_playoffs.append((debater1, debater2, _win_rate, _num_matches))

    # for logging
    for debater1, debater2, win_rate, num_matches in new_playoffs:
        print(f"{debater1} vs {debater2}: {win_rate}, {num_matches}")

    playoffs = new_playoffs

    # Plot Accuracy
    data = playoffs

    # Elo
    seperate_data = [
        (x[0] + "_correct", x[1] + "_incorrect", x[2], x[3]) for x in playoffs
    ]

    elo = get_elo_ratings(data)
    sep_elo = get_elo_ratings(seperate_data)

    # Seperate Elo
    ts = get_trueskill_ratings(data)
    sep_ts = get_trueskill_ratings(seperate_data)

    # add uncertainty to each elo rating = 0
    elo = {debater: [rating, 0] for debater, rating in elo.items()}
    sep_elo = {debater: [rating, 0] for debater, rating in sep_elo.items()}

    ts = {debater: [rating.mu, rating.sigma] for debater, rating in ts.items()}
    sep_ts = {debater: [rating.mu, rating.sigma] for debater, rating in sep_ts.items()}

    elo = pd.DataFrame.from_dict(
        elo, columns=["rating", "uncertainty"], orient="index"
    ).reset_index()
    sep_elo = pd.DataFrame.from_dict(
        sep_elo, columns=["rating", "uncertainty"], orient="index"
    ).reset_index()
    ts = pd.DataFrame.from_dict(
        ts, columns=["rating", "uncertainty"], orient="index"
    ).reset_index()
    sep_ts = pd.DataFrame.from_dict(
        sep_ts, columns=["rating", "uncertainty"], orient="index"
    ).reset_index()

    # lets tidy up some of the columns
    elo["position"] = "aggregate"
    ts["position"] = "aggregate"

    # make new column position which is the final _ from 'index'
    sep_elo["position"] = sep_elo["index"].map(lambda x: x.split("_")[-1])

    sep_elo["index"] = sep_elo["index"].map(
        lambda x: x.replace("_incorrect", "").replace("_correct", "")
    )

    sep_ts["position"] = sep_ts["index"].map(lambda x: x.split("_")[-1])

    sep_ts["index"] = sep_ts["index"].map(
        lambda x: x.replace("_incorrect", "").replace("_correct", "")
    )

    elo = elo.rename(columns={"rating": "elo"})
    sep_elo = sep_elo.rename(columns={"rating": "elo"})

    ts = ts.rename(columns={"rating": "ts"})
    sep_ts = sep_ts.rename(columns={"rating": "ts"})

    # pivot dataframe so that we have a column for each method
    df_elo = pd.merge(
        sep_elo[sep_elo["position"] == "correct"],
        sep_elo[sep_elo["position"] == "incorrect"],
        on=["index"],
        suffixes=("_correct", "_incorrect"),
    )
    df_elo = pd.merge(elo, df_elo, on=["index"], suffixes=("_agg", "_sep"))

    df_ts = pd.merge(
        sep_ts[sep_ts["position"] == "correct"],
        sep_ts[sep_ts["position"] == "incorrect"],
        on=["index"],
        suffixes=("_correct", "_incorrect"),
    )
    df_ts = pd.merge(ts, df_ts, on=["index"], suffixes=("_agg", "_sep"))
    df = pd.merge(df_elo, df_ts, on=["index"], suffixes=("_elo", "_ts"))

    df = df.rename(columns={"index": "model"})

    if judge_name is None:
        judge_name = "all"
    df["judge_rating_model"] = judge_name
    df.to_csv(
        f"{tournament_dir}/ratings_{judge_name}.csv", index=False, encoding="utf-8"
    )


if __name__ == "__main__":
    fire.Fire(main)
