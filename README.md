# College FAQ Chatbot (Python-only)

This repository contains a Python-only FastAPI backend implementing a RAG-based college FAQ chatbot.

Files:
- `api.py` — FastAPI application exposing `/chat`, `/search`, and admin CRUD endpoints.
- `genai.py` — simple generative-wrapper (OpenAI optional).
- `rag_store.py` — builds and queries FAISS index using sentence-transformers.
- `seed_faqs.py` — seeds the SQLite `faqs` table with sample FAQs.
- `requirements.txt` — Python dependencies.

Quick start

1. Create and activate a venv:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) set admin API key and OpenAI key:

```bash
setx ADMIN_API_KEY "your-key"
setx OPENAI_API_KEY "sk-..."
# or use .env loader in your shell
```

4. Seed DB:

```bash
python seed_faqs.py
```

5. (Optional) build RAG index:

```bash
python -c "import rag_store; print('built=', rag_store.build_index())"
```

6. Run server:

```bash
uvicorn api:app --reload --port 8000
```

Endpoints

- `POST /chat` — JSON `{ "message": "..." }` → `{ answer, sources, matches }`
- `GET /search?q=...` — search and aggregated answer
- Admin (require header `x-api-key` matching `ADMIN_API_KEY`): `GET/POST/PUT/DELETE /admin/faqs`

If you want the static web UI back later, I can recreate it. For now this is a Python-only backend you can run locally.
