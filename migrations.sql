-- =============================================================================
-- KANA - Migrasi skema minimal untuk keperluan uji performa head-to-head
-- =============================================================================
-- Jalankan sekali di database PostgreSQL kamu (Neon/Supabase/Aiven/dll), mis:
--   psql "$DATABASE_URL" -f migrations.sql
--
-- Kalau tim KANA sudah punya skema `products` / `material_requests` sendiri,
-- ABAIKAN file ini dan sesuaikan query di evaluate_matching.py ke skema kalian
-- (kolom minimal yang dibutuhkan skrip: id, title, description, latitude,
-- longitude, status -- lihat komentar di evaluate_matching.py).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto; -- untuk gen_random_uuid(), kalau belum ada

-- -----------------------------------------------------------------------------
-- Tabel: products
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    category_branch  TEXT NOT NULL DEFAULT 'RAW_MATERIAL',
    latitude         DOUBLE PRECISION NOT NULL,
    longitude        DOUBLE PRECISION NOT NULL,
    listing_type     TEXT NOT NULL CHECK (listing_type IN ('HIBAH', 'JUAL_BORONGAN')),
    status           TEXT NOT NULL DEFAULT 'AVAILABLE',
    search_vector    TSVECTOR,               -- dipakai Baseline 2 (full-text search)
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ASUMSI: PostgreSQL tidak menyediakan text-search configuration 'indonesian'
-- bawaan (berbeda dengan 'english'/'german'/dst), jadi baseline full-text di
-- evaluate_matching.py memakai configuration 'simple' (tokenisasi tanpa
-- stemming). Kalau kalian sudah pasang dictionary Bahasa Indonesia custom di
-- server Postgres kalian, ganti 'simple' di trigger & query jadi nama
-- configuration tersebut untuk hasil Baseline 2 yang lebih representatif.
CREATE OR REPLACE FUNCTION products_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('simple', coalesce(NEW.title, '') || ' ' || coalesce(NEW.description, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_search_vector ON products;
CREATE TRIGGER trg_products_search_vector
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION products_search_vector_update();

CREATE INDEX IF NOT EXISTS idx_products_search_vector ON products USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_products_status ON products (status);
CREATE INDEX IF NOT EXISTS idx_products_lat_lon ON products (latitude, longitude);

-- -----------------------------------------------------------------------------
-- Tabel: material_requests  (posting #CariMaterial)
-- -----------------------------------------------------------------------------
-- NB: id di sini TEXT (bukan UUID) karena seed_queries.json memakai id
-- ringkas seperti "q001" untuk memudahkan pembacaan tabel hasil evaluasi.
-- Kalau skema produksi kalian butuh UUID asli, ganti ke UUID DEFAULT
-- gen_random_uuid() dan sesuaikan id di seed_queries.json.
CREATE TABLE IF NOT EXISTS material_requests (
    id                     TEXT PRIMARY KEY,
    raw_text               TEXT NOT NULL,
    latitude               DOUBLE PRECISION NOT NULL,
    longitude              DOUBLE PRECISION NOT NULL,
    -- ASUMSI: kolom relevant_listing_ids BUKAN bagian dari skema produksi KANA
    -- sesungguhnya -- ini hanya dipakai untuk menyimpan ground truth evaluasi
    -- (dari seed_queries.json) supaya bisa dipakai ulang lewat SQL kalau perlu.
    -- Kalau kalian ingin skema material_requests yang 100% bersih tanpa kolom
    -- eval-only ini, hapus kolom ini -- evaluate_matching.py tetap bisa jalan
    -- karena ground truth juga dibaca langsung dari seed_queries.json.
    -- TEXT[] (bukan UUID[]) supaya insert dari psycopg2 tidak perlu cast
    -- eksplisit; evaluate_matching.py sendiri membaca ground truth langsung
    -- dari seed_queries.json, jadi kolom ini murni untuk keperluan audit manual.
    relevant_listing_ids   TEXT[] NOT NULL DEFAULT '{}',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_material_requests_lat_lon ON material_requests (latitude, longitude);
