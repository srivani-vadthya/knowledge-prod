import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "indexed_docs.json")

def load_indexed_docs():
    if not os.path.exists(INDEX_FILE):
        return []
    if os.path.getsize(INDEX_FILE) == 0:
        return []

    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            docs = json.load(f)
    except json.JSONDecodeError:
        return []

    return docs if isinstance(docs, list) else []

def save_indexed_doc(filename):
    docs = load_indexed_docs()
    if filename not in docs:
        docs.append(filename)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)

def is_already_indexed(filename):
    docs = load_indexed_docs()
    return filename in docs
