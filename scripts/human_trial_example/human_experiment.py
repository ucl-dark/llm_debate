import asyncio
import glob
import json
import random
from fractions import Fraction
from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer
from pydantic import BaseModel

import core.load.quality as quality
import web.backend.database.models as models
from core.agents.debater_base import DebaterConfig
from core.agents.judge_base import JudgeConfig
from core.agents.judge_quality import JudgeQuality
from core.create_agents import create_debater, create_judge, create_rollout
from core.file_handler import ConsultantType, DebateType, Experiment, Method
from core.llm_api.llm import ModelAPI
from core.rollouts.rollout_base import RolloutConfig
from core.rollouts.utils import Round
from core.utils import TranscriptConfig, load_yaml, setup_environment, typer_async
from web.backend.repositories.debate_repository import (
    CreateDebateInput,
    DebateRepository,
)
from web.backend.repositories.experiment_respository import (
    CreateExperimentInput,
    ExperimentRepository,
)
from web.backend.repositories.user_repository import UserRepository

app = typer.Typer()


class QuestionConfig(BaseModel):
    split: List[str]
    limit: int
    sources: List[str]
    difficulty: int
    max_answerability: float
    min_untimed_accuracy: float
    max_speed_accuracy: float
    min_context_required: float
    skip_conflicting_labels: bool


class HumanExperimentVariant(BaseModel):
    portion: str
    name: str
    method: Method
    debate_type: Optional[DebateType]
    consultant_type: Optional[ConsultantType]
    rollout_config: Path
    debater_config: Optional[Path]
    cross_examiner_config: Optional[Path]
    judge_bon_config: Optional[Path]
    judge_critic_config: Optional[Path]
    rollout_steps: int
    max_steps: Optional[int]
    min_steps: Optional[int]
    allow_judge_interaction: Optional[bool]


class HumanExperimentConfig(BaseModel):
    experiment_config: CreateExperimentInput
    question_config: QuestionConfig
    variants: List[HumanExperimentVariant]


BASELINE_INSTRUCTIONS = """
There is no assistance from debaters or consultants on this question. Just try your best to guess the correct answer!
"""


def load_exp_config(exp_config: Path):
    assert exp_config.exists()
    config = HumanExperimentConfig(**load_yaml(exp_config))
    return config


def find_variant_by_name(variants: List[HumanExperimentVariant], name: str):
    for variant in variants:
        if variant.name == name:
            return variant
    raise ValueError("Could not find variant!")


async def run_debate(
    index: int,
    semaphore: asyncio.Semaphore,
    api_handler: ModelAPI,
    variant: HumanExperimentVariant,
    row: pd.Series,
    cache_dir: Path,
    swap: Optional[bool] = None,
    retry=0,
    max_retries=5,
):
    if retry > 0:
        print(f"Running debate - retry {retry}")
    else:
        print("Running debate")
    rollout_config = RolloutConfig(**load_yaml(variant.rollout_config))

    if variant.rollout_steps is not None:
        rollout_config.num_steps = variant.rollout_steps

    correct_debater, incorrect_debater, cross_examiner = (
        None,
        None,
        None,
    )

    debater_config = None
    if variant.debater_config:
        debater_config = DebaterConfig(**load_yaml(variant.debater_config))
    consultant_type = variant.consultant_type
    if variant.method == Method.consultancy and consultant_type is None:
        consultant_type = random.choice(list(ConsultantType))

    if variant.method == "debate" or consultant_type == "correct":
        correct_debater = create_debater(
            variant.method,
            debater_config,
            True,
            api_handler,
        )

    if variant.method == "debate" or consultant_type == "incorrect":
        incorrect_debater = create_debater(
            variant.method,
            debater_config,
            False,
            api_handler,
        )

    if variant.cross_examiner_config:
        cross_examiner = create_judge(
            variant.method,
            JudgeConfig(**load_yaml(variant.cross_examiner_config)),
            rollout_config,
            api_handler,
        )

    bon_pm = None
    critic = None
    critique_pm = None
    if debater_config:
        if debater_config.bon_pm_config:
            judge_config = JudgeConfig(**load_yaml(debater_config.bon_pm_config))
            bon_pm = JudgeQuality(
                variant.method, judge_config, rollout_config, api_handler
            )

        if debater_config.critic_config:
            judge_config = JudgeConfig(**load_yaml(debater_config.critic_config))
            critic = JudgeQuality(
                variant.method, judge_config, rollout_config, api_handler
            )

        if debater_config.critique_pm_config:
            judge_config = JudgeConfig(**load_yaml(debater_config.critique_pm_config))
            critique_pm = JudgeQuality(
                variant.method, judge_config, rollout_config, api_handler
            )

    rollout = create_rollout(
        variant.method,
        rollout_config,
        cache_dir,
        correct_debater,
        incorrect_debater,
        cross_examiner,
        bon_pm,
        bon_pm,
        critic,
        critic,
        critique_pm,
        critique_pm,
    )
    if swap is None:
        swap = random.choice([True, False])
    async with semaphore:
        try:
            result = await rollout.run(index, row, swap)
            if not result["complete"]:
                raise RuntimeError("Debate did not complete")
            if variant.method == Method.baseline:
                transcript = TranscriptConfig(**json.loads(result["transcript"]))
                transcript.names.cross_examiner = "System"
                round = Round(type="sim", cross_examiner=BASELINE_INSTRUCTIONS)
                transcript.rounds = [round]
                return transcript.json()
            return result["transcript"]
        except Exception as e:
            if retry < max_retries:
                print(f"Debate failed. Retrying {retry} of {max_retries}.\n{e}")
                return await run_debate(
                    index=index,
                    semaphore=semaphore,
                    api_handler=api_handler,
                    variant=variant,
                    row=row,
                    swap=swap,
                    cache_dir=cache_dir,
                    retry=retry + 1,
                    max_retries=max_retries,
                )
            else:
                print("Debate retries exhausted")
                raise e


