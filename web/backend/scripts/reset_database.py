from sqlalchemy import inspect, text

from web.backend.database.connection import engine
from web.backend.database.models import Base


def main():
    raise ValueError("Stop. Don't. Bad idea.")
    with engine.connect() as connection:
        insp = inspect(engine)
        with connection.begin():
            for table in insp.get_table_names():
                connection.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
