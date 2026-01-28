from fastapi import FastAPI
from .api_router import router
from .models.user import create_users_table
from app.models.book import create_books_table, create_transactions_table
from .common.db import database

app = FastAPI()

app.include_router(router)

@app.on_event("startup")
async def on_startup():
    await database.connect()
    await create_users_table()
    await create_books_table()
    await create_transactions_table()

@app.get("/")
async def root():
    return {"message": "Hello World"}