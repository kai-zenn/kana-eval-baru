"""
Mock NLP Service - KANA
=========================
Replika sederhana dari NLP service asli (embedding + matching) supaya backend
Go dan skrip evaluasi bisa mulai dikembangkan/diuji tanpa menunggu model ML
sungguhan selesai.

PENTING (baca ini agar tidak salah interpretasi hasil):
- Endpoint /v1/embed di sini TIDAK menjalankan model ML apa pun. Vektor yang
  dikembalikan adalah angka pseudo-random yang DETERMINISTIK terhadap hash
  dari teks input (teks yang sama -> vektor yang sama), tapi vektor ini TIDAK
  merepresentasikan makna semantik teks sungguhan.
- Konsekuensinya: kalau skrip evaluasi (evaluate_matching.py) dijalankan dalam
  Mode A (mock) ini, metrik "NLP Pipeline" TIDAK akan mencerminkan keunggulan
  semantic similarity yang sesungguhnya -- mock ini hanya untuk memvalidasi
  bahwa KONTRAK API dan pipeline Go/eval berjalan dengan benar (wiring test),
  bukan untuk membuktikan keunggulan pendekatan NLP. Pembuktian keunggulan
  harus dilakukan di Mode B, memakai NLP service asli.
- Skor bm25_score DI DALAM mock ini dihitung dengan BM25 sungguhan (rank_bm25)
  atas teks kandidat yang dikirim, jadi bagian "Stage 2 filter" tetap
  representatif. Yang tidak representatif hanya bagian semantic_score-nya.

Jalankan:
    uvicorn mock_nlp_service:app --port 8001 --reload
"""

import hashlib
import time
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

try:
    from rank_bm25 import BM25Okapi
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "rank_bm25 belum terpasang. Jalankan: pip install rank-bm25"
    ) from e

import config  # loader .env bersama -- lihat config.py & .env.example

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 384
MODEL_NAME = "mock-minilm-l12-v2"

# Dibaca dari .env lewat config.py (key: NLP_SERVICE_API_KEY). # TODO: ISI INI
# di .env -- harus SAMA PERSIS dengan yang dipakai evaluate_matching.py &
# backend Go. Kalau dikosongkan, auth check DIMATIKAN (mode dev longgar) --
# jangan pakai mode ini di luar localhost.
NLP_SERVICE_API_KEY = config.NLP_API_KEY

app = FastAPI(title="KANA Mock NLP Service", version="0.1.0")


# ---------------------------------------------------------------------------
# Skema request/response - HARUS PERSIS mengikuti kontrak API final
# ---------------------------------------------------------------------------
class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: List[float]
    model: str
    dim: int


class MatchConfig(BaseModel):
    bm25_top_k: int = 10
    final_top_k: int = 3
    semantic_threshold: float = 0.80


class Candidate(BaseModel):
    listing_id: str
    text: str
    embedding: List[float]
    distance_meters: float


class MatchRequest(BaseModel):
    request_id: str
    query_text: str
    query_embedding: List[float]
    candidates: List[Candidate]
    config: MatchConfig = Field(default_factory=MatchConfig)


class MatchResult(BaseModel):
    listing_id: str
    bm25_score: float
    semantic_score: float
    final_score: float
    rank: int


class MatchResponse(BaseModel):
    request_id: str
    matches: List[MatchResult]
    stage2_survivor_count: int
    stage3_survivor_count: int
    model: str
    processed_in_ms: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model: str


# ---------------------------------------------------------------------------
# Helper: auth, embedding generation, tokenisasi ringan untuk BM25
# ---------------------------------------------------------------------------
def check_auth(authorization: Optional[str]) -> None:
    """Validasi header 'Authorization: Bearer <key>'. Dilewati jika
    NLP_SERVICE_API_KEY tidak di-set (mode dev)."""
    if not NLP_SERVICE_API_KEY:
        return
    expected = f"Bearer {NLP_SERVICE_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def text_to_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Menghasilkan vektor pseudo-random deterministik dari hash teks.
    Teks yang sama -> vektor yang sama. Dinormalisasi (unit vector) supaya
    cosine similarity tetap well-defined secara matematis, meski nilainya
    tidak punya makna semantik sungguhan (lihat catatan di docstring modul)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], byteorder="big") % (2**32 - 1)
    rng = np.random.RandomState(seed)
    vec = rng.normal(loc=0.0, scale=1.0, size=dim)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def simple_tokenize(text: str) -> List[str]:
    """Tokenisasi sangat sederhana untuk BM25: lowercase + split non-alfanumerik.
    # ASUMSI: tidak melakukan stemming/stopword-removal Bahasa Indonesia di sini
    # karena mock ini hanya perlu 'cukup masuk akal', bukan production-grade.
    """
    import re
    return re.findall(r"[a-z0-9]+", text.lower())


