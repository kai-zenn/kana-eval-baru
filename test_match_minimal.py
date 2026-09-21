import requests
import json

BASE = "http://localhost:8001"

# Query
query_text = "kain katun bersih"
r = requests.post(f"{BASE}/v1/embed", json={"text": query_text})
query_emb = r.json()["embedding"]

# Test 1: 50 candidates
print("=== Test 1: 50 candidates ===")
candidates = []
for i in range(50):
    r = requests.post(f"{BASE}/v1/embed", json={"text": f"kain bekas {i}"})
    candidates.append({
        "listing_id": f"c{i}",
        "text": f"kain bekas {i}",
        "embedding": r.json()["embedding"],
        "distance_meters": 1000.5
    })

payload = {
    "request_id": "test-50",
    "query_text": query_text,
    "query_embedding": query_emb,
    "candidates": candidates,
    "config": {"bm25_top_k": 10, "final_top_k": 3, "semantic_threshold": 0.80}
}
resp = requests.post(f"{BASE}/v1/match", json=payload)
print(f"Status: {resp.status_code}")
assert resp.status_code == 200
fallback_response = resp.json()
assert fallback_response["stage2_survivor_count"] == 10
assert fallback_response["stage3_survivor_count"] == 0
assert fallback_response["matches"]
assert fallback_response["matches"][0]["final_score"] == fallback_response["matches"][0]["bm25_score"]

# Test 2: 51 candidates
print("\n=== Test 2: 51 candidates ===")
r = requests.post(f"{BASE}/v1/embed", json={"text": "kain bekas 50"})
candidates.append({
    "listing_id": "c50",
    "text": "kain bekas 50",
    "embedding": r.json()["embedding"],
    "distance_meters": 1000.5
})

payload["request_id"] = "test-51"
payload["candidates"] = candidates
resp = requests.post(f"{BASE}/v1/match", json=payload)
print(f"Status: {resp.status_code}")

# Test 3: 100 candidates
print("\n=== Test 3: 100 candidates ===")
for i in range(51, 100):
    r = requests.post(f"{BASE}/v1/embed", json={"text": f"kain bekas {i}"})
    candidates.append({
        "listing_id": f"c{i}",
        "text": f"kain bekas {i}",
        "embedding": r.json()["embedding"],
        "distance_meters": 1000.5
    })

payload["request_id"] = "test-100"
payload["candidates"] = candidates
resp = requests.post(f"{BASE}/v1/match", json=payload)
print(f"Status: {resp.status_code}")