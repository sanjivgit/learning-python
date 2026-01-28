from fastapi import APIRouter, Depends
from ..schema.userSchema import Book
from app.controller.book import create_book, get_book_list
from app.middleware.auth import get_current_user

router = APIRouter()

@router.post("/create/book")
async def create(book: Book, user_id: dict = Depends(get_current_user)):
    return await create_book(book, user_id)

@router.get("/book/list")
async def get_books(limit, pageNo, user_id: dict = Depends(get_current_user)):
    return await get_book_list(user_id, int(pageNo), int(limit))