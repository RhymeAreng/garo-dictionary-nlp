from fastapi import FastAPI
from schemas import EntryCreate
from database import Base, engine
import models

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def root():
    return {"status": "alive"}

@app.get("/entries/{entry_id}")
def get_entry_placeholder(entry_id: int):
    return {"entry_id": entry_id, "note": "this is just a placeholder for now"}


@app.get("/search-placeholder")
def search_placeholder(q: str = "", limit: int = 10):
    return {"query": q, "limit": limit}

