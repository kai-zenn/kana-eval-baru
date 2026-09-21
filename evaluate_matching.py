"""
Skrip Evaluasi Head-to-Head - KANA
=====================================
Membandingkan 3 pendekatan matching untuk posting #CariMaterial:

  1. Keyword (SQL ILIKE sederhana)
  2. BM25 / PostgreSQL full-text search (to_tsvector + ts_rank)
  3. NLP Pipeline (BM25 Stage 2 -> semantic similarity Stage 3, via NLP service)

Cara pakai singkat (lihat README.md untuk detail):
  1. Salin .env.example -> .env, isi kredensial DB & NLP service.
  2. Jalankan migrations.sql di database kamu.
  3. Jalankan mock_nlp_service.py (Mode A) ATAU set NLP_BASE_URL ke NLP service
     asli rekan tim (Mode B) -- cukup ubah .env, tidak ada kode yang berubah.
  4. python evaluate_matching.py

Skrip ini akan:
  - Load seed_products.json & seed_queries.json ke database (idempotent).
  - Untuk tiap query, ambil kandidat via Stage 1 (Haversine radius filter),
    lalu jalankan ketiga pendekatan di atas terhadap kandidat yang sama.
  - Menghitung Precision@K, Recall@K, MRR, nDCG@K, dan latensi rata-rata.
  - [REVISI] Juga menghitung Success@K (K=3,5), Coverage, MAP, P95 Latency,
    dan Diversity@3 -- metrik tambahan untuk cerita "kapan sistem ini
    berguna bagi user", bukan cuma metrik akademis. Lihat bagian
    "5b. Metrik tambahan" di bawah dan README.md bagian
    "Revisi Metrik Tambahan" untuk penjelasan & asumsi masing-masing.
  - Menulis hasil ke CSV + Markdown (path dari config.py / .env).
"""

import csv
import math
import re
import statistics
import time
import uuid
from typing import Dict, List, Optional, Sequence

import psycopg2
import psycopg2.extras
import requests

import config

# =============================================================================
# 0. Util umum
# =============================================================================

def load_seed_json(path: str) -> list:
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Jarak great-circle antara dua koordinat, dalam kilometer."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


# =============================================================================
# 1. Koneksi & seeding database
# =============================================================================

def get_db_connection():
    dsn = config.DATABASE_URL
    if "user:pass@host:port" in dsn:
        # DATABASE_URL masih placeholder -> coba rakit dari field DB_* terpisah.
        if config.DB_HOST and config.DB_USER and config.DB_NAME:
            dsn = (
                f"postgresql://{config.DB_USER}:{config.DB_PASSWORD}"
                f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
            )
        else:
            raise SystemExit(
                "DATABASE_URL / DB_* belum diisi.\n"
                "TODO: ISI INI -> salin .env.example jadi .env lalu isi kredensial database kamu."
            )
    return psycopg2.connect(dsn)


def seed_database(conn, products: list, queries: list) -> None:
    """Load seed data ke database. Idempotent: aman dijalankan berkali-kali
    berkat ON CONFLICT (id) DO NOTHING -- baris yang sudah ada tidak diubah
    atau diduplikasi."""
    with conn.cursor() as cur:
        for p in products:
            cur.execute(
                """
                INSERT INTO products (id, title, description, category_branch,
                                       latitude, longitude, listing_type, status)
                VALUES (%(id)s, %(title)s, %(description)s, %(category_branch)s,
                        %(latitude)s, %(longitude)s, %(listing_type)s, %(status)s)
                ON CONFLICT (id) DO NOTHING
                """,
                p,
            )
        for q in queries:
            cur.execute(
                """
                INSERT INTO material_requests (id, raw_text, latitude, longitude, relevant_listing_ids)
                VALUES (%(id)s, %(raw_text)s, %(latitude)s, %(longitude)s, %(relevant_listing_ids)s)
                ON CONFLICT (id) DO NOTHING
                """,
                {**q, "relevant_listing_ids": q.get("relevant_listing_ids", [])},
            )
    conn.commit()


