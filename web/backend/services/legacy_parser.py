import re

import web.backend.database.models as models
from core.rollouts.utils import Answers, DebaterNames, Round, TranscriptConfig
from core.utils import SEPARATOR
from web.backend.utils import get_debate_type


class LegacyTranscriptParser:
    # TODO: Add support for proof rollouts

    @classmethod
    def clean_argument(cls, argument, names):
        lines = argument.splitlines()
        # Strip lines indicating whose turn it is
        regex_pattern = "|".join([f"{name}:" for name in names])
        regex_pattern = f"(Turn \\d+:|{regex_pattern})"
        regex = re.compile(regex_pattern)
        clean = "\n".join(
            [line for line in lines if not re.fullmatch(regex, line.strip())]
        ).strip()
        return clean

    @classmethod
    def parse_transcript_cot(
        cls, file: models.File, row: models.Row
    ) -> TranscriptConfig:
        parts = row.transcript.split(SEPARATOR.strip())
        first_name = parts[0].strip().splitlines()[0].split(":")[0]
        second_name = parts[1].strip().splitlines()[0].split(":")[0]
        first_content = "\n".join(parts[0].strip().splitlines()[1:])
        second_content = "\n".join(parts[1].strip().splitlines()[1:])
        # Sub isolated newlines with doubles to give a nice break after the question
        first_content = re.sub("(?<!\n)\n(?!\n)", "\n\n", first_content)
        second_content = re.sub("(?<!\n)\n(?!\n)", "\n\n", second_content)

        answers = Answers(
            correct=row.question.correct_answer, incorrect=row.question.incorrect_answer
        )
        names = {}
        names["correct"] = first_name if not cls.is_swapped(file.path) else second_name
        names["incorrect"] = (
            second_name if not cls.is_swapped(file.path) else first_name
        )
        rounds = []
        if not cls.is_swapped(file.path):
            rounds.append(
                Round(
                    correct=cls.clean_argument(
                        first_content, [first_name, second_name]
                    ),
                    incorrect=cls.clean_argument(
                        second_content, [first_name, second_content]
                    ),
                    type="sim",
                )
            )
        else:
            rounds.append(
                Round(
                    correct=cls.clean_argument(
                        second_content, [first_name, second_content]
                    ),
                    incorrect=cls.clean_argument(
                        first_content, [first_name, second_name]
                    ),
                    type="sim",
                )
            )
        transcript = TranscriptConfig(
            index=0,
            question=row.question.question_text,
            answers=answers,
            names=DebaterNames(**names),
            swap=cls.is_swapped(file.path),
            rounds=rounds,
            rollout_type="",
        )
        return transcript

    @classmethod
    def parse_transcript_conversational(
        cls, file: models.File, row: models.Row
    ) -> TranscriptConfig:
        parts = row.transcript.split(SEPARATOR.strip())
        first_content = parts[0].strip()
        second_content = parts[1].strip()
        first_name = "Debater 1"
        second_name = "Debater 2"
        answers = Answers(
            correct=row.question.correct_answer, incorrect=row.question.incorrect_answer
        )
        names = {}
        names["correct"] = first_name if not cls.is_swapped(file.path) else second_name
        names["incorrect"] = (
            second_name if not cls.is_swapped(file.path) else first_name
        )
        rounds = []

        if not cls.is_swapped(file.path):
            rounds.append(
                Round(
                    correct=cls.clean_argument(
                        first_content, [first_name, second_name]
                    ),
                    incorrect=cls.clean_argument(
                        second_content, [first_name, second_content]
                    ),
                    type="sim",
                )
            )
        else:
            rounds.append(
                Round(
                    correct=cls.clean_argument(
                        second_content, [first_name, second_content]
                    ),
                    incorrect=cls.clean_argument(
                        first_content, [first_name, second_name]
                    ),
                    type="sim",
                )
            )

        transcript = TranscriptConfig(
            index=0,
            question=row.question.question_text,
            answers=answers,
            names=DebaterNames(**names),
            swap=cls.is_swapped(file.path),
            rounds=rounds,
            rollout_type="",
        )
        return transcript

    @classmethod
    def is_cot(cls, path):
        filename = path.split("/")[-1]
        return "cot_" in filename or "_cot" in filename

    @classmethod
    def is_conversational(cls, path):
        filename = path.split("/")[-1]
        return "conversational" in filename

    @classmethod
    def parse_original_transcript(
        cls, file: models.File, row: models.Row
    ) -> TranscriptConfig | None:
        transcript = row.transcript
        correct_answer = row.question.correct_answer
        incorrect_answer = row.question.incorrect_answer

        rounds = row.transcript.split(SEPARATOR.strip())
        if len(rounds) < 2:
            # In debate transcripts, the first "round" is just the question, so we should always see at least 2 here
            return None
        names = cls.extract_debater_names(transcript, correct_answer, incorrect_answer)
        if not names[1] or not names[0]:
            return None

        correct, incorrect = cls.correct_incorrect_debater_names(
            transcript, correct_answer, incorrect_answer
        )

        if not correct or not incorrect:
            return None
        parsed_rounds = []

        # Old school transcripts didn't put swap in the filename, they had a more complicated system, but this is an easy check
        is_swap = correct != names[0]
        # Skip the first "round" as it is just the question
        for round in rounds[1:]:
            sides = round.split(f"{names[1]}:\n", 1)

            if len(sides) < 2:
                continue

            parsed_round = Round(
                correct=cls.clean_argument(sides[0], names)
                if not is_swap
                else cls.clean_argument(sides[1], names),
                incorrect=cls.clean_argument(sides[1], names)
                if not is_swap
                else cls.clean_argument(sides[0], names),
                type="sim",
            )
            parsed_rounds.append(parsed_round)

        answers = Answers(
            correct=row.question.correct_answer, incorrect=row.question.incorrect_answer
        )
        names = DebaterNames(correct=correct, incorrect=incorrect)
        transcript = TranscriptConfig(
            index=0,
            question=row.question.question_text,
            answers=answers,
            names=names,
            swap=is_swap,
            rounds=parsed_rounds,
            rollout_type="",
        )
        return transcript

    @classmethod
    def parse(cls, file: models.File, row: models.Row) -> TranscriptConfig | None:
        if cls.is_cot(file.path):
            return cls.parse_transcript_cot(file, row)
        if cls.is_conversational(file.path):
            return cls.parse_transcript_conversational(file, row)
        return cls.parse_original_transcript(file, row)

    @classmethod
    def answer_in_line(cls, answer, line):
        pattern = re.compile(rf":\s*I claim the answer is\s*{re.escape(answer)}")
        return bool(pattern.search(line))

    @classmethod
    def correct_incorrect_debater_names_cot(cls, transcript, path):
        names = cls.extract_debater_names_cot(transcript)
        debate_type = get_debate_type(path)
        if debate_type in ["SwapNew"]:
            return names[1], names[0]
        else:
            return names[0], names[1]

    @classmethod
    def correct_incorrect_debater_names(
        cls, transcript, correct_answer, incorrect_answer
    ):
        first_debater, second_debater = cls.extract_debater_names(
            transcript, correct_answer, incorrect_answer
        )

        lines = transcript.splitlines()
        for line in lines:
            if line.strip().startswith(f"{first_debater}:") and cls.answer_in_line(
                correct_answer, line
            ):
                return first_debater, second_debater

            elif line.strip().startswith(f"{second_debater}:") and cls.answer_in_line(
                correct_answer, line
            ):
                return second_debater, first_debater

        return None, None

    @classmethod
    def extract_debater_names_cot(cls, transcript):
        parts = transcript.split(SEPARATOR)
        names = [part.strip().splitlines()[0].split(":")[0] for part in parts[:2]]
        return names

    @classmethod
    def extract_debater_names(
        cls, transcript: str, correct_answer: str, incorrect_answer: str
    ) -> tuple[str | None, str | None]:
        # Used for old transcript format where the preable included each debater stating their answer
        first_debater, second_debater = [None, None]
        lines = transcript.splitlines()

        for line in lines:
            if first_debater and second_debater:
                break
            if cls.answer_in_line(correct_answer, line) or cls.answer_in_line(
                incorrect_answer, line
            ):
                if not first_debater:
                    first_debater = line.split(":")[0].strip()

                elif not second_debater:
                    potential_debater = line.split(":")[0].strip()
                    if potential_debater != first_debater:
                        second_debater = potential_debater

        return first_debater, second_debater

    @classmethod
    def is_swapped(cls, path):
        debate_type = get_debate_type(path)
        return (
            True
            if debate_type in ["SwapNew", "SwapAnswer"] or "swap_" in path
            else False
        )
