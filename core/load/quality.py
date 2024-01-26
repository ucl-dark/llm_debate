import csv
import json
import os
import random
import tempfile
from datetime import datetime
from itertools import chain, zip_longest
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import fire
import pandas
import requests
import tiktoken
from pydantic import BaseModel

from core.utils import typer_async

EXPERIMENT_ALIASES: Dict[str, List[str]] = {
    "6": ["Experiment 6"],
    "7": ["Experiment 7"],
    "8": ["Experiment 8a", "Experiment 8b", "Experiment 8c"],
}

EXCLUDED_STORIES: List[str] = [
    "Boys Do Bleed",
    "MONICA!",
    "The Girl in His Mind",
]

# (question, article.title)
EXCLUDED_QUESTIONS: List[Tuple[str, str]] = [
    ("What is the relationship between the humans and the Belphins?", "The Blue Tower"),
    ("What will happen if Anne becomes pregnant?", "Conditionally Human"),
    (
        "Why does Adrian think the Callistans will be willing to fight against the league?",
        "Conspiracy on Callisto",
    ),
    (
        "All of the following terms describe how Infield would characterize Price EXCEPT for:",
        "Name Your Symptom",
    ),
    (
        "How did the Mafia grow the business of prostitution on Mars?",
        "Mars Confidential",
    ),
    ("What crime has Zeckler committed to warrant imprisonment?", "Letter of the Law"),
    (
        "The humans in the fourth dimension acquire all of the following remarkable abilities EXCEPT for:",
        "Judas Ram",
    ),
    (
        "The Movement believes all of the following EXCEPT: Questioning the failings of the old society, failings have put them in the dome; failure of foreign policy (self-containment)",
        "A Fall of Glass",
    ),
    (
        "What is the Boyar's ultimate goal for Flamme?",
        "The Desert and the Stars",  # claude 2.1 can't answer
    ),
]

NYU_ARTICLE_IDS = [
    "63477",
    "61007",
    "63109",
    "62569",
    "55933",
    "61499",
    "63899",
    "52844",
    "63640",
    "63631",
    "50893",
    "61090",
    "63527",
    "62619",
    "62198",
    "61053",
    "63890",
    "53269",
    "61380",
    "51201",
    "43046",
    "30029",
    "63523",
    "63401",
    "61285",
    "62314",
    "61430",
    "62085",
    "61119",
    "61467",
    "52855",
    "60412",
    "63855",
    "63633",
    "61434",
    "61146",
    "63862",
    "63392",
    "63130",
    "62382",
    "63833",
    "20002",
    "63150",
    "63473",
    "51483",
    "51461",
    "50818",
    "51027",
    "51267",
    "51351",
    "51126",
    "51320",
    "51395",
    "51274",
    "51650",
    "51605",
    "51150",
    "51295",
    "51688",
    "51256",
]


class ValidationUntimed(BaseModel):
    untimed_annotator_id: str
    untimed_answer: str
    untimed_eval1_answerability: int  # Is the question answerable and unambiguous? 1: Single correct answer, 2: Multiple correct answers, 3: Unclear or unrelated question/answers.
    untimed_eval2_context: int  # How much of the passage/text is needed as context to answer this question correctly? 1: Sentence or two, 2: Long paragraph, 3: A third of the passage, 4: Most or all of the passage.
    untimed_best_distractor: int  # Which of the options that you did not select was the best "distractor" item (i.e., an answer choice that you might be tempted to select if you hadn't read the text very closely)? The numbers correspond to the option numbers (1-indexed). This is "untimed_eval3_distractor" in the docs but not in the data file


class SpeedValidation(BaseModel):
    speed_annotator_id: str
    speed_answer: str


class QualityQuestion(BaseModel):
    question: str
    options: List[str]  # A list of four answer options.
    gold_label: int  # The correct answer by majority vote of annotators + original writer's label. 1-indexed.
    writer_label: int  # The label the writer provided. 1-indexed.
    validation: List[
        ValidationUntimed
    ]  # A list of dictionaries containing untimed validation results.
    speed_validation: List[
        SpeedValidation
    ]  # A list of dictionaries containing speed validation results.
    difficult: int  # Binary value: 1 means less than 50% speed annotations were correct, otherwise 0.


