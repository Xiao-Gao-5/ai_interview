from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.interview import chat, create_session, get_session
from backend.llm import list_models
from backend.resume_parser import extract_text_from_pdf, parse_resume

app = FastAPI(title="AI Interview Backend", version="2.0.0")

BASE_DIR = Path(__file__).resolve().parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_upload_tmp(file: UploadFile, suffix: str | None = None) -> str:
    suffix = suffix or Path(file.filename or "").suffix
    fd, path = tempfile.mkstemp(prefix="ai_interview_", suffix=suffix)
    os.close(fd)
    return path


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/models")
def models():
    return list_models()


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    path = _save_upload_tmp(file, ".pdf")
    try:
        with open(path, "wb") as out:
            out.write(await file.read())
        text = extract_text_from_pdf(path)
        result = parse_resume(text)
        return {"filename": file.filename, "result": result}
    finally:
        if os.path.exists(path):
            os.remove(path)


@app.post("/start-interview")
async def start_interview(resume: dict):
    session_id = create_session(resume)
    reply, is_end = chat(session_id, None)
    return {"session_id": session_id, "reply": reply, "is_end": is_end}


@app.post("/chat")
async def interview_chat(data: dict):
    session_id = data.get("session_id")
    user_msg = data.get("message", "")
    if not session_id:
        return {"error": "缺少 session_id"}

    reply, is_end = chat(session_id, user_msg)
    if reply is None:
        return {"error": "会话不存在"}
    return {"reply": reply, "is_end": is_end}


@app.post("/end-interview")
async def end_interview(data: dict):
    session_id = data.get("session_id")
    session = get_session(session_id)
    if not session:
        return {"error": "会话不存在"}

    session.phase = "scoring"
    reply, is_end = chat(session_id, "用户主动结束面试")
    return {"reply": reply, "is_end": is_end}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
