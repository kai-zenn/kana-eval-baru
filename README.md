# KANA - Uji Performa Head-to-Head Matching

Membandingkan **3 pendekatan matching** untuk posting **#CariMaterial** pada platform KANA.

| # | Pendekatan                  | Teknologi                                                      |
| - | --------------------------- | -------------------------------------------------------------- |
| 1 | Keyword (Baseline)          | SQL `ILIKE` sederhana                                          |
| 2 | BM25 / Full-text (Baseline) | PostgreSQL `to_tsquery` + `ts_rank`                            |
| 3 | NLP Pipeline (Solusi)       | BM25 Stage 2 → Semantic Similarity Stage 3 melalui NLP Service |

Proyek ini dibuat untuk mendukung persiapan **Samsung Solve for Tomorrow 2026**, dengan tujuan menyediakan data empiris untuk membandingkan performa pipeline NLP dengan pendekatan pencarian baseline.

---

## 📌 Catatan Perbaikan Evaluasi

### Bug Fix pada `evaluate_matching.py`

Telah diperbaiki bug pada fungsi `nlp_pipeline_search()` yang sebelumnya melakukan pemotongan kandidat (`[:50]`) **sebelum proses sorting**.

#### Masalah

Kandidat diambil dari database tanpa `ORDER BY`. Akibatnya, listing dengan ID pendek, khususnya `p0XX` pada baris 51–150 seed data, dapat terpotong secara tidak konsisten.

Hal ini menyebabkan query `q028`–`q050` mendapatkan nilai `Precision@3 = 0.0` secara salah.

#### Perbaikan

Kandidat sekarang:

1. Dihitung jaraknya.
2. Diurutkan berdasarkan `distance_km`.
3. Baru dibatasi menjadi maksimal 50 kandidat.

```python
candidates_sorted[:50]
```

Dengan demikian, kandidat terdekat tidak lagi terpotong secara acak sebelum masuk ke tahap NLP.

---

# 📁 Struktur Folder

```text
kana-eval/
│
├── mock_nlp_service.py
│   └── Replika kontrak API NLP Service (FastAPI, port 8001)
│
├── evaluate_matching.py
│   └── Skrip utama untuk menjalankan evaluasi
│
├── config.py
│   └── Konfigurasi terpusat dan pembacaan .env
│
├── .env.example
│   └── Template konfigurasi environment
│
├── migrations.sql
│   └── DDL tabel products dan material_requests
│
├── seed_products.json
│   └── 150 listing produk untuk data pengujian
│
├── seed_queries.json
│   └── 50 query #CariMaterial beserta ground truth
│
├── requirements.txt
│   └── Dependency Python
│
├── test_metrics.py
│   └── Unit test untuk metrik tambahan
│
├── _generate_seed_data.py
│   └── Generator seed data (opsional)
│
└── README.md
    └── Dokumentasi proyek
```

> `_generate_seed_data.py` bukan bagian dari alur evaluasi utama dan tidak dipanggil oleh `evaluate_matching.py`.
>
> File tersebut disediakan untuk transparansi, terutama untuk melihat bagaimana `relevant_listing_ids` pada `seed_queries.json` dibuat atau untuk membuat ulang data menggunakan seed acak yang sama (`random.seed(42)`).

---

# 🚀 Cara Menjalankan

## 1. Install Dependency

Pastikan Python sudah terinstall, kemudian jalankan:

```bash
pip install -r requirements.txt
```

---

## 2. Konfigurasi Environment

Salin file `.env.example` menjadi `.env`:

```bash
cp .env.example .env
```

> **Windows Command Prompt:** gunakan cara yang sesuai dengan shell yang digunakan, misalnya:
>
> ```cmd
> copy .env.example .env
> ```

Kemudian buka `.env` dan isi konfigurasi yang ditandai:

```env
DATABASE_URL=...
NLP_SERVICE_API_KEY=...
```

### Variabel utama

| Variable              | Keterangan                                                                  |
| --------------------- | --------------------------------------------------------------------------- |
| `DATABASE_URL`        | Connection string database cloud seperti Neon, Supabase, Aiven, dan lainnya |
| `NLP_SERVICE_API_KEY` | Shared secret antara mock service, evaluation script, dan backend           |
| `NLP_BASE_URL`        | URL NLP Service                                                             |
| `NLP_MODE`            | Mode NLP Service (`mock` atau `real`)                                       |

Secara default, konfigurasi diarahkan ke mock NLP service lokal.

---

## 3. Jalankan Migrasi Database

Pastikan `psql` tersedia, kemudian jalankan:

```bash
psql "$DATABASE_URL" -f migrations.sql
```

