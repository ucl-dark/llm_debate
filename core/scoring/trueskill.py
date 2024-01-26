import math
from random import shuffle

import numpy as np
import trueskill
from scipy.optimize import minimize

# data = [debater1, debater2, win_rate, num_matches]


def expected_win_rate_elo(r1, r2):
    """Compute the expected win rate for player 1 against player 2 based on Elo ratings."""
    return 1.0 / (1 + 10 ** ((r2 - r1) / 400))


def cost_elo(ratings, data):
    """Squared error cost between the predicted win rate based on Elo and the actual win rate."""
    cost = 0
    for debater1, debater2, win_rate, num_matches in data:
        predicted_win_rate = expected_win_rate_elo(ratings[debater1], ratings[debater2])
        cost += (predicted_win_rate - win_rate) ** 2
    return cost


def get_elo_ratings(data):
    unique_debaters = list(set([item[0] for item in data] + [item[1] for item in data]))
    ratings = {
        debater: 1500
        for debater in set([item[0] for item in data] + [item[1] for item in data])
    }

    result = minimize(
        lambda x: cost_elo(dict(zip(unique_debaters, x)), data),
        list(ratings.values()),
        method="Nelder-Mead",
    )

    optimized_ratings = dict(zip(unique_debaters, result.x))
    return optimized_ratings


def get_trueskill_ratings(data):
    # TrueSkill
    matches = []
    num_repeats = 10
    print("TrueSkill randomised over {} repeats".format(num_repeats))
    trueskill.setup(draw_probability=0.0)

    # min_num_matches = min([item[2] * item[3] for item in data])
    # print("Minimum number of matches: {}".format(min_num_matches))
    for debater1, debater2, win_rate, num_matches in data:
        wins_debater1 = int(win_rate * num_matches)
        wins_debater2 = num_matches - wins_debater1
        matches = (
            matches
            + [(debater1, debater2)] * wins_debater1
            + [(debater2, debater1)] * wins_debater2
        )

    aggregate_ratings = []

    for _ in range(10):
        shuffle(matches)

        ratings = {
            debater: trueskill.Rating()
            for debater in set([item[0] for item in data] + [item[1] for item in data])
        }

        # Update ratings for each match
        for debater1, debater2 in matches:
            ratings[debater1], ratings[debater2] = trueskill.rate_1vs1(
                ratings[debater1], ratings[debater2]
            )

        aggregate_ratings.append(ratings)

    for debater in ratings:
        ratings[debater] = trueskill.Rating(
            mu=np.mean([rating[debater].mu for rating in aggregate_ratings]),
            sigma=np.sqrt(
                np.mean([rating[debater].sigma ** 2 for rating in aggregate_ratings])
            ),
        )

    return ratings


def win_probability(player1, player2):
    delta_mu = player1.mu - player2.mu
    sum_sigma = player1.sigma**2 + player2.sigma**2
    denom = math.sqrt(2 * (trueskill.BETA * trueskill.BETA) + sum_sigma)
    ts = trueskill.global_env()
    return ts.cdf(delta_mu / denom)
