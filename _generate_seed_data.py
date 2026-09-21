"""
Skrip internal untuk MEMBANGKITKAN seed_products.json dan seed_queries.json.
Ini bukan bagian dari deliverable utama (evaluate_matching.py tidak butuh file ini
untuk berjalan) -- ini hanya dipakai sekali untuk menghasilkan data seed yang
konsisten, realistis, dan dengan ground truth yang bisa dipertanggungjawabkan
(ground truth dihitung dari kategori+kondisi material sebenarnya, bukan dari
kecocokan string).

Dijalankan sekali dengan seed acak tetap (deterministic) agar hasilnya reproducible.
"""
import json
import random
import uuid

random.seed(42)

# -----------------------------------------------------------------------
# 1. Master data kategori material (limbah industri kreatif, fokus tekstil)
#    Tiap kategori punya beberapa varian frasa (formal/informal/sinonim)
#    yang dipakai untuk judul & deskripsi produk maupun query.
# -----------------------------------------------------------------------
CATEGORIES = {
    "perca_katun": {
        "label": "kain perca katun",
        "title_variants": [
            "Kain Perca Katun {cond}",
            "Sisa Kain Katun {cond}",
            "Perca Katun Campur Warna {cond}",
            "Cutting Kain Katun {cond}",
        ],
        "desc_variants": [
            "Kain perca katun campur warna dan motif, {cond_desc}, sisa produksi konveksi kaos.",
            "Sisa jahitan katun ukuran variatif, {cond_desc}, cocok untuk bahan tas atau quilting.",
            "Perca katun aneka warna, {cond_desc}, sisa potongan pabrik garmen.",
            "Deadstock katun sisa produksi, {cond_desc}, tersedia dalam karung.",
        ],
    },
    "perca_batik": {
        "label": "kain perca batik",
        "title_variants": [
            "Kain Perca Batik {cond}",
            "Sisa Kain Batik {cond}",
            "Potongan Batik Campur Motif {cond}",
        ],
        "desc_variants": [
            "Kain perca batik campur warna, ukuran variatif, {cond_desc}, sisa produksi konveksi.",
            "Sisa kain batik motif campur, {cond_desc}, bekas cutting produksi seragam batik.",
            "Potongan batik aneka motif, {cond_desc}, cocok untuk kerajinan tangan dan tas.",
        ],
    },
    "denim": {
        "label": "kain denim / jeans bekas",
        "title_variants": [
            "Limbah Denim Sisa Produksi {cond}",
            "Potongan Jeans Bekas {cond}",
            "Scrap Denim Konveksi {cond}",
        ],
        "desc_variants": [
            "Sisa potongan denim dari produksi celana, {cond_desc}, tebal dan kuat untuk upcycle.",
            "Limbah jeans bekas cutting pabrik, {cond_desc}, cocok untuk tas atau dompet.",
            "Scrap denim campur warna biru tua dan muda, {cond_desc}.",
        ],
    },
    "flanel": {
        "label": "kain flanel sisa",
        "title_variants": [
            "Sisa Kain Flanel {cond}",
            "Potongan Flanel Aneka Warna {cond}",
            "Perca Flanel Produksi Boneka {cond}",
        ],
        "desc_variants": [
            "Sisa kain flanel aneka warna dari produksi boneka, {cond_desc}, ukuran kecil-sedang.",
            "Potongan flanel sisa kerajinan, {cond_desc}, cocok untuk prakarya anak.",
        ],
    },
    "benang_wol": {
        "label": "benang wol / rajut sisa",
        "title_variants": [
            "Sisa Benang Wol Rajut {cond}",
            "Cone Benang Sisa Produksi {cond}",
            "Limbah Benang Rajut Aneka Warna {cond}",
        ],
        "desc_variants": [
            "Sisa cone benang wol dari produksi sweater, {cond_desc}, beberapa warna tersedia.",
            "Limbah benang rajut sisa pabrik, {cond_desc}, panjang bervariasi per gulung.",
        ],
    },
    "tulle": {
        "label": "kain tulle / tile sisa",
        "title_variants": [
            "Sisa Kain Tulle {cond}",
            "Potongan Tile Produksi Gaun {cond}",
        ],
        "desc_variants": [
            "Sisa kain tulle dari produksi gaun pesta, {cond_desc}, warna pastel campur.",
            "Potongan tile sisa jahit, {cond_desc}, cocok untuk dekorasi atau kerajinan.",
        ],
    },
    "kulit_sintetis": {
        "label": "kulit sintetis sisa",
        "title_variants": [
            "Sisa Kulit Sintetis Produksi Tas {cond}",
            "Cutting Kulit Oscar Sisa {cond}",
            "Limbah Kulit Imitasi Konveksi {cond}",
        ],
        "desc_variants": [
            "Sisa cutting kulit sintetis dari produksi tas dan dompet, {cond_desc}.",
            "Limbah kulit imitasi (kulit oscar) sisa produksi sepatu, {cond_desc}.",
        ],
    },
    "satin_sutra": {
        "label": "kain satin / sutra sintetis sisa",
        "title_variants": [
            "Sisa Kain Satin {cond}",
            "Potongan Sutra Sintetis Produksi {cond}",
        ],
        "desc_variants": [
            "Sisa kain satin dari produksi kebaya, {cond_desc}, warna mengkilap campur.",
            "Potongan sutra sintetis sisa jahit, {cond_desc}, licin dan lembut.",
        ],
    },
    "karton": {
        "label": "kertas karton bekas",
        "title_variants": [
            "Limbah Karton Percetakan {cond}",
            "Sisa Kardus Bekas Produksi {cond}",
        ],
        "desc_variants": [
            "Sisa karton dari percetakan kemasan, {cond_desc}, tebal 2-3mm, cocok untuk prakarya.",
            "Limbah kardus bekas gudang, {cond_desc}, ukuran lembaran bervariasi.",
        ],
    },
    "plastik_pet": {
        "label": "plastik PET / botol bekas",
        "title_variants": [
            "Limbah Botol PET Bekas {cond}",
            "Sisa Plastik PET Cacahan {cond}",
        ],
        "desc_variants": [
            "Botol plastik PET bekas sudah dipilah, {cond_desc}, siap untuk didaur ulang jadi kerajinan.",
            "Cacahan plastik PET sisa produksi, {cond_desc}, dalam karung.",
        ],
    },
    "limbah_kayu": {
        "label": "limbah kayu / serbuk kayu",
        "title_variants": [
            "Sisa Serbuk Gergaji Mebel {cond}",
            "Limbah Potongan Kayu Bekas {cond}",
        ],
        "desc_variants": [
            "Serbuk gergaji sisa produksi mebel, {cond_desc}, kering dan bersih dari paku.",
            "Potongan kayu sisa bengkel mebel, {cond_desc}, ukuran kecil-sedang.",
        ],
    },
    "karet_ban": {
        "label": "karet ban dalam bekas",
        "title_variants": [
            "Limbah Ban Dalam Bekas {cond}",
            "Sisa Karet Ban Vulkanisir {cond}",
        ],
        "desc_variants": [
            "Ban dalam bekas motor, {cond_desc}, cocok untuk kerajinan dompet atau sandal.",
            "Sisa karet dari bengkel vulkanisir, {cond_desc}, elastis dan tebal.",
        ],
    },
}

