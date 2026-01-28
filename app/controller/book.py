from app.dao.book import create, get_books
from app.schema.userSchema import Book
from fastapi import HTTPException
import math

async def create_book(book: Book, user_id: int):
    try:
        return await create(book, user_id)
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = str(e)
        )


async def get_book_list(userId: int, pageNo: int, limit: int):
    try:
        records, total_count = await get_books(userId, pageNo, limit)

        total_pages = math.ceil(total_count / limit)

        return {
            "data": [dict(record) for record in records],
            "total_pages": total_pages,
            "total_count": total_count,
            "page": pageNo,
            "limit": limit,
            "has_next": total_pages > pageNo,
            "has_prev": pageNo > 1
        }
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = str(e)
        )