class QualityQuestionsForArticle(BaseModel):
    article_id: str  # In each split, there are exactly two lines containing the same article_id, because two writers wrote questions for the same article.
    set_unique_id: str  # The unique ID corresponding to the set of questions.
    batch_num: str  # 23 means the third batch in the second group
    writer_id: str
    source: str
    title: str
    author: str
    topic: str
    url: str  # The URL of the original unprocessed source article.
    year: Optional[int]  # The (often approximate) publication year of the article.
    license: str  # The license information for the article.
    article: str  # The HTML of the article.
    questions: List[QualityQuestion]
    split: Optional[str]


class Article(BaseModel):
    article_id: str  # In each split, there are exactly two lines containing the same article_id, because two writers wrote questions for the same article.
    source: str
    title: str
    author: str
    topic: str
    url: str  # The URL of the original unprocessed source article.
    year: Optional[int]  # The (often approximate) publication year of the article.
    license: str  # The license information for the article.
    article: str  # The HTML of the article.
    num_tokens: Optional[int]


class QuestionWithArticle(BaseModel):
    question: str
    options: List[str]  # A list of four answer options.
    gold_label: int  # The correct answer by majority vote of annotators + original writer's label. 1-indexed.
    writer_label: int  # The label the writer provided. 1-indexed.
    validation: List[
        ValidationUntimed
    ]  # A list of dictionaries containing untimed validation results.
    speed_validation: List[
        SpeedValidation
    ]  # A list of dictionaries containing speed validation results.
    difficult: int  # Binary value: 1 means less than 50% speed annotations were correct, otherwise 0.
    set_unique_id: str  # The unique ID corresponding to the set of questions.
    batch_num: str  # 23 means the third batch in the second group
    writer_id: str
    split: Optional[str]
    article: Article


# def untimed_accuracy(question):
#     correct_answer = question['gold_label']
#     annotator_answers = [a['untimed_answer'] for a in question['validation']]
#     return sum([1 if a == correct_answer else 0 for a in annotator_answers]) / len(annotator_answers)


def find_question(
    question_text: str, story_title: str, questions: List[QuestionWithArticle]
):
    for q in questions:
        if (
            q.question.strip() == question_text.strip()
            and q.article.title.strip() == story_title.strip()
        ):
            return q


def best_distractor_for_question(question: QuestionWithArticle):
    annotator_answers = [a.untimed_best_distractor for a in question.validation]
    annotator_answers = [a for a in annotator_answers if a != int(question.gold_label)]
    # 1-indexed, return 0-indexed
    best_distractor_index = max(set(annotator_answers), key=annotator_answers.count) - 1
    return question.options[best_distractor_index]


def correct_answer_for_question(question: QuestionWithArticle):
    correct_index = question.gold_label - 1  # 1-indexed
    return question.options[correct_index]


def get_token_length_for_question(question: QuestionWithArticle):
    enc = tiktoken.encoding_for_model("gpt-4")
    return len(enc.encode(question.article.article))


def answerability(question: QuestionWithArticle):
    answerability_scores = [v.untimed_eval1_answerability for v in question.validation]
    answerability = sum(answerability_scores) / len(answerability_scores)
    return answerability


def untimed_accuracy(question: QuestionWithArticle):
    scores = [
        1 if int(v.untimed_answer) == question.gold_label else 0
        for v in question.validation
    ]
    accuracy = sum(scores) / len(scores)
    return accuracy


def speed_accuracy(question: QuestionWithArticle):
    scores = [
        1 if int(v.speed_answer) == question.gold_label else 0
        for v in question.speed_validation
    ]
    accuracy = sum(scores) / len(scores)
    return accuracy


def context_required(question: QuestionWithArticle):
    context_scores = [int(v.untimed_eval2_context) for v in question.validation]
    context_required = sum(context_scores) / len(context_scores)
    return context_required


def incompatible_answers(label: str):
    return (
        "all of the above" in label.lower()
        or "neither of these" in label.lower()
        or "none of the above" in label.lower()
    )


