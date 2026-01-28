from app.common.db import database

async def create_books_table():
    query = """
    CREATE TABLE IF NOT EXISTS books (
     id SERIAL PRIMARY KEY,
     user_id INT NOT NULL,
     name VARCHAR(100) NOT NULL,
     author VARCHAR(100) NOT NULL,
     isbn VARCHAR(50) NOT NULL UNIQUE,
     price Float,
     quantity INT,
     description TEXT
    )
    """
    async with database.pool.acquire() as conn:
        await conn.execute(query)


async def create_students_table():
    qeury = """
    CREATE TABLE IF NOT EXISTS students (
     id serial primary key,
     roll_no int not null,
     class VARCHAR(20) not null,
     about text,
     constraint unique_class_roll_no UNIQUE(class, roll_no)
    )
    """

async def create_transactions_table():
    enum_query = """
    DO $$
    BEGIN
    IF NOT EXISTS (
        SELECT 1 from pg_type where pg_type.typname = 'transaction_status'
    ) THEN CREATE TYPE transaction_status as ENUM ('issued', 'returned');
    
    END IF;

    END$$
    """


    query = """
    CREATE TABLE IF NOT EXISTS transactions (
    id serial primary key,
    student_id int not null,
    book_id int not null,
    issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    returned TIMESTAMP,
    status transaction_status DEFAULT "issued",
    )
    """

    async with database.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT typname from pg_type where pg_type.typname = 'transaction_status'")
        if not row:
            print("Not exist")
            await conn.execute("CREATE TYPE transaction_status as ENUM ('issued', 'returned')")
        else:
            print("already exist")

        
