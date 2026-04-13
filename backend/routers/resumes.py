from __future__ import annotations
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import pypdf

from core.security import get_current_user
from db.database import get_connection

router = APIRouter()


def _extract_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


@router.post("/upload", status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    contents = await file.read()
    text = _extract_text(contents)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO resumes (user_id, filename, content)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                    SET filename    = EXCLUDED.filename,
                        content     = EXCLUDED.content,
                        updated_at  = NOW()
                """,
                (int(user_id), file.filename, text),
            )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Resume uploaded successfully", "filename": file.filename}


@router.get("/me")
def get_my_resume(user_id: str = Depends(get_current_user)):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT filename, content, uploaded_at, updated_at FROM resumes WHERE user_id = %s",
                (int(user_id),),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="No resume on file")

    return {
        "filename":    row[0],
        "content":     row[1],
        "uploaded_at": row[2],
        "updated_at":  row[3],
    }


@router.delete("/me", status_code=204)
def delete_my_resume(user_id: str = Depends(get_current_user)):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM resumes WHERE user_id = %s", (int(user_id),))
        conn.commit()
    finally:
        conn.close()
