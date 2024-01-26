import asyncio
import logging
import os
from collections import defaultdict
from itertools import chain
from pathlib import Path
from typing import Callable, Literal, Optional, Union

import attrs

from core.llm_api.anthropic_llm import ANTHROPIC_MODELS, AnthropicChatModel
from core.llm_api.base_llm import LLMResponse, ModelAPIProtocol
from core.llm_api.openai_llm import (
    BASE_MODELS,
    GPT_CHAT_MODELS,
    OAIBasePrompt,
    OAIChatPrompt,
    OpenAIBaseModel,
    OpenAIChatModel,
)
from core.utils import load_secrets

LOGGER = logging.getLogger(__name__)


@attrs.define()
class ModelAPI:
    anthropic_num_threads: int = 5
    openai_fraction_rate_limit: float = attrs.field(
        default=0.99, validator=attrs.validators.lt(1)
    )
    organization: str = "DEFAULT_ORG"
    print_prompt_and_response: bool = False

    _openai_base: OpenAIBaseModel = attrs.field(init=False)
    _openai_chat: OpenAIChatModel = attrs.field(init=False)
    _anthropic_chat: AnthropicChatModel = attrs.field(init=False)

    running_cost: float = attrs.field(init=False, default=0)
    model_timings: dict[str, list[float]] = attrs.field(init=False, default={})
    model_wait_times: dict[str, list[float]] = attrs.field(init=False, default={})

    def __attrs_post_init__(self):
        secrets = load_secrets("SECRETS")
        if self.organization is None:
            self.organization = "DEFAULT_ORG"
        self._openai_base = OpenAIBaseModel(
            frac_rate_limit=self.openai_fraction_rate_limit,
            organization=secrets[self.organization],
            print_prompt_and_response=self.print_prompt_and_response,
        )
        self._openai_chat = OpenAIChatModel(
            frac_rate_limit=self.openai_fraction_rate_limit,
            organization=secrets[self.organization],
            print_prompt_and_response=self.print_prompt_and_response,
        )
        self._anthropic_chat = AnthropicChatModel(
            num_threads=self.anthropic_num_threads,
            print_prompt_and_response=self.print_prompt_and_response,
        )
        Path("./prompt_history").mkdir(exist_ok=True)

    async def call_single(
        self,
        model_ids: Union[str, list[str]],
        prompt: Union[list[dict[str, str]], str],
        max_tokens: int,
        print_prompt_and_response: bool = False,
        n: int = 1,
        max_attempts_per_api_call: int = 10,
        num_candidates_per_completion: int = 1,
        is_valid: Callable[[str], bool] = lambda _: True,
        insufficient_valids_behaviour: Literal[
            "error", "continue", "pad_invalids"
        ] = "error",
        **kwargs,
    ) -> str:
        assert n == 1, f"Expected a single response. {n} responses were requested."
        responses = await self(
            model_ids,
            prompt,
            max_tokens,
            print_prompt_and_response,
            n,
            max_attempts_per_api_call,
            num_candidates_per_completion,
            is_valid,
            insufficient_valids_behaviour,
            **kwargs,
        )
        assert len(responses) == 1, "Expected a single response."
        return responses[0].completion

    async def __call__(
        self,
        model_ids: Union[str, list[str]],
        prompt: Union[list[dict[str, str]], str],
        max_tokens: int,
        print_prompt_and_response: bool = False,
        n: int = 1,
        max_attempts_per_api_call: int = 10,
        num_candidates_per_completion: int = 1,
        is_valid: Callable[[str], bool] = lambda _: True,
        insufficient_valids_behaviour: Literal[
            "error", "continue", "pad_invalids"
        ] = "error",
        **kwargs,
    ) -> list[LLMResponse]:
        """
        Make maximally efficient API requests for the specified model(s) and prompt.

        Args:
            model_ids: The model(s) to call. If multiple models are specified, the output will be sampled from the
                cheapest model that has capacity. All models must be from the same class (e.g. OpenAI Base,
                OpenAI Chat, or Anthropic Chat). Anthropic chat will error if multiple models are passed in.
                Passing in multiple models could speed up the response time if one of the models is overloaded.
            prompt: The prompt to send to the model(s). Type should match what's expected by the model(s).
            max_tokens: The maximum number of tokens to request from the API (argument added to
                standardize the Anthropic and OpenAI APIs, which have different names for this).
            print_prompt_and_response: Whether to print the prompt and response to stdout.
            n: The number of completions to request.
            max_attempts_per_api_call: Passed to the underlying API call. If the API call fails (e.g. because the
                API is overloaded), it will be retried this many times. If still fails, an exception will be raised.
            num_candidates_per_completion: How many candidate completions to generate for each desired completion. n*num_candidates_per_completion completions will be generated, then is_valid is applied as a filter, then the remaining completions are returned up to a maximum of n.
            is_valid: Candiate completions are filtered with this predicate.
            insufficient_valids_behaviour: What should we do if the remaining completions after applying the is_valid filter is shorter than n.
                error: raise an error
                continue: return the valid responses, even if they are fewer than n
                pad_invalids: pad the list with invalid responses up to n
        """

        assert (
            "max_tokens_to_sample" not in kwargs
        ), "max_tokens_to_sample should be passed in as max_tokens."

        if isinstance(model_ids, str):
            model_ids = [model_ids]
            # # trick to double rate limit for most recent model only
            # if model_ids.endswith("-0613"):
            #     model_ids = [model_ids, model_ids.replace("-0613", "")]
            #     print(f"doubling rate limit for most recent model {model_ids}")
            # elif model_ids.endswith("-0914"):
            #     model_ids = [model_ids, model_ids.replace("-0914", "")]
            # else:
            #     model_ids = [model_ids]

        def model_id_to_class(model_id: str) -> ModelAPIProtocol:
            if model_id in BASE_MODELS:
                return self._openai_base
            elif model_id in GPT_CHAT_MODELS or "ft:gpt-3.5-turbo" in model_id:
                return self._openai_chat
            elif model_id in ANTHROPIC_MODELS:
                return self._anthropic_chat
            raise ValueError(f"Invalid model id: {model_id}")

        model_classes = [model_id_to_class(model_id) for model_id in model_ids]
        if len(set(str(type(x)) for x in model_classes)) != 1:
            raise ValueError("All model ids must be of the same type.")

        model_class = model_classes[0]
        if isinstance(model_class, AnthropicChatModel):
            max_tokens = max_tokens if max_tokens is not None else 2000
            kwargs["max_tokens_to_sample"] = max_tokens
        else:
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

        num_candidates = num_candidates_per_completion * n
        if isinstance(model_class, AnthropicChatModel):
            candidate_responses = list(
                chain.from_iterable(
                    await asyncio.gather(
                        *[
                            model_class(
                                model_ids,
                                prompt,
                                print_prompt_and_response,
                                max_attempts_per_api_call,
                                **kwargs,
                            )
                            for _ in range(num_candidates)
                        ]
                    )
                )
            )
        else:
            candidate_responses = await model_class(
                model_ids,
                prompt,
                print_prompt_and_response,
                max_attempts_per_api_call,
                n=num_candidates,
                **kwargs,
            )

        valid_responses = [
            response
            for response in candidate_responses
            if is_valid(response.completion)
        ]
        num_valid = len(valid_responses)
        success_rate = num_valid / num_candidates
        if success_rate < 1:
            LOGGER.info(f"`is_valid` success rate: {success_rate * 100:.2f}%")

        if num_valid < n:
            match insufficient_valids_behaviour:
                case "error":
                    raise RuntimeError(
                        f"Only found {num_valid} valid responses from {num_candidates} candidates."
                    )
                case "continue":
                    responses = valid_responses
                case "pad_invalids":
                    invalid_responses = [
                        response
                        for response in candidate_responses
                        if not is_valid(response.completion)
                    ]
                    invalids_needed = n - num_valid
                    responses = [*valid_responses, *invalid_responses[:invalids_needed]]
                    LOGGER.info(
                        f"Padded {num_valid} valid responses with {invalids_needed} invalid responses to get {len(responses)} total responses"
                    )
        else:
            responses = valid_responses

        self.running_cost += sum(response.cost for response in valid_responses)
        for response in responses:
            self.model_timings.setdefault(response.model_id, []).append(
                response.api_duration
            )
            self.model_wait_times.setdefault(response.model_id, []).append(
                response.duration - response.api_duration
            )
        return responses[:n]

    def reset_cost(self):
        self.running_cost = 0


