from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Модель данных
class Entry(BaseModel):
    id: int
    title: str
    content: str

# "База данных" в памяти
entries = []

# CRUD операции
@app.post("/entries/")
def create_entry(entry: Entry):
    entries.append(entry)
    return {"message": "Entry created", "entry": entry}

@app.get("/entries/", response_model=List[Entry])
def read_entries():
    return entries

@app.get("/entries/{entry_id}")
def read_entry(entry_id: int):
    entry = next((e for e in entries if e.id == entry_id), None)
    if not entry:
        return {"error": "Entry not found"}
    return entry

@app.put("/entries/{entry_id}")
def update_entry(entry_id: int, updated_entry: Entry):
    for idx, entry in enumerate(entries):
        if entry.id == entry_id:
            entries[idx] = updated_entry
            return {"message": "Entry updated", "entry": updated_entry}
    return {"error": "Entry not found"}

@app.delete("/entries/{entry_id}")
def delete_entry(entry_id: int):
    global entries
    entries = [e for e in entries if e.id != entry_id]
    return {"message": "Entry deleted"}