def filter_question(
    question: QuestionWithArticle,
    sources=["Gutenberg"],
    difficulty=1,
    max_tokens=None,
    ignore_nyu=True,
    questions_to_avoid: List[Tuple[str, str]] = [],
    stories_to_avoid: List[str] = [],
    max_answerability: Optional[float] = 2.0,
    min_untimed_accuracy: Optional[float] = 0.5,
    max_speed_accuracy: Optional[float] = 0.5,
    min_context_required: Optional[float] = 1.0,
    skip_conflicting_labels: Optional[bool] = False,
    human_experiments: Optional[List[str]] = None,
    human_questions=None,
):
    if human_questions is not None and human_experiments:
        permitted_experiments = []
        for exp_name in human_experiments:
            if exp_name in EXPERIMENT_ALIASES:
                permitted_experiments += EXPERIMENT_ALIASES[exp_name]
            else:
                permitted_experiments.append(exp_name)

        human_question = human_questions[
            (human_questions["question"].str.strip() == question.question.strip())
            & (
                human_questions["debate_name"].str.strip()
                == question.article.title.strip()
            )
        ]
        if human_question.empty:
            return False
        else:
            experiment_name = human_question["experiment_name"].iloc[0]
            if experiment_name not in permitted_experiments:
                return False
        # if we're filtering based on human experiment, we probably don't want to apply any other filters.
        return True

    if sources is not None and not question.article.source in sources:
        return False

    if difficulty is not None and not question.difficult == difficulty:
        return False

    if max_tokens and get_token_length_for_question(question) > max_tokens:
        return False

    if question.article.article_id in NYU_ARTICLE_IDS and ignore_nyu:
        return False

    if (
        question.question.strip(),
        question.article.title.strip(),
    ) in questions_to_avoid:
        return False

    if question.article.title.strip() in stories_to_avoid:
        return False

    if max_answerability and max_answerability < answerability(question):
        return False

    if min_untimed_accuracy and min_untimed_accuracy > untimed_accuracy(question):
        return False

    if max_speed_accuracy and max_speed_accuracy < speed_accuracy(question):
        return False

    if min_context_required and min_context_required > context_required(question):
        return False

    if skip_conflicting_labels and question.writer_label != question.gold_label:
        return False

    return True


def deduplicate_stories(
    questions: List[QuestionWithArticle], max_num_from_same_story: int
) -> List[QuestionWithArticle]:
    existing_stories = {}
    new_questions = []

    for question in questions:
        story_title = question.article.title
        if story_title not in existing_stories:
            existing_stories[story_title] = 1
            new_questions.append(question)
        elif existing_stories[story_title] < max_num_from_same_story:
            existing_stories[story_title] += 1
            new_questions.append(question)

    return new_questions


def order_questions_for_humans(
    questions: List[QuestionWithArticle], previous_human_questions
):
    previous_stories = {}
    ordered_questions = []
    stories_with_questions = {}
    for question, story_title, _ in previous_human_questions:
        if story_title in previous_stories:
            previous_stories[story_title] += 1
        else:
            previous_stories[story_title] = 1

    for title, count in previous_stories.items():
        skips = []
        for _ in range(count):
            skips.append(None)
        stories_with_questions[title] = skips

    for question in questions:
        title = question.article.title
        if title in stories_with_questions:
            stories_with_questions[title].append(question)
        else:
            stories_with_questions[title] = [question]

    ordered_questions = list(
        chain.from_iterable(list(zip_longest(*stories_with_questions.values())))
    )
    ordered_questions = [q for q in ordered_questions if q is not None]

    return ordered_questions


