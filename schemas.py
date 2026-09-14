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

    class Config:
        from_attributes = True