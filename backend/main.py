import io
import tempfile
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Load environment variables before any configuration or imports that need them.
load_dotenv()

from agents import run_chat_turn, run_career_scholarship_crew, MAX_TURNS
from database import init_db, save_chat, get_all_chats, get_chat, delete_chat

# Production logging: default to WARNING unless LOG_LEVEL is set.
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))
# Suppress noisy third-party logs in the terminal; our own logger still reports errors.
logging.getLogger("crewai.flow.runtime").setLevel(logging.CRITICAL)
logging.getLogger("crewai").setLevel(logging.CRITICAL)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(title="Career & Scholarship AI Agent API")

init_db()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatInput(BaseModel):
    messages: List[ChatMessage]
    turn: int

class SaveChatInput(BaseModel):
    userId: str
    id: str
    title: str
    messages: List[ChatMessage]
    turn: int
    isFinal: bool
    started: bool

class RecommendationInput(BaseModel):
    profile_text: str
    answers: str

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts).strip()
    except Exception as e:
        raise ValueError(f"Could not read PDF: {str(e)}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        doc = Document(tmp_path)
        text_parts = [paragraph.text for paragraph in doc.paragraphs]
        os.unlink(tmp_path)
        return "\n".join(text_parts).strip()
    except Exception as e:
        raise ValueError(f"Could not read DOCX: {str(e)}")


@app.get("/")
def home():
    return {"status": "Backend Server Running Successfully!"}

@app.post("/chat")
def chat(data: ChatInput):
    try:
        messages = [{"role": m.role, "content": m.content} for m in data.messages]
        reply, is_final = run_chat_turn(messages, data.turn)
        return {"reply": reply, "is_final": is_final}
    except Exception as e:
        error_text = str(e)
        # Produce a concise log line without the full Groq JSON payload.
        concise = error_text
        if "Rate limit reached" in error_text:
            concise = "Groq rate limit reached"
        elif "does not exist" in error_text.lower():
            concise = "Model not found"
        elif "decommissioned" in error_text.lower():
            concise = "Model decommissioned"
        logger.error("Chat endpoint failed: %s", concise)
        logger.debug("Chat endpoint traceback", exc_info=True)
        # Return a concise, user-friendly message.
        if "rate limit" in error_text.lower():
            user_msg = "Groq daily token limit reached. Please wait a few minutes and try again, or upgrade your Groq plan."
        else:
            user_msg = concise
        raise HTTPException(status_code=500, detail=f"Chat failed: {user_msg}")

@app.get("/chats")
def list_chats(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    return {"chats": get_all_chats(user_id)}


@app.get("/chats/{chat_id}")
def read_chat(chat_id: str, user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    chat = get_chat(user_id, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@app.post("/chats")
def create_or_update_chat(data: SaveChatInput):
    try:
        save_chat(
            data.userId,
            data.id,
            data.title,
            [{"role": m.role, "content": m.content} for m in data.messages],
            data.turn,
            data.isFinal,
            data.started,
        )
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save chat: {str(e)}")


@app.delete("/chats/{chat_id}")
def remove_chat(chat_id: str, user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        delete_chat(user_id, chat_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {str(e)}")


@app.post("/upload")
def upload_document(file: UploadFile = File(...)):
    try:
        content = file.file.read()
        filename = file.filename.lower()

        if filename.endswith(".txt"):
            text = content.decode("utf-8").strip()
        elif filename.endswith(".pdf"):
            text = extract_text_from_pdf(content)
        elif filename.endswith(".docx"):
            text = extract_text_from_docx(content)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload .txt, .pdf, or .docx."
            )

        if not text:
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the file."
            )

        preview = text[:2000]
        if len(text) > 2000:
            preview += "\n\n[Document truncated. Only the first 2000 characters were extracted.]"

        return {
            "filename": file.filename,
            "extracted_text": preview,
            "length": len(text)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/recommend")
def get_recommendation(data: RecommendationInput):
    try:
        result = run_career_scholarship_crew(data.profile_text, data.answers)
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {str(e)}"
        )

@app.post("/advisor")
def get_advisor_recommendation(data: RecommendationInput):
    try:
        result = run_career_scholarship_crew(data.profile_text, data.answers)
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {str(e)}"
        )
