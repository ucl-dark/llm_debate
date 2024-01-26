from pprint import pprint

from sqlalchemy import select

import web.backend.database.models as models
from web.backend.database.connection import SessionLocal
from web.backend.services.parser import TranscriptParser


def main():
    session = SessionLocal()
    with session:
        files = session.execute(select(models.File)).all()
        failures = []
        for item in reversed(files):
            file: models.File = item[0]
            for row in file.rows:
                transcript = TranscriptParser.parse(file, row)
                correct = TranscriptParser.is_judgement_correct(file, row)
                if transcript is None:
                    failures.append((file.path, row.row_number))
                    break

        pprint(failures)
        print(f"{len(failures)} failures")


if __name__ == "__main__":
    main()
