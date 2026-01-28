from fastapi import APIRouter, Depends
from ..schema.userSchema import User
from ..controller.userController import login
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

router = APIRouter()

@router.post("/login")
async def login_user(user: User):
    return await login(user)

@router.post("/token")
async def generate_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    return await login(form_data)