@app.command()
@typer_async
async def load(
    exp_dir: Path, exp_config: Path, user_group: str, overwrite: bool = False
):
    config = load_exp_config(exp_config)
    load_path = exp_dir / "questions.csv"
    if load_path.exists() and not overwrite:
        raise ValueError("Load file already exists!")

    load_path.parent.mkdir(parents=True, exist_ok=True)

    await quality.main(
        load_path,
        ignore_nyu=False,
        avoid_duplicates_for_user_group=user_group,
        minimize_story_duplication=True,
        max_num_from_same_story=2,
        **config.question_config.dict(),
    )


@app.command()
@typer_async
async def assign_questions(exp_dir: Path, exp_config: Path, user_group: str):
    config = load_exp_config(exp_config)
    variant_names = [v.name for v in config.variants]
    assert len(variant_names) == len(
        set(variant_names)
    ), "Variant names must be unique!"
    load_path = exp_dir / "questions.csv"
    assignments_dir = exp_dir / "assignments"
    assignments_dir.mkdir(exist_ok=True)
    judges = UserRepository.find_users_by_group_name(user_group)
    df = pd.read_csv(load_path, keep_default_na=False, na_values=[""])
    num_questions = len(df)
    for i, judge in enumerate(judges):
        judge_df = df.copy()
        variant_portions = [(v.name, v.portion) for v in config.variants]
        assert sum(Fraction(portion) for _, portion in variant_portions) == 1
        assignments = []
        for variant, portion in variant_portions:
            count = int(num_questions * Fraction(portion))
            assignments.extend([variant] * count)
        if len(assignments) != num_questions:
            print(
                "Warning: Variant portions did not divide evenly. Randomly assigning remainder"
            )
            diff = num_questions - len(assignments)
            for _ in range(diff):
                extra_variant = random.choice(config.variants)
                assignments.append(extra_variant.name)
        offset = i % len(assignments)
        assignments = (
            assignments[offset:] + assignments[:offset]
        )  # apply latin-squares shifting

        judge_df["variant"] = assignments
        judge_df.to_csv(assignments_dir / f"user_{judge.id}.csv")


@app.command()
@typer_async
async def debate(
    exp_dir: Path,
    exp_config: Path,
    question_limit: int = 100,
    user_limit: int = 100,
):
    threads = 50
    config = load_exp_config(exp_config)
    load_path = exp_dir / "questions.csv"
    if not load_path.exists():
        raise ValueError("No load file found!")

    (exp_dir / "debates").mkdir(exist_ok=True)
    variant_names = [v.name for v in config.variants]
    assert len(variant_names) == len(
        set(variant_names)
    ), "Variant names must be unique!"
    semaphore = asyncio.Semaphore(threads)
    setup_environment(
        logger_level="debug",
        anthropic_tag="ANTHROPIC_API_KEY",
    )
    api_handler = ModelAPI(
        anthropic_num_threads=threads,
        openai_fraction_rate_limit=0.9,
        organization="DEFAULT_ORG",
    )

    debate_files = glob.glob(f"{exp_dir}/assignments/*.csv")
    for file in debate_files[:user_limit]:
        filepath = Path(file)
        full_df = pd.read_csv(filepath, keep_default_na=False, na_values=[""])
        df = full_df.head(question_limit)
        cache_dir = filepath.parent / f"cache_{filepath.stem}"
        jobs = []
        for i, (_, row) in enumerate(df.iterrows()):
            variant = find_variant_by_name(config.variants, row["variant"])
            jobs.append(
                run_debate(
                    index=i,
                    row=row,
                    cache_dir=cache_dir,
                    semaphore=semaphore,
                    api_handler=api_handler,
                    variant=variant,
                )
            )
        results = await asyncio.gather(*jobs)
        df.update(
            pd.DataFrame(
                {
                    "transcript": [result for result in results],
                    "complete": [True for _ in results],
                },
                index=df.index,
            )
        )
        full_df.update(df)
        full_df.to_csv(f"{exp_dir}/debates/{filepath.name}")


