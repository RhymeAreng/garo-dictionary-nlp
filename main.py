from fastapi import FastAPI
from database import Base, engine
import models
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from schemas import EntryCreate, EntryOut
from models import Entry
from fastapi import HTTPException

Base.metadata.create_all(bind=engine)

app = FastAPI()

#@app.get("/")
#def root():
#    return {"status": "alive"}

#@app.get("/entries/{entry_id}")
#def get_entry_placeholder(entry_id: int):
#    return {"entry_id": entry_id, "note": "this is just a placeholder for now"}


#@app.get("/search-placeholder")
#def search_placeholder(q: str = "", limit: int = 10):
#    return {"query": q, "limit": limit}

@app.post("/entries", response_model=EntryOut)
def create_entry(entry: EntryCreate, db: Session = Depends(get_db)):
    db_entry = Entry(**entry.model_dump())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.get("/entries/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry