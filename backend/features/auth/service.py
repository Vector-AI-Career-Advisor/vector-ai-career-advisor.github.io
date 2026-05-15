from fastapi import HTTPException
from db.postgres import get_connection
from core.security import hash_password, verify_password, create_access_token
from features.auth.schemas import UserCreate, UserLogin, TokenResponse


def signup(user: UserCreate):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

            cur.execute(
                "INSERT INTO users (email, password) VALUES (%s, %s)",
                (user.email, hash_password(user.password)),
            )
        conn.commit()
        return {"message": "Account created successfully"}
    finally:
        conn.close()


def login(user: UserLogin) -> TokenResponse:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password FROM users WHERE email = %s", (user.email,)
            )
            row = cur.fetchone()

        if not row or not verify_password(user.password, row[1]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return TokenResponse(access_token=create_access_token(row[0]))
    finally:
        conn.close()


def get_me(user_id: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, created_at FROM users WHERE id = %s",
                (int(user_id),),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return {"email": row[0], "created_at": row[1]}
    finally:
        conn.close()
