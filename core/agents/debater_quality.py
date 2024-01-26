import asyncio
import logging
import random
import re
from typing import List, Optional

from core.agents.debater_base import DebaterBase
from core.agents.judge_base import JudgeBase
from core.file_handler import Method, get_few_shot_messages
from core.llm_api.base_llm import add_assistant_message
from core.rollouts.utils import CacheManager, TranscriptConfig
from core.utils import SEPARATOR
from web.backend.services.parser import TranscriptParser

LOGGER = logging.getLogger(__name__)

TOKEN_LIMIT_ARGUMENT = (
    "Round ended so no comment made. Judge - do not count this round."
)


class DebaterQuality(DebaterBase):
    def get_transcript_string(self, transcript: TranscriptConfig):
        transcript, _ = TranscriptParser.verify_strict(transcript)
        our_name, opponent_name = self.names_from_transcript(transcript)
        transcript_string = ""
        for i, round in enumerate(transcript.rounds):
            our_arg, opponent_arg = self.args_from_round(round)
            transcript_string += f"Round {i + 1}:\n\n"
            if round.judge is not None and len(round.judge) > 0:
                judge_name = "Judge"
                transcript_string += f'{judge_name}: """{round.judge}"""\n\n'
            if round.cross_examiner is not None and len(round.cross_examiner) > 0:
                cross_examiner_name = transcript.names.cross_examiner or "Judge"
                transcript_string += (
                    f'{cross_examiner_name}: """{round.cross_examiner}"""\n\n'
                )
            transcript_string += (
                f'{our_name}: """{our_arg}"""\n\n' if our_arg is not None else ""
            )
            if self.method == Method.debate:
                transcript_string += (
                    f'{opponent_name}: """{opponent_arg}"""\n\n'
                    if opponent_arg is not None
                    else ""
                )
            if i + 1 < len(transcript.rounds):
                # Don't add separator after last round
                transcript_string += f"{SEPARATOR}\n\n"
        return transcript_string.strip()

    def truncate(self, argument: str, word_limit: Optional[int] = None):
        if word_limit is None:
            word_limit = self.config.language_model.max_words

        words = argument.split(" ")
        new_arg = " ".join(words[:word_limit])

        # Make sure we don't end with a partial quote
        for quote_tag in ["quote", "u_quote", "v_quote"]:
            if not f"<{quote_tag}>" in new_arg:
                continue
            quotes = new_arg.split(f"<{quote_tag}>")
            if f"</{quote_tag}>" not in quotes[-1]:
                new_arg = f"<{quote_tag}>".join(quotes)
                new_arg = f"{new_arg}</{quote_tag}>"

        if len(new_arg) != len(argument):
            return f"{new_arg}... <TRUNCATED>"
        else:
            return new_arg

    def extract_argument(self, response, strict=True):
        for quote_tag in ["<v_quote>", "<u_quote>"]:
            response = response.replace(quote_tag, "<quote>")
        for quote_tag in ["</v_quote>", "</u_quote>"]:
            response = response.replace(quote_tag, "</quote>")
        # sometimes gpt-3.5 doesn't use the argument tag and just puts their argument after thinking
        if self.config.language_model.model == "gpt-3.5-turbo-16k":
            if "<argument>" not in response and "</thinking>" in response:
                response_ = response.split("</thinking>")[1].strip()
                if response_:
                    response = f"<argument>{response_}</argument>"
            elif "<argument>" not in response:
                response_ = (
                    response.replace("</thinking>", "")
                    .replace("<thinking>", "")
                    .strip()
                )
                if response_:
                    response = f"<argument>{response_}</argument>"
        if self.config.language_model.model == "claude-2.1":
            if "<argument>" not in response and "Argument:" in response:
                response_ = response.split("Argument:")[1].strip()
                response_ = (
                    response_.replace("</thinking>", "")
                    .replace("<thinking>", "")
                    .strip()
                )
                response_ = response_.replace("</argument>", "").strip()
                if response_:
                    response = f"<argument>{response_}</argument>"
            elif "I apologize" in response:
                response = f"<argument>{response}</argument>"
            elif "<argument>" not in response:
                response = "<argument>I have nothing more to add.</argument>"
        if "<argument>" not in response:
            if strict:
                raise ValueError("No argument tag in response", response)
            else:
                response = f"<argument>{response}</argument>"
        argument = response.split("<argument>")[1].split("</argument>")[0]
        if self.config.transcript_quotes is not None:
            return self.handle_quotes(argument)
        else:
            return argument

    def create_transcript_message(self, transcript: TranscriptConfig):
        if len(transcript.rounds) == 0:
            return ""
        else:
            return self.fill_in_content(self.partials["transcript"], transcript)

    def get_new_argument_request(self, transcript: TranscriptConfig):
        if len(self.our_args(transcript)) == 0:
            return self.fill_in_content(
                self.partials["opening_argument_request"], transcript
            )
        else:
            return self.fill_in_content(
                self.partials["nth_argument_request"], transcript
            )

    def get_thinking_advice(self, transcript: TranscriptConfig):
        if len(self.our_args(transcript)) == 0:
            return self.fill_in_content(
                self.partials["first_round_thinking"], transcript
            )
        elif len(self.our_args(transcript)) == 1:
            return self.fill_in_content(
                self.partials["second_round_thinking"], transcript
            )
        else:
            return self.fill_in_content(self.partials["nth_round_thinking"], transcript)

    def create_few_shot_message(self, transcript: TranscriptConfig):
        if not self.config.few_shot_num_samples > 0:
            return ""
        else:
            content = self.fill_in_content(self.partials["few_shot"], transcript)
            return "\n" + content + "\n"

    def unpack_few_shot_messages(self, transcript: TranscriptConfig):
        if not self.config.few_shot_num_samples > 0:
            return ""
        else:
            few_shot_messages = get_few_shot_messages(
                self.method,
                self.config.few_shot_base,
                self.config.few_shot_num_samples,
            )
            few_shot_messages_modified = []
            for message in few_shot_messages:
                if transcript.question in message:
                    print(f"{transcript.question} in few shot message")
                    continue
                # message_with_name_filled_in = self.fill_in_content(message, transcript)
                few_shot_messages_modified.append(message)
            return "\n\n".join(few_shot_messages_modified)

    def fill_in_content(self, content: str, transcript: TranscriptConfig):
        answer_defending, answer_opposing = self.answers_from_transcript(transcript)
        letter_defending, letter_opposing = self.answer_letters_from_transcript(
            transcript
        )
        name, opponent_name = self.names_from_transcript(transcript)
        placeholders = {
            "QUESTION": lambda: transcript.question,
            "STORY": lambda: transcript.story,
            "NAME": lambda: name,
            "OPPONENT_NAME": lambda: opponent_name,
            "ANSWER_DEFENDING": lambda: answer_defending,
            "ANSWER_DEFENDING_LETTER": lambda: letter_defending,
            "ANSWER_OPPOSING_LETTER": lambda: letter_opposing,
            "ANSWER_OPPOSING": lambda: answer_opposing,
            "ANSWER_A": lambda: transcript.answers.correct
            if not transcript.swap
            else transcript.answers.incorrect,
            "ANSWER_B": lambda: transcript.answers.incorrect
            if not transcript.swap
            else transcript.answers.correct,
            "TRANSCRIPT_MESSAGE": lambda: self.create_transcript_message(transcript),
            "TRANSCRIPT": lambda: self.get_transcript_string(transcript),
            "NEW_ARGUMENT_REQUEST": lambda: self.get_new_argument_request(transcript),
            "THINKING_ADVICE": lambda: self.get_thinking_advice(transcript),
            "FEW_SHOT_MESSAGE": lambda: self.create_few_shot_message(transcript),
            "FEW_SHOTS": lambda: self.unpack_few_shot_messages(transcript),
            "WORD_LIMIT": lambda: str(self.config.prompts.word_limit),
            "WORD_LIMIT_REFINEMENT": lambda: str(self.config.prompts.word_limit),
        }

        for placeholder, placeholder_filler in placeholders.items():
            if f"<{placeholder}>" in content:
                content = content.replace(f"<{placeholder}>", placeholder_filler())

        return content

    def handle_quotes(self, argument: str):
        # normalize quotes
        argument = argument.replace("”", '"').replace("“", '"')
        match self.config.transcript_quotes:
            case "normal":
                # can add similarity info here later
                return argument
            case "none":
                argument = re.sub(
                    r'"[^"]*"', "", argument
                )  # Remove double quotes and anything enclosed by them.
                argument = re.sub(
                    r"  +", " ", argument
                )  # Replace multiple consecutive spaces with a single space
                return argument
            case "only":
                matches = re.findall(r"(<quote>.*?<\/quote>)", argument)
                return "\n\n".join(matches)
            case _:
                return argument

    def construct_messages(self, transcript: TranscriptConfig):
        messages = []
        for message in self.messages:
            messages.append(
                {
                    "role": message["role"],
                    "content": self.fill_in_content(message["content"], transcript),
                }
            )

        return messages

    def is_valid(self, completion: str):
        if "<argument>" not in completion:
            return False
        try:
            argument = self.extract_argument(completion)
        except ValueError:
            return False
        if "<quote>" not in argument:
            return False
        word_count = len(argument.split(" "))
        return (
            word_count >= self.config.language_model.min_words
            and word_count <= self.config.language_model.max_words
        )

    async def get_completion(self, transcript: TranscriptConfig) -> List[str]:
        prompt = self.construct_messages(transcript)
        # sometimes the transcript is too long for the fine-tuned model
        # in this case, we just return a default argument that the debate is over
        if (
            "ft:" in self.config.language_model.model
            or "gpt-3.5-turbo" == self.config.language_model.model
        ):
            content = "\n".join([x["content"] for x in prompt])
            num_tokens = len(self.tokenizer.encode(content))
            if num_tokens > 3750:
                arguments = [
                    f"<argument>{TOKEN_LIMIT_ARGUMENT}</argument>"
                ] * self.config.BoN
                LOGGER.warning(
                    f"Prompt doesn't fit in fine-tuned model with {num_tokens} tokens. Using round end argument {arguments[0]}"
                )
                return arguments

        responses = await self.api_handler(
            model_ids=self.config.language_model.model,
            prompt=prompt,
            temperature=self.config.language_model.temperature,
            top_p=self.config.language_model.top_p,
            max_tokens=self.config.language_model.max_tokens,
            n=self.config.BoN,
            num_candidates_per_completion=self.config.language_model.num_candidates_per_completion,
            is_valid=self.is_valid,
            insufficient_valids_behaviour="pad_invalids",  # TODO: this should be in config
        )
        responses = [x.completion.strip() for x in responses]
        assert len(responses) == self.config.BoN
        return responses

    async def get_refinements(
        self, transcript: TranscriptConfig, initial_response: str, critique: str
    ) -> str:
        messages = self.construct_messages(transcript)
        messages = add_assistant_message(messages, initial_response)

        for message in self.config.prompts.messages1:
            messages.append(
                {
                    "role": message["role"],
                    "content": message["content"].replace("<CRITIQUE>", critique),
                }
            )
        refinements = await self.api_handler(
            model_ids=self.config.language_model.model,
            prompt=messages,
            temperature=self.config.language_model.temperature,
            top_p=self.config.language_model.top_p,
            max_tokens=self.config.language_model.max_tokens,
            n=self.config.BoN,
            num_candidates_per_completion=self.config.language_model.num_candidates_per_completion,
            is_valid=lambda x: self.is_valid(x) and "critique" not in x.lower(),
            insufficient_valids_behaviour="pad_invalids",
        )
        refinements = [x.completion.strip() for x in refinements]
        assert len(refinements) == self.config.BoN
        return refinements

    async def get_critique(
        self,
        truncated_argument: str,
        transcript: TranscriptConfig,
        current_step: int,
        cache_manager: CacheManager,
        judge_critic: JudgeBase,
        judge_critique_pm: JudgeBase,
    ):
        # Get N critiques of argument
        assert self.config.cBoN > 0
        critiques = None
        critique_key = f"critiques_{self.side}"
        if current_step < len(cache_manager.results):
            critiques = cache_manager.results[current_step].get(critique_key, None)
        if critiques is None:
            critiques = await judge_critic.get_critiques(
                transcript, self.side, truncated_argument, self.config.cBoN
            )
            assert len(critiques) == self.config.cBoN
            cache_manager.save_item(current_step, critique_key, critiques)
        assert (
            len(critiques) == self.config.cBoN
        ), f"Num critiques: {len(critiques)} != BoN Config: {self.config.cBoN}"

        critic_word_limit = judge_critic.config.language_model.max_words
        # Get helpfulness of critique ratings
        if self.config.cBoN > 1:
            jobs = []
            for critique in critiques:
                truncated_critique = self.truncate(critique, critic_word_limit)
                jobs.append(
                    judge_critique_pm.get_critique_rating(
                        transcript, self.side, truncated_argument, truncated_critique
                    )
                )

            ratings = await asyncio.gather(*jobs)
            critique = critiques[ratings.index(max(ratings))]
        else:
            critique = critiques[0]

        return self.truncate(critique, critic_word_limit)

    async def judge_preference(
        self,
        responses: list,
        transcript: TranscriptConfig,
        judge: JudgeBase,
        strict=True,
    ):
        assert self.config.BoN > 1
        jobs = []
        for response in responses:
            argument = self.extract_argument(response, strict=strict)
            truncated_argument = self.truncate(argument)
            jobs.append(
                judge.get_argument_rating(
                    transcript,
                    truncated_argument,
                    self.side,
                    self.method,
                )
            )

        ratings = await asyncio.gather(*jobs)
        response = responses[ratings.index(max(ratings))]
        # get list of tuples of ordered responses from high rating to low rating e.g. [(rating, response), ...]
        sorted_responses = sorted(
            zip(ratings, responses), key=lambda x: x[0], reverse=True
        )
        # format as string with 1. rating=rating, response=response
        responses_string = "\n".join(
            [
                f"{i+1}. rating={rating}, response={response}\n====================="
                for i, (rating, response) in enumerate(sorted_responses)
            ]
        )
        return response, responses_string

    async def take_turn(
        self,
        transcript: TranscriptConfig,
        current_step: int,
        cache_manager: CacheManager,
        judge: JudgeBase = None,
        judge_critic: JudgeBase = None,
        judge_critique_pm: JudgeBase = None,
    ):
        # get argument(s) for debater
        responses = None
        response_key = f"responses_{self.side}"
        if current_step < len(cache_manager.results):
            responses = cache_manager.results[current_step].get(response_key, None)
        if responses is None:
            responses = await self.get_completion(transcript)
            extractable_responses = []
            for response in responses:
                try:
                    # Try to extract an argument from the response
                    _ = self.extract_argument(response)
                    extractable_responses.append(response)
                except ValueError:
                    LOGGER.warning(
                        f"Response could not be extracted. Response: {response}"
                    )
                    continue

            # only save cache if responses are all extractable otherwise you have to manually delete cache on rerun
            if len(extractable_responses) == len(responses):
                cache_manager.save_item(current_step, response_key, responses)
            else:
                raise ValueError(
                    f"{len(responses)-len(extractable_responses)} responses are invalid, retry."
                )

        assert (
            len(responses) == self.config.BoN
        ), f"Num Response: {len(responses)} != BoN Config: {self.config.BoN}"

        # run BoN on argument
        if self.config.BoN > 1:
            assert judge is not None, "Judge (preference) must be provided for BoN > 1"
            response, responses_string = await self.judge_preference(
                responses, transcript, judge
            )
        else:
            response = responses[0]
            responses_string = response
        argument = self.extract_argument(response)
        truncated_argument = self.truncate(argument)

        # get refinement(s) of argument
        if self.config.cBoN > 0:
            assert (
                judge_critic is not None
            ), "Judge (critic) must be provided for cBoN > 0"
            assert (
                judge_critique_pm is not None
            ), "Judge (critique_pm) must be provided for cBoN > 0"
            critique = await self.get_critique(
                truncated_argument,
                transcript,
                current_step,
                cache_manager,
                judge_critic,
                judge_critique_pm,
            )

            # Do refinement of argument based on most helpful critique
            refinements = None
            refinement_key = f"refinement_{self.side}"
            if current_step < len(cache_manager.results):
                refinements = cache_manager.results[current_step].get(
                    refinement_key, None
                )
            if refinements is None:
                refinements = await self.get_refinements(transcript, response, critique)
                cache_manager.save_item(current_step, refinement_key, refinements)

            # run BoN on refinement
            if self.config.BoN > 1:
                # don't be strict due issue with claude refusing
                refinement, refinements_string = await self.judge_preference(
                    refinements, transcript, judge, strict=False
                )
            else:
                refinement = refinements[0]
                refinements_string = refinement
            # 0.5% of questions the refinement goes wrong due to e.g. claude refusing to answer and apologizing
            # in this case, we just use the original argument
            if "<argument>" in refinement:
                argument = self.extract_argument(refinement)
                truncated_argument = self.truncate(argument)
            else:
                LOGGER.warning(
                    f"Refinement had issue. Using original argument instead. Refinement: {refinement}"
                )
                LOGGER.warning(
                    f"Question: {transcript.question}, id {transcript.index}, answers {transcript.answers}, side {self.side}"
                )
            word_count = len(truncated_argument.split(" "))
            responses_string += f"\n\nCritique:\n\n{critique}\n\nRefinements:{refinements_string}\n\nFinal argument ({word_count} words):{truncated_argument}"

        return truncated_argument, responses_string

    # A bunch of experimental stuff that's not being used right now
    # def filter_long_arguments(self, arguments):
    #     # remove args that are too long
    #     lengths = [len(s) for s in arguments]
    #     median_length = sorted(lengths)[len(lengths) // 2]
    #     threshold = 1.5 * median_length
    #     return [s for s in arguments if len(s) <= threshold]
    #
    # def count_quote_chars(self, argument, transcript: TranscriptConfig):
    #     quotes = re.findall(r"<quote>(.*?)</quote>", argument, re.DOTALL)
    #     quotes = [q.strip().rstrip("'\"").lstrip("'\"") for q in quotes]
    #     verified_count = sum(len(q) for q in quotes if q in transcript.story)
    #     return verified_count
    #
    # def filter_arguments(self, arguments, transcript: TranscriptConfig):
    #     # Apply some basic prefiltering, like selecting arguments with more quotes
    #     arguments = self.filter_long_arguments(arguments)
    #     most_quoted = sorted(
    #         arguments, key=lambda s: self.count_quote_chars(s, transcript), reverse=True
    #     )
    #     return most_quoted
    # async def try_judge_bon(self, argument, turn_input, answer_defending, answer_opposing, rounds, position):
    #     try:
    #         response = await get_judge_rating(argument, turn_input, answer_defending, answer_opposing, rounds, position)
    #         return response
    #     except BaseException as e:
    #         print(e)
    #         return 0
    #
    # async def try_judge_voting(self, arguments, turn_input, answer_defending, answer_opposing, rounds, position):
    #     try:
    #         response = await get_judge_preference(arguments, turn_input, answer_defending, answer_opposing, rounds, position)
    #         return int(response)
    #     except BaseException as e:
    #         print(e)

    # async def choose_best_argument_bon(self, arguments, turn_input):
    #     answer_defending, answer_opposing = self.answers_from_turn_input(turn_input)
    #     rounds = self.group_turns(turn_input)
    #     ratings = await asyncio.gather(*[self.try_judge_bon(argument, turn_input, answer_defending, answer_opposing, rounds, self.position) for argument in arguments])
    #     best_args = sorted(zip(ratings, arguments), key=lambda x: x[0], reverse=True)
    #     return best_args[0][1]
    #
    #
    # async def choose_best_argument_voting(self, arguments, turn_input):
    #     answer_defending, answer_opposing = self.answers_from_turn_input(turn_input)
    #     rounds = self.group_turns(turn_input)
    #     votes = await asyncio.gather(*[self.try_judge_voting(arguments, turn_input, answer_defending, answer_opposing, rounds, self.position) for _ in range(self.config.votes)])
    #     votes = [v for v in votes if v is not None]
    #     if len(votes) == 0:
    #         raise HTTPException(status_code=500, detail="Failed to generate any arguments")
    #     vote = max(set(votes), key=votes.count)
    #     breakpoint()
    #     return arguments[vote]