Jika `DATABASE_URL` belum diekspor sebagai environment variable, gunakan connection string database secara langsung.

---

## 4. Jalankan NLP Service

### Mode A - Mock NLP Service

Mode ini digunakan ketika NLP Service asli belum tersedia.

Jalankan:

```bash
uvicorn mock_nlp_service:app --port 8001
```

Secara default, service berjalan pada:

```text
http://localhost:8001
```

### Mode B - NLP Service Asli

Jika NLP Service asli sudah tersedia, ubah `.env`:

```env
NLP_BASE_URL=http://alamat-nlp-service-asli:PORT
NLP_MODE=real
```

Tidak perlu mengubah kode evaluasi karena mock service dan NLP service asli menggunakan kontrak API yang sama.

---

## 5. Jalankan Evaluasi

Jalankan:

```bash
python evaluate_matching.py
```

Script akan secara otomatis:

1. Melakukan seed database.
2. Mengambil kandidat berdasarkan radius geografis.
3. Menjalankan ketiga pendekatan matching.
4. Menghitung metrik evaluasi.
5. Menghasilkan file hasil evaluasi.

Proses seed bersifat **idempotent**, sehingga aman dijalankan lebih dari satu kali.

---

## 6. Jalankan Unit Test

Unit test tidak membutuhkan database atau NLP Service.

Dengan `unittest`:

```bash
python -m unittest test_metrics.py -v
```

Atau jika menggunakan `pytest`:

```bash
pytest test_metrics.py -v
```

Test mencakup:

* Success@K
* Coverage
* MAP
* P95 Latency
* Diversity@3

---

# 📊 Output Evaluasi

Setelah evaluasi selesai, sistem menghasilkan tiga file utama:

| File                   | Keterangan                                     |
| ---------------------- | ---------------------------------------------- |
| `results.md`           | Ringkasan hasil evaluasi dalam format Markdown |
| `results.csv`          | Hasil evaluasi dalam format CSV                |
| `results_detailed.csv` | Detail hasil per query dan pendekatan          |

### `results.md`

Berisi tabel ringkasan yang dapat digunakan untuk dokumentasi atau presentasi.

### `results.csv`

Berguna untuk:

* Spreadsheet
* Analisis lanjutan
* Visualisasi
* Presentasi

### `results_detailed.csv`

Berisi satu baris untuk setiap kombinasi:

```text
query × pendekatan
```

File ini dapat digunakan untuk melakukan audit ketika suatu pendekatan mendapatkan hasil yang buruk pada query tertentu.

---

# 📈 Metrik Evaluasi

Metrik yang digunakan:

* Precision@3
* Recall@3
* nDCG@3
* Precision@5
* Recall@5
* nDCG@5
* MRR
* Success@3
* Success@5
* Coverage
* MAP
* Diversity@3
* Average Latency
* P95 Latency

Nilai `K` untuk metrik standar dapat dikonfigurasi melalui:

```env
EVAL_K_VALUES
```

---

## Metrik Tambahan

### Success@3 dan Success@5

Mengukur apakah minimal satu hasil relevan muncul di Top-K.

```text
1 = terdapat minimal satu hasil relevan
0 = tidak terdapat hasil relevan
```

Metrik ini menggambarkan apakah pengguna mendapatkan setidaknya satu hasil yang sesuai dalam beberapa hasil pertama.

---

### Coverage

Mengukur persentase query yang menghasilkan minimal satu hasil.

Coverage berbeda dengan Success@K:

* **Coverage** → apakah sistem menghasilkan hasil?
* **Success@K** → apakah hasil relevan muncul di Top-K?

---

### MAP

**Mean Average Precision (MAP)** merupakan rata-rata Average Precision dari seluruh query.

MAP mempertimbangkan posisi dokumen relevan dalam hasil retrieval, sehingga memberikan gambaran yang lebih menyeluruh dibandingkan Precision@K saja.

---

### P95 Latency

P95 adalah nilai latensi pada persentil ke-95.

Artinya, sekitar 95% pengukuran berada pada atau di bawah nilai tersebut.

Konfigurasinya dapat diubah melalui:

```env
EVAL_PERCENTILE_LATENCY
```

P95 digunakan karena rata-rata latency dapat menyembunyikan sebagian request yang jauh lebih lambat.

---

### Diversity@3

Mengukur jumlah kategori material yang berbeda pada tiga hasil teratas.

Nilainya berada pada rentang:

```text
1 → semua hasil berasal dari kategori yang sama
3 → ketiga hasil memiliki kategori berbeda
```

Kategori ditentukan berdasarkan keyword material pada `title` dan `description`.

---

# 🗄️ Skema Database

Struktur database utama terdapat pada:

```text
migrations.sql
```

## `products`

