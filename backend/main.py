# main.py
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer
from sqlmodel import select
from pydantic import BaseModel

# 同層 import，避免找不到模組
from db import init_db, get_session
from models import User, Message
from auth import hash_password, verify_password, create_token, get_current_user
from llm_client import generate_reply

# ========================================
# Security
# ========================================
security = HTTPBearer()  # 讓 Swagger UI 出現鎖頭 Authorize

# ========================================
# FastAPI App
# ========================================
app = FastAPI(
    title="Chat Room API",
    description="A secured chat API with JWT Auth",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發階段允許全部
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 初始化
init_db()

# ========================================
# Pydantic Models
# ========================================
class RegisterIn(BaseModel):
    username: str
    password: str

class LoginIn(BaseModel):
    username: str
    password: str

class ChatIn(BaseModel):
    content: str

# ========================================
# Auth APIs
# ========================================
@app.post("/auth/register")
def register(data: RegisterIn, session=Depends(get_session)):
    exists = session.exec(select(User).where(User.username == data.username)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=data.username, hashed_password=hash_password(data.password))
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_token(user.id, user.username)
    return {"token": token, "username": user.username, "user_id": user.id}


@app.post("/auth/login")
def login(data: LoginIn, session=Depends(get_session)):
    user = session.exec(select(User).where(User.username == data.username)).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user.id, user.username)
    return {"token": token, "username": user.username, "user_id": user.id}

# ========================================
# Chat APIs (Secured)
# ========================================
@app.get("/chat/history", dependencies=[Depends(security)])
def get_history(session=Depends(get_session), auth=Depends(get_current_user)):
    user_id = auth["sub"]
    msgs = session.exec(
        select(Message).where(Message.user_id == user_id).order_by(Message.created_at)
    ).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]


@app.post("/chat/send", dependencies=[Depends(security)])
async def send_message(payload: ChatIn, session=Depends(get_session), auth=Depends(get_current_user)):
    user_id = auth["sub"]

    # 儲存使用者訊息
    user_msg = Message(user_id=user_id, role="user", content=payload.content)
    session.add(user_msg)
    session.commit()
    session.refresh(user_msg)

    # 將歷史紀錄傳給 LLM
    msgs = session.exec(
        select(Message).where(Message.user_id == user_id).order_by(Message.created_at)
    ).all()
    history = [{"role": m.role, "content": m.content} for m in msgs]

    try:
        reply = await generate_reply(history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # 儲存 AI 訊息
    assistant_msg = Message(user_id=user_id, role="assistant", content=reply)
    session.add(assistant_msg)
    session.commit()
    session.refresh(assistant_msg)

    return {"reply": reply}

# ========================================
# serve 前端
# ========================================
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))

# 若有 assets 資料夾，可掛載
ASSETS_PATH = os.path.join(FRONTEND_PATH, "assets")
if os.path.exists(ASSETS_PATH):
    app.mount("/assets", StaticFiles(directory=ASSETS_PATH), name="assets")
