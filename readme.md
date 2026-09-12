# Living Document for the project "Garo Dictionary NLP"

## Day 2 — Local LLM Setup (Ollama)

**Goal:** Why I chose gemma4b instead of Llama 3b model.

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



## Day 3 — OCR Tooling Setup

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


