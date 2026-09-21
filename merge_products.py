import json

# 40 produk baru
new_products = [
    {"id": "p061", "title": "kain perca kaos", "description": "perca kaos bekas produksi, warna campur, 5kg, kondisi masih oke sih, ga kotor", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2245, "longitude": 106.8995, "status": "AVAILABLE"},
    {"id": "p062", "title": "sisa jahitan daster", "description": "sisa jahitan bikin daster, kain katun, 3kg, udah dipisah per warna", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2250, "longitude": 106.9000, "status": "AVAILABLE"},
    {"id": "p063", "title": "prca jins", "description": "prca jins bekas bikin celana, 4kg, warna biru2, ada yg tua ada yg muda, blm disortir", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2255, "longitude": 106.9005, "status": "AVAILABLE"},
    {"id": "p064", "title": "deadstock kaos polos", "description": "deadstock kaos polos sisa order, 10kg, warna putih sm hitam, msh bagus bgt", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2240, "longitude": 106.8988, "status": "AVAILABLE"},
    {"id": "p065", "title": "kain flanel sisa", "description": "kain flanel sisa bikin boneka, 2kg, warna aneka, lumayan buat prakarya", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2268, "longitude": 106.9012, "status": "AVAILABLE"},
    {"id": "p066", "title": "kardus aqua", "description": "kardus bekas aqua galon, banyak bgt, ukuran gede, kondisi kering", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2260, "longitude": 106.9018, "status": "AVAILABLE"},
    {"id": "p067", "title": "karton bekas indomie", "description": "karton bekas indomie, 5kg, masih kokoh, cocok buat packing atau prakarya", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2248, "longitude": 106.9002, "status": "AVAILABLE"},
    {"id": "p068", "title": "botol plastik aqua", "description": "botol aqua plastik, udah dicuci, 100pcs, bersih bgt", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2265, "longitude": 106.9015, "status": "AVAILABLE"},
    {"id": "p069", "title": "plastik kresek", "description": "kresek bekas belanja, numpuk banyak, campur warna, blm disortir", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2280, "longitude": 106.9025, "status": "AVAILABLE"},
    {"id": "p070", "title": "kaleng sprite", "description": "kaleng sprite sm fanta bekas, udah dicuci bersih, 50pcs", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2258, "longitude": 106.9008, "status": "AVAILABLE"},
    {"id": "p071", "title": "koran bekas", "description": "koran bekas numpuk, 10kg, ada yg udah agak kuning", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2248, "longitude": 106.8998, "status": "AVAILABLE"},
    {"id": "p072", "title": "kertas hvs bekas", "description": "kertas hvs bekas print, 1 sisi aja, 5kg, masih putih", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2235, "longitude": 106.8985, "status": "AVAILABLE"},
    {"id": "p073", "title": "ban motor bekas", "description": "ban motor bekas, udah dipotong kecil2, 3kg, karet tebel", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2262, "longitude": 106.9012, "status": "AVAILABLE"},
    {"id": "p074", "title": "palet kayu", "description": "palet kayu bekas, 3 buah, kondisi kering tp ada yg patah dikit", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2275, "longitude": 106.9022, "status": "AVAILABLE"},
    {"id": "p075", "title": "kain katun putih", "description": "kain katun putih sisa produksi, 5kg, bersih, ada bekas pola dikit", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2242, "longitude": 106.8992, "status": "AVAILABLE"},
    {"id": "p076", "title": "polyester sisa", "description": "kain polyester sisa, 4kg, warna variatif, lumayan bersih", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2253, "longitude": 106.9003, "status": "AVAILABLE"},
    {"id": "p077", "title": "sutra sisa", "description": "sisa kain sutra, 1kg, warna emas sm merah, kondisi premium", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2238, "longitude": 106.8988, "status": "AVAILABLE"},
    {"id": "p078", "title": "perca wol", "description": "perca wol bekas rajutan, 2kg, warna campur, agak berbulu", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2268, "longitude": 106.9018, "status": "AVAILABLE"},
    {"id": "p079", "title": "kain tenun ikat", "description": "kain tenun ikat sisa, 3kg, motif khas NTT, masih bagus", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2245, "longitude": 106.9005, "status": "AVAILABLE"},
    {"id": "p080", "title": "satin sisa", "description": "satin sisa produksi gaun, 4kg, warna pastel, halus", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2250, "longitude": 106.8995, "status": "AVAILABLE"},
    {"id": "p081", "title": "styrofoam", "description": "styrofoam bekas wadah makanan, 20pcs, udah dicuci", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2272, "longitude": 106.9028, "status": "AVAILABLE"},
    {"id": "p082", "title": "bubble wrap", "description": "bubble wrap bekas packing, 5m, msh bagus", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2257, "longitude": 106.9010, "status": "AVAILABLE"},
    {"id": "p083", "title": "drill hitam", "description": "kain drill hitam sisa, 3kg, kualitas ok, bersih", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2240, "longitude": 106.9000, "status": "AVAILABLE"},
    {"id": "p084", "title": "linen sisa", "description": "linen sisa produksi, warna natural, 2kg, tekstur bagus", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2265, "longitude": 106.9008, "status": "AVAILABLE"},
    {"id": "p085", "title": "kulit sintetis", "description": "kulit sintetis sisa bikin tas, hitam, 2kg, masih lentur", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2232, "longitude": 106.8998, "status": "AVAILABLE"},
    {"id": "p086", "title": "kain batik", "description": "kain batik sisa, 6kg, motif tradisional, warna cerah, bersih", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2247, "longitude": 106.9001, "status": "AVAILABLE"},
    {"id": "p087", "title": "kain sifon", "description": "kain sifon sisa, 3kg, warna pastel, tipis", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2252, "longitude": 106.8996, "status": "AVAILABLE"},
    {"id": "p088", "title": "perca sprei", "description": "perca kain sprei, 4kg, warna campur, kondisi bersih", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2260, "longitude": 106.9004, "status": "AVAILABLE"},
    {"id": "p089", "title": "kain parasut", "description": "kain parasut sisa, 3kg, warna army, kokoh", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2243, "longitude": 106.8990, "status": "AVAILABLE"},
    {"id": "p090", "title": "kain jersey", "description": "kain jersey sisa produksi kaos olahraga, 5kg, warna aneka", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2249, "longitude": 106.9007, "status": "AVAILABLE"},
    {"id": "p091", "title": "prca kemeja", "description": "prca kain kemeja, 3kg, warna biru sm putih, blm disortir", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2263, "longitude": 106.9013, "status": "AVAILABLE"},
    {"id": "p092", "title": "kain tile", "description": "kain tile sisa bikin dekor, 2kg, warna putih, agak tipis", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2236, "longitude": 106.8986, "status": "AVAILABLE"},
    {"id": "p093", "title": "perca rajut", "description": "perca benang rajut, 2kg, warna aneka, cocok buat kerajinan", "category_branch": "RAW_MATERIAL", "listing_type": "HIBAH", "latitude": -6.2272, "longitude": 106.9020, "status": "AVAILABLE"},
    {"id": "p094", "title": "kain cordura", "description": "cordura sisa bikin tas, 2kg, warna hitam, kuat", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2241, "longitude": 106.8993, "status": "AVAILABLE"},
    {"id": "p095", "title": "kain satin velvet", "description": "velvet sisa, 3kg, warna burgundy, mewah", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2256, "longitude": 106.9006, "status": "AVAILABLE"},
    {"id": "p096", "title": "kain linen putih", "description": "linen putih sisa, 4kg, bersih, cocok buat produksi", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2244, "longitude": 106.8997, "status": "AVAILABLE"},
    {"id": "p097", "title": "prca jins biru", "description": "prca jins biru muda, 3kg, kondisi oke", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2254, "longitude": 106.9000, "status": "AVAILABLE"},
    {"id": "p098", "title": "kain lace", "description": "kain lace sisa, 2kg, warna krem, halus", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2239, "longitude": 106.8991, "status": "AVAILABLE"},
    {"id": "p099", "title": "kain semi sutra", "description": "semi sutra sisa produksi, 5kg, warna pastel, jatuh", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2247, "longitude": 106.9003, "status": "AVAILABLE"},
    {"id": "p100", "title": "kain tropikal", "description": "tropikal sisa bikin seragam, 6kg, warna army, tebel", "category_branch": "RAW_MATERIAL", "listing_type": "JUAL_BORONGAN", "latitude": -6.2251, "longitude": 106.8999, "status": "AVAILABLE"}
]

# Load existing
existing = json.load(open('seed_products.json'))
existing_ids = {p['id'] for p in existing}

# Only add those that don't exist
added = 0
for p in new_products:
    if p['id'] not in existing_ids:
        existing.append(p)
        added += 1

# Save
json.dump(existing, open('seed_products.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print(f'Added {added} new products. Total now: {len(existing)}')