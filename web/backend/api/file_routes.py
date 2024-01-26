from typing import Optional, Union

from fastapi import APIRouter, HTTPException

import web.backend.api.schemas as schemas
from core.agents.debater_base import TranscriptConfig
from web.backend.repositories.file_repository import FileRepository
from web.backend.services.parser import TranscriptParser
from web.backend.utils import create_path_hash, get_judge_model

router = APIRouter()


class GetFileResponseRow(schemas.Row):
    question: schemas.Question
    is_judgement_correct: Union[bool, None] = None


class GetFileResponse(schemas.File):
    rows: list[GetFileResponseRow]


@router.get("/{path_hash}", response_model=GetFileResponse)
def get_file(path_hash):
    # TODO: pagination
    if path_hash == "random":
        file = FileRepository.find_random(True)
    else:
        file = FileRepository.find_by_path_hash(path_hash, True)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    response_rows = [
        GetFileResponseRow(
            **r.__dict__,
            is_judgement_correct=TranscriptParser.is_judgement_correct(file, r),
        )
        for r in file.rows
    ]

    file_dict = file.__dict__
    file_dict["rows"] = sorted(response_rows, key=lambda x: x.row_number)
    response = GetFileResponse(**file_dict, path_hash=create_path_hash(file.path))
    return response


class GetFilesResponseItem(schemas.File):
    row_count: Union[int, None] = None


@router.get("", response_model=list[GetFilesResponseItem])
def get_files():
    files = FileRepository.find_all()

    response = [
        GetFilesResponseItem(
            **f.__dict__, row_count=rc, path_hash=create_path_hash(f.path)
        )
        for f, rc in files
    ]

    return response


class Judgement(schemas.Model):
    judgement_text: str
    judge_name: str
    is_correct: Optional[bool]


class GetRowResponse(schemas.Row):
    question: schemas.Question
    file: schemas.File
    raw_transcript: str
    transcript: Optional[TranscriptConfig]
    judgement: Optional[Judgement]
    next_available: Optional[bool]


@router.get("/{path_hash}/row/{row_number}", response_model=GetRowResponse)
def get_row(path_hash: str, row_number: str):
    if path_hash == "random":
        file = FileRepository.find_random()
    else:
        file = FileRepository.find_by_path_hash(path_hash)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    row = FileRepository.find_row_for_file(file.id, int(row_number))

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    next_row = FileRepository.find_row_for_file(file.id, int(row_number) + 1)

    transcript = TranscriptParser.parse(file, row)
    if transcript.story is not None:
        transcript, _ = TranscriptParser.verify_strict(transcript)
    response_file = schemas.File(**file.__dict__, path_hash=create_path_hash(file.path))
    if row.judgement_text and len(row.judgement_text.strip()) > 0:
        judgement = Judgement(
            judgement_text=row.judgement_text,
            judge_name=get_judge_model(file.path),
            is_correct=TranscriptParser.is_judgement_correct(file, row),
        )
    else:
        judgement = None

    response = GetRowResponse(
        id=row.id,
        row_number=row.row_number,
        file=response_file,
        question=row.question,
        transcript=transcript,
        judgement=judgement,
        raw_transcript=row.transcript,
        next_available=True if next_row else False,
    )

    return response
