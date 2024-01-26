import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


class InputConfig(BaseModel):
    index: int
    question: str
    correct_answer: str
    incorrect_answer: str
    transcript: Optional[str] = None


class Answers(BaseModel):
    correct: str
    incorrect: str


class DebaterNames(BaseModel):
    correct: Optional[str] = None
    incorrect: Optional[str] = None
    cross_examiner: Optional[str] = None
    judge: Optional[str] = None


class Round(BaseModel):
    correct: Optional[Union[str, dict]] = None
    incorrect: Optional[Union[str, dict]] = None
    cross_examiner: Optional[Union[str, dict]] = None
    judge: Optional[str] = None
    type: Optional[str]


class TranscriptConfig(BaseModel):
    index: int
    question: str
    question_set_id: Optional[str] = None
    story: Optional[str] = None
    story_title: Optional[str] = None
    answers: Answers
    names: DebaterNames
    swap: bool
    rollout_type: Optional[str]
    rounds: List[Round] = []
    responses: Optional[List[Round]] = []
    extra: Dict[str, Any] = {}


class RolloutConfig(BaseModel):
    rollout_type: str
    num_steps: int
    name1: str
    name2: str
    consultant_name: Optional[str]
    cross_examiner_name: Optional[str]
    judge_name: Optional[str]


class CacheManager:
    def __init__(self, cache_dir: Path, index: int) -> None:
        self.index = index
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_dir / f"{self.index}.json"
        self.results = self.load_results()

    def load_results(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    results = json.load(f)
            except json.decoder.JSONDecodeError:
                logging.info(f"Corrupted cache file: {self.cache_file}")
                results = []
        else:
            results = []
        return results

    def save_json(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.results, f)

    # saving individual responses
    def save_item(self, step, key, value):
        if len(self.results) <= step:
            self.results.append({})
        self.results[step][key] = value
        self.save_json()

    def unpack_results(self):
        current_step = 0
        transcript = None
        transcript_debater2 = None
        if len(self.results) > 0:
            if "transcript" in self.results[-1]:
                current_step = len(self.results)
            else:
                # partially completed step
                current_step = len(self.results) - 1

            if current_step > 0:
                assert (
                    "transcript" in self.results[current_step - 1]
                ), f"transcript missing for {self.cache_file}"
                transcript = self.results[current_step - 1]["transcript"]
                transcript_debater2 = self.results[current_step - 1].get(
                    "transcript_debater2", None
                )
        return current_step, transcript, transcript_debater2


class StubCacheManager:
    def __init__(self, *args, **kwargs) -> None:
        self.index = 0
        self.cache_file = ""
        self.results = []

    def load_results(self, *args, **kwargs):
        return []

    def save_json(self, *args, **kwargs):
        pass

    def save_item(self, *args, **kwargs):
        pass

    def unpack_results(self, *args, **kwargs):
        return 0, None, None

    def __getattr__(self, name):
        # Return a no-op function for any attribute not found in this class
        def method(*args, **kwargs):
            pass

        return method
