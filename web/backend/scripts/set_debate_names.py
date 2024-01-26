from web.backend.repositories.debate_repository import DebateRepository
from web.backend.utils import create_debate_name

PLACEHOLDER_NAMES = ["", "debate"]


def main():
    for debate in DebateRepository.find_all():
        if debate.name in PLACEHOLDER_NAMES:
            story_title = debate.transcript["story"].splitlines()[0]
            debate.name = create_debate_name(story_title)
            DebateRepository.commit(debate)


if __name__ == "__main__":
    main()
