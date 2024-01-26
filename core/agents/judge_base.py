from typing import Optional

import tiktoken
from pydantic import BaseModel

from core.file_handler import Method
from core.llm_api.base_llm import LanguageModelConfig, PromptConfig
from core.llm_api.llm import ModelAPI
from core.rollouts.utils import RolloutConfig


class JudgeConfig(BaseModel):
    language_model: LanguageModelConfig
    prompts: PromptConfig
    judge_type: Optional[str] = "quality"
    permissions: Optional[dict] = None
    use_logprobs: Optional[bool] = False
    few_shot_num_samples: Optional[int] = 0
    few_shot_base: Optional[str] = None


class JudgeBase:
    def __init__(
        self,
        method: Method,
        config: JudgeConfig,
        rollout_config: RolloutConfig,
        api_handler: ModelAPI,
    ):
        self.method = method
        self.api_handler = api_handler
        self.config = config
        self.rollout_config = rollout_config
        self.name = self.rollout_config.judge_name
        self.rollout_type = rollout_config.rollout_type
        self.messages = self.config.prompts.messages
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

    async def make_decision(
        self,
        index,
        row,
        swap: bool = False,
        round_limit: int = None,
    ):
        raise NotImplementedError