def cosine_similarity(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", model_loaded=True, model=MODEL_NAME)


@app.post("/v1/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest, authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=422, detail="text tidak boleh kosong")
    vec = text_to_embedding(req.text)
    return EmbedResponse(embedding=vec, model=MODEL_NAME, dim=len(vec))


@app.post("/v1/match", response_model=MatchResponse)
def match(req: MatchRequest, authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)
    start = time.perf_counter()

    if not req.candidates:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return MatchResponse(
            request_id=req.request_id,
            matches=[],
            stage2_survivor_count=0,
            stage3_survivor_count=0,
            model=MODEL_NAME,
            processed_in_ms=elapsed_ms,
        )

    cfg = req.config

    # --- Stage 2: BM25 filter (sungguhan, memakai rank_bm25) -------------
    tokenized_corpus = [simple_tokenize(c.text) for c in req.candidates]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = simple_tokenize(req.query_text)
    bm25_scores = bm25.get_scores(query_tokens)  # array sejajar dengan req.candidates

    scored = list(zip(req.candidates, bm25_scores))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    stage2_survivors = scored[: cfg.bm25_top_k]
    stage2_survivor_count = len(stage2_survivors)

    # --- Stage 3: semantic similarity + threshold -------------------------
    stage3_survivors = []
    for candidate, bm25_score in stage2_survivors:
        sem_score = cosine_similarity(req.query_embedding, candidate.embedding)
        if sem_score >= cfg.semantic_threshold:
            stage3_survivors.append((candidate, float(bm25_score), sem_score))
    stage3_survivor_count = len(stage3_survivors)

    # Kalau tidak ada yang lolos threshold, mock ini fallback ke seluruh
    # stage2 survivor supaya tetap ada hasil untuk dievaluasi (final_top_k
    # tetap dihormati). # ASUMSI: perilaku fallback ini spesifik mock,
    # NLP service asli boleh punya kebijakan berbeda (mis. return kosong).
    #
    # Catatan desain: saat fallback, pool diurutkan berdasarkan bm25_score
    # (bukan semantic_score) karena BM25 di mock ini dihitung sungguhan
    # (rank_bm25), sedangkan semantic_score dari embedding acak murni noise --
    # mengurutkan berdasarkan noise saat threshold gagal cuma akan
    # menyembunyikan sinyal BM25 yang sebenarnya valid.
    if stage3_survivors:
        pool = stage3_survivors
        pool.sort(key=lambda triple: triple[2], reverse=True)  # urutkan by semantic_score
        use_semantic_final_score = True
    else:
        pool = [
            (c, float(s), cosine_similarity(req.query_embedding, c.embedding))
            for c, s in stage2_survivors
        ]
        pool.sort(key=lambda triple: triple[1], reverse=True)  # fallback: urutkan by bm25_score
        use_semantic_final_score = False

    top = pool[: cfg.final_top_k]

    matches = [
        MatchResult(
            listing_id=candidate.listing_id,
            bm25_score=round(bm25_score, 4),
            semantic_score=round(sem_score, 4),
            final_score=round(sem_score if use_semantic_final_score else bm25_score, 4),
            rank=i + 1,
        )
        for i, (candidate, bm25_score, sem_score) in enumerate(top)
    ]

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return MatchResponse(
        request_id=req.request_id,
        matches=matches,
        stage2_survivor_count=stage2_survivor_count,
        stage3_survivor_count=stage3_survivor_count,
        model=MODEL_NAME,
        processed_in_ms=elapsed_ms,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_nlp_service:app", host="0.0.0.0", port=8001, reload=True)
