import json
import math
import random
from typing import Callable, Dict, List, Tuple


def pair_players(
    names: List[str], previous_matchups: Dict[str, set]
) -> List[Tuple[str, str]]:
    def can_be_paired(player1, player2):
        return player2 not in previous_matchups.get(player1, set())

    def find_pairings():
        if not unpaired_names:
            return []

        player = unpaired_names.pop(0)
        for opponent in unpaired_names:
            if can_be_paired(player, opponent):
                unpaired_names.remove(opponent)
                previous_matchups[player].add(opponent)
                previous_matchups[opponent].add(player)
                return [(player, opponent)] + find_pairings()

        # Assign a bye if no opponent is found
        print(f"Bye for {player}")
        return [(player, None)] + find_pairings()

    unpaired_names = names[:]

    return find_pairings()


def play_round(
    pairings: List[Tuple[str, str]],
    players: Dict[str, Tuple[str, str, dict]],
    run_match: Callable,
    tournament_dir: str = None,
    round_num: int = 0,
) -> List[Tuple[str, str, float]]:
    """
    Play out a round of the tournament and return results.
    """
    results = []
    for player_a, player_b in pairings:
        if player_b is None:
            # Player A gets a bye
            results.append((player_a, player_b, 1.0))  # Player A wins by default
        else:
            wins_a_correct, wins_b_incorrect = run_match(
                players[player_a], players[player_b]
            )
            wins_b_correct, wins_a_incorrect = run_match(
                players[player_b], players[player_a]
            )
            win_rate_a = (wins_a_correct + wins_a_incorrect) / (
                wins_a_correct + wins_b_incorrect + wins_a_incorrect + wins_b_correct
            )
            if win_rate_a > 0.5:
                results.append((player_a, player_b, win_rate_a))
            else:
                results.append((player_b, player_a, 1 - win_rate_a))
        # save results list as a json to tournament_dir
        if tournament_dir is not None:
            with open(f"{tournament_dir}/round{round_num+1}_win_rates.json", "w") as f:
                json.dump(results, f)
    return results


def update_scores(scores: Dict[str, int], results: List[Tuple[str, str, float]]):
    """
    Update player scores based on round results.
    """
    for winner, loser, _ in results:
        scores[winner] += 1
        if loser is not None:
            scores[loser] += 0  # Loser gets no points


def swiss_tournament(
    players: Dict[str, Tuple[str, str, dict]],
    run_match: Callable,
    tournament_dir: str = None,
) -> Tuple[List[str], Dict[str, int], List[List[Tuple[str, str, float]]]]:
    """
    Conduct a Swiss-system tournament.
    """
    player_names = list(players.keys())
    scores = {player_name: 0 for player_name in player_names}
    initial_seeding = player_names.copy()
    num_rounds = math.ceil(math.log2(len(player_names)))
    previous_matchups = {p: set() for p in player_names}
    results_all = []
    print("Number of rounds:", num_rounds)

    for round_num in range(num_rounds):
        player_names.sort(
            key=lambda p: (-scores[p], initial_seeding.index(p))
        )  # Sort by scores, then initial seed
        if tournament_dir is not None:
            with open(
                f"{tournament_dir}/round{round_num+1}_initial_order.json", "w"
            ) as f:
                json.dump(player_names, f)
        pairings = pair_players(
            list(player_names), previous_matchups
        )  # Pair players for the round
        results = play_round(
            pairings,
            players,
            run_match,
            tournament_dir=tournament_dir,
            round_num=round_num,
        )  # Play the round
        results_all.append(results)  # Save results
        update_scores(scores, results)  # Update scores
        print(f"Round {round_num+1} Scores: {scores}")
        if tournament_dir is not None:
            with open(
                f"{tournament_dir}/round{round_num+1}_final_scores.json", "w"
            ) as f:
                json.dump(scores, f)
        if round_num == 2:
            break

    # Sort players by their final scores for the final ranking
    final_ranking = sorted(player_names, key=lambda p: -scores[p])
    return final_ranking, scores, results_all


def save_results(
    players: Dict[str, Tuple[str, str, dict]],
    tournament_dir: str,
    final_ranking: List[str],
    scores: Dict[str, int],
    results: List[List[Tuple[str, str, float]]],
):
    grid = [[0 for _ in range(len(players))] for _ in range(len(players))]
    debater_names = list(players.keys())
    for i, round_results in enumerate(results):
        for winner, loser, _ in round_results:
            if loser is not None:
                winner_index = debater_names.index(winner)
                loser_index = debater_names.index(loser)
                grid[winner_index][loser_index] += 1
                grid[loser_index][winner_index] += 1

    # save results
    with open(tournament_dir / "results.txt", "w") as f:
        f.write(f"Final Ranking: {final_ranking}\n")
        f.write(f"Scores: {scores}\n")
        f.write(f"Sum of scores: {sum(scores.values())}\n")
        f.write(f"Results: {results}\n")
        f.write(",".join(debater_names) + "\n")
        f.write("\n".join(debater_names) + "\n")
        for row in grid:
            f.write(",".join(map(str, row)) + "\n")


if __name__ == "__main__":
    num_players = 8

    def dummy_run(player_a: Tuple[str, str, dict], player_b: Tuple[str, str, dict]):
        """
        Placeholder function for running a debate match between player_a and player_b.
        Returns the win rate for player A against player B.
        """
        name1, _, _ = player_a
        name2, _, _ = player_b
        # For demonstration, return a random win rate correlated with the seed difference
        seed_a = name1.split("Player")[1]
        seed_b = name2.split("Player")[1]

        seed_diff = int(seed_a) - int(seed_b)
        if seed_diff > 0:
            win_rate = (
                0.5 + 0.5 * (abs(seed_diff) / num_players) - 0.1 * random.random()
            )
        else:
            win_rate = (
                0.5 - 0.5 * (abs(seed_diff) / num_players) + 0.1 * random.random()
            )

        a_wins = int(win_rate * 300)
        b_wins = 300 - a_wins

        return a_wins, b_wins

    # Example usage
    random.seed(0)
    players = {
        f"Player{i}": (f"Player{i}", None, None) for i in range(num_players, 0, -1)
    }
    final_ranking, scores, results = swiss_tournament(players, dummy_run)
    print("Final Ranking:", final_ranking)
    print("Scores:", scores)
    print("Sum of scores:", sum(scores.values()))

    grid = [[0 for _ in range(num_players)] for _ in range(num_players)]
    for i, round_results in enumerate(results):
        print(f"Round {i+1} Results:")
        for winner, loser, win_rate in round_results:
            print(f"{winner} beat {loser} with win rate {win_rate:.2f}")
            if loser is not None:
                grid[int(winner.split("Player")[1]) - 1][
                    int(loser.split("Player")[1]) - 1
                ] += 1
                grid[int(loser.split("Player")[1]) - 1][
                    int(winner.split("Player")[1]) - 1
                ] += 1

    print("Grid of match ups:")
    for row in grid:
        print(",".join([str(x) for x in row]))