def filter_questions(
    questions: List[QuestionWithArticle],
    sources=["Gutenberg"],
    difficulty=1,
    max_tokens=None,
    limit=None,
    take_from_end=False,
    ignore_nyu=True,
    avoid_duplicates_for_user_group: Optional[str] = None,
    minimize_story_duplication: Optional[bool] = False,
    max_answerability: Optional[float] = 2.0,  # Lower is better, 1 is min
    min_untimed_accuracy: Optional[float] = 0.5,
    max_speed_accuracy: Optional[float] = 0.5,
    min_context_required: Optional[float] = 1.0,
    skip_conflicting_labels: Optional[bool] = False,
    max_num_from_same_story: int = 1,
    human_experiments: Optional[List[str]] = None,
):
    questions_to_avoid = [*EXCLUDED_QUESTIONS]
    stories_to_avoid = [*EXCLUDED_STORIES]
    previous_human_questions = []
    if avoid_duplicates_for_user_group:
        from web.backend.repositories.user_repository import UserRepository

        user_group = UserRepository.find_group_by_name(avoid_duplicates_for_user_group)
        if not user_group:
            raise ValueError("Group does not exist")
        previous_human_questions = UserRepository.find_questions_from_user_group(
            user_group
        )
        questions_to_avoid += [
            (q.strip(), s.strip()) for q, s, _ in previous_human_questions
        ]

    human_questions = None
    if human_experiments:
        # load this here so we don't need to load it for every question
        human_questions = pandas.read_csv("core/load/human_questions.csv")

    questions = [
        q
        for q in questions
        if filter_question(
            q,
            sources,
            difficulty,
            max_tokens,
            ignore_nyu,
            questions_to_avoid,
            stories_to_avoid,
            max_answerability,
            min_untimed_accuracy,
            max_speed_accuracy,
            min_context_required,
            skip_conflicting_labels,
            human_experiments,
            human_questions,
        )
    ]

    if minimize_story_duplication:
        questions = deduplicate_stories(questions, max_num_from_same_story)

    random.seed(42)
    shuffled = questions.copy()
    random.shuffle(shuffled)

    if avoid_duplicates_for_user_group and minimize_story_duplication:
        shuffled = order_questions_for_humans(questions, previous_human_questions)

    if limit:
        limit = int(limit)
        if take_from_end:
            shuffled = shuffled[-min(limit, len(questions)) :]
        else:
            shuffled = shuffled[: min(limit, len(questions))]

    return shuffled


def create_question_with_article(
    question: QualityQuestion, question_set: QualityQuestionsForArticle
):
    return QuestionWithArticle(
        **question.dict(),
        set_unique_id=question_set.set_unique_id,
        batch_num=question_set.batch_num,
        writer_id=question_set.writer_id,
        split=question_set.split,
        article=Article(**question_set.dict()),
    )


def dataset_to_questions(
    question_sets: List[QualityQuestionsForArticle],
) -> List[QuestionWithArticle]:
    questions = []
    for question_set in question_sets:
        for question in question_set.questions:
            questions.append(create_question_with_article(question, question_set))

    return questions


async def parse_dataset(split: str = "train") -> List[QualityQuestionsForArticle]:
    dataset_path = await fetch_dataset(split)
    with open(dataset_path, "r") as f:
        text = f.read()
        parsed = []
        for line in text.splitlines():
            question_set = QualityQuestionsForArticle.parse_raw(line)
            parsed.append(question_set)
    return parsed


async def fetch_dataset(split: str = "train", force_download: bool = False):
    dataset_name = f"QuALITY.v1.0.1.htmlstripped.{split}"
    cache_path = os.path.join(tempfile.gettempdir(), f"{dataset_name}")
    if force_download or not os.path.exists(cache_path):
        url = f"https://github.com/nyu-mll/quality/blob/main/data/v1.0.1/{dataset_name}?raw=true"
        response = requests.get(url)
        response.raise_for_status()

        text = response.text.replace("\u2028", "").replace(
            "\u2029", ""
        )  # unusual line terminators
        text = text.replace("\xa0", " ")  # non-breaking space
        with open(cache_path, "w") as f:
            f.write(text)

    return cache_path


