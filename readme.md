# Living Document for the project "Garo Dictionary NLP"

## Step-1 — Local LLM Setup (Ollama)

**Goal:** Why I chose gemma4b instead of Llama 3b model
### What I did
- Pulled `gemma3:4b`
- Chatted with it directly via `ollama run gemma3:4b`
- Confirmed the local API responds via `curl http://localhost:11434/api/generate`

### Model choice: Gemma 3 4B (over Llama 3.2 3B)
Chose Gemma 3 4B specifically for its instruction-following strength — this matters
more than raw "smartness" for this project, since the chat feature (Phase 9) depends
on the model reliably obeying "only answer from the provided context, say you don't
know otherwise." A model that occasionally ignores that instruction is worse here
than a slightly less capable one that never does.

Ruled out smaller models (0.5B–1B) after testing — too weak at instruction-following
to be trustworthy for grounded RAG answers, even though they're faster/lighter.

### Hardware note
Running on 16GB RAM alongside VS Code + Chrome. Gemma 3 4B (Q4 quantized) uses
roughly 4-5GB while active — workable but not generous margin if Chrome has many
tabs open. Will monitor and switch to `llama3.2:3b` if this becomes a real problem
later, but not needed yet.

### Confirmed
Confirmed model has no real knowledge of Garo (asked directly, got a
plausible-sounding but wrong/hallucinated answer) 

**---------------------------------------------------------------------------**

## Step-2 — OCR Tooling Setup

**Goal:** Get Tesseract + Poppler + pdf2image working, confirmed with a sanity test.

### What I did
- Installed Tesseract OCR (UB Mannheim Windows build)
- Installed Poppler (Windows build)
- Added both to PATH (System/User environment variables)
- Installed `pytesseract`, `pdf2image`, `pillow` via pip
- Generated `requirements.txt` with `pip freeze`

### What I learned
- Tesseract and Poppler are standalone C/C++ programs — need a real installer
  and a PATH entry, same as installing something like Git.
- `pytesseract` and `pdf2image` are thin Python wrapper libraries — they don't
  do OCR/conversion themselves, they just call the real underlying programs.
- Pillow is a pure Python image-handling library, unrelated to Poppler/Tesseract
  as a dependency — it's the common image format the other two hand off through.

### Windows-specific troubleshooting
- Accidentally added Tesseract as a standalone environment variable instead of
  appending it inside the actual `Path` variable — these are not the same thing.
  Fixed by adding the folder as a new entry inside `Path` itself.
- PATH changes require a full VS Code restart (not just a new terminal tab) to
  take effect reliably.

### Confirmed
- [x] `tesseract --version` works from Git Bash
- [x] `pdftoppm -v` works from Git Bash
- [x] `requirements.txt` generated and committed

**---------------------------------------------------------------------------**

## Step-3 — FastAPI Project Skeleton

**Goal:** Get a minimal FastAPI app running and explore the auto-generated swagger docs UI.

### What I did
- Installed fastapi, uvicorn, httpx, sqlalchemy
- Created main.py with a single GET / endpoint
- Ran it with uvicorn main:app --reload
- Confirmed it responds at localhost:8000
- Explored the Swagger docs UI at localhost:8000/docs

### What I learned
- uvicorn is the actual server process; FastAPI is just the framework that
  defines what happens when a request comes in. They're separate pieces.
- /docs is auto-generated from my code, not something I have to write myself.
  This will be my main tool for testing endpoints going forward.

### Confirmed
- [x] localhost:8000 returns {"status": "alive"}
- [x] /docs loads and "Try it out" works
- [x] requirements.txt updated and committed

**---------------------------------------------------------------------------**

## Step-4 — Designing the Entries Schema and Mental Model 

**Goal:** Design the `entries` table schema that the OCR pipeline (Phase 3) will
populate and the review tool (Phase 4) will operate on.

### Schema
id (PK), headword, part_of_speech, definition, direction, source_file,
source_page, needs_review (bool), review_reason, created_at

### Design decisions
- `id` as auto-increment primary key, not `headword` (a word can have multiple
  senses/entries)
- `direction` column supports both source dictionaries (Garo→English from
  "The School", English→Garo from the 1905 dictionary) in one table
- `source_file` + `source_page` kept for traceability back to the original scan
- `review_reason` is a single text field for now — may revisit if an entry
  needs multiple simultaneous flags once real review data shows it's necessary

  **-------------------------------------------------------------------------**
  
## Step-5 — SQLAlchemy Setup

**Goal:** Create the real project database and translate the Day 7 schema
sketch into an actual SQLAlchemy model.

### What I did
- Created database.py (engine, session, Base)
- Created models.py with the Entry model matching my Day 7 schema
- Wired Base.metadata.create_all() into main.py so tables are created on startup
- Verified via sqlite3 CLI: .tables shows `entries`, .schema entries matches
  my intended columns

### What I learned
- `check_same_thread: False` is a SQLite-specific setting needed for FastAPI's
  threading model — not something every database needs
- `index=True` on headword will matter once I build search in Phase 5 —
  speeds up lookups on that column specifically
- ` SELECT name FROM sqlite_master WHERE type='table';`
- ` SELECT sql FROM sqlite_master WHERE type='table' AND name='entries';`
  Check for tables in the sqlite.

**------------------------------------------------------------------------**




