import requests
import numpy as np

BASE = "http://localhost:8001"

# Ambil 3 pasang query-candidate yang mirip
test_pairs = [
    ("kain katun bersih", "kain katun bersih 5kg"),
    ("perca batik", "kain perca batik campur warna"),
    ("kardus bekas", "kardus bekas ukuran besar"),
    ("sisa jahitan", "sisa jahitan katun sisa produksi"),
    ("botol plastik PET", "botol plastik PET udah dicuci"),
]

print("=" * 70)
print(f"{'Query':<25} {'Candidate':<30} {'Sim':>6}")
print("=" * 70)

similarities = []
for q, c in test_pairs:
    q_emb = requests.post(f"{BASE}/v1/embed", json={"text": q}).json()["embedding"]
    c_emb = requests.post(f"{BASE}/v1/embed", json={"text": c}).json()["embedding"]
    
    # Hitung manual cosine similarity
    q_arr, c_arr = np.array(q_emb), np.array(c_emb)
    sim = float(np.dot(q_arr, c_arr) / (np.linalg.norm(q_arr) * np.linalg.norm(c_arr)))
    similarities.append(sim)
    print(f"{q[:24]:<25} {c[:29]:<30} {sim:.4f}")

print("=" * 70)
print(f"Min:  {min(similarities):.4f}")
print(f"Mean: {np.mean(similarities):.4f}")
print(f"Max:  {max(similarities):.4f}")
print("=" * 70)