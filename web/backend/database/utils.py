from web.backend.utils import load_secrets


def get_database_url():
    secrets = load_secrets("SECRETS")
    # secrets = load_secrets("PROD_SECRETS")
    user = secrets["DB_USER"]
    password = secrets["DB_PASSWORD"]
    host = secrets["DB_HOST"]
    port = secrets["DB_PORT"]
    database = secrets["DB_NAME"]

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"
