from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from dao.users import get_users, create_user
from database import init_db
from serializer.user import UserCreate, UserMessage
from connectionManager import ConnectionManager
from callAI import stream_ai
from dotenv import load_dotenv
from agents import run_agent
load_dotenv()

app = FastAPI()


# @app.on_event("startup")
# async def startup():
#     await init_db()

manager = ConnectionManager()

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

@app.websocket("/ws/chat")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:    
        while True:
            data = await ws.receive_text()
            await ws.send_text(f"Echo: {data}")

    except WebSocketDisconnect:
        manager.disconnect(ws)

@app.websocket("/ws/chat-bot")
async def websocket_endpoint_for_bot(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()

            try:
                await ws.send_text(f"Your : {data} \n Assistat : ")
                async for chunk in stream_ai(data):
                    await ws.send_text(f"{chunk}")
            except Exception as e:
                await ws.send_text(f"⚠️ AI error, please try again: {e}")

    except WebSocketDisconnect:
        manager.disconnect(ws)

@app.post("/chat")
async def chat(data: UserMessage):
    user_message = data.message
    response = run_agent(user_message)
    return {"response": response}
