"""
Konfigurasi terpusat untuk mock_nlp_service.py dan evaluate_matching.py.

Cara pakai:
  1. Copy .env.example menjadi .env lalu isi nilainya, ATAU
  2. Set langsung sebagai environment variable sebelum menjalankan script.

Modul ini membaca .env kalau ada (loader minimal buatan sendiri, TANPA
dependency tambahan seperti python-dotenv, supaya tetap sesuai batasan
"jangan pakai library berat"), lalu fallback ke os.environ / default di bawah.
"""
import os


def _load_dotenv(path: str = ".env") -> None:
    """Parser .env sangat sederhana: KEY=VALUE per baris, '#' untuk komentar.
    Tidak menimpa environment variable yang sudah di-set sebelumnya."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv()

# ---------------------------------------------------------------------------
# Database PostgreSQL
# ---------------------------------------------------------------------------
# TODO: ISI INI - connection string database cloud kamu (Neon/Supabase/Aiven/dll).
# Contoh Neon: postgresql://user:pass@ep-xxxx.ap-southeast-1.aws.neon.tech/kana?sslmode=require
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://user:pass@host:port/dbname"
)

# Alternatif: kalau lebih suka pisah per-field daripada satu connection string
# (evaluate_matching.py memakai DATABASE_URL kalau ada isinya; field di bawah
# hanya dipakai sebagai fallback kalau DATABASE_URL masih placeholder).
DB_HOST = os.environ.get("DB_HOST", "")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "")

# ---------------------------------------------------------------------------
# NLP Service
# ---------------------------------------------------------------------------
# TODO: ISI INI - base URL NLP service. Default mengarah ke mock service lokal.
NLP_BASE_URL = os.environ.get("NLP_BASE_URL", "http://localhost:8001")

# TODO: ISI INI - shared secret NLP service. Harus SAMA PERSIS dengan yang
# dipakai mock_nlp_service.py (atau NLP service asli) dan backend Go.
NLP_API_KEY = os.environ.get("NLP_SERVICE_API_KEY", "")

# Mode A ("mock") vs Mode B ("real"). Ganti ke "real" begitu NLP service asli
# rekan tim sudah siap -- HANYA variabel ini yang perlu diubah untuk pindah
# mode, tidak ada kode lain yang perlu disentuh.
NLP_MODE = os.environ.get("NLP_MODE", "mock")  # "mock" | "real"

# Parameter yang dikirim sebagai "config" pada body POST /v1/match.
# final_top_k TIDAK diset di sini secara statis -- evaluate_matching.py
# menghitungnya otomatis dari max(EVAL_K_VALUES) supaya selalu cukup dalam
# untuk semua nilai K yang dievaluasi.
NLP_BM25_TOP_K = int(os.environ.get("NLP_BM25_TOP_K", "10"))
NLP_SEMANTIC_THRESHOLD = float(os.environ.get("NLP_SEMANTIC_THRESHOLD", "0.80"))

# ---------------------------------------------------------------------------
# Evaluasi
# ---------------------------------------------------------------------------
# Radius pencarian kandidat dalam km (mensimulasikan Stage 1 Haversine filter
# yang di produksi dilakukan oleh backend Go).
STAGE1_RADIUS_KM = float(os.environ.get("STAGE1_RADIUS_KM", "50"))

# Nilai K untuk metrik Precision@K / Recall@K / nDCG@K, pisahkan dengan koma.
EVAL_K_VALUES = [int(k) for k in os.environ.get("EVAL_K_VALUES", "3,5").split(",")]

# Path file output hasil evaluasi
OUTPUT_CSV_PATH = os.environ.get("OUTPUT_CSV_PATH", "results.csv")
OUTPUT_MARKDOWN_PATH = os.environ.get("OUTPUT_MARKDOWN_PATH", "results.md")

# Path file seed data
SEED_PRODUCTS_PATH = os.environ.get("SEED_PRODUCTS_PATH", "seed_products.json")
SEED_QUERIES_PATH = os.environ.get("SEED_QUERIES_PATH", "seed_queries.json")

# ---------------------------------------------------------------------------
# Revisi Metrik Tambahan (Success@K, Coverage, MAP, P95 Latency, Diversity@3)
# ---------------------------------------------------------------------------
# ASUMSI: variabel ini BARU ditambahkan untuk revisi metrik, bukan mengubah
# variabel yang sudah ada di atas -- konsisten dengan batasan "jangan ubah
# format .env dan config.py yang SUDAH ADA". Diminta secara eksplisit oleh
# spesifikasi revisi supaya persentil P95 bisa diatur tanpa mengubah kode.
# Persentil untuk metrik P95 Latency (mis. 95 = P95, 99 = P99).
EVAL_PERCENTILE_LATENCY = float(os.environ.get("EVAL_PERCENTILE_LATENCY", "95"))