def get_candidates(conn, query: dict, radius_km: float) -> List[dict]:
    """Stage 1 (simulasi): ambil produk AVAILABLE dalam radius_km dari lokasi
    query. Difilter di sisi Python (bukan SQL/PostGIS) -- cukup untuk skala
    data uji ini (puluhan-ratusan baris) dan tidak butuh ekstensi tambahan.
    # ASUMSI: di backend Go produksi, Stage 1 sesungguhnya kemungkinan memakai
    # PostGIS atau bounding-box index; di sini cukup Haversine langsung.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT id, title, description, latitude, longitude "
            "FROM products WHERE status = 'AVAILABLE'"
        )
        rows = cur.fetchall()
    candidates = []
    for row in rows:
        dist = haversine_km(query["latitude"], query["longitude"], row["latitude"], row["longitude"])
        if dist <= radius_km:
            candidates.append({**row, "distance_km": dist})
    return candidates


# =============================================================================
# 2. Baseline 1: Keyword search (SQL ILIKE)
# =============================================================================

# ASUMSI: daftar stopword & kata generik #CariMaterial ini sengaja sederhana
# (bukan library NLP proper) -- konsisten dengan sifat Baseline 1 sebagai
# pendekatan "naif". Tujuannya cuma membuang noise paling jelas (hashtag,
# kata sambung, kata basa-basi permintaan) supaya baseline tidak konyol,
# bukan membuatnya secanggih BM25.
INDONESIAN_STOPWORDS = {
    "yang", "untuk", "dengan", "dari", "ke", "di", "dan", "atau", "ini", "itu",
    "saya", "aku", "kami", "kita", "ada", "ya", "min", "kak", "gan", "mau",
    "bisa", "juga", "buat", "kalau", "kalo", "gak", "ga", "tidak", "boleh",
    "dong", "sih", "nya", "para", "para", "akan", "pada", "adalah", "apa",
    "cari", "carimaterial", "butuh", "membutuhkan", "mencari", "nyari",
    "dicari", "area", "lokasi", "kirim", "kirim2", "harga", "nego", "aja",
}


def extract_keywords(raw_text: str) -> List[str]:
    """Ekstraksi keyword sangat sederhana: lowercase, buang hashtag/tanda
    baca, buang stopword & token pendek (<=2 huruf)."""
    text = raw_text.lower()
    text = re.sub(r"#\w+", " ", text)
    tokens = re.findall(r"[a-z]+", text)
    return [t for t in tokens if t not in INDONESIAN_STOPWORDS and len(t) > 2]


def baseline_keyword_search(conn, candidate_ids: Sequence[str], keywords: Sequence[str], top_n: int) -> List[str]:
    """Baseline 1: skor = jumlah keyword query yang ditemukan (ILIKE) di
    title+description. Hanya produk dengan skor > 0 yang dikembalikan --
    ini secara realistis menunjukkan kelemahan keyword search: kalau tidak
    ada kata yang cocok literal, produk yang sebenarnya relevan tidak akan
    pernah muncul, walau isinya bersinonim persis."""
    if not candidate_ids or not keywords:
        return []
    sql = """
        WITH kw AS (SELECT unnest(%(keywords)s::text[]) AS keyword)
        SELECT p.id,
               count(*) FILTER (
                   WHERE (p.title || ' ' || p.description) ILIKE '%%' || kw.keyword || '%%'
               ) AS score
        FROM products p
        CROSS JOIN kw
        WHERE p.id = ANY(%(candidate_ids)s::text[])
        GROUP BY p.id
        HAVING count(*) FILTER (
            WHERE (p.title || ' ' || p.description) ILIKE '%%' || kw.keyword || '%%'
        ) > 0
        ORDER BY score DESC, p.id
        LIMIT %(limit)s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, {"keywords": list(keywords), "candidate_ids": list(candidate_ids), "limit": top_n})
        rows = cur.fetchall()
    return [r["id"] for r in rows]


# =============================================================================
# 3. Baseline 2: PostgreSQL full-text search (BM25-ish via ts_rank)
# =============================================================================

