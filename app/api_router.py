from fastapi import APIRouter
from .routers import users, books

router = APIRouter()

router.include_router(users.router, tags=["user"])
router.include_router(books.router, tags=["books"])