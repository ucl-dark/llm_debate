from fastapi import APIRouter, HTTPException, Response

import web.backend.api.schemas as schemas
from web.backend.repositories.user_repository import UserRepository

router = APIRouter()


class LoginPayload(schemas.Model):
    user_name: str


@router.post("/login")
def login(response: Response, payload: LoginPayload):
    user = UserRepository.find_by_name(payload.user_name)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    response.set_cookie(key="user_id", value=str(user.id))

    return {"success": True}


@router.get("/{user_id}")
def getUser(user_id: str):
    user = UserRepository.find_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return schemas.User(**user.__dict__)