@app.command()
@typer_async
async def make_exp(
    exp_dir: Path,
    exp_config: Path,
    user_group: str,
    error_on_missing: Optional[bool] = True,
    error_on_existing: Optional[bool] = True,
):
    config = load_exp_config(exp_config)
    debate_files = glob.glob(f"{exp_dir}/debates/*.csv")
    group = UserRepository.find_group_by_name(user_group)
    assert group is not None

    if error_on_missing:
        user_ids = [int(name.split("_")[-1].split(".")[0]) for name in debate_files]
        assert set(user_ids) == set(group.user_ids)

    experiment = ExperimentRepository.find_by_name(config.experiment_config.name)
    if experiment is None:
        experiment = ExperimentRepository.create(config.experiment_config)
    assert experiment is not None

    for file in debate_files:
        df = pd.read_csv(file)
        user_id = int(file.split("_")[-1].split(".")[0])
        user = UserRepository.find_by_id(user_id)
        assert user is not None
        existing_exp_debates = DebateRepository.find_experiment_debates_for_user(
            user_id
        )
        existing_exp_debates = [
            d for d in existing_exp_debates if d.experiment_id == experiment.id
        ]
        if len(existing_exp_debates) > 0:
            if error_on_existing:
                raise ValueError(
                    f"User {user_id} already has debates for experiment {experiment.id}"
                )
            else:
                # if a user already has exp debates and we don't want to error we'll just skip importing this file
                # this is useful when we're onboarding new users to existing exps
                continue

        # randomize order of rows - users see debates in creation order so this avoids sequence effects
        df = df.sample(frac=1).reset_index(drop=True)
        for _, row in df.iterrows():
            variant = find_variant_by_name(config.variants, row["variant"])
            transcript = TranscriptConfig(**json.loads(row["transcript"]))
            assert transcript.story_title
            cross_examiner_config_path = (
                str(variant.cross_examiner_config)
                if variant.cross_examiner_config
                else None
            )
            DebateRepository.create(
                CreateDebateInput(
                    name=transcript.story_title,
                    max_turns=variant.max_steps,
                    min_turns=variant.min_steps,
                    method=variant.method,
                    allow_judge_interaction=bool(variant.allow_judge_interaction),
                    config_path=str(variant.debater_config),
                    cross_examiner_config_path=cross_examiner_config_path,
                    transcript=transcript,
                    experiment_id=experiment.id,
                    user_id=user.id,
                )
            )


