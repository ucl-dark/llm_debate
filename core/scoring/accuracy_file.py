import typer

from core.scoring.accuracy import score_file

if __name__ == "__main__":
    typer.run(score_file)
