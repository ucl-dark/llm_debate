import copy
import json
import re
import string
from functools import lru_cache

import web.backend.database.models as models
from core.rollouts.utils import Answers, DebaterNames, Round, TranscriptConfig
from core.scoring.accuracy import func_correct_ab
from web.backend.services.legacy_parser import LegacyTranscriptParser


class TranscriptParser:
    @classmethod
    def is_string_transcript(cls, row: models.Row) -> bool:
        # Transcript is legacy if it's not a valid JSON object
        try:
            json.loads(row.transcript)
            return False
        except json.decoder.JSONDecodeError:
            return True

    @classmethod
    def is_legacy_transcript_config(cls, row: models.Row) -> bool:
        transcript = json.loads(row.transcript)
        legacy_keys = ["ans1", "ans2", "ansA", "ansB", "name1", "name2"]

        if any(key in transcript for key in legacy_keys):
            return True
        else:
            return False

    @classmethod
    def load_legacy_transcript_config(
        cls, transcript_string: str, file
    ) -> TranscriptConfig:
        # A and B work better for display than 1 & 2, because the answers are referred to as A and B.
        def update_legacy_names(name):
            if name in ["Debater 1", "Debater1"]:
                return "Debater A"
            if name in ["Debater 2", "Debater2"]:
                return "Debater B"
            return name

        transcript = json.loads(transcript_string)
        if "ansA" in transcript:
            transcript["ans1"] = transcript["ansA"]
            transcript["ans2"] = transcript["ansB"]
            del transcript["ansA"]
            del transcript["ansB"]

        transcript["name1"] = update_legacy_names(transcript["name1"])
        transcript["name2"] = update_legacy_names(transcript["name2"])
        is_consultancy = len(transcript["rounds"][0]) == 1
        honest = "_honest_" in file.path.split("/")[-1]
        swap = transcript["swap"]
        rounds = []

        for old_round in transcript["rounds"]:
            if is_consultancy:
                new_round = Round(
                    correct=old_round[0] if honest else None,
                    incorrect=old_round[0] if not honest else None,
                    type="sim",
                )
            else:
                new_round = Round(
                    correct=old_round[0] if not swap else old_round[1],
                    incorrect=old_round[1] if not swap else old_round[0],
                    type="sim",
                )
            rounds.append(new_round)

        if is_consultancy:
            names = DebaterNames(
                correct="Consultant" if honest else None,
                incorrect="Consultant" if not honest else None,
            )
        else:
            names = DebaterNames(
                correct=transcript["name1"]
                if not transcript["swap"]
                else transcript["name2"],
                incorrect=transcript["name2"]
                if not transcript["swap"]
                else transcript["name1"],
            )
        return TranscriptConfig(
            index=transcript["index"],
            story=getattr(transcript, "story", None),
            question=transcript["question"],
            answers=Answers(
                correct=transcript["ans1"]
                if not transcript["swap"]
                else transcript["ans2"],
                incorrect=transcript["ans2"]
                if not transcript["swap"]
                else transcript["ans1"],
            ),
            names=names,
            swap=transcript["swap"],
            rounds=rounds,
            rollout_type="",
        )

    @classmethod
    def load_transcript_config(cls, transcript_string: str) -> TranscriptConfig:
        transcript = json.loads(transcript_string)
        return TranscriptConfig(**transcript)

    @classmethod
    def parse(cls, file: models.File, row: models.Row) -> TranscriptConfig | None:
        try:
            if cls.is_string_transcript(row):
                transcript = LegacyTranscriptParser.parse(file, row)
            elif cls.is_legacy_transcript_config(row):
                transcript = cls.load_legacy_transcript_config(row.transcript, file)
            else:
                transcript = cls.load_transcript_config(row.transcript)
            return transcript
        except Exception as e:
            print(f"Failed to parse {file.path}")
            print(e)
            return None

    @classmethod
    def normalize_text(cls, text):
        text = text.replace("”", '"').replace("“", '"')
        text = text.replace("’", "'").replace("‘", "'")
        text = text.translate(str.maketrans("", "", string.punctuation)).lower()
        text = " ".join(text.split())
        return text

    @classmethod
    def add_missing_quote_tags(cls, transcript: TranscriptConfig) -> TranscriptConfig:
        transcript = copy.deepcopy(transcript)

        def add_quote_tags(s, exclude=None):
            # put quotations on inside of tags first and normalise quotation mark type
            s = s.replace('"<quote>', '<quote>"').replace('</quote>"', '"</quote>')
            s = s.replace("”", '"').replace("“", '"')
            s = s.replace("’", "'").replace("‘", "'")
            ignore_regions = [
                (m.start(), m.end()) for m in re.finditer(r"<quote>.*?</quote>", s)
            ]
            should_ignore = lambda start, end: any(
                ig_start <= start <= ig_end or ig_start <= end <= ig_end
                for ig_start, ig_end in ignore_regions
            )

            if exclude is not None:
                exclude = [cls.normalize_text(e) for e in exclude]

            parts = []
            last_end = 0

            for match in re.finditer(r'"[^"]*"', s):
                start, end = match.span()

                match_normalised = cls.normalize_text(s[start:end])
                quote_not_in_exclude = (
                    exclude is None or match_normalised not in exclude
                )
                for e in exclude:
                    if match_normalised in e:
                        quote_not_in_exclude = False
                quote_not_too_small = len(s[start:end].split()) > 2
                if (
                    not should_ignore(start, end)
                    and quote_not_in_exclude
                    and quote_not_too_small
                ):
                    parts.append(s[last_end:start])
                    parts.append("<quote>" + s[start:end] + "</quote>")
                else:
                    parts.append(s[last_end:end])

                last_end = end

            parts.append(s[last_end:])
            return "".join(parts)

        transcript_new = transcript.dict()
        exclude = [
            transcript.answers.correct.lower(),
            transcript.answers.incorrect.lower(),
            transcript.question.lower(),
        ]
        for round in transcript_new["rounds"]:
            for key in ["correct", "incorrect"]:
                if round[key] is not None:
                    round[key] = add_quote_tags(round[key], exclude=exclude)

        return TranscriptConfig(**transcript_new)

    @classmethod
    def verify(cls, transcript: TranscriptConfig) -> (TranscriptConfig, dict):
        transcript = copy.deepcopy(transcript)

        @lru_cache(maxsize=50)
        def get_ngrams(text, n):
            words = text.split()
            return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}

        story_normalised = cls.normalize_text(transcript.story)
        story_ngrams = get_ngrams(story_normalised, n=3)

        def add_similarity_to_tag(s):
            for quote_tag in ["<v_quote>", "<u_quote>"]:
                s = s.replace(quote_tag, "<quote>")
            for quote_tag in ["</v_quote>", "</u_quote>"]:
                s = s.replace(quote_tag, "</quote>")
            sim_values = []
            quotes = []

            def add_similarity(match):
                quote = match.group(1)
                sim = get_quote_similarity(quote)
                sim_values.append(sim)
                quotes.append(quote)
                return f"<quote sim={sim}>{quote}</quote>"

            modified_s = re.sub(r"<quote>(.*?)</quote>", add_similarity, s)
            return modified_s, sim_values, quotes

        def get_quote_similarity(quote):
            quote_normalised = cls.normalize_text(quote)
            if quote_normalised in story_normalised:
                return 1.0

            quote_ngrams = get_ngrams(quote_normalised, n=3)
            quote_ngram_count = len(quote_ngrams)

            # Ensure that we're not dividing by zero
            sim = (
                0
                if quote_ngram_count == 0
                else len(story_ngrams.intersection(quote_ngrams)) / quote_ngram_count
            )
            return sim

        transcript_new = transcript.dict()
        quotes_info = {
            "correct": {"sim_values": [], "quotes": []},
            "incorrect": {"sim_values": [], "quotes": []},
        }
        for round in transcript_new["rounds"]:
            for key in ["correct", "incorrect"]:
                if round[key] is not None:
                    round[key], sim_values, quotes = add_similarity_to_tag(round[key])
                    quotes_info[key]["sim_values"].extend(sim_values)
                    quotes_info[key]["quotes"].extend(quotes)

        return TranscriptConfig(**transcript_new), quotes_info

    @classmethod
    def verify_strict(cls, transcript: TranscriptConfig) -> (TranscriptConfig, dict):
        transcript = copy.deepcopy(transcript)
        story_normalised = cls.normalize_text(transcript.story)

        def is_quote_present(quote):
            quote_normalised = cls.normalize_text(quote)
            return quote_normalised in story_normalised

        def verify_quotes(s):
            for quote_tag in ["<v_quote>", "<u_quote>"]:
                s = s.replace(quote_tag, "<quote>")
            for quote_tag in ["</v_quote>", "</u_quote>"]:
                s = s.replace(quote_tag, "</quote>")
            verified_quotes = []
            unverified_quotes = []

            def change_tag(match):
                quote = match.group(1)
                if is_quote_present(quote):
                    verified_quotes.append(quote)
                    return f"<v_quote>{quote}</v_quote>"
                else:
                    unverified_quotes.append(quote)
                    return f"<u_quote>{quote}</u_quote>"

            modified_s = re.sub(r"<quote>(.*?)</quote>", change_tag, s)
            return modified_s, verified_quotes, unverified_quotes

        transcript_new = transcript.dict()
        quotes_info = {
            "correct": {"unverified_quotes": [], "verified_quotes": []},
            "incorrect": {"unverified_quotes": [], "verified_quotes": []},
        }
        for round in transcript_new["rounds"]:
            for key in ["correct", "incorrect"]:
                if round[key] is not None:
                    round[key], verified_quotes, unverified_quotes = verify_quotes(
                        round[key]
                    )
                    quotes_info[key]["verified_quotes"].extend(verified_quotes)
                    quotes_info[key]["unverified_quotes"].extend(unverified_quotes)

        for response in transcript_new["responses"]:
            for key in ["correct", "incorrect"]:
                if response[key] is not None:
                    response[key], _, _ = verify_quotes(response[key])

        return TranscriptConfig(**transcript_new), quotes_info

    @classmethod
    def is_judgement_correct(cls, file: models.File, row: models.Row) -> bool | None:
        try:
            if cls.is_string_transcript(row):
                # we've deleted the old scoring code so no way to score legacy transcripts
                return None
            else:
                transcript = cls.parse(file, row)
                if transcript is None:
                    return None

                decision_correct = func_correct_ab(row.judgement_text, transcript.swap)

            if type(decision_correct) == bool:
                return decision_correct
            else:
                # Use None instead of "Unknown"
                return None

        except Exception as e:
            print(f"Failed to parse {file.path}")
            print(e)
            return None
