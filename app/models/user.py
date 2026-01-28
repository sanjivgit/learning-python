from ..common.db import database
from ..common.hashing import get_password_hash

async def insert_user_data():
    query = """
    INSERT INTO users (name, username, password) VALUES ($1, $2, $3)
    """
    username = "sanjiv@123"
    password = "123456"

    hashed_password =  get_password_hash(password)
    
    async with database.pool.acquire() as conn:
            
        isExist = await conn.fetchrow("SELECT username FROM users where username = $1", username)
        
        if not isExist:
            await conn.execute(query, "sanjiv", username, hashed_password)
            print("user data inserted into users table")
            
        else:
            print("user already exist")
        



async def create_users_table():
    query = """
    CREATE TABLE IF NOT EXISTS users (
     id SERIAL PRIMARY KEY,
     name VARCHAR(100) NOT NULL,
     username VARCHAR(100) NOT NULL UNIQUE,
     password TEXT NOT NULL
    )
    """

    async with database.pool.acquire() as conn:
        await conn.execute(query)
        print("users table created successfully")
    

    await insert_user_data()