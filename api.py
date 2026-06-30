from fastapi import FastAPI, HTTPException, Depends, Header  # type: ignore
import os
from fastapi.responses import HTMLResponse, Response  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from pydantic import BaseModel  # type: ignore
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Table, MetaData, text  # type: ignore

from genai import GenAI
import rag_store

DB_URL = "sqlite:///./faqs.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

faqs = Table(
    "faqs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("question", Text, nullable=False),
    Column("answer", Text, nullable=False),
    Column("tags", String(200), nullable=True),
)


def init_db():
    metadata.create_all(engine)
    conn = engine.raw_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS faqs_fts USING fts5(question, answer, content='faqs', content_rowid='id')"
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


init_db()
# sessionmaker is available if needed; create sessions via `sessionmaker(bind=engine)` when required

app = FastAPI(title="College FAQ Chatbot API")
genai = GenAI()

# Serve static browser UI from the `static` folder (chat + admin pages)
app.mount("/static", StaticFiles(directory="static"), name="static")


def _check_api_key(x_api_key: str = Header(None)):
    """Simple API key check using `ADMIN_API_KEY` env var."""
    expected = os.getenv("ADMIN_API_KEY")
    if expected is None:
        # no admin key configured — deny admin access
        raise HTTPException(status_code=403, detail="Admin API key not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Enable CORS so the chat UI (served from this app or elsewhere) can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: static UI was removed by request; this service provides API endpoints only.


@app.get("/", response_class=HTMLResponse)
def home():
        return """
        <html>
            <head>
                <meta charset='utf-8'/>
                <title>College FAQ Chatbot API</title>
            </head>
            <body>
                <h2>College FAQ Chatbot API</h2>
                <p>Use the <a href="/docs">OpenAPI docs</a> to explore the API.</p>
            </body>
        </html>
        """


@app.get("/favicon.ico")
def favicon():
        # no favicon provided; return empty success to avoid 404 noise
        return Response(status_code=204)


@app.get("/health")
def health():
        return {"status": "ok"}


class FAQCreate(BaseModel):
    question: str
    answer: str
    tags: Optional[List[str]] = None


class FAQOut(BaseModel):
    id: int
    question: str
    answer: str
    tags: Optional[List[str]] = None


class SearchResponse(BaseModel):
    answer: str
    sources: List[int]
    matches: List[FAQOut]


@app.post("/faqs", response_model=FAQOut)
def add_faq(payload: FAQCreate):
    with engine.begin() as conn:
        res = conn.execute(
            faqs.insert().values(
                question=payload.question, answer=payload.answer, tags=",".join(payload.tags) if payload.tags else None
            )
        )
        # try to obtain the inserted row id in a portable way
        try:
            rowid = None
            if hasattr(res, "inserted_primary_key") and res.inserted_primary_key:
                rowid = res.inserted_primary_key[0]
        except Exception:
            rowid = None

        if not rowid:
            try:
                rowid = conn.execute(text("SELECT last_insert_rowid()")).scalar()
            except Exception:
                # as a final fallback, attempt to read the max id
                r = conn.execute(text("SELECT id FROM faqs ORDER BY id DESC LIMIT 1")).fetchone()
                rowid = int(r[0]) if r else None

        # Try to update the FTS index; ignore errors if FTS not available
        try:
            conn.execute(
                text("INSERT INTO faqs_fts(rowid, question, answer) VALUES (:rowid, :q, :a)"),
                {"rowid": rowid, "q": payload.question, "a": payload.answer},
            )
        except Exception:
            pass

        return FAQOut(id=rowid, question=payload.question, answer=payload.answer, tags=payload.tags)


@app.get("/admin/faqs", response_model=List[FAQOut])
def admin_list_faqs(auth: bool = Depends(_check_api_key)):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, question, answer, tags FROM faqs ORDER BY id DESC")).fetchall()
        out = []
        for r in rows:
            tags = r[3].split(",") if r[3] else None
            out.append(FAQOut(id=r[0], question=r[1], answer=r[2], tags=tags))
        return out


@app.put("/admin/faqs/{faq_id}")
def admin_update_faq(faq_id: int, payload: FAQCreate, auth: bool = Depends(_check_api_key)):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE faqs SET question = :q, answer = :a, tags = :t WHERE id = :id"),
            {"q": payload.question, "a": payload.answer, "t": ",".join(payload.tags) if payload.tags else None, "id": faq_id},
        )
        # update FTS entry if present
        try:
            conn.execute(
                text("INSERT OR REPLACE INTO faqs_fts(rowid, question, answer) VALUES (:rowid, :q, :a)"),
                {"rowid": faq_id, "q": payload.question, "a": payload.answer},
            )
        except Exception:
            pass
    return {"status": "ok"}