def baseline_fulltext_search(conn, candidate_ids: Sequence[str], query_text: str, top_n: int) -> List[str]:
    """Baseline 2: to_tsquery (OR antar keyword) + ts_rank atas search_vector
    (dibangun trigger di migrations.sql). Memakai text-search configuration
    'simple' -- lihat catatan ASUMSI di migrations.sql soal tidak adanya
    konfigurasi 'indonesian' bawaan PostgreSQL.

    # ASUMSI: sengaja memakai to_tsquery dengan OPERATOR OR antar keyword
    # (bukan plainto_tsquery bawaan yang meng-AND-kan SEMUA kata di query
    # mentah). plainto_tsquery('simple', <kalimat panjang>) mensyaratkan
    # SEMUA token termasuk kata basa-basi ("untuk", "ya", "kak", dst) ada di
    # dokumen -- hampir tidak pernah match dan membuat baseline ini gagal
    # total. Dengan OR + ts_rank (skor terakumulasi per term yang cocok),
    # perilakunya jauh lebih dekat ke ranking berbasis term-frequency ala
    # BM25, yang memang jadi maksud baseline ini ("BM25 / full-text search").
    """
    if not candidate_ids:
        return []
    keywords = extract_keywords(query_text)
    if not keywords:
        return []
    tsquery_str = " | ".join(keywords)
    sql = """
        SELECT p.id, ts_rank(p.search_vector, to_tsquery('simple', %(tsquery)s)) AS score
        FROM products p
        WHERE p.id = ANY(%(candidate_ids)s::text[])
          AND p.search_vector @@ to_tsquery('simple', %(tsquery)s)
        ORDER BY score DESC, p.id
        LIMIT %(limit)s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, {"tsquery": tsquery_str, "candidate_ids": list(candidate_ids), "limit": top_n})
        rows = cur.fetchall()
    return [r["id"] for r in rows]


# =============================================================================
# 4. Solusi NLP: panggil NLP service (mock ATAU asli -- kontraknya identik)
# =============================================================================

def nlp_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if config.NLP_API_KEY:
        headers["Authorization"] = f"Bearer {config.NLP_API_KEY}"
    return headers


def nlp_embed(session: requests.Session, text: str) -> List[float]:
    try:
        resp = session.post(
            f"{config.NLP_BASE_URL}/v1/embed",
            json={"text": text},
            headers=nlp_headers(),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise SystemExit(
            f"Gagal menghubungi NLP service di {config.NLP_BASE_URL}/v1/embed ({e}).\n"
            "Pastikan mock_nlp_service.py sudah jalan:\n"
            "  uvicorn mock_nlp_service:app --port 8001\n"
            "atau NLP_BASE_URL / NLP_MODE di .env sudah benar untuk NLP service asli."
        )
    return resp.json()["embedding"]


def nlp_match(session: requests.Session, payload: dict) -> dict:
    try:
        resp = session.post(
            f"{config.NLP_BASE_URL}/v1/match",
            json=payload,
            headers=nlp_headers(),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        # Print detail error dari FastAPI (biasanya ada di response body)
        print("\n=== DETAIL ERROR DARI NLP SERVICE ===")
        print(f"Status: {resp.status_code}")
        print(f"Response body: {resp.text}")
        print(f"Payload yang dikirim:")
        import json
        # Print payload tanpa embedding (biar nggak kepanjangan)
        payload_debug = {**payload}
        payload_debug["query_embedding"] = f"<{len(payload.get('query_embedding', []))} dims>"
        if "candidates" in payload_debug:
            payload_debug["candidates"] = [
                {**c, "embedding": f"<{len(c.get('embedding', []))} dims>"}
                for c in payload_debug["candidates"]
            ]
        print(json.dumps(payload_debug, indent=2, default=str))
        print("=" * 50)
        raise SystemExit(f"Gagal memanggil {config.NLP_BASE_URL}/v1/match ({e}).")
    return resp.json()

def nlp_pipeline_search(
    session: requests.Session,
    query: dict,
    candidates: List[dict],
    product_embeddings: Dict[str, List[float]],
    top_n: int,
) -> List[str]:
    """Stage 2 (BM25) + Stage 3 (semantic) lewat NLP service."""
    if not candidates:
        return []
    query_embedding = nlp_embed(session, query["raw_text"])

    # FIX: Sort kandidat berdasarkan jarak terdekat (distance_km) sebelum di-cap ke 50.
    # Memastikan kandidat paling relevan secara geografis tidak terpotong acak.
    candidates_sorted = sorted(candidates, key=lambda c: c["distance_km"])
    candidates_capped = candidates_sorted[:50]
    
    payload = {
        "request_id": str(uuid.uuid4()),
        "query_text": query["raw_text"],
        "query_embedding": query_embedding,
        "candidates": [
            {
                "listing_id": c["id"],
                "text": f"{c['title']} {c['description']}",
                "embedding": product_embeddings[c["id"]],
                "distance_meters": float(c["distance_km"] * 1000),
            }
            for c in candidates_capped
        ],
        "config": {
            "bm25_top_k": config.NLP_BM25_TOP_K,
            "final_top_k": top_n,
            "semantic_threshold": config.NLP_SEMANTIC_THRESHOLD,
        },
    }
    resp = nlp_match(session, payload)
    ranked = sorted(resp["matches"], key=lambda m: m["rank"])
    return [m["listing_id"] for m in ranked]


# =============================================================================
# 5. Metrik IR: Precision@K, Recall@K, MRR, nDCG@K
# =============================================================================
# ASUMSI: untuk query dengan relevant_listing_ids kosong (edge case di seed
# data), Recall/MRR/nDCG tidak terdefinisi secara matematis (pembagi = 0) --
# di sini nilainya dikembalikan sebagai None dan DIKECUALIKAN dari rata-rata
# agregat (bukan dihitung sebagai 0), supaya tidak menghukum pipeline secara
# tidak adil untuk kasus yang memang tidak punya ground truth. Precision@K
# tetap terdefinisi (0 kalau tidak ada hit) sehingga tetap dihitung penuh.

def precision_at_k(retrieved: List[str], relevant: set, k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    hits = len(set(top_k) & relevant)
    return hits / k


def recall_at_k(retrieved: List[str], relevant: set, k: int) -> Optional[float]:
    if not relevant:
        return None
    top_k = retrieved[:k]
    hits = len(set(top_k) & relevant)
    return hits / len(relevant)


def reciprocal_rank(retrieved: List[str], relevant: set) -> Optional[float]:
    if not relevant:
        return None
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved: List[str], relevant: set, k: int) -> Optional[float]:
    if not relevant:
        return None
    top_k = retrieved[:k]
    dcg = sum((1.0 if item in relevant else 0.0) / math.log2(i + 1) for i, item in enumerate(top_k, start=1))
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return (dcg / idcg) if idcg > 0 else 0.0


# =============================================================================
# 5b. Metrik tambahan (REVISI: cerita "kapan sistem berguna bagi user")
# =============================================================================
# Nilai K untuk Success@K dan Diversity@3 SENGAJA di-hardcode ke 3 dan 5
# (bukan mengikuti config.EVAL_K_VALUES yang bisa diubah pengguna).
# # ASUMSI: spesifikasi revisi eksplisit meminta "Success@K (K=3, K=5)" dan
# "Diversity@3" sebagai nama metrik yang tetap/literal, bukan template yang
# ikut berubah kalau EVAL_K_VALUES di .env diganti pengguna.
SUCCESS_K_VALUES = [3, 5]
DIVERSITY_K = 3


def success_at_k(retrieved: List[str], relevant: set, k: int) -> float:
    """1.0 kalau MINIMAL SATU hasil relevan muncul di Top-K, selain itu 0.0.

    # ASUMSI: berbeda dari Recall/MRR/nDCG, Success@K TIDAK melibatkan
    # pembagian dengan len(relevant), jadi tetap terdefinisi secara matematis
    # (=0.0) bahkan untuk query dengan relevant_listing_ids kosong -- bukan
    # kasus 0/0. Karena itu, Success@K TIDAK dikecualikan dari rata-rata
    # (berbeda perlakuan dari Recall/MRR/nDCG/MAP yang memang butuh
    # pengecualian karena pembaginya bisa nol).
    """
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    return 1.0 if (set(top_k) & relevant) else 0.0


def coverage_indicator(retrieved: List[str]) -> float:
    """1.0 kalau sistem mengembalikan MINIMAL SATU hasil (relevan atau tidak),
    selain itu 0.0. Tidak butuh ground truth sama sekali -- dihitung untuk
    SEMUA query, termasuk query edge-case dengan relevant_listing_ids kosong."""
    return 1.0 if len(retrieved) > 0 else 0.0


def average_precision(retrieved: List[str], relevant: set) -> Optional[float]:
    """Average Precision (AP) untuk satu query: rata-rata Precision@k di
    setiap posisi k di mana dokumen relevan muncul, dibagi jumlah TOTAL
    dokumen relevan (bukan cuma yang berhasil ditemukan) -- definisi standar
    Information Retrieval. MAP = rata-rata AP di seluruh query.

    # ASUMSI: seperti Recall/MRR/nDCG, AP tidak terdefinisi kalau relevant
    # kosong (pembagi = 0) -- dikembalikan None dan dikecualikan dari MAP,
    # sesuai instruksi eksplisit di spesifikasi revisi.
    # ASUMSI: karena `retrieved` sudah dibatasi kedalamannya (top_n, sama
    # seperti yang dipakai MRR/nDCG di script ini), AP yang dihasilkan
    # sebenarnya "AP@top_n" (bukan AP atas seluruh katalog produk) -- ini
    # konsisten dengan cara metrik lain di script ini sudah bekerja.
    """
    if not relevant:
        return None
    hits = 0
    sum_precisions = 0.0
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            hits += 1
            sum_precisions += hits / i
    return sum_precisions / len(relevant)  # tetap dibagi total relevan, bukan `hits`


def percentile(values: Sequence[float], pct: float) -> float:
    """Persentil ke-`pct` dari `values`, interpolasi linier (metode yang sama
    dengan default numpy.percentile) -- diimplementasikan manual supaya tidak
    perlu menambah dependency numpy ke evaluate_matching.py."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (len(sorted_vals) - 1) * (pct / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return sorted_vals[int(rank)]
    weight_upper = rank - lower
    return sorted_vals[lower] * (1 - weight_upper) + sorted_vals[upper] * weight_upper


