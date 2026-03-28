import os
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from backend.database.models import get_db_connection
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finclosepilot_super_secret_key_123456789")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: str

def verify_password(plain_password, hashed_password):
    import hashlib
    sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    try:
        return bcrypt.checkpw(sha256_hash.encode(), hashed_password.encode())
    except Exception:
        return False

def get_password_hash(password):
    import hashlib
    sha256_hash = hashlib.sha256(password.encode()).hexdigest()
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(sha256_hash.encode(), salt).decode()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(username: str):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = %s", (username,)).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def get_user_by_email(email: str):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
        
    user_dict = get_user(token_data.username)
    if user_dict is None:
        raise credentials_exception
        
    return User(
        id=user_dict["id"],
        username=user_dict["username"],
        email=user_dict["email"],
        role=user_dict["role"],
        created_at=user_dict["created_at"]
    )

def check_manager_role(user: User = Depends(get_current_user)):
    if user.role != "MANAGER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to Managers only"
        )
    return user