@app.delete("/admin/faqs/{faq_id}")
def admin_delete_faq(faq_id: int, auth: bool = Depends(_check_api_key)):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM faqs WHERE id = :id"), {"id": faq_id})
        try:
            conn.execute(text("DELETE FROM faqs_fts WHERE rowid = :id"), {"id": faq_id})
        except Exception:
            pass
    return {"status": "deleted"}


@app.post("/admin/faqs", response_model=FAQOut)
def admin_create_faq(payload: FAQCreate, auth: bool = Depends(_check_api_key)):
    # re-use add_faq implementation but require admin key
    return add_faq(payload)


@app.get("/faqs", response_model=List[FAQOut])
def list_faqs(skip: int = 0, limit: int = 100):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, question, answer, tags FROM faqs ORDER BY id DESC LIMIT :lim OFFSET :skip"), {"lim": limit, "skip": skip}).fetchall()
        out = []
        for r in rows:
            tags = r[3].split(",") if r[3] else None
            out.append(FAQOut(id=r[0], question=r[1], answer=r[2], tags=tags))
        return out


@app.get("/faq/{faq_id}", response_model=FAQOut)
def get_faq(faq_id: int):
    with engine.connect() as conn:
        r = conn.execute(text("SELECT id, question, answer, tags FROM faqs WHERE id = :id"), {"id": faq_id}).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="FAQ not found")
        tags = r[3].split(",") if r[3] else None
        return FAQOut(id=r[0], question=r[1], answer=r[2], tags=tags)


@app.get("/search", response_model=SearchResponse)
def search(q: str, k: int = 5, temperature: float = 0.0):
    # Try RAG retrieval first using sentence-transformers + FAISS
    contexts = []
    matches = []
    try:
        docs = rag_store.retrieve(q, k=k)
        for d in docs:
            contexts.append({"id": d["id"], "question": d["question"], "answer": d["answer"]})
            matches.append(FAQOut(id=d["id"], question=d["question"], answer=d["answer"], tags=None))
    except Exception:
        docs = []

    if not contexts:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, question, answer FROM faqs WHERE question LIKE :pat OR answer LIKE :pat LIMIT :k"),
                {"pat": f"%{q}%", "k": k},
            ).fetchall()
            for r in rows:
                rid, question, answer = r[0], r[1], r[2]
                contexts.append({"id": int(rid), "question": question, "answer": answer})
                matches.append(FAQOut(id=int(rid), question=question, answer=answer, tags=None))

    answer, sources = genai.get_answer(q, contexts, temperature=float(temperature), top_k=k)
    return SearchResponse(answer=answer, sources=sources, matches=matches)


@app.post("/chat")
def chat_endpoint(payload: dict):
    """POST /chat with JSON {"message": "..."} returns {answer, sources, matches}.

    This is a convenience endpoint used by the static UI.
    """
    msg = payload.get("message") if isinstance(payload, dict) else None
    if not msg:
        raise HTTPException(status_code=400, detail="message required")

    # read optional params from payload: k and temperature
    k = int(payload.get("k", 5)) if isinstance(payload, dict) else 5
    temperature = float(payload.get("temperature", 0.0)) if isinstance(payload, dict) else 0.0

    # RAG retrieval
    contexts = []
    matches = []
    try:
        docs = rag_store.retrieve(msg, k=k)
        for d in docs:
            contexts.append({"id": d["id"], "question": d["question"], "answer": d["answer"]})
            matches.append({"id": d["id"], "question": d["question"], "answer": d["answer"]})
    except Exception:
        docs = []

    # fallback to DB text search
    if not contexts:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, question, answer FROM faqs WHERE question LIKE :pat OR answer LIKE :pat LIMIT :k"),
                {"pat": f"%{msg}%", "k": 5},
            ).fetchall()
            for r in rows:
                rid, question, answer = r[0], r[1], r[2]
                contexts.append({"id": int(rid), "question": question, "answer": answer})
                matches.append({"id": int(rid), "question": question, "answer": answer})

    answer, sources = genai.get_answer(msg, contexts, temperature=float(temperature), top_k=k)
    return {"answer": answer, "sources": sources, "matches": matches}
