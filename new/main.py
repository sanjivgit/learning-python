from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from dao.users import get_users, create_user
from database import init_db
from serializer.user import UserCreate

app = FastAPI()


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await get_users(db)
    return users

@app.post("/users")
async def create_users(user: UserCreate, db: AsyncSession = Depends(get_db)):
    users = await create_user(db, user.name, user.email)
    return users