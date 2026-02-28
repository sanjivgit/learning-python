from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from model.user import Base

DATABASE_URL="postgresql+asyncpg://postgres:Postgres%402024@localhost:5432/mydb"

GROQ_API_KEY=""

engine = create_async_engine(
    DATABASE_URL,
    echo=True,          # logs SQL (good for learning)
    pool_size=10,       # connection pool
    max_overflow=20
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
