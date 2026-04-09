import secrets
from datetime import datetime, timedelta

import psycopg2
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

# ───────── App ─────────
app = FastAPI()

# ───────── Security Config ─────────
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt_sha256"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ───────── DB Config ─────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "users",
    "user": "postgres",
    "password": "asd12345679",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ───────── Init DB ─────────
def init_users_table():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
    conn.commit()
    conn.close()

init_users_table()

# ───────── Schemas ─────────
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# ───────── Password Utils ─────────
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# ───────── JWT Utils ─────────
def create_access_token(user_id: str):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ───────── Routes ─────────

@app.get("/")
def read_root():
    return {"message": "API is running"}

# 🔐 Signup
@app.post("/signup")
def signup(user: UserCreate):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        hashed_password = hash_password(user.password)

        cur.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (user.email, hashed_password)
        )
        conn.commit()

        return {"message": "User created successfully"}

    finally:
        cur.close()
        conn.close()

# 🔐 Login → returns JWT
@app.post("/login")
def login(user: UserLogin):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT id, email, password FROM users WHERE email = %s",
            (user.email,)
        )
        db_user = cur.fetchone()

        if not db_user:
            raise HTTPException(status_code=400, detail="Invalid email or password")

        user_id, email, hashed_password = db_user

        if not verify_password(user.password, hashed_password):
            raise HTTPException(status_code=400, detail="Invalid email or password")

        token = create_access_token(str(user_id))

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    finally:
        cur.close()
        conn.close()

# 🔒 Protected Route
@app.get("/protected")
def protected_route(user_id: str = Depends(get_current_user)):
    return {
        "message": "You are authenticated",
        "user_id": user_id
    }