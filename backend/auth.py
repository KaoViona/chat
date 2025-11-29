# auth.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import os
from fastapi import HTTPException, Header
from typing import Optional

# -----------------------------
# 密碼 Hash 設定
# -----------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------------------
# JWT 設定
# -----------------------------
# 固定秘密字串測試用，正式部署請設環境變數
JWT_SECRET = os.environ.get("JWT_SECRET", "change_this_secret")
JWT_ALGO = "HS256"
JWT_EXPIRE_MINUTES = 60*24  # 1 day

# -----------------------------
# 密碼函式
# -----------------------------
def hash_password(plain: str) -> str:
    """Hash 密碼，bcrypt 最多 72 bytes"""
    truncated = plain[:72]
    return pwd_context.hash(truncated)

def verify_password(plain: str, hashed: str) -> bool:
    """驗證密碼"""
    truncated = plain[:72]
    return pwd_context.verify(truncated, hashed)

# -----------------------------
# JWT 函式
# -----------------------------
def create_token(user_id: int, username: str) -> str:
    """生成 JWT token"""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def decode_token(token: str) -> dict:
    """解碼 JWT token"""
    try:
        # 去掉 token 前後空白，避免出現 Invalid token
        token = token.strip()
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

# -----------------------------
# 取得目前使用者
# -----------------------------
def get_current_user(authorization: Optional[str] = Header(None)):
    """
    從 Authorization Header 取得使用者資訊
    Header 格式: Authorization: Bearer <token>
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    scheme, _, token = authorization.partition(" ")
    
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid auth scheme")
    
    # 解碼 token
    return decode_token(token)
