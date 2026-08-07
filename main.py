from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from backend.resume_parser import extract_text_from_pdf, parse_resume
from backend.interview import create_session, get_session, chat
import os
from backend.speech import speech_to_text

app = FastAPI(title="AI模拟面试系统", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/speech-to-text")
async def speech_api(file: UploadFile = File(...)):
    path = f"temp_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())

    text = speech_to_text(path, token=os.getenv("ASR_TOKEN"))

    os.remove(path)

    return {"text": text}

@app.get("/")
def root():
    return {"msg": "AI Interview Backend is running", "docs": "/docs"}


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    text = extract_text_from_pdf(file_path)
    result = parse_resume(text)
    os.remove(file_path)
    return {"filename": file.filename, "result": result}


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