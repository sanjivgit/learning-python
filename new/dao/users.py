from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from model.user import User

async def create_user(db: AsyncSession, name: str, email: str):
    stmt = insert(User).values(name=name, email=email)
    await db.execute(stmt)
    await db.commit()


async def get_users(db: AsyncSession):
    stmt = select(User)
    result = await db.execute(stmt)
    return result.scalars().all()