# ASUMSI: seed_products.json TIDAK punya field kategori material yang
# diskriminatif -- `category_branch` bernilai 'RAW_MATERIAL' untuk SEMUA
# produk (lihat migrations.sql & seed data), jadi tidak bisa dipakai untuk
# mengukur diversity. Kategori untuk Diversity@3 di bawah ini diturunkan dari
# kata kunci material yang muncul di title+description (mis. 'batik', 'denim',
# 'flanel', dst -- kata kunci ini konsisten dengan kategori yang dipakai saat
# seed data dibuat di _generate_seed_data.py, tapi di sini direkonstruksi
# ulang dari teks yang terlihat, BUKAN dari field tersembunyi). File seed data
# sendiri TIDAK diubah -- ini murni logika di sisi evaluate_matching.py.
CATEGORY_KEYWORDS = {
    "kain_perca_katun": [r"\bkatun\b"],
    "kain_perca_batik": [r"\bbatik\b"],
    "denim": [r"\bdenim\b", r"\bjeans\b"],
    "flanel": [r"\bflanel\b"],
    "benang_wol": [r"\bbenang\b", r"\bwol\b", r"\brajut\b"],
    "tulle": [r"\btulle\b", r"\btile\b"],
    "kulit_sintetis": [r"\bkulit\b"],
    "satin_sutra": [r"\bsatin\b", r"\bsutra\b"],
    "karton": [r"\bkarton\b", r"\bkardus\b"],
    "plastik_pet": [r"\bplastik\b", r"\bpet\b", r"\bbotol\b"],
    "limbah_kayu": [r"\bkayu\b", r"\bgergaji\b", r"\bserbuk\b"],
    "karet_ban": [r"\bkaret\b", r"\bban\b"],
}


