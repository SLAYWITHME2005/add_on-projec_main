import os
from typing import List, Dict, Any

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
except Exception:
    SentenceTransformer = None
    np = None
    faiss = None

from sqlalchemy import create_engine, text

DB_URL = "sqlite:///./faqs.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

INDEX_PATH = "faqs.index"
IDS_PATH = "faqs_ids.npy"
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _load_faqs_from_db() -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, question, answer FROM faqs")
        ).fetchall()

    return [
        {
            "id": int(r[0]),
            "question": r[1],
            "answer": r[2]
        }
        for r in rows
    ]


def build_index(force: bool = False):

    if SentenceTransformer is None:
        return False

    faqs = _load_faqs_from_db()

    if not faqs:
        return False

    ids = np.array([f["id"] for f in faqs], dtype=np.int64)

    texts = [
        f["question"] + "\n" + f["answer"]
        for f in faqs
    ]

    model = SentenceTransformer(EMB_MODEL)

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])

    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)

    np.save(IDS_PATH, ids)

    return True


def _load_index():

    if faiss is None or np is None:
        return None, None

    if not os.path.exists(INDEX_PATH):

        if not build_index():
            return None, None

    index = faiss.read_index(INDEX_PATH)

    ids = np.load(IDS_PATH)

    return index, ids


def retrieve(
    query: str,
    k: int = 1,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:

    if SentenceTransformer is None or faiss is None:
        return []

    index, ids = _load_index()

    if index is None:
        return []

    model = SentenceTransformer(EMB_MODEL)

    q_emb = model.encode(
        [query],
        convert_to_numpy=True
    )

    faiss.normalize_L2(q_emb)

    D, I = index.search(q_emb, k)

    scores = D[0]
    positions = I[0]

    results = []

    with engine.connect() as conn:

        for pos, score in zip(positions, scores):

            if pos < 0:
                continue

            if score < min_score:
                continue

            db_id = int(ids[pos])

            row = conn.execute(
                text(
                    "SELECT id, question, answer FROM faqs WHERE id=:id"
                ),
                {"id": db_id},
            ).fetchone()

            if row:

                results.append(
                    {
                        "id": int(row[0]),
                        "question": row[1],
                        "answer": row[2],
                        "score": float(score),
                    }
                )

    return results
