from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from database import Base

class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    headword: Mapped[str] = mapped_column(String, index=True)
    part_of_speech: Mapped[str] = mapped_column(String)
    definition: Mapped[str] = mapped_column(String)
    direction: Mapped[str] = mapped_column(String)
    source_file: Mapped[str] = mapped_column(String)
    source_page: Mapped[int] = mapped_column(Integer)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=True)
    review_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))