def infer_category(product: dict) -> str:
    """Menurunkan label kategori material dari title+description (lihat
    catatan ASUMSI di atas). Kembali 'lainnya' kalau tidak ada kata kunci
    yang cocok."""
    text = f"{product.get('title', '')} {product.get('description', '')}".lower()
    for cat, patterns in CATEGORY_KEYWORDS.items():
        if any(re.search(p, text) for p in patterns):
            return cat
    return "lainnya"


def diversity_at_k(retrieved: List[str], product_categories: Dict[str, str], k: int) -> float:
    """Jumlah kategori BERBEDA yang muncul di Top-K hasil (bukan proporsi).
    # ASUMSI: kalau sistem mengembalikan hasil < k (mis. baseline keyword
    # cuma dapat 1 kandidat), diversity dihitung atas apa yang benar-benar
    # dikembalikan -- nilainya otomatis terbatas oleh jumlah hasil itu
    # sendiri, ini bukan bug melainkan konsekuensi wajar dari definisi."""
    top_k = retrieved[:k]
    cats = {product_categories.get(pid, "lainnya") for pid in top_k}
    return float(len(cats))


# =============================================================================
# 6. Orkestrasi evaluasi
# =============================================================================

def run_evaluation() -> List[dict]:
    conn = get_db_connection()
    products = load_seed_json(config.SEED_PRODUCTS_PATH)
    queries = load_seed_json(config.SEED_QUERIES_PATH)

    print(f"[1/4] Seeding database ({len(products)} produk, {len(queries)} query)...")
    seed_database(conn, products, queries)

    k_values = config.EVAL_K_VALUES
    # ASUMSI: top_n diperluas supaya juga mencakup SUCCESS_K_VALUES dan
    # DIVERSITY_K (bukan cuma k_values dari .env) -- kalau EVAL_K_VALUES
    # pengguna diubah ke nilai yang lebih kecil dari 5 (mis. cuma "3"),
    # retrieval tetap cukup dalam untuk menghitung Success@5/Diversity@3
    # dengan benar. Ini TIDAK mengubah baseline_keyword_search /
    # baseline_fulltext_search itu sendiri, hanya nilai top_n yang dikirim
    # ke keduanya dari sini.
    top_n = max(k_values + SUCCESS_K_VALUES + [DIVERSITY_K])

    print(f"[2/4] Precomputing embedding untuk semua produk (NLP_MODE={config.NLP_MODE})...")
    session = requests.Session()
    product_embeddings = {}
    product_categories = {}
    for p in products:
        text = f"{p['title']} {p['description']}"
        product_embeddings[p["id"]] = nlp_embed(session, text)
        product_categories[p["id"]] = infer_category(p)

    print(f"[3/4] Menjalankan {len(queries)} query x 3 pendekatan...")
    detailed_rows = []
    for q in queries:
        candidates = get_candidates(conn, q, config.STAGE1_RADIUS_KM)
        candidate_ids = [c["id"] for c in candidates]
        relevant = set(q.get("relevant_listing_ids", []))

        keywords = extract_keywords(q["raw_text"])
        t0 = time.perf_counter()
        kw_ranked = baseline_keyword_search(conn, candidate_ids, keywords, top_n)
        kw_latency_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        ft_ranked = baseline_fulltext_search(conn, candidate_ids, q["raw_text"], top_n)
        ft_latency_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        nlp_ranked = nlp_pipeline_search(session, q, candidates, product_embeddings, top_n)
        nlp_latency_ms = (time.perf_counter() - t0) * 1000  # end-to-end wall clock, termasuk network

        for approach, ranked, latency_ms in [
            ("Keyword", kw_ranked, kw_latency_ms),
            ("BM25", ft_ranked, ft_latency_ms),
            ("NLP Pipeline", nlp_ranked, nlp_latency_ms),
        ]:
            row = {
                "query_id": q["id"],
                "approach": approach,
                "num_candidates": len(candidates),
                "num_relevant": len(relevant),
                "latency_ms": round(latency_ms, 2),
            }
            for k in k_values:
                row[f"precision@{k}"] = precision_at_k(ranked, relevant, k)
                row[f"recall@{k}"] = recall_at_k(ranked, relevant, k)
                row[f"ndcg@{k}"] = ndcg_at_k(ranked, relevant, k)
            row["mrr"] = reciprocal_rank(ranked, relevant)

            # --- [REVISI] Metrik tambahan ---
            for k in SUCCESS_K_VALUES:
                row[f"success@{k}"] = success_at_k(ranked, relevant, k)
            row["coverage"] = coverage_indicator(ranked)
            row["average_precision"] = average_precision(ranked, relevant)
            row[f"diversity@{DIVERSITY_K}"] = diversity_at_k(ranked, product_categories, DIVERSITY_K)

            detailed_rows.append(row)

    conn.close()
    print("[4/4] Selesai menjalankan evaluasi.")
    return detailed_rows


