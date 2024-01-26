from pathlib import Path
from typing import Optional

import pandas as pd

from core.agents.debater_base import DebaterBase
from core.agents.judge_base import JudgeBase
from core.file_handler import Method
from core.rollouts.utils import RolloutConfig


class RolloutBase:
    def __init__(
        self,
        method: Method,
        config: RolloutConfig,
        cache_dir: Path,
        correct_debater: Optional[DebaterBase] = None,
        incorrect_debater: Optional[DebaterBase] = None,
        cross_examiner: Optional[JudgeBase] = None,
        correct_judge_BoN: Optional[JudgeBase] = None,
        incorrect_judge_BoN: Optional[JudgeBase] = None,
        correct_judge_critic: Optional[JudgeBase] = None,
        incorrect_judge_critic: Optional[JudgeBase] = None,
        correct_judge_critique_pm: Optional[JudgeBase] = None,
        incorrect_judge_critique_pm: Optional[JudgeBase] = None,
    ):
        self.method = method
        self.config = config
        self.cache_dir = cache_dir
        self.correct_debater = correct_debater
        self.incorrect_debater = incorrect_debater
        self.cross_examiner = cross_examiner
        self.correct_judge_BoN = correct_judge_BoN
        self.incorrect_judge_BoN = incorrect_judge_BoN
        self.correct_judge_critic = correct_judge_critic
        self.incorrect_judge_critic = incorrect_judge_critic
        self.correct_judge_critique_pm = correct_judge_critique_pm
        self.incorrect_judge_critique_pm = incorrect_judge_critique_pm

        assert any(
            [correct_debater, incorrect_debater, cross_examiner]
        ), "At least one debater must be provided"

    async def run(self, index: int, row: pd.Series, swap: bool = False):
        raise NotImplementedError
