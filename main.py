from fastapi import FastAPI
from database import Base, engine
import models
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db
from schemas import EntryCreate, EntryOut, EntryUpdate
from models import Entry
from fastapi import HTTPException
from typing import Optional
from fastapi.staticfiles import StaticFiles




Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

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


@app.get("/entries/needs-review", response_model=list[EntryOut])
def list_entries_needing_review(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List entries flagged for manual review, prioritized so the most
    important flags surface first.

    Entries with an apostrophe-related flag are shown before other flagged
    entries, since Garo stress marks are the highest-stakes correctness
    issue in this project -- an OCR error here silently changes the
    meaning of a word, not just its spelling.

    Args:
        limit: maximum number of entries to return.
        offset: number of entries to skip (for paging through the queue).
        db: database session, injected by FastAPI.

    Returns:
        A list of unverified entries, apostrophe-flagged ones first.
    """
    query = db.query(Entry).filter(Entry.needs_review == True)

    query = query.order_by(
        Entry.review_reason.like("%apostrophe%").desc(),
        Entry.id.asc()
    )

    return query.offset(offset).limit(limit).all()



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


@app.get("/entries", response_model=list[EntryOut])
def list_entries(
    direction: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List dictionary entries with optional filtering and pagination.

    Args:
        direction: if provided, only return entries matching this direction
            (e.g. "garo_to_english" or "english_to_garo"). If omitted,
            entries from both directions are returned.
        limit: maximum number of entries to return in this response.
        offset: number of entries to skip before starting to return results
            (used together with limit to page through results).
        db: database session, injected by FastAPI.

    Returns:
        A list of entries, shaped as EntryOut, matching the given filters.
    """
    query = db.query(Entry)

    if direction is not None:
        query = query.filter(Entry.direction == direction)

    return query.offset(offset).limit(limit).all()