def aggregate_results(detailed_rows: List[dict], k_values: List[int]):
    approaches = ["Keyword", "BM25", "NLP Pipeline"]
    summary = {}
    for approach in approaches:
        rows = [r for r in detailed_rows if r["approach"] == approach]
        metrics = {}
        for k in k_values:
            prec_vals = [r[f"precision@{k}"] for r in rows]
            rec_vals = [r[f"recall@{k}"] for r in rows if r[f"recall@{k}"] is not None]
            ndcg_vals = [r[f"ndcg@{k}"] for r in rows if r[f"ndcg@{k}"] is not None]
            metrics[f"Precision@{k}"] = statistics.mean(prec_vals) if prec_vals else 0.0
            metrics[f"Recall@{k}"] = statistics.mean(rec_vals) if rec_vals else 0.0
            metrics[f"nDCG@{k}"] = statistics.mean(ndcg_vals) if ndcg_vals else 0.0
        mrr_vals = [r["mrr"] for r in rows if r["mrr"] is not None]
        metrics["MRR"] = statistics.mean(mrr_vals) if mrr_vals else 0.0

        # --- [REVISI] Metrik tambahan ---
        # Success@K: dihitung atas SEMUA baris (lihat catatan ASUMSI di
        # success_at_k -- berbeda dari Recall/MRR/nDCG, tidak dikecualikan).
        for k in SUCCESS_K_VALUES:
            success_vals = [r[f"success@{k}"] for r in rows]
            metrics[f"Success@{k}"] = statistics.mean(success_vals) if success_vals else 0.0
        # Coverage: dihitung atas SEMUA baris, termasuk query tanpa ground truth.
        coverage_vals = [r["coverage"] for r in rows]
        metrics["Coverage"] = statistics.mean(coverage_vals) if coverage_vals else 0.0
        # MAP: rata-rata AP, KECUALI query tanpa ground truth (AP = None).
        ap_vals = [r["average_precision"] for r in rows if r["average_precision"] is not None]
        metrics["MAP"] = statistics.mean(ap_vals) if ap_vals else 0.0
        # Diversity@3: dihitung atas SEMUA baris (tidak butuh ground truth).
        diversity_vals = [r[f"diversity@{DIVERSITY_K}"] for r in rows]
        metrics[f"Diversity@{DIVERSITY_K}"] = statistics.mean(diversity_vals) if diversity_vals else 0.0

        metrics["Latensi rata-rata (ms)"] = statistics.mean([r["latency_ms"] for r in rows]) if rows else 0.0
        # P95 Latency: persentil (bukan rata-rata) dari SELURUH latency_ms
        # approach ini -- persentilnya dari config.EVAL_PERCENTILE_LATENCY
        # (default 95), bisa diubah lewat .env tanpa mengubah kode.
        metrics["P95 Latency (ms)"] = percentile(
            [r["latency_ms"] for r in rows], config.EVAL_PERCENTILE_LATENCY
        )

        summary[approach] = metrics
    n_excluded = sum(1 for r in detailed_rows if r["approach"] == "Keyword" and r["num_relevant"] == 0)
    return summary, n_excluded


