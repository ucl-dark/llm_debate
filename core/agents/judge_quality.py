import copy
import json
import logging
from copy import deepcopy

from core.agents.judge_base import JudgeBase
from core.file_handler import Method, get_few_shot_messages
from core.llm_api.base_llm import convert_to_prob
from core.rollouts.utils import CacheManager, Round, TranscriptConfig
from core.utils import log_model_timings, softmax
from web.backend.services.parser import TranscriptParser

LOGGER = logging.getLogger(__name__)


class JudgeQuality(JudgeBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config.use_logprobs:
            assert self.config.language_model.model in [
                "gpt-4-1106-preview",
                "gpt-4-base",
                "gpt-3.5-turbo-instruct",
            ], "Only davinci and gpt-4-base support logprobs"
            LOGGER.info(f"Using logprobs: {self.config.use_logprobs}")

    def swap_transcript(self, transcript: TranscriptConfig) -> TranscriptConfig:
        swapped_transcript = copy.deepcopy(transcript).dict()
        if self.method == Method.debate:
            # We don't want to swap names in a consultancy because we only have one debater
            swapped_transcript["names"] = {
                **dict(transcript.names),
                "correct": transcript.names.incorrect,
                "incorrect": transcript.names.correct,
            }
        swapped_transcript["swap"] = True

        # The cross examiner know names (unlike debaters) so will refer to them. Therefore swap these.
        for i, round in enumerate(swapped_transcript["rounds"]):
            new_round = dict(round)
            if (
                new_round["cross_examiner"]
                and transcript.names.correct
                and transcript.names.incorrect
            ):
                new_round["cross_examiner"] = new_round["cross_examiner"].replace(
                    transcript.names.correct, "<TEMP>"
                )
                new_round["cross_examiner"] = new_round["cross_examiner"].replace(
                    transcript.names.incorrect, transcript.names.correct
                )
                new_round["cross_examiner"] = new_round["cross_examiner"].replace(
                    "<TEMP>", transcript.names.incorrect
                )
            swapped_transcript["rounds"][i] = new_round

        swapped_transcript = TranscriptConfig(**swapped_transcript)
        return swapped_transcript

    def get_transcript(self, transcript):
        transcript, _ = TranscriptParser.verify_strict(transcript)
        transcript_string = ""
        if not transcript.swap:
            positions = ["judge", "cross_examiner", "correct", "incorrect"]
        else:
            positions = ["judge", "cross_examiner", "incorrect", "correct"]

        for i, round in enumerate(transcript.rounds):
            transcript_string += f"Round {i + 1}:\n\n"
            for position in positions:
                message = getattr(round, position, None)
                if message:
                    if position == "judge":
                        # in human-judged experiments we store the username here, but we want to anonymize the transcript when a model sees it
                        name = "Judge"
                    else:
                        name = getattr(transcript.names, position, position)
                    assert name is not None
                    transcript_string += f'{name}: """{message}"""\n\n'
        return transcript_string

    def fill_in_content(self, content: str, transcript: TranscriptConfig):
        placeholders = {
            "QUESTION": lambda: transcript.question,
            "ANSWER_A": lambda: transcript.answers.correct
            if not transcript.swap
            else transcript.answers.incorrect,
            "ANSWER_B": lambda: transcript.answers.incorrect
            if not transcript.swap
            else transcript.answers.correct,
            "NAME_A": lambda: "Debater A",
            "NAME_B": lambda: "Debater B",
            "TRANSCRIPT": lambda: self.get_transcript(transcript),
            "STORY": lambda: transcript.story,
            "CONSULTANT_ANSWER": lambda: transcript.answers.correct
            if transcript.names.correct
            else transcript.answers.incorrect,
            "CONSULTANT_ANSWER_LETTER": lambda: "A"
            if (transcript.names.correct and not transcript.swap)
            or (transcript.names.incorrect and transcript.swap)
            else "B",
            "CONSULTANT_ANSWER_OPPOSING": lambda: transcript.answers.incorrect
            if transcript.names.correct
            else transcript.answers.correct,
            "CONSULTANT_ANSWER_OPPOSING_LETTER": lambda: "B"
            if (transcript.names.correct and not transcript.swap)
            or (transcript.names.incorrect and transcript.swap)
            else "A",
            "ANSWER_CORRECT": lambda: transcript.answers.correct,
            "ANSWER_INCORRECT": lambda: transcript.answers.incorrect,
            "FEW_SHOT_MESSAGE": lambda: "",  # TODO support few shot for intermediary judge
            "WORD_LIMIT": lambda: str(self.config.prompts.word_limit),
        }
        for placeholder, placeholder_filler in placeholders.items():
            if f"<{placeholder}>" in content:
                content = content.replace(f"<{placeholder}>", placeholder_filler())

        return content

    def construct_messages(self, transcript: TranscriptConfig):
        messages = []
        if self.config.few_shot_num_samples > 0:
            assert self.config.few_shot_base is not None
            few_shot_messages = get_few_shot_messages(
                self.method,
                self.config.few_shot_base,
                self.config.few_shot_num_samples,
            )
            for message in few_shot_messages:
                if transcript.question in message["content"]:
                    print(f"{transcript.question} in few shot message")
                    # append to file in root data/few_shot_clash.txt
                    with open("./data/few_shot_clash.txt", "a") as f:
                        f.write(f"{transcript.question}\n")
                    continue
                messages.append(message)
        for message in self.messages:
            messages.append(
                {
                    "role": message["role"],
                    "content": self.fill_in_content(message["content"], transcript),
                }
            )

        return messages

    def load_transcript_object(self, transcript_string: str):
        return TranscriptConfig(**json.loads(transcript_string))

    def maybe_swap_transcript(self, transcript: TranscriptConfig, swap: bool):
        if swap:
            # swap answers and arguments by debaters so (B) will be the correct choice rather than (A)
            if transcript.swap == False:
                assert (
                    "seq" not in self.rollout_type
                ), "Please run your debate rollout in swap if sequential, can't swap at judge time"
                transcript = self.swap_transcript(transcript)
            else:
                LOGGER.debug("Already swapped transcript")
        else:
            assert (
                transcript.swap == False
            ), f"Expected swap to be False, got {transcript.swap}"
        return transcript

    def slice_transcript_rounds(self, transcript: TranscriptConfig, num_rounds: int):
        sliced_transcript = copy.deepcopy(transcript).dict()
        sliced_transcript["rounds"] = sliced_transcript["rounds"][:num_rounds]
        sliced_transcript = TranscriptConfig(**sliced_transcript)
        return sliced_transcript

    async def make_decision(
        self,
        index,
        row,
        swap: bool = False,
        round_limit: int = None,
    ):
        transcript = self.load_transcript_object(row["transcript"])
        transcript = self.maybe_swap_transcript(transcript, swap)
        if round_limit is not None:
            transcript = self.slice_transcript_rounds(transcript, round_limit)
        messages = self.construct_messages(transcript)

        try:
            if not self.config.use_logprobs:
                response = await self.api_handler.call_single(
                    prompt=messages,
                    model_ids=self.config.language_model.model,
                    temperature=self.config.language_model.temperature,
                    top_p=self.config.language_model.top_p,
                    max_tokens=self.config.language_model.max_tokens,
                    timeout=self.config.language_model.timeout,
                )
            else:
                responses = await self.api_handler(
                    prompt=messages,
                    model_ids=self.config.language_model.model,
                    temperature=self.config.language_model.temperature,
                    top_p=self.config.language_model.top_p,
                    max_tokens=self.config.language_model.max_tokens,
                    logprobs=5,
                )
                assert len(responses) == 1, "Expected a single response."
                _, logit1, logit2 = convert_to_prob(
                    responses[0].logprobs[0], ["A", "B"]
                )
                probs = softmax([logit1, logit2])
                answer = "A" if logit1 > logit2 else "B"
                response = f"Logit A: {logit1}, Logit B: {logit2}, Prob A: {probs[0]:.4f}, Prob B: {probs[1]:.4f}\nAnswer: {answer}"
            complete = True
        except RuntimeError as e:
            LOGGER.info(f"Error message: {e}")
            response = f"Error message: {e}"
            complete = False
        if complete:
            LOGGER.info(f"Completed {index}")
            LOGGER.info(f"Total cost: {self.api_handler.running_cost:.3f}")
            log_model_timings(
                self.api_handler, save_location="./data/judge_timings.png"
            )
        return {
            "judgement": response,
            "complete": complete,
            "transcript": transcript.json(),
        }

    async def get_argument_rating(
        self,
        transcript,
        response,
        side,
        method,
    ):
        new_transcript = deepcopy(transcript).dict()
        dummy_answer = "My answer is the best choice and my opponent is wrong."
        if method == Method.debate:
            new_transcript["rounds"][-1] = {
                **dict(new_transcript["rounds"][-1]),
                "correct": response if side == "correct" else dummy_answer,
                "incorrect": response if side == "incorrect" else dummy_answer,
            }
        else:
            new_transcript["rounds"][-1] = {
                **dict(new_transcript["rounds"][-1]),
                side: response,
            }
        new_transcript = TranscriptConfig(**new_transcript)

        messages = self.construct_messages(new_transcript)

        responses = await self.api_handler(
            model_ids=self.config.language_model.model,
            prompt=messages,
            temperature=self.config.language_model.temperature,
            top_p=self.config.language_model.top_p,
            max_tokens=self.config.language_model.max_tokens,
            logprobs=5,
        )
        assert len(responses) == 1, "Expected a single response."

        # convert_to_prob returns prob on first token
        if not new_transcript.swap:
            # If side of debater is correct they are arguing for (A) so we want the prob of (A)
            # If side of debater is incorrect they are arguing for (B) so we want the prob of (B)
            tokens = ["A", "B"] if side == "correct" else ["B", "A"]
        else:
            tokens = ["B", "A"] if side == "correct" else ["A", "B"]
        # rating corresponds to prob of first token
        rating, _, _ = convert_to_prob(responses[0].logprobs[0], tokens)
        return rating

    def extract_critique(self, response):
        try:
            critique = response.split("<critique>")[1].split("</critique>")[0]
        except IndexError:
            critique = response
        return critique

    def replace_tag_in_messages(self, messages, tag, replacement):
        messages_out = []
        for message in messages:
            messages_out.append(
                {
                    "role": message["role"],
                    "content": message["content"].replace(tag, replacement.strip()),
                }
            )
        return messages_out

    def process_messages_for_critique(
        self, transcript: TranscriptConfig, side: str, argument: str
    ) -> list[dict]:
        assert (
            transcript.rounds[-1].correct is None
            and transcript.rounds[-1].incorrect is None
        )
        new_transcript = copy.deepcopy(transcript).dict()
        new_transcript["rounds"][-1] = Round(**{side: argument})
        new_transcript = TranscriptConfig(**new_transcript)

        if not transcript.swap:
            letter = "A" if side == "correct" else "B"
            other_letter = "B" if side == "correct" else "A"
        else:
            letter = "B" if side == "correct" else "A"
            other_letter = "A" if side == "correct" else "B"

        messages = self.construct_messages(new_transcript)
        messages = self.replace_tag_in_messages(
            messages, "<NAME>", transcript.names.dict()[side]
        )
        messages = self.replace_tag_in_messages(
            messages, "<ANSWER>", transcript.answers.dict()[side]
        )
        messages = self.replace_tag_in_messages(messages, "<LETTER>", letter)
        messages = self.replace_tag_in_messages(
            messages, "<OTHER_LETTER>", other_letter
        )
        assert len(transcript.rounds) > 0
        if len(transcript.rounds) == 1:
            messages = self.replace_tag_in_messages(
                messages,
                "<ROUND_SPECIFIC>",
                self.config.prompts.partials["first_round"],
            )
        elif len(transcript.rounds) == 2:
            messages = self.replace_tag_in_messages(
                messages,
                "<ROUND_SPECIFIC>",
                self.config.prompts.partials["second_round"],
            )
        else:
            messages = self.replace_tag_in_messages(
                messages,
                "<ROUND_SPECIFIC>",
                self.config.prompts.partials["nth_round"],
            )
        return messages

    async def get_critiques(
        self, transcript: TranscriptConfig, side: str, argument: str, num_critiques: int
    ):
        messages = self.process_messages_for_critique(transcript, side, argument)

        critiques = await self.api_handler(
            model_ids=self.config.language_model.model,
            prompt=messages,
            temperature=self.config.language_model.temperature,
            top_p=self.config.language_model.top_p,
            max_tokens=self.config.language_model.max_tokens,
            n=num_critiques,
        )
        critiques = [self.extract_critique(x.completion.strip()) for x in critiques]
        assert len(critiques) == num_critiques
        return critiques

    async def get_critique_rating(
        self, transcript: TranscriptConfig, side: str, argument: str, critique: str
    ):
        messages = self.process_messages_for_critique(transcript, side, argument)
        messages = self.replace_tag_in_messages(messages, "<CRITIQUE>", critique)

        responses = await self.api_handler(
            model_ids=self.config.language_model.model,
            prompt=messages,
            temperature=self.config.language_model.temperature,
            top_p=self.config.language_model.top_p,
            max_tokens=self.config.language_model.max_tokens,
            logprobs=5,
        )
        assert len(responses) == 1, "Expected a single response."

        tokens = ["Y", "N"]
        rating, _, _ = convert_to_prob(responses[0].logprobs[0], tokens)
        return rating

    async def get_question(self, transcript: TranscriptConfig):
        # used for interactive judging
        messages = self.construct_messages(transcript)

        # sometimes for fine-tuned models the transcript is too long for the prompt
        # in this case just return a general question to round off the debate
        if "ft:" in self.config.language_model.model:
            content = "\n".join([x["content"] for x in messages])
            num_tokens = len(self.tokenizer.encode(content))
            if num_tokens > 3800:
                question = (
                    "Can you please write your closing arguments so I can decide?"
                )
                LOGGER.warning(
                    f"Prompt doesn't fit in fine-tuned model with {num_tokens} tokens. Using default question: {question}"
                )
                return question

        response = await self.api_handler.call_single(
            prompt=messages,
            model_ids=self.config.language_model.model,
            temperature=self.config.language_model.temperature,
            top_p=self.config.language_model.top_p,
            max_tokens=self.config.language_model.max_tokens,
            timeout=self.config.language_model.timeout,
        )

        return response

    async def take_turn(
        self,
        transcript: TranscriptConfig,
        current_step: int,
        cache_manager: CacheManager,
    ):
        response = None
        response_key = "response_judge"
        if current_step < len(cache_manager.results):
            response = cache_manager.results[current_step].get(response_key, None)
        if response is None:
            response = await self.get_question(transcript)
            cache_manager.save_item(current_step, response_key, response)

        if "gpt-3.5-turbo" in self.config.language_model.model:
            if "<question>" not in response and "</thinking>" in response:
                response = response.split("</thinking>")[1].strip()
                if response:
                    response = f"<question>{response}</question>"
            elif "<question>" not in response:
                response = (
                    response.replace("</thinking>", "")
                    .replace("<thinking>", "")
                    .strip()
                )
                if response:
                    response = f"<question>{response}</question>"
            elif "<question></question>" in response:
                response = response.split("</question>")[1].strip()
                if response:
                    response = f"<question>{response}</question>"

        question = response.split("<question>")[1].split("</question>")[0]
        return question.strip(), response