CONDITIONS = [
    ("bersih", "kondisi bersih dan kering"),
    ("bersih", "sudah dicuci, bersih, siap pakai"),
    ("campur", "kondisi campur, sebagian bersih sebagian perlu dicuci ulang"),
    ("kotor", "kondisi apa adanya, belum dicuci, sedikit kotor sisa produksi"),
]

CITIES = [
    ("Jakarta Selatan", -6.2615, 106.8106),
    ("Jakarta Timur", -6.2250, 106.9004),
    ("Jakarta Barat", -6.1352, 106.8133),
    ("Jakarta Utara", -6.1214, 106.8827),
    ("Jakarta Pusat", -6.1805, 106.8284),
    ("Bekasi", -6.2383, 107.0009),
    ("Tangerang", -6.1783, 106.6319),
    ("Depok", -6.4025, 106.7942),
    ("Bogor", -6.5971, 106.8060),
    ("Bandung", -6.9175, 107.6191),
]

LISTING_TYPES = ["JUAL_BORONGAN", "JUAL_BORONGAN", "JUAL_BORONGAN", "HIBAH"]  # weighted


def jitter(v, amt=0.05):
    return v + random.uniform(-amt, amt)


products = []
category_to_ids = {}          # category_key -> list of all product ids
category_clean_to_ids = {}    # category_key -> list of product ids with condition == bersih

