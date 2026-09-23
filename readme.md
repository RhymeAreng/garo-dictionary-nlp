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

## Step 6 — Path & Query Parameters

**Goal:** Understand the difference between path parameters and query
parameters, and get comfortable testing endpoints in /docs.

### What I did
- Built a throwaway /entries/{entry_id} endpoint (path parameter)
- Built a throwaway /search-placeholder endpoint (query parameters with
  defaults)
- Tested both in the browser directly and via /docs "Try it out"
- Confirmed FastAPI auto-validates types (e.g. rejects non-integer entry_id)

### What I learned
- Path parameters identify a specific resource ("which one")
- Query parameters filter/modify a request ("how do you want it") and are
  optional with sensible defaults
- Type hints in function signatures aren't just documentation — FastAPI
  actually validates against them automatically

### Confirmed
- [x] /entries/5 works, /entries/hello correctly rejected
- [x] /search-placeholder works with and without query params
- [x] Comfortable using /docs "Try it out" for testing

**-----------------------------------------------------------------**

## Step-7 — Pydantic Models for Validation

**Goal:** Understand why request/response schemas are separate from database
models, and see FastAPI's automatic validation in action.

### What I did
- Created schemas.py with EntryCreate (input) and EntryOut (output) models
- Tested validation via a temporary placeholder endpoint in /docs
- Confirmed missing fields and wrong types are auto-rejected with clear
  422 errors, no manual validation code needed

### What I learned
- Database models (models.py) and API schemas (schemas.py) serve different
  purposes: EntryCreate shouldn't accept id/needs_review, but EntryOut should
  return them
- from_attributes = True is required to convert a SQLAlchemy object into a
  Pydantic response model directly

### Confirmed
- [x] Missing required field correctly triggers a 422 error
- [x] Wrong data type correctly triggers a 422 error
- [x] schemas.py committed


**-----------------------------------------------------------------------**
## Step 8 — CRUD: Create & Read

**Goal:** Wire schemas.py and models.py together into real, working database
endpoints.

### What I did
- Added get_db() dependency in database.py for per-request database sessions
- Built POST /entries (create) using EntryCreate for validation and EntryOut
  for the response
- Built GET /entries/{entry_id} (read), returning 404 for a missing entry
- Replaced the Day 10 placeholder endpoint with the real one

### What I learned
- FastAPI's Depends() pattern hands a database session to my endpoint
  automatically rather than me creating one manually each time
- db.commit() + db.refresh() is the pattern for getting database-assigned
  values (id, created_at) back after an insert
- response_model shapes the output using my Pydantic schema, which relies on
  from_attributes = True from Step 7

### Confirmed
- [x] POST /entries creates a real row with auto-generated id and created_at
- [x] GET /entries/{id} returns the correct entry
- [x] GET /entries/999 (nonexistent) returns a clean 404, not a crash


**----------------------------------------------------------------**
## Step 9 — Continuous Integration with GitHub Actions and ran starting Test files

**Goal:** Get pytest running automatically on every push/PR, and tested the
branch → PR → merge workflow.

### What I did
- Created .github/workflows/tests.yml (checkout, setup Python 3.11, install
  requirements, run pytest)
- Practiced full branch workflow: feature/day14-ci branch, pushed, opened PR,
  reviewed diff, merged, deleted branch
- Confirmed CI runs automatically both on the PR and after merging to main

### What I learned
- CI runs in a clean environment with no pre-existing garo_dictionary.db
  (since it's gitignored) — meaning CI test runs sidestep the "tests pollute
  my real database" issue, at least for CI specifically

### Confirmed
- [x] .github/workflows/tests.yml created and pushed
- [x] CI check appeared and passed on the PR
- [x] CI also triggered after merging to main
- [x] Completed first full branch → PR → merge cycle

**-------------------------------------------------------------------**


## Step 10 — Pagination & Filtering

**Goal:** Build a listing endpoint that scales to thousands of entries,
combining optional filtering with pagination.

### What I did
- Built GET /entries with optional `direction` filter, plus `limit`/`offset`
  pagination
- Confirmed offset+limit correctly pages through non-overlapping results
- Confirmed an offset beyond the data returns an empty list, not an error
- Wrote tests for limit, direction filtering, and the past-the-end edge case

### What I learned
- Pagination (how many/which chunk) and filtering (which subset matches a
  condition) are separate concerns that combine naturally in one endpoint
- Query building is incremental: start unfiltered, conditionally narrow with
  .filter(), then apply .offset().limit() last

### Confirmed
- [x] limit correctly caps result count
- [x] offset correctly skips ahead without duplicating results
- [x] direction filter returns only matching entries
- [x] out-of-range offset returns [] rather than erroring

**----------------------------------------------------------------------**

## Step 11 — Rasterizing PDF Pages to Images

**Goal:** Convert a single PDF page into an image, as the first step of the
OCR pipeline. Started the Phase 3 feature branch.

### What I did
- Created feature/phase3-ocr-pipeline branch
- Wrote rasterize_page() using pdf2image, at 300 DPI
- Confirmed output image renders correctly and is sharp enough to read

### What I learned
- OCR tools operate on images, not PDFs directly — Poppler (via pdf2image)
  handles the PDF-to-image conversion step
- Restricting to first_page/last_page keeps the dev loop fast while testing,
  rather than converting the entire 200+ page document each run
- Higher DPI improves OCR accuracy, especially relevant later for apostrophe
  stress-mark detection

### Confirmed
- [x] rasterize_page() produces a correct, readable image from a real PDF page

**------------------------------------------------------------------------**

## Step 12 — First OCR Pass (Naive)

**Goal:** Run unmodified Tesseract OCR on a real page and observe the
two-column interleaving problem firsthand before fixing it.

### What I did
- Added ocr_raw() — a bare pytesseract.image_to_string() call, no cleanup
- Ran it against page 20 of "The School"
- Saved the output to ocr_output_naive.txt for later before/after comparison

### What I observed
- Text from the left and right columns interleaves line-by-line, breaking
  sentences apart mid-thought — confirms the known limitation rather than
  indicating something broken in my setup

### Important discovery: a second diacritic-mangling pattern
Noticed OCR converts a middle-dot character (·, used in "The School" for
syllable/stress marking — e.g. "A·we") into a plain hyphen ("A-we"). This is
distinct from the apostrophe-mangling issue in the 1905 dictionary, and more
dangerous: a hyphen looks like ordinary, high-confidence text, unlike a
visibly garbled apostrophe substitution. Day 23's flagging logic will need a
second check specifically for this pattern (short prefix + hyphen), not just
the apostrophe check originally planned.

### Confirmed
- [x] Naive OCR runs successfully and produces text (however garbled)
- [x] Two-column interleaving problem is visibly reproduced and saved for
      comparison


**----------------------------------------------------------------**
## Step 13 — Column-Split OCR

**Goal:** Guarantee correct left-to-right, top-to-bottom reading order on
two-column pages, rather than relying on Tesseract's automatic (and
inconsistent) layout detection.

