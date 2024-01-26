import asyncio
import json
import logging
import time
import traceback
from typing import Optional

import pandas as pd

from core.agents.debater_quality import TOKEN_LIMIT_ARGUMENT
from core.file_handler import Method
from core.rollouts.rollout_base import RolloutBase
from core.rollouts.utils import (
    Answers,
    CacheManager,
    DebaterNames,
    Round,
    StubCacheManager,
    TranscriptConfig,
)
from core.utils import log_model_timings

LOGGER = logging.getLogger(__name__)


class QualitySimRollout(RolloutBase):
    async def debate_turn(
        self,
        transcript: TranscriptConfig,
        current_step: int,
        cache_manager: CacheManager | StubCacheManager,
        judge_message: Optional[str] = None,
    ):
        new_round = {"type": "sim", "judge": judge_message}
        new_responses = {"type": "sim", "judge": judge_message}
        # don't run cross examiner on first round
        if self.cross_examiner and current_step != 0:
            question, response = await self.cross_examiner.take_turn(
                transcript,
                current_step,
                cache_manager,
            )
            new_round["cross_examiner"] = question
            new_responses["cross_examiner"] = response
        transcript.rounds.append(Round(**new_round))
        transcript.responses.append(Round(**new_responses))

        calls = {}
        if self.correct_debater:
            calls["correct"] = self.correct_debater.take_turn(
                transcript,
                current_step,
                cache_manager,
                self.correct_judge_BoN,
                self.correct_judge_critic,
                self.correct_judge_critique_pm,
            )

        if self.incorrect_debater:
            calls["incorrect"] = self.incorrect_debater.take_turn(
                transcript,
                current_step,
                cache_manager,
                self.incorrect_judge_BoN,
                self.incorrect_judge_critic,
                self.incorrect_judge_critique_pm,
            )

        results = await asyncio.gather(*calls.values(), return_exceptions=True)

        for key, result in zip(calls.keys(), results):
            if isinstance(result, Exception):
                raise result
            argument, response = result
            new_round[key] = argument
            new_responses[key] = response
        if TOKEN_LIMIT_ARGUMENT in new_responses.values():
            assert self.method == Method.debate, "Token limit only applies to debate"
            LOGGER.info(
                f"Token limit reached for one debater so ending debate and removing opponent argument"
            )
            new_round = {
                "type": "sim",
                "correct": TOKEN_LIMIT_ARGUMENT,
                "incorrect": TOKEN_LIMIT_ARGUMENT,
            }
        # update the round with the new arguments
        transcript.rounds[-1] = Round(**new_round)
        transcript.responses[-1] = Round(**new_responses)

        cache_manager.save_item(current_step, "transcript", transcript.json())

        return transcript

    # No need for swap, it will be judge-time
    async def run(self, index: int, row: pd.Series, swap=False):
        names = {}
        if self.method == Method.debate:
            names["correct"] = self.config.name1 if not swap else self.config.name2
            names["incorrect"] = self.config.name2 if not swap else self.config.name1
            names["cross_examiner"] = (
                self.config.cross_examiner_name if self.cross_examiner else None
            )
        elif self.method == Method.consultancy:
            names["correct"] = (
                self.config.consultant_name if self.correct_debater else None
            )
            names["incorrect"] = (
                self.config.consultant_name if self.incorrect_debater else None
            )
            names["cross_examiner"] = (
                self.config.cross_examiner_name if self.cross_examiner else None
            )

        transcript = TranscriptConfig(
            index=index,
            story=row["story"],
            story_title=row["story_title"],
            question=row["question"],
            question_set_id=row["question_set_id"],
            answers=Answers(
                correct=row["correct answer"], incorrect=row["negative answer"]
            ),
            names=DebaterNames(**names),
            swap=swap,
            rollout_type=self.config.rollout_type,
        )
        # Load cached results if they exist
        cache_manager = CacheManager(self.cache_dir, transcript.index)
        current_step, transcript_cache, _ = cache_manager.unpack_results()
        if transcript_cache is not None:
            transcript = TranscriptConfig(**json.loads(transcript_cache))
        transcript_string = transcript.json()

        # Run the debate
        duration = 0
        while current_step < int(self.config.num_steps):
            if self.correct_debater or self.incorrect_debater or self.cross_examiner:
                try:
                    start_time = time.time()
                    transcript = await self.debate_turn(
                        transcript, current_step, cache_manager
                    )
                    duration = time.time() - start_time
                    LOGGER.info(
                        f"Step {current_step} completed in {duration:.3f} (index {index})"
                    )
                    current_step += 1
                    transcript_string = transcript.json()
                except (RuntimeError, IndexError, ValueError) as e:
                    transcript_string = f"Error occurred on debate {transcript.index}, step {current_step}. Error message: {e}."
                    current_step = -1
                    LOGGER.info(transcript_string)
                    LOGGER.info(traceback.format_exc())
                    break
            else:
                current_step += 1
        complete = current_step >= int(self.config.num_steps)
        if complete:
            if self.correct_debater or self.incorrect_debater:
                debater = (
                    self.correct_debater
                    if self.correct_debater
                    else self.incorrect_debater
                )
                LOGGER.info(f"Total cost: {debater.api_handler.running_cost:.3f}")
                log_model_timings(
                    debater.api_handler, save_location="./data/model_timings.png"
                )
            LOGGER.info(f"Completed: {transcript.index}")

        return {
            "transcript": transcript_string,
            "complete": complete,
        }
