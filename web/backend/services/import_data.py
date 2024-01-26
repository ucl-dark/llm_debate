import datetime
import os

import pandas as pd
from sqlalchemy import select
from tqdm import tqdm

import web.backend.database.models as models
from web.backend.database.connection import SessionLocal

REQUIRED_COLS = [
    "question",
    "correct answer",
    "negative answer",
    "transcript",
]


def should_import(path):
    try:
        file = path.split("/")[-1]
        if not file.endswith(".csv"):
            return False
        with open(path, "r") as f:
            header_line = f.readline().strip()
        columns = header_line.split(",")
        if any(col not in columns for col in REQUIRED_COLS):
            return False
        return True
    except Exception as e:
        print(e)
        return False


def delete_db_file_if_exists(session, path):
    existing_db_file = session.scalar(
        select(models.File).where(models.File.path == path)
    )
    if existing_db_file:
        session.delete(existing_db_file)
        session.commit()
        return True

    return False


def create_db_file(path):
    creation_time = datetime.datetime.fromtimestamp(os.path.getctime(path))

    db_file = models.File(path=path, created_at=creation_time)

    return db_file


def well_formed_debate(row):
    # TODO: This is broken for open-ended because answer cols are different
    if any(col not in row.index or row[col] == "" for col in REQUIRED_COLS):
        return False

    return True


def find_or_create_question(session, row):
    question_text = row["question"]
    correct_answer = row["correct answer"]
    incorrect_answer = row["negative answer"]

    question = session.scalar(
        select(models.Question).where(
            models.Question.question_text == question_text,
            models.Question.correct_answer == correct_answer,
            models.Question.incorrect_answer == incorrect_answer,
        )
    )

    if not question:
        question = models.Question(
            question_text=question_text,
            correct_answer=correct_answer,
            incorrect_answer=incorrect_answer,
        )

    return question


def create_db_row(row, row_number, question, db_file):
    db_row = models.Row(
        file=db_file,
        row_number=row_number,
        transcript=row["transcript"],
        judgement_text=row["answer_judge"],
        question=question,
    )

    return db_row


def import_csv(session, path):
    try:
        delete_db_file_if_exists(session, path)
        db_file = create_db_file(path)
        string_cols = [
            "correct answer",
            "negative answer",
            "transcript",
            "question",
        ]
        dtype_dict = {col: str for col in string_cols}
        df = pd.read_csv(path, dtype=dtype_dict)
        if not "answer_judge" in df.columns:
            df["answer_judge"] = ""

        new_debate_count = 0
        bad_rows = []
        for i, row in df.iterrows():
            if not well_formed_debate(row):
                bad_rows.append(f'"{path} row {i}"')
                continue

            for col in string_cols:
                row[col] = str(row[col]).strip()

            question = find_or_create_question(session, row)
            db_row = create_db_row(row, i + 1, question, db_file)
            db_file.rows.append(db_row)
            new_debate_count += 1

        db_file.imported_at = datetime.datetime.now()
        db_file.import_complete = True
        session.add(db_file)
        session.commit()

        # TODO: Add url to row
        # df.to_csv(path_or_buf=path, index=False)
    except BaseException as e:
        print(f"Error importing debate at {path}: {e}")
        raise e
    return new_debate_count, bad_rows


def already_imported(path, db_files):
    existing_db_files = [f for f in db_files if f.path == path]
    if len(existing_db_files) > 0:
        db_file = existing_db_files[0]
        file_modified_at = os.path.getmtime(path)
        return (
            file_modified_at < db_file.imported_at.timestamp() + 30
            and db_file.import_complete is True
        )


def import_dir(data_dir):
    # recursively import all csv files in data_dir
    session = SessionLocal()
    start = datetime.datetime.now()
    files_imported = 0
    debates_imported = 0
    bad_rows = []
    db_files = session.execute(select(models.File)).scalars().all()
    imported_files = []
    data_files = []
    with session:
        for dirpath, _, filenames in os.walk(data_dir, followlinks=True):
            data_files += [os.path.join(dirpath, f) for f in filenames]

        for path in tqdm(data_files, desc="Importing files"):
            if already_imported(path, db_files):
                imported_files.append(path)
                continue

            if not should_import(path):
                continue

            results = import_csv(session, path)
            if results:
                imported_files.append(path)
                new_debate_count, bads = results
                files_imported += 1
                debates_imported += new_debate_count
                bad_rows += bads

        # delete any db files that are no longer in the data dir
        remaining_files = [f for f in db_files if f.path not in imported_files]
        for db_file in remaining_files:
            session.delete(db_file)
            session.commit()

    print(
        f"Imported {files_imported} files and {debates_imported} debates in {datetime.datetime.now() - start}. Deleted {len(remaining_files)} files."
    )
    print(f"Skipped { len(bad_rows) } bad rows")
