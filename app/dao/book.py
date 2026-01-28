from app.common.db import database
from app.schema.userSchema import Book

async def create(book:Book, user_id: int):
    query = """
    INSERT INTO books (user_id, name, author, price, description, quantity, isbn) values ($1, $2, $3, $4, $5, $6, $7) RETURNING *
    """
    async with database.pool.acquire() as conn:
        row = await conn.fetchrow(query, user_id, book.name, book.author, book.price, book.description, book.quantity, book.isbn)
        return dict(row)


async def get_books(userId: int, pageNo: int, limit: int):
    offset = (pageNo - 1) * limit
    query = """
    SELECT id, user_id, name as book_name, author, description, price, quantity, isbn from books where user_id = $1 limit $2 offset $3
    """

    count_query = """
    SELECT COUNT(*) from books where user_id = $1
    """

    async with database.pool.acquire() as conn:
        records = await conn.fetch(query, userId, limit, offset)
        total_count = await conn.fetchval(count_query, userId)
        return records, total_count