PRODUCTS_PER_CATEGORY = 5

for cat_key, cat in CATEGORIES.items():
    category_to_ids[cat_key] = []
    category_clean_to_ids[cat_key] = []
    for i in range(PRODUCTS_PER_CATEGORY):
        cond_tag, cond_desc = CONDITIONS[i % len(CONDITIONS)]
        city_name, lat, lon = random.choice(CITIES)
        weight_kg = random.choice([3, 5, 8, 10, 15, 20, 25, 30, 50])
        title_tpl = random.choice(cat["title_variants"])
        desc_tpl = random.choice(cat["desc_variants"])
        cond_label = {"bersih": "Bersih", "campur": "Campur", "kotor": "Kondisi Apa Adanya"}[cond_tag]

        title = title_tpl.format(cond=cond_label) + f" - {weight_kg}kg"
        description = (
            desc_tpl.format(cond_desc=cond_desc)
            + f" Berat sekitar {weight_kg}kg. Lokasi {city_name}."
        )

        pid = str(uuid.uuid4())
        product = {
            "id": pid,
            "title": title,
            "description": description,
            "category_branch": "RAW_MATERIAL",
            "latitude": round(jitter(lat), 6),
            "longitude": round(jitter(lon), 6),
            "listing_type": random.choice(LISTING_TYPES),
            "status": "AVAILABLE",
            # metadata below is extra context for the eval script / humans reading the
            # seed file; it is NOT part of the real KANA product schema.
            "_material_category": cat_key,
            "_condition": cond_tag,
            "_weight_kg": weight_kg,
            "_city": city_name,
        }
        products.append(product)
        category_to_ids[cat_key].append(pid)
        if cond_tag in ("bersih", "campur"):
            category_clean_to_ids[cat_key].append(pid)

random.shuffle(products)

# -----------------------------------------------------------------------
# 2. Query templates (#CariMaterial). Sengaja dibuat dengan variasi gaya
#    bahasa (formal / informal / sinonim / typo ringan) supaya baseline
#    keyword & BM25 diuji dengan realistis -- beberapa query TIDAK memakai
#    kata yang sama persis dengan listing target, untuk melihat apakah
#    pipeline semantik unggul dibanding pencocokan string literal.
# -----------------------------------------------------------------------
QUERY_TEMPLATES = [
    # (category_key, require_clean, raw_text_template)
    ("perca_katun", True,
     "#CariMaterial Membutuhkan kain katun bersih minimal 5kg untuk produksi tas, area Jaksel ya kak"),
    ("perca_katun", False,
     "#CariMaterial butuh perca kain katun, yg penting banyak, buat isian bantal, kondisi ga masalah"),
    ("perca_katun", True,
     "#CariMaterial cari sisa jahitan katun buat bahan quilting, mesti bersih dan kering"),
    ("perca_batik", False,
     "#CariMaterial nyari kain sisa produksi batik, mau dijadiin tas etnik, warna bebas"),
    ("perca_batik", True,
     "#CariMaterial Membutuhkan potongan batik kondisi bersih untuk kerajinan dompet, sekitar 3-5kg"),
    ("denim", False,
     "#CariMaterial ada yg jual limbah jeans/denim ga? buat bikin apron sama tote bag"),
    ("denim", True,
     "#CariMaterial cari deadstock denim bersih, mau dipakai produksi dompet kecil, kirim2 boleh"),
    ("flanel", False,
     "#CariMaterial butuh potongan flanel warna-warni buat prakarya anak sekolah, ga usah bersih bgt"),
    ("benang_wol", False,
     "#CariMaterial nyari sisa benang rajut/wol, buat proyek merajut tas, warna campur juga oke"),
    ("tulle", True,
     "#CariMaterial cari kain tulle sisa produksi gaun, kondisi bersih, buat bikin dekorasi pernikahan"),
    ("kulit_sintetis", True,
     "#CariMaterial Membutuhkan sisa kulit sintetis (oscar) kondisi bersih untuk produksi dompet"),
    ("kulit_sintetis", False,
     "#CariMaterial ada limbah kulit imitasi ga min, buat sol sepatu handmade, ga masalah kalau agak kotor"),
    ("satin_sutra", False,
     "#CariMaterial cari sisa kain satin atau sutra sintetis buat aksesoris rambut"),
    ("karton", False,
     "#CariMaterial butuh limbah karton tebal dari percetakan buat bikin diorama, banyakin aja"),
    ("plastik_pet", True,
     "#CariMaterial nyari botol PET bekas yang udah dipilah bersih, buat proyek ecobrick sekolah"),
    ("limbah_kayu", False,
     "#CariMaterial ada sisa serbuk gergaji atau potongan kayu mebel? buat campuran kerajinan resin"),
    ("karet_ban", False,
     "#CariMaterial cari ban dalam bekas motor buat bikin dompet karet, kondisi apa aja gpp"),
    ("perca_katun", False,
     "#CariMaterial deadstock tekstil katun dicari, jumlah besar untuk borongan, harga nego"),
    ("perca_batik", False,
     "#CariMaterial ada perca batik ga kak buat campuran patchwork, warna semenarik mungkin"),
    ("denim", False,
     "#CariMaterial scrap denim konveksi dicari, buat bahan produksi ecoprint tas"),
    ("flanel", True,
     "#CariMaterial cari sisa flanel kondisi bersih buat boneka jahit tangan, kualitas rapi ya"),
    ("tulle", False,
     "#CariMaterial ada potongan tile sisa jahit ga, buat bikin rok tutu anak"),
    ("benang_wol", True,
     "#CariMaterial butuh cone benang sisa bersih untuk produksi syal rajut, warna netral diutamakan"),
    ("satin_sutra", True,
     "#CariMaterial mencari kain satin sisa dengan kondisi bersih untuk produksi mukena"),
    ("karet_ban", True,
     "#CariMaterial dicari limbah karet ban yang sudah bersih, buat sandal handmade custom"),
]

# Dua query "edge case": mencari material yang TIDAK ada sama sekali di seed
# products, untuk menguji bahwa sistem (dan skrip metrik) tetap aman ketika
# relevant_listing_ids kosong (tidak divide-by-zero, precision/recall = 0).
EDGE_CASE_QUERIES = [
    "#CariMaterial cari limbah akrilik bening sisa laser cutting, ada yang punya?",
    "#CariMaterial butuh sisa kaca patri untuk kerajinan, lokasi Jakarta",
]

queries = []
for idx, (cat_key, require_clean, raw_text) in enumerate(QUERY_TEMPLATES, start=1):
    city_name, lat, lon = random.choice(CITIES)
    relevant_ids = (
        category_clean_to_ids[cat_key] if require_clean else category_to_ids[cat_key]
    )
    queries.append({
        "id": f"q{idx:03d}",
        "raw_text": raw_text,
        "latitude": round(jitter(lat), 6),
        "longitude": round(jitter(lon), 6),
        "relevant_listing_ids": relevant_ids,
        "_target_category": cat_key,
        "_require_clean": require_clean,
    })

for j, raw_text in enumerate(EDGE_CASE_QUERIES, start=len(QUERY_TEMPLATES) + 1):
    city_name, lat, lon = random.choice(CITIES)
    queries.append({
        "id": f"q{j:03d}",
        "raw_text": raw_text,
        "latitude": round(jitter(lat), 6),
        "longitude": round(jitter(lon), 6),
        "relevant_listing_ids": [],
        "_target_category": None,
        "_require_clean": None,
    })

# Buang field metadata berawalan underscore dari produk sebelum ditulis final,
# TAPI simpan versi "debug" terpisah supaya masih bisa diperiksa manusia.
def strip_private(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}

products_public = [strip_private(p) for p in products]
queries_public = [strip_private(q) for q in queries]

with open("seed_products.json", "w", encoding="utf-8") as f:
    json.dump(products_public, f, ensure_ascii=False, indent=2)

with open("seed_queries.json", "w", encoding="utf-8") as f:
    json.dump(queries_public, f, ensure_ascii=False, indent=2)

with open("_seed_debug.json", "w", encoding="utf-8") as f:
    json.dump({"products": products, "queries": queries}, f, ensure_ascii=False, indent=2)

print(f"products: {len(products_public)}")
print(f"queries: {len(queries_public)}")
print("relevant count per query:")
for q in queries_public:
    print(" ", q["id"], len(q["relevant_listing_ids"]))
