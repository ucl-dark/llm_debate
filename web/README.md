# Web

## Install

A recent version of Node should be installed. Check the version with `node -v`. If it's less than v18 then follow the instructions [here](https://github.com/nodesource/distributions#using-debian-as-root) to install it.

The backend dependencies are in the repo's `requirements.txt`, so simply `pip install -r requirements.txt` in the project root.

To install the frontend dependencies, cd into `web/frontend` and run `npm install`

You'll also need to install Postgres and create a database for the project.

Create a `SECRETS` file in the project root with the database creds:

```
DB_USER=<insert value>
DB_PASSWORD=<insert value>
DB_HOST=localhost
DB_PORT=5432
DB_NAME=<insert value>
```

The OpenAI API keys and orgs also go in the SECRETS file.

Install postgres. On Mac run this:

```
brew install postgresql
brew services start postgresql
createuser -P psqluser
createdb -O psqluser debate
psql -U psqluser -d debate
INSERT INTO users (user_name, full_name, admin) VALUES ('john.h', 'John Hughes', TRUE);
```

To create the database schema, run `python -m web.backend.scripts.reset_database` from the project root (uncomment the raise errorif you are local otherwise don't run this).

To import csv files into the frontend, run `SQLALCHEMY_ECHO=0 .venv/bin/python -m web.backend.scripts.import --dir <Your data dir>`

## Running

Backend: From the project root, run `uvicorn web.backend.main:app --reload`

Frontend: From `web/frontend` run `npm run dev`