### What I did
- Added split_columns() to crop a page into left/right halves
- Added ocr_page_by_columns() to OCR each half separately and concatenate
- Compared against Day 20's naive output on both source PDFs

### What I learned
- Tesseract's automatic column detection isn't reliable across different
  scan qualities — explicit splitting removes the guesswork
- This approach roughly doubles OCR processing time per page (two OCR calls
  instead of one) — an acceptable tradeoff for correctness at this scale

### Confirmed
- [x] Column-split OCR produces correctly-ordered text
- [x] Compared naive vs. column-split output on the harder (1905) source


**------------------------------------------------------------------------**
## Step 14 — Word-Level Confidence Scores

**Goal:** Get per-word OCR confidence scores, laying the groundwork for
flagging unreliable words in Day 23.

### What I did
- Added ocr_with_confidence() using pytesseract.image_to_data()
- Printed and sorted results by confidence to find the worst-recognized words
- Specifically checked whether the Day 20 hyphen-misread ("A-we") shows high
  or low confidence

### What I found
- [fill in: did "A-we" show high confidence despite being wrong?]
- 1905 dictionary source shows [more/fewer — fill in] low-confidence words
  than "The School", consistent with its worse scan quality

### Confirmed
- [x] ocr_with_confidence() returns per-word confidence scores correctly
- [x] Identified confidence range that seems to separate trustworthy vs.
      questionable words on real pages

**-------------------------------------------------------------------**
## Step 15 — Diacritic-Aware Flagging

**Goal:** Build flagging logic covering both known diacritic-mangling
failure modes — apostrophes (1905 source) and the newly-discovered
middle-dot-to-hyphen misread ("The School" source) — plus low confidence.

### What I did
- Built has_apostrophe(), has_suspicious_hyphen(), and a combined
  flag_word_for_review() that reports every triggered reason
- Confirmed "A-we" is correctly caught by the hyphen pattern despite its
  high OCR confidence
- Wrote tests covering both diacritic checks and the combined flagging logic
- Checked for false positives from the hyphen pattern

### What I learned
- Two structurally different error types need two independent checks —
  neither confidence nor a single pattern check alone covers both
- Never assume one source's diacritic problem (apostrophes) is the only
  one — the hyphen misread was only found by actually looking closely at
  real output, not by following the original plan alone

### Confirmed
- [x] "A-we" correctly flagged with reason "suspicious_hyphen_pattern"
- [x] Apostrophe detection works for both straight and curly variants
- [x] All new tests pass


**-----------------------------------------------------------**
## Step 16 — Structured Entry Parsing

**Goal:** Convert OCR text into structured entries using a regex validated
against real transcribed pages, and scope diacritic flagging to headwords only.

### What I did
- Built ENTRY_START regex, tested and fixed against 5 real page images
  (bug found and fixed: commas must be allowed inside the headword group
  to correctly capture multi-variant headwords like "A·ni, A·ani, adj.")
- Added has_embedded_sense_marker() for multi-sense entries (e.g. "Giila,
  adj. ...—n. ...—v. ...")
- Scoped has_apostrophe/has_suspicious_hyphen checks to headword only,
  eliminating false flags from ordinary English possessives in definitions
- Confirmed pronunciation-guide hyphens (e.g. "(a-ba-ku)") don't false-flag

### Known limitation (accepted, not fixed)
Entries with no POS tag at all (e.g. "-a, Ending of a verb in the
infinitive.") are not detected — they get absorbed into the preceding
entry's definition. This category is narrow enough that catching it during
Phase 4 manual review is more reliable than the regex complexity needed to
detect it without false-matching ordinary text.

### Confirmed
- [x] Multi-variant headwords correctly grouped as single entries
- [x] Combined POS tags ("v. & adj.") captured correctly
- [x] Multi-sense entries flagged without being incorrectly split
- [x] All tests pass