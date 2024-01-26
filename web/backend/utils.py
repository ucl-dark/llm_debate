import hashlib
import re
import string


def load_secrets(path):
    secrets = {}
    with open(path) as f:
        for line in f:
            key, value = line.strip().split("=", 1)
            secrets[key] = value
    return secrets


def get_debate_type(path):
    """
    In "Normal" debate, ie debate0.csv, we have a transcript column where Alice is the first debater and she gives the arguments for the correct side.
    In "Alt" debate, AKA "SwapPos", ie altdebate0.csv, we have the same transcript column as Normal, and additionally an alt_transcript col that has the argument positions reversed. Alice is still giving the arguments for the correct side, but she goes second in each round
    In "Reversed" debate, AKA "SwapNames", ie debate0_reversed.csv, the transcript col has the names swapped. So now Bob goes first and is arguing for the correct side.
    In "AltReversed" debate, AKA "SwapAnswer", ie altdebate0_reversed.csv, we have the same transcript col as in "Reversed", ie with names swapped. Additionally we have an alt_transcript col, where the positions are swapped relative to Reversed. So Alice goes first but gives the arguments for the incorrect side.

    In all files, the transcript col will always have the correct arguments first in each round, with the names swapped in the reversed case.

    UPDATE: SwapNew means the Answers are swapped, but in the transcript column. Also it's a brand new debate rollout, so it doesn't make sense to associate with a normal debate. These should essentially be treated like normal debates, except Debater1 is wrong and Debater2 is right.
    """
    filename = path.split("/")[-1]
    # Returns the debate type
    if "debate" in filename:
        if "swap_" in filename:
            return "SwapNew"
        elif "altdebate" in filename and "reversed" in filename:
            return "SwapAnswer"
        elif "reversed" in filename:
            return "SwapNames"
        elif "altdebate" in filename:
            return "SwapPos"
        else:
            return "Normal"
    else:
        return None


def get_judgement_type(path):
    judgement_type = get_debate_type(path)
    if not judgement_type:
        return None

    if "_plus" in path:
        judgement_type += " Plus"

    return judgement_type


def get_judge_model(path):
    parts = path.split("/")
    # Go backwards through the parents so that the closest parent takes priority
    for part in reversed(parts):
        if "gpt-4" in part or "gpt" in part:
            return "GPT-4"
        elif "claude" in part:
            return "Claude"

    return "Unknown Model"


def create_path_hash(path):
    return hashlib.sha256(path.encode()).hexdigest()


def create_short_path_hash(path):
    return create_path_hash(path)[:8]


def create_debate_name(story_title):
    # this is pretty simple, and will not capitalize chars after hyphens. May need to upgrade
    return string.capwords(story_title)