@app.command()
@typer_async
async def export_results(
    output_dir: Path,
    user_group: str,
    experiment_id: Optional[str] = None,
    limit: Optional[int] = None,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    cols = [
        "debate_id",
        "user_name",
        "experiment_name",
        "debate_name",
        "question",
        "debate_method",
        "consultant_type",
        "interactive_judge",
        "debater_config",
        "swap",
        "max_turns_allowed",
        "min_turns_required",
        "turns_used",
        "transcript_char_count",
        "correct",
        "confidence_correct",
        "confidence",
        "judgement_time",
        "explanation",
        "answerability",
        "untimed_accuracy",
        "speed_accuracy",
        "context_required",
        "transcript",
        "dataset_split",
    ]
    rows = []
    users = UserRepository.find_users_by_group_name(user_group)
    dataset: List[quality.QualityQuestionsForArticle] = []
    for s in ["train", "dev"]:
        data = await quality.parse_dataset(s)
        for qs in data:
            qs.split = s
        dataset += data

    questions: List[quality.QuestionWithArticle] = quality.dataset_to_questions(dataset)
    for user in users:
        if limit and len(rows) > limit:
            continue
        debates = DebateRepository.find_completed_experiment_debates_for_user(user.id)
        for debate in sorted(debates, key=lambda d: d.id):
            if limit and len(rows) > limit:
                continue
            if experiment_id and debate.experiment_id != int(experiment_id):
                continue

            transcript = TranscriptConfig(**debate.transcript)
            if not transcript.story_title:
                raise ValueError(f"Debate {debate.id} has no story title!")
            question = quality.find_question(
                transcript.question, transcript.story_title, questions
            )
            if not question:
                raise ValueError(f"Could not find question for Debate {debate.id}")
            correct = debate.judgement.confidence_correct > 50
            confidence = None
            if correct:
                confidence = debate.judgement.confidence_correct
            else:
                confidence = 100 - debate.judgement.confidence_correct
            consultant_type = ""
            if debate.method == Method.consultancy:
                if transcript.names.correct:
                    consultant_type = "correct"
                else:
                    consultant_type = "incorrect"

            row = (
                debate.id,
                user.user_name,
                debate.experiment.name,
                debate.name,
                transcript.question,
                debate.method,
                consultant_type,
                debate.allow_judge_interaction,
                debate.config_path,
                transcript.swap,
                debate.max_turns,
                debate.min_turns,
                len(transcript.rounds),
                len(json.dumps(debate.transcript["rounds"])),
                correct,
                debate.judgement.confidence_correct,
                confidence,
                debate.judgement.created_at,
                debate.judgement.explanation,
                quality.answerability(question),
                quality.untimed_accuracy(question),
                quality.speed_accuracy(question),
                quality.context_required(question),
                debate.transcript,
                question.split,
            )
            rows.append(row)

    filename = (
        f"{user_group}_exp{experiment_id}_debates.csv"
        if experiment_id
        else f"{user_group}_all_debates.csv"
    )
    df = pd.DataFrame(rows, columns=cols)

    df.to_csv(output_dir / filename)


@app.command()
def export_transcripts_by_users(
    output_dir: Path, user_group: str, experiment_id: Optional[str] = None
):
    output_dir.mkdir(parents=True, exist_ok=True)
    cols = [
        "question",
        "correct answer",
        "negative answer",
        "transcript",
        "story",
        "answer_judge",
        "story_title",
        "complete",
    ]
    users = UserRepository.find_users_by_group_name(user_group)
    for user in users:
        rows = []
        debates = DebateRepository.find_completed_experiment_debates_for_user(user.id)
        for debate in sorted(debates, key=lambda d: d.judgement.created_at):
            if experiment_id and debate.experiment_id != int(experiment_id):
                continue

            judgement = debate.judgement
            answer = f"{judgement.explanation}\n\nConfidence correct: {judgement.confidence_correct / 100.0}"
            transcript = TranscriptConfig(**debate.transcript)
            row = (
                transcript.question,
                transcript.answers.correct,
                transcript.answers.incorrect,
                json.dumps(debate.transcript),
                transcript.story,
                answer,
                transcript.story_title,
                True,
            )
            rows.append(row)

        filename = f"{user.user_name}_judgement.csv"
        df = pd.DataFrame(rows, columns=cols)
        df.to_csv(output_dir / filename)


@app.command()
def export_transcripts_for_experiment(output_dir: Path, experiment_id: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    cols = [
        "question",
        "correct answer",
        "negative answer",
        "transcript",
        "story",
        "answer_judge",
        "story_title",
        "complete",
        "complete_judge",
    ]
    debates = DebateRepository.find_completed_debates_for_experiment(experiment_id)
    # mapping of output filenames to the rows that will go into them
    judge_files = {}
    debate_files = {}
    for debate in sorted(debates, key=lambda d: d.judgement.created_at):
        transcript = TranscriptConfig(**debate.transcript)
        method_type = None
        if debate.method == "consultancy":
            if transcript.names.correct:
                method_type = "correct"
            elif transcript.names.incorrect:
                method_type = "incorrect"
        elif debate.method == "debate":
            method_type = "sim"

        if method_type is None:
            raise ValueError()

        experiment_file_handler = Experiment(
            output_dir, debate.method, method_type, debate.allow_judge_interaction
        )
        judgement = debate.judgement
        user = debate.user
        if user.user_name == "pareto.test":
            continue
        if debate.allow_judge_interaction:
            transcript.names.judge = user.user_name
        transcript.extra["judge_name"] = user.user_name
        answer = f"{judgement.explanation}\n\nConfidence correct: {judgement.confidence_correct / 100.0}"
        row = (
            transcript.question,
            transcript.answers.correct,
            transcript.answers.incorrect,
            json.dumps(transcript.dict()),
            transcript.story,
            answer,
            transcript.story_title,
            True,
            True,
        )
        judge_filename = experiment_file_handler.get_judge_filename(
            "human_judge", swap=transcript.swap
        )
        debate_filename = experiment_file_handler.get_debate_filename(
            swap=transcript.swap
        )

        if judge_filename in judge_files:
            judge_files[judge_filename].append(row)
        else:
            judge_files[judge_filename] = [row]

        if debate_filename in debate_files:
            debate_files[debate_filename].append(row)
        else:
            debate_files[debate_filename] = [row]

    for judge_filename, rows in judge_files.items():
        df = pd.DataFrame(rows, columns=cols)
        judge_filename.parent.mkdir(exist_ok=True, parents=True)
        df.to_csv(judge_filename)

    for debate_filename, rows in debate_files.items():
        df = pd.DataFrame(rows, columns=cols)
        debate_filename.parent.mkdir(exist_ok=True, parents=True)
        df.to_csv(debate_filename)


if __name__ == "__main__":
    app()
