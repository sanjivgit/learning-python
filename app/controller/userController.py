from ..schema.userSchema import User
from app.dao.user import login_user

async def login(user: User):
    return await login_user(user)