def write_questions(questions: List[QuestionWithArticle], filepath):
    # Make sure the directory exists
    parent = os.path.dirname(filepath)
    os.makedirs(parent, exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(
            [
                "id",
                "question",
                "correct answer",
                "negative answer",
                "complete",
                "transcript",
                "answer",
                "prompt",
                "cot prompt",
                "story",
                "story_title",
                "question_set_id",
                "story tokens",
            ]
        )

        for i, question in enumerate(questions):
            id = i
            question_text = question.question
            correct_answer = correct_answer_for_question(question)
            negative_answer = best_distractor_for_question(question)
            complete = False
            transcript = ""
            answer = ""
            prompt = ""
            cot_prompt = ""
            story = question.article.article
            story_title = question.article.title
            question_set_id = question.set_unique_id
            story_tokens = get_token_length_for_question(question)  # slow

            # do some filtering of bad answers
            if correct_answer == negative_answer:
                print(f"Skipping question {id} as correct answer is negative answer")
                continue

            if incompatible_answers(correct_answer) or incompatible_answers(
                negative_answer
            ):
                print(
                    f"Skipping question {id} as correct answer or negative answer is incompatible"
                )
                continue

            csv_writer.writerow(
                [
                    id,
                    question_text,
                    correct_answer,
                    negative_answer,
                    complete,
                    transcript,
                    answer,
                    prompt,
                    cot_prompt,
                    story,
                    story_title,
                    question_set_id,
                    story_tokens,
                ]
            )


@typer_async
async def main(
    filepath: Path,
    split: List[str] = ["train"],
    max_tokens: Optional[int] = None,
    limit: Optional[int] = None,
    take_from_end: bool = False,
    write_to_file: bool = True,
    sources: List[str] = ["Gutenberg"],
    difficulty: Optional[int] = 1,
    ignore_nyu: bool = True,
    avoid_duplicates_for_user_group: Optional[str] = None,
    minimize_story_duplication: Optional[bool] = False,
    max_answerability: Optional[float] = 1.0,  # Lower is better, 1 is min
    min_untimed_accuracy: Optional[
        float
    ] = 1.0,  # Percentage of untimed annotators who got the correct answer
    max_speed_accuracy: Optional[
        float
    ] = 0.5,  # Percentage of timed annotators who got correct answer. 0.5 is equivalent to difficulty=1 subset
    min_context_required: Optional[
        float
    ] = 1.0,  # how much of the story is required to answer the question
    skip_conflicting_labels: Optional[
        bool
    ] = False,  # conflicting labels means the writer_label and gold_label disagree
    max_num_from_same_story: Optional[
        int
    ] = 1,  # limit the number of questions from the same story but only if minimize_story_duplication is True
    human_experiments: Optional[List[str] | str | int] = None,
):
    if isinstance(human_experiments, str) or isinstance(human_experiments, int):
        human_experiments = [str(human_experiments)]
    elif human_experiments is not None:
        human_experiments = [str(he) for he in human_experiments]

    if split == "both":
        split = ["train", "dev"]
    if isinstance(split, str):
        if "[" in split:
            split = json.loads(split.replace("'", '"'))
        else:
            split = [split]
    max_num_from_same_story = int(max_num_from_same_story)
    # typer doesn't allow you to pass None via CLI as it enforces an int
    if difficulty == -1:
        difficulty = None

    dataset = []
    for s in list(split):
        print(f"Loading QuALITY {s} dataset")
        data = await parse_dataset(s)
        print(f"Downloaded {len(data)} question sets for {s}")
        dataset += data

    print(f"Take from end: {take_from_end}")
    print(f"Limit: {limit}")
    print(f"Max tokens: {max_tokens}")
    print(f"Sources: {sources}")
    print(f"Difficulty: {difficulty}")
    if minimize_story_duplication:
        print(f"max_num_from_same_story: {max_num_from_same_story}")

    questions = filter_questions(
        dataset_to_questions(dataset),
        max_tokens=max_tokens,
        limit=limit,
        take_from_end=take_from_end,
        sources=sources,
        difficulty=difficulty,
        ignore_nyu=ignore_nyu,
        avoid_duplicates_for_user_group=avoid_duplicates_for_user_group,
        minimize_story_duplication=minimize_story_duplication,
        max_answerability=max_answerability,
        min_untimed_accuracy=min_untimed_accuracy,
        max_speed_accuracy=max_speed_accuracy,
        min_context_required=min_context_required,
        skip_conflicting_labels=skip_conflicting_labels,
        max_num_from_same_story=max_num_from_same_story,
        human_experiments=human_experiments,
    )

    if write_to_file:
        print(f"Writing {len(questions)} questions to csv")
        write_questions(questions, filepath)

    return questions


if __name__ == "__main__":
    fire.Fire(main)