async def demo():
    model_api = ModelAPI(anthropic_num_threads=2, openai_fraction_rate_limit=1)
    anthropic_requests = [
        model_api(
            "claude-instant-1",
            "\n\nHuman: What's your name?\n\nAssistant:",
            True,
            max_tokens_to_sample=2,
        )
    ]
    oai_chat_messages = [
        [
            {"role": "system", "content": "You are a comedic pirate."},
            {"role": "user", "content": "Hello!"},
        ],
        [
            {
                "role": "system",
                "content": "You are a swashbuckling space-faring voyager.",
            },
            {"role": "user", "content": "Hello!"},
        ],
    ]
    oai_chat_models = ["gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613"]
    oai_chat_requests = [
        model_api(
            oai_chat_models,
            prompt=message,
            n=6,
            max_tokens=16_000,
            print_prompt_and_response=True,
        )
        for message in oai_chat_messages
    ]
    oai_messages = ["1 2 3", ["beforeth they cometh", "whence afterever the storm"]]
    oai_models = ["davinci-002"]
    oai_requests = [
        model_api(oai_models, prompt=message, n=1, print_prompt_and_response=True)
        for message in oai_messages
    ]
    answer = await asyncio.gather(
        *anthropic_requests, *oai_chat_requests, *oai_requests
    )

    costs = defaultdict(int)
    for responses in answer:
        for response in responses:
            costs[response.model_id] += response.cost

    print("-" * 80)
    print("Costs:")
    for model_id, cost in costs.items():
        print(f"{model_id}: ${cost}")
    return answer


if __name__ == "__main__":
    asyncio.run(demo())
