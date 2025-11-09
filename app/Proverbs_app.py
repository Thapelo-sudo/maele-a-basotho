# Proverbs_app.py
import streamlit as st
import random
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
from typing import List, Dict

# ----------------------
# PAGE / PWA META (optional)
# ----------------------
st.set_page_config(page_title="Maele a Basotho", page_icon="📜", layout="centered")

# ----------------------
# FIREBASE INITIALIZATION
# ----------------------
def init_firebase():
    """
    Initialize firebase-admin either from Streamlit secrets (st.secrets["firebase"])
    or from a local file firebase-key.json placed in the same folder as this script.
    Returns (True, info_str) on success or (False, error_str) on failure.
    """
    if firebase_admin._apps:
        return True, "already-initialized"

    try:
        # Check Streamlit secrets first (structure: st.secrets["firebase"] should be a mapping)
        if "firebase" in st.secrets and st.secrets["firebase"]:
            # convert mappingproxy to dict if necessary
            key_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            return True, "initialized-from-secrets"

        # Local dev fallback: expect firebase-key.json next to this script
        here = Path(__file__).resolve().parent
        local_key = here / "firebase-key.json"
        if not local_key.exists():
            return False, f"local-key-missing: {local_key}"
        cred = credentials.Certificate(str(local_key))
        firebase_admin.initialize_app(cred)
        return True, "initialized-from-local-file"

    except Exception as e:
        return False, str(e)


ok, msg = init_firebase()
if not ok:
    st.error("⚠️ Firebase initialization failed: " + str(msg))
    st.stop()

# Firestore client and collection ref
db = firestore.client()
proverbs_ref = db.collection("proverbs")

# ----------------------
# Firestore helpers
# ----------------------
def load_proverbs() -> List[Dict]:
    """Load all proverbs from Firestore and return as a list of dicts."""
    try:
        docs = proverbs_ref.stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in docs]
    except Exception as e:
        st.error(f"Error loading proverbs: {e}")
        return []

def add_proverb_doc(doc: Dict) -> None:
    """Add a proverb document to Firestore."""
    try:
        proverbs_ref.add(doc)
    except Exception as e:
        st.error(f"Failed to add proverb: {e}")

def update_proverb_doc(doc_id: str, data: Dict) -> None:
    """Update a proverb document by id."""
    try:
        proverbs_ref.document(doc_id).set(data)
    except Exception as e:
        st.error(f"Failed to update: {e}")

def delete_proverb_doc(doc_id: str) -> None:
    """Delete a proverb document by id."""
    try:
        proverbs_ref.document(doc_id).delete()
    except Exception as e:
        st.error(f"Failed to delete: {e}")

# ----------------------
# Utilities
# ----------------------
def search_proverbs(proverbs: List[Dict], keyword: str, search_in_meaning: bool=True) -> List[Dict]:
    """Case-insensitive search over 'text' and optionally 'meaning' fields."""
    k = keyword.lower().strip()
    if not k:
        return []
    results = []
    for p in proverbs:
        text = (p.get("text") or "").lower()
        meaning = (p.get("meaning") or "").lower()
        if k in text or (search_in_meaning and k in meaning):
            results.append(p)
    return results

def categories_from(proverbs: List[Dict]) -> List[str]:
    """Return sorted list of unique categories (fallback to 'Uncategorized')."""
    cats = sorted({((p.get("category") or "Uncategorized").strip()) for p in proverbs})
    return cats

def display_proverb(p: Dict, language: str):
    """Render a single proverb card."""
    text = p.get("text") or ""
    meaning = p.get("meaning") or ""
    translation = p.get("translation") or ""
    st.markdown("#### " + text)
    st.write(f"**Tlhaloso (Sesotho):** {meaning}")
    if translation:
        st.write(f"**English translation:** {translation}")
    st.write("---")

# ----------------------
# UI
# ----------------------
st.title("📖 Maele a Basotho — Basotho Proverbs Explorer")

# Load data fresh
proverbs = load_proverbs()

# Language toggle (display only - dataset fields are "text","meaning","translation")
language = st.radio("Choose language view:", ("Sesotho", "English"))

# Sidebar nav
st.sidebar.header("Navigation")
option = st.sidebar.radio("Choose an option:",
                          ["Search by Keyword", "Filter by Category", "Random Proverb", "Admin Interface", "View All"])

# --- Search by Keyword ---
if option == "Search by Keyword":
    st.subheader("🔍 Search by Keyword (e.g., Khomo, Ntja, Tau, Metsi)")
    st.write("Quick keywords: 🐄 Khomo | 🦁 Tau | 🐕 Ntja | 💧 Metsi | 🦊 Phiri")
    # Suggested keyword buttons
    suggested = [("🐄 Khomo","Khomo"), ("🦁 Tau","Tau"), ("🐕 Ntja","Ntja"),
                 ("💧 Metsi","Metsi"), ("🦊 Phiri","Phiri"), ("🐦 Nonyana","Nonyana"),
                 ("❤️ Lerato","Lerato")]
    cols = st.columns(3)
    for i, (label, val) in enumerate(suggested):
        if cols[i % 3].button(label):
            st.session_state["keyword"] = val

    keyword = st.text_input("Enter keyword (Sesotho):", value=st.session_state.get("keyword", ""))
    search_meaning = st.checkbox("Also search in meanings", value=True)

    if keyword:
        matches = search_proverbs(proverbs, keyword, search_meaning)
        if matches:
            st.success(f"Found {len(matches)} result(s)")
            for p in matches:
                display_proverb(p, language)
        else:
            st.warning("No matching proverbs found.")

# --- Filter by Category ---
elif option == "Filter by Category":
    st.subheader("📂 Filter by Category")
    cats = categories_from(proverbs)
    if not cats:
        st.info("No categories found yet.")
    else:
        c = st.selectbox("Select category:", cats)
        if c:
            filtered = [p for p in proverbs if ((p.get("category") or "Uncategorized").strip()) == c]
            st.success(f"{len(filtered)} proverb(s)")
            for p in filtered:
                display_proverb(p, language)

# --- Random Proverb ---
elif option == "Random Proverb":
    st.subheader("🎲 Random Proverb")
    if proverbs:
        display_proverb(random.choice(proverbs), language)
    else:
        st.info("No proverbs available.")

# --- View All ---
elif option == "View All":
    st.subheader("All Proverbs")
    if proverbs:
        for p in proverbs:
            display_proverb(p, language)
    else:
        st.info("No proverbs found. Admin can add some.")

# --- Admin Interface ---
elif option == "Admin Interface":
    st.subheader("🔒 Admin (password protected)")

    # Read admin password from Streamlit secrets
    admin_pw = st.secrets.get("ADMIN_PASSWORD")
    if not admin_pw:
        st.warning("⚠️ Admin password not configured. Set ADMIN_PASSWORD in .streamlit/secrets.toml")
    password = st.text_input("Enter Admin password:", type="password")

    if admin_pw and password == admin_pw:
        st.success("Welcome admin.")

        st.markdown("### ➕ Add new proverb")
        new_text = st.text_input("Proverb (Sesotho):", key="add_text")
        new_meaning = st.text_area("Meaning (Sesotho):", key="add_meaning")
        new_translation = st.text_input("English translation (optional):", key="add_trans")
        new_category = st.text_input("Category (e.g., Wisdom, Animals):", key="add_cat")

        if st.button("Add Proverb"):
            # duplicate check by exact text (case insensitive)
            existing_texts = [ (p.get("text") or "").strip().lower() for p in proverbs ]
            if not new_text.strip() or not new_meaning.strip():
                st.error("Proverb text and meaning are required.")
            elif new_text.strip().lower() in existing_texts:
                st.error("This proverb already exists. It will not be added.")
            else:
                doc = {
                    "text": new_text.strip(),
                    "meaning": new_meaning.strip(),
                    "translation": new_translation.strip(),
                    "category": new_category.strip() or "Uncategorized",
                    "keywords": [w.lower() for w in new_text.split()]
                }
                add_proverb_doc(doc)
                st.success("✅ Added successfully!")
                st.rerun()

        st.markdown("---")
        st.markdown("### ✏️ Edit / Delete")

        if proverbs:
            choice_texts = [p.get("text") or "" for p in proverbs]
            sel = st.selectbox("Select proverb to edit:", choice_texts)
            selected = next((p for p in proverbs if (p.get("text") or "") == sel), None)

            if selected:
                edit_text = st.text_input("Proverb:", value=selected.get("text", ""), key="edit_text")
                edit_meaning = st.text_area("Meaning:", value=selected.get("meaning", ""), key="edit_meaning")
                edit_translation = st.text_input("Translation:", value=selected.get("translation", ""), key="edit_trans")
                edit_category = st.text_input("Category:", value=selected.get("category", ""), key="edit_cat")

                if st.button("Save Changes"):
                    # check duplicate when renaming
                    other_texts = [ (p.get("text") or "").strip().lower() for p in proverbs if p["id"] != selected["id"] ]
                    if edit_text.strip().lower() in other_texts:
                        st.error("Cannot rename: another proverb with that exact text exists.")
                    else:
                        updated = {
                            "text": edit_text.strip(),
                            "meaning": edit_meaning.strip(),
                            "translation": edit_translation.strip(),
                            "category": edit_category.strip() or "Uncategorized",
                            "keywords": [w.lower() for w in edit_text.split()]
                        }
                        update_proverb_doc(selected["id"], updated)
                        st.success("✅ Updated successfully!")
                        st.rerun()

                if st.button("Delete Proverb"):
                    delete_proverb_doc(selected["id"])
                    st.success("🗑️ Deleted successfully!")
                    st.rerun()

        else:
            st.info("No proverbs to edit/delete.")
    elif password:
        st.error("❌ Invalid password. Only admin can access.")