Kolom minimal:

```text
id
title
description
category_branch
latitude
longitude
listing_type
status
search_vector
```

`search_vector` digunakan oleh baseline PostgreSQL Full-text Search dan diisi secara otomatis melalui trigger.

---

## `material_requests`

Kolom:

```text
id
raw_text
latitude
longitude
relevant_listing_ids
created_at
```

`relevant_listing_ids` digunakan khusus untuk kebutuhan evaluasi dan ground truth.

Kolom tersebut bukan bagian dari skema produksi KANA yang sesungguhnya.

Jika project KANA sudah memiliki skema `material_requests` sendiri, tabel evaluasi ini dapat disesuaikan.

Ground truth pada proses evaluasi dibaca langsung dari:

```text
seed_queries.json
```

---

# ⚙️ Ringkasan Pendekatan Matching

## 1. Keyword Baseline

Menggunakan pencarian sederhana dengan PostgreSQL:

```sql
ILIKE
```

Pendekatan ini berfungsi sebagai baseline sederhana berbasis pencocokan kata.

---

## 2. BM25 / Full-text Baseline

Menggunakan PostgreSQL:

```text
to_tsquery
ts_rank
```

Konfigurasi text search menggunakan:

```text
simple
```

Baseline menggunakan OR antar keyword signifikan untuk menghasilkan ranking berbasis term matching.

---

## 3. NLP Pipeline

Pipeline utama menggunakan dua tahap:

```text
Stage 1
Spatial Filtering
       ↓
Stage 2
BM25 Candidate Ranking
       ↓
Stage 3
Semantic Similarity
       ↓
Final Ranking
```

Stage 1 melakukan filtering berdasarkan jarak geografis.

Stage 2 melakukan retrieval kandidat menggunakan BM25.

Stage 3 melakukan semantic similarity melalui NLP Service.

---

# 🧠 Asumsi dan Keputusan Teknis

## 1. PostgreSQL Text Search

Digunakan konfigurasi:

```text
simple
```

bukan:

```text
indonesian
```

PostgreSQL tidak menyediakan konfigurasi Bahasa Indonesia bawaan.

Jika server memiliki dictionary Bahasa Indonesia custom, konfigurasi dapat disesuaikan.

---

## 2. Query Full-text

Baseline menggunakan:

```text
to_tsquery
```

dengan OR antar keyword signifikan.

Hal ini dipilih karena `plainto_tsquery` terhadap kalimat penuh dapat menghasilkan pencarian yang terlalu ketat akibat seluruh kata dianggap sebagai bagian dari query.

---

## 3. Keyword Extraction

Ekstraksi keyword dibuat sederhana:

* lowercase
* menghapus hashtag
* menghapus stopword
* menghapus kata basa-basi umum #CariMaterial

Pendekatan ini memang dibuat sebagai **baseline sederhana**, bukan sebagai NLP pipeline penuh.

---

## 4. Spatial Filtering

Stage 1 disimulasikan menggunakan perhitungan **Haversine** di Python terhadap data `products`.

Belum menggunakan:

* PostGIS
* Bounding-box index

Pendekatan ini cukup untuk ukuran dataset pengujian yang relatif kecil.

---

## 5. Candidate Sorting

Sebelum kandidat dibatasi menjadi 50:

```python
candidates_sorted[:50]
```

kandidat diurutkan berdasarkan:

```text
distance_km
```

Hal ini mencegah kandidat yang relevan terpotong secara acak akibat database tidak memberikan urutan default.

---

## 6. Mock Semantic Score

Pada mock NLP service:

```text
final_score = semantic_score
```

Embedding yang digunakan merupakan vektor pseudo-random dan bukan model machine learning sebenarnya.

---

## 7. Fallback Semantic Threshold

Jika tidak ada kandidat yang melewati `semantic_threshold`, fallback menggunakan:

```text
bm25_score
```

sebagai sinyal ranking.

Hal ini dilakukan agar mock service tetap berguna untuk melakukan sanity check terhadap pipeline.

---

## 8. Query Tanpa Ground Truth

Query yang memiliki:

```text
relevant_listing_ids = []
```

tidak digunakan dalam perhitungan:

* Recall
* MRR
* nDCG
* MAP

karena metrik tersebut tidak terdefinisi tanpa ground truth.

Namun:

* Precision@K
* Success@K
* Coverage
* Diversity@3

tetap dapat dihitung sesuai definisinya.

---

## 9. ID Material Request

`material_requests.id` menggunakan:

```text
TEXT
```

bukan UUID.

Hal ini memungkinkan penggunaan ID sederhana seperti:

```text
q001
q002
q003
```

sehingga hasil evaluasi lebih mudah dibaca.

---

