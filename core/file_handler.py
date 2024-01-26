import random
from enum import StrEnum
from pathlib import Path

from core.utils import load_yaml_cached


class Method(StrEnum):
    debate = "debate"
    consultancy = "consultancy"
    baseline = "baseline"


class DebateType(StrEnum):
    sim = "sim"
    seq = "seq"


class BaselineType(StrEnum):
    blind = "blind"
    oracle = "oracle"


class ConsultantType(StrEnum):
    correct = "correct"
    incorrect = "incorrect"


class Experiment:
    def __init__(
        self,
        exp_dir: Path,
        method: Method,
        method_type: [DebateType, ConsultantType, BaselineType] = None,
        use_intermediary: bool = False,
    ):
        self.exp_dir = exp_dir
        self.config_dir = Path.cwd() / "core/config/quality"
        self.method = method
        self.method_type = method_type
        self.use_intermediary = use_intermediary
        self.validate_input()

    def validate_input(self):
        if self.method is None:
            raise ValueError("You must specify a method.")
        if self.method not in Method.__members__.values():
            raise ValueError(f"Method must be one of {Method.__members__.values()}.")
        if self.method == Method.debate and self.method_type is None:
            raise ValueError("You must specify a debate_type if type is debate.")

        if self.method == Method.consultancy and self.method_type is None:
            raise ValueError(
                "You must specify a consultant_type if type is consultant."
            )
        if not self.exp_dir.exists():
            raise ValueError(f"Experiment directory {self.exp_dir} does not exist.")

    def __str__(self):
        return self.get_debate_root().replace("/", "_")

    def get_debate_root(self) -> str:
        dir = f"{self.method}_{self.method_type}"
        if self.use_intermediary:
            dir += "_intermediary"
        return dir

    def get_debate_filename(self, seed=0, swap=False) -> Path:
        dirs = self.get_debate_root()
        file = f"data{seed}.csv" if not swap else f"data{seed}_swap.csv"
        return self.exp_dir / dirs / file

    def get_judge_filename(
        self, judge_model, seed=0, swap=False, exp_suffix=""
    ) -> Path:
        dirs = self.get_debate_root()
        file = (
            f"data{seed}_judgement{exp_suffix}.csv"
            if not swap
            else f"data{seed}_swap_judgement{exp_suffix}.csv"
        )
        return self.exp_dir / dirs / judge_model / file


def get_few_shot_messages(
    method: Method, base_dir: Path, num_examples=8, few_shot_model: str = None
) -> list:
    # load few shots from each yaml file (swap and non swap)
    base_dir = Path(base_dir)
    if method == Method.debate:
        yaml_dir = base_dir / "debate"
        if few_shot_model is not None:
            yaml_dir = yaml_dir / few_shot_model
        files = list(yaml_dir.glob("*.yaml"))
    else:
        yaml_dir_correct = base_dir / f"correct_consultant"
        yaml_dir_incorrect = base_dir / f"incorrect_consultant"
        if few_shot_model is not None:
            yaml_dir_correct = yaml_dir_correct / few_shot_model
            yaml_dir_incorrect = yaml_dir_incorrect / few_shot_model
        files = list(yaml_dir_correct.glob("*.yaml")) + list(
            yaml_dir_incorrect.glob("*.yaml")
        )
    # sample from each yaml file
    num_files = len(files)
    num_examples_per_split = num_examples // num_files
    few_shots = []
    for file in files:
        few_shot = load_yaml_cached(file)
        num_samples = min(num_examples_per_split, len(few_shot))
        print(f"Sampling {num_samples} from {file}")
        if num_samples < num_examples_per_split:
            print(f"WARNING: {num_samples} < {num_examples_per_split}")
        few_shots.extend(random.sample(few_shot, num_samples))
    random.shuffle(few_shots)
    # flatten list of lists
    if any(isinstance(x, list) for x in few_shots):
        few_shots = [item for sublist in few_shots for item in sublist]
    return few_shots
