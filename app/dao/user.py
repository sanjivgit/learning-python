from ..schema.userSchema import User
from ..common.db import database 
from ..common.hashing import verify_password
from fastapi import HTTPException
from ..middleware.auth import create_access_token

async def login_user(user: User):

    async with database.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, name, username, password FROM users where username = $1", user.username)
        
        if not row:
            raise HTTPException(status_code=401, detail="Username or Password wrong")
        
        verified = verify_password(user.password, row["password"])
        if not verified:
            raise HTTPException(status_code=401, detail="Username or Password wrong")

        data = {
            "id": row["id"],
            "name": row["name"],
            "username": row["username"]
        }

        token = create_access_token(data=data)
        
        return {
            "access_token" : token,
            "token_type": "bearer",
            "id": row["id"],
            "name": row["name"],
            "username": row["username"]
        }
        # return {
        #     "access_token": token,
        #     "token_type": "bearer"
        # }

