from pydantic import BaseModel
from datetime import datetime

class EntryCreate(BaseModel):
    headword: str
    part_of_speech: str
    definition: str
    direction: str
    source_file: str
    source_page: int

class EntryOut(BaseModel):
    id: int
    headword: str
    part_of_speech: str
    definition: str
    direction: str
    source_file: str
    source_page: int
    needs_review: bool
    review_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

class EntryUpdate(BaseModel):
    """
    Schema for updating an existing entry. All fields are optional so a
    caller can update just one field (e.g. only the definition) without
    resending the entire entry.
    """
    headword: str | None = None
    part_of_speech: str | None = None
    definition: str | None = None
    direction: str | None = None
    needs_review: bool | None = None
    review_reason: str | None = None