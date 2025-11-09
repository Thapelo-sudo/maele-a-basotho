# upload_json_to_firestore.py
import json
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore

# Paths based on your stated folder structure
project_root = Path(__file__).resolve().parent
app_folder = project_root / "app"
data_folder = project_root / "data"

firebase_key_path = app_folder / "firebase-key.json"
proverbs_json_path = data_folder / "proverbs.json"

# Validate required files
if not firebase_key_path.exists():
    raise SystemExit(f"❌ firebase-key.json not found at: {firebase_key_path}")

if not proverbs_json_path.exists():
    raise SystemExit(f"❌ proverbs.json not found at: {proverbs_json_path}")

# Initialize Firebase
cred = credentials.Certificate(str(firebase_key_path))
firebase_admin.initialize_app(cred)

db = firestore.client()
proverbs_ref = db.collection("proverbs")

# Load JSON
with open(proverbs_json_path, "r", encoding="utf-8") as f:
    proverbs = json.load(f)

# Upload (avoid duplicates)
existing = {
    (doc.to_dict().get("text") or "").strip().lower(): doc.id
    for doc in proverbs_ref.stream()
}

added_count = 0

for p in proverbs:
    text = (p.get("text") or "").strip()
    if not text:
        continue
    
    key = text.lower()
    if key in existing:
        continue  # skip duplicates

    data = {
        "text": text,
        "meaning": p.get("meaning", "").strip(),
        "translation": p.get("translation", "").strip(),
        "category": p.get("category", "").strip() or "Uncategorized",
        "keywords": [w.lower() for w in text.split()]
    }

    proverbs_ref.add(data)
    added_count += 1

print(f"✅ Upload complete — {added_count} new proverb(s) added.")
