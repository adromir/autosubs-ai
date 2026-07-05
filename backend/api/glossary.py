from pydantic import BaseModel
from typing import List
from fastapi import APIRouter
import uuid
import json
import os
from pathlib import Path

router = APIRouter(prefix="/glossary", tags=["Glossary"])

GLOSSARY_FILE = Path(__file__).parent.parent / "data" / "glossary.json"

class GlossaryEntry(BaseModel):
    id: str
    source_lang: str
    target_lang: str
    source_term: str
    target_term: str

class GlossaryCreate(BaseModel):
    source_lang: str
    target_lang: str
    source_term: str
    target_term: str

def load_glossary():
    if not GLOSSARY_FILE.exists():
        return []
    try:
        with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_glossary(data):
    GLOSSARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOSSARY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@router.get("/")
def get_glossary():
    return load_glossary()

@router.post("/")
def add_glossary_entry(entry: GlossaryCreate):
    data = load_glossary()
    new_entry = {
        "id": str(uuid.uuid4()),
        "source_lang": entry.source_lang,
        "target_lang": entry.target_lang,
        "source_term": entry.source_term,
        "target_term": entry.target_term
    }
    data.append(new_entry)
    save_glossary(data)
    return new_entry

@router.delete("/{entry_id}")
def delete_glossary_entry(entry_id: str):
    data = load_glossary()
    new_data = [e for e in data if e.get("id") != entry_id]
    save_glossary(new_data)
    return {"status": "ok"}
