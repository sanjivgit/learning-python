from pydantic import BaseModel

class User(BaseModel):
    username: str
    password: str

class Book(BaseModel):
    name: str
    author: str
    price: float
    quantity: int
    description: str
    isbn: str
