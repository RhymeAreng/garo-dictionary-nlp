from fastapi import FastAPI
from database import Base, engine
import models
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from schemas import EntryCreate, EntryOut, EntryUpdate
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


@app.put("/entries/{entry_id}", response_model=EntryOut)
def update_entry(entry_id: int, updates: EntryUpdate, db: Session = Depends(get_db)):
    """
    Update an existing entry with partial data.

    Only fields explicitly provided in the request are changed; omitted
    fields keep their current database value.

    Args:
        entry_id: the id of the entry to update.
        updates: the fields to change, with any subset left unset.
        db: database session, injected by FastAPI.

    Returns:
        The updated entry, shaped as EntryOut.

    Raises:
        HTTPException: 404 if no entry with that id exists.
    """
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Delete an entry permanently.

    Args:
        entry_id: the id of the entry to delete.
        db: database session, injected by FastAPI.

    Raises:
        HTTPException: 404 if no entry with that id exists.
    """
    entry = db.query(Entry).filter(Entry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    db.delete(entry)
    db.commit()