import pprint

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse

from core.utils import setup_environment
from web.backend.api import (
    debate_routes,
    experiment_routes,
    file_routes,
    nyu_routes,
    playground_routes,
    user_routes,
)

app = FastAPI()


@app.exception_handler(ResponseValidationError)
async def validation_exception_handler(response, exc):
    pp = pprint.PrettyPrinter(indent=4)
    err = exc.__dict__["_errors"][0]
    print("RESPONSE VALIDATION ERROR:")
    pp.pprint(err)
    return JSONResponse(str(exc), status_code=500)


root = APIRouter()


@root.get("/")
def read_root():
    return {"Hello": "World"}


setup_environment(
    logger_level="debug",
    anthropic_tag="ANTHROPIC_API_KEY",
)

app.include_router(root, prefix="/api")
app.include_router(file_routes.router, prefix="/api/files")
app.include_router(playground_routes.router, prefix="/api/playground")
app.include_router(experiment_routes.router, prefix="/api/experiments")
app.include_router(debate_routes.router, prefix="/api/debates")
app.include_router(user_routes.router, prefix="/api/users")

app.include_router(nyu_routes.router)