def build_metric_order(k_values: List[int]) -> List[str]:
    """Urutan baris metrik yang dipakai bersama oleh write_outputs() dan
    print_console_summary(), supaya urutannya selalu konsisten di
    results.md, results.csv, dan output konsol. Urutan metrik tambahan
    (Success@K, Coverage, MAP, Diversity@3, P95 Latency) mengikuti urutan
    yang diminta di spesifikasi revisi: disisipkan SETELAH metrik lama,
    tanpa menghapus satupun metrik yang sudah ada."""
    metric_order = []
    for k in k_values:
        metric_order += [f"Precision@{k}", f"Recall@{k}", f"nDCG@{k}"]
    metric_order += ["MRR"]
    metric_order += [f"Success@{k}" for k in SUCCESS_K_VALUES]
    metric_order += ["Coverage", "MAP", f"Diversity@{DIVERSITY_K}"]
    metric_order += ["Latensi rata-rata (ms)", "P95 Latency (ms)"]
    return metric_order


def write_outputs(summary: dict, k_values: List[int], n_excluded_queries: int, detailed_rows: List[dict]) -> None:
    approaches = ["Keyword", "BM25", "NLP Pipeline"]
    metric_order = build_metric_order(k_values)

    # --- Ringkasan CSV ---
    with open(config.OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metrik"] + approaches)
        for metric in metric_order:
            writer.writerow([metric] + [f"{summary[a][metric]:.4f}" for a in approaches])

    # --- Ringkasan Markdown ---
    with open(config.OUTPUT_MARKDOWN_PATH, "w", encoding="utf-8") as f:
        f.write("# Hasil Evaluasi Head-to-Head: Keyword vs BM25 vs NLP Pipeline\n\n")
        f.write(f"Mode NLP service: **{config.NLP_MODE}**\n\n")
        if config.NLP_MODE == "mock":
            f.write(
                "> Catatan: berjalan di mode **mock** -- embedding yang dipakai NLP Pipeline "
                "adalah vektor pseudo-random (bukan model ML sungguhan), jadi angka NLP Pipeline "
                "di tabel ini HANYA membuktikan bahwa wiring/kontrak API berjalan, BUKAN keunggulan "
                "semantik sesungguhnya. Ulangi evaluasi ini dengan `NLP_MODE=real` (dan `NLP_BASE_URL` "
                "mengarah ke NLP service asli) untuk angka yang bisa dipakai membuktikan keunggulan pipeline.\n\n"
            )
        f.write("| Metrik | Keyword | BM25 | NLP Pipeline |\n")
        f.write("|---|---|---|---|\n")
        for metric in metric_order:
            f.write(
                f"| {metric} | {summary['Keyword'][metric]:.4f} | {summary['BM25'][metric]:.4f} "
                f"| {summary['NLP Pipeline'][metric]:.4f} |\n"
            )
        f.write(
            f"\n_{n_excluded_queries} dari total query tidak punya ground truth "
            f"(relevant_listing_ids kosong) dan dikecualikan dari rata-rata "
            f"Recall/MRR/nDCG/MAP. Success@K dan Coverage TETAP menghitung "
            f"semua query (termasuk yang tanpa ground truth) karena keduanya "
            f"tidak melibatkan pembagian dengan jumlah relevan._\n\n"
            f"_Success@K, Coverage, dan MAP berskala 0-1 (kalikan 100 untuk "
            f"persen). Diversity@{DIVERSITY_K} berupa jumlah kategori berbeda "
            f"(1 sampai {DIVERSITY_K}), bukan skala 0-1. P95 Latency dihitung "
            f"pada persentil ke-{config.EVAL_PERCENTILE_LATENCY:g} "
            f"(`EVAL_PERCENTILE_LATENCY` di .env)._\n"
        )

    # --- Detail per-query CSV (untuk debugging / audit) ---
    detailed_path = config.OUTPUT_CSV_PATH.replace(".csv", "_detailed.csv")
    if detailed_rows:
        fieldnames = list(detailed_rows[0].keys())
        with open(detailed_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(detailed_rows)

    print(f"\nOutput ditulis ke:\n  - {config.OUTPUT_CSV_PATH}\n  - {config.OUTPUT_MARKDOWN_PATH}\n  - {detailed_path}")


def print_console_summary(summary: dict, k_values: List[int]) -> None:
    approaches = ["Keyword", "BM25", "NLP Pipeline"]
    metric_order = build_metric_order(k_values)

    col_w = 16
    print("\n" + "Metrik".ljust(24) + "".join(a.rjust(col_w) for a in approaches))
    print("-" * (24 + col_w * len(approaches)))
    for metric in metric_order:
        print(metric.ljust(24) + "".join(f"{summary[a][metric]:.4f}".rjust(col_w) for a in approaches))


if __name__ == "__main__":
    detailed_rows = run_evaluation()
    summary, n_excluded = aggregate_results(detailed_rows, config.EVAL_K_VALUES)
    print_console_summary(summary, config.EVAL_K_VALUES)
    write_outputs(summary, config.EVAL_K_VALUES, n_excluded, detailed_rows)