# 🔬 Asumsi Tambahan untuk Metrik

### `EVAL_PERCENTILE_LATENCY`

Variabel:

```env
EVAL_PERCENTILE_LATENCY
```

ditambahkan sebagai konfigurasi baru untuk menentukan percentile latency.

---

### Success@K

Nilai K yang digunakan:

```text
3
5
```

dan tidak mengikuti `EVAL_K_VALUES`.

---

### Diversity@3

Diversity selalu dihitung pada:

```text
Top-3
```

---

### Diversity Category

Kategori diturunkan dari keyword pada:

```text
title + description
```

bukan `category_branch`.

Hal ini karena `category_branch` pada seed data bernilai:

```text
RAW_MATERIAL
```

untuk seluruh produk sehingga tidak cukup diskriminatif untuk mengukur diversity.

---

### Retrieval Depth

`top_n` secara otomatis mencakup kebutuhan:

```text
SUCCESS_K_VALUES
DIVERSITY_K
EVAL_K_VALUES
```

Hal ini memastikan metrik tetap valid meskipun nilai `EVAL_K_VALUES` diubah menjadi lebih kecil dari 5.

---

### MAP

MAP dihitung berdasarkan retrieved list yang sudah dibatasi oleh:

```text
top_n
```

Sehingga secara teknis pengukuran ini dapat dipahami sebagai MAP pada kedalaman retrieval yang digunakan.

---

# ⚠️ Catatan Penting: Mock vs NLP Service Asli

**Jangan menggunakan angka dari Mode Mock sebagai bukti bahwa NLP Pipeline lebih unggul.**

Mock service menggunakan embedding pseudo-random:

```text
Pseudo-random embedding
        ≠
Real semantic model
```

Mode Mock hanya digunakan untuk memastikan:

* Pipeline berjalan.
* Kontrak API berjalan.
* Integrasi antar komponen berjalan.
* Perhitungan metrik berjalan.
* Evaluasi dapat direproduksi.

Untuk mendapatkan hasil yang dapat digunakan sebagai bukti performa NLP Pipeline, evaluasi harus dilakukan menggunakan:

```text
NLP_MODE=real
```

dengan NLP Service asli.

---

# 🎯 Checklist Sebelum Presentasi

Sebelum menggunakan hasil evaluasi untuk presentasi kepada mentor atau juri:

* [ ] Isi `DATABASE_URL` dengan database cloud yang sebenarnya.
* [ ] Pastikan NLP Service asli sudah tersedia.
* [ ] Jalankan evaluasi menggunakan **Mode B / NLP Service asli**.
* [ ] Jangan menggunakan angka dari Mock Mode sebagai bukti keunggulan semantic matching.
* [ ] Pastikan hasil evaluasi memenuhi target yang telah ditentukan.
* [ ] Jika membutuhkan dataset yang lebih representatif, tambahkan listing dan query.
* [ ] Pastikan `relevant_listing_ids` tetap konsisten dengan ground truth.
* [ ] Review seluruh asumsi teknis sebelum presentasi.
* [ ] Jalankan seluruh unit test sebelum finalisasi.

Target evaluasi yang digunakan saat ini:

```text
Precision@3 ≥ 0.4867
MRR         ≥ 0.6944
Success@3   ≥ 0.8000
```

---

# 🧪 Reproducibility

Seed data menggunakan:

```python
random.seed(42)
```

sehingga data yang dihasilkan dapat direproduksi selama input dan proses generator tidak diubah.

Untuk membuat ulang seed data, gunakan:

```bash
python _generate_seed_data.py
```

> Jalankan generator dengan hati-hati jika seed data yang sedang digunakan sudah menjadi bagian dari hasil evaluasi yang ingin dipertahankan.

---

# 📌 Ringkasan Pipeline

Secara sederhana, sistem evaluasi membandingkan:

```text
                    #CariMaterial Query
                            │
                            ▼
                  ┌───────────────────┐
                  │ Spatial Filtering │
                  │     Stage 1       │
                  └─────────┬─────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       Keyword          Full-text      NLP Pipeline
       Baseline          Baseline           │
             │              │               ▼
             │              │          BM25 Stage 2
             │              │               │
             │              │               ▼
             │              │       Semantic Stage 3
             │              │               │
             └──────────────┴───────────────┘
                            │
                            ▼
                    Evaluation Metrics
                            │
                            ▼
               results.md / results.csv
                     / detailed.csv
```

Tujuan akhirnya bukan sekadar menghasilkan satu angka, tetapi menyediakan evaluasi yang dapat digunakan untuk memahami **bagaimana setiap pendekatan bekerja, kapan gagal, dan bagaimana performanya dibandingkan pada dataset yang sama**.
