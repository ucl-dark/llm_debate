import asyncio
import random
from typing import List, Optional, Tuple

from core.load.quality import (
    QualityQuestion,
    QualityQuestionsForArticle,
    QuestionWithArticle,
    create_question_with_article,
    filter_question,
    parse_dataset,
)


async def get_dataset(split: Optional[str] = None):
    if not split:
        train, dev = await asyncio.gather(parse_dataset("train"), parse_dataset("dev"))
        dataset = train + dev
    else:
        dataset = await parse_dataset(split)

    return dataset


async def get_random_question() -> QuestionWithArticle:
    dataset = []
    for s in ["train"]:
        data = await parse_dataset(s)
        dataset += data
    questions_with_sets: List[Tuple[QualityQuestion, QualityQuestionsForArticle]] = [
        (q, qs) for qs in dataset for q in qs.questions
    ]

    tries = 0
    max_tries = 100
    while tries < max_tries:
        tries += 1
        question, question_set = random.choice(questions_with_sets)
        question_with_article = create_question_with_article(question, question_set)
        if filter_question(
            question_with_article,
            sources=["Gutenberg"],
            difficulty=1,
            ignore_nyu=False,
            max_answerability=1,
            min_untimed_accuracy=1.0,
            max_speed_accuracy=0.5,
            min_context_required=1.5,
            skip_conflicting_labels=True,
        ):
            return question_with_article

    raise ValueError("Could not find valid question")
