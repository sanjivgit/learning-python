from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class UserMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)