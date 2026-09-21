# Dayglass

Local screen memory and ask. Capture stays on this Mac. Answers come from a local model (LM Studio). There is no weekly cloud AI meter.

## Why

Screenpipe’s capture is useful and its cloud ask hits a credit cap. Dayglass is our own product: screenshot + OCR into a local database, then ask that history through whatever model is already running on localhost.

This is original code. It is not a Screenpipe fork.

## What v0 does

- `capture` — one screenshot, OCR, store
- `watch` — keep capturing
- `search` — full-text over what was on screen
- `ask` — answer from recent screen text via LM Studio
- `recap` — today’s screen text, summarized locally

## Acceptance

- [x] Capture writes OCR into `~/.dayglass/dayglass.sqlite` with no network call
- [x] `ask` posts only to `127.0.0.1` (LM Studio), never to a hosted chat API
- [ ] Menu-bar app (later)
- [ ] Mic / meeting audio (later)

## Run

```bash
python3 -m dayglass capture
python3 -m dayglass watch --interval 45
python3 -m dayglass search "stock"
python3 -m dayglass ask "what was I looking at this morning?"
python3 -m dayglass recap
```

Needs `tesseract` and LM Studio on `http://127.0.0.1:1235/v1` (falls back to `:1234`). Default model: `qwen3.8-27b-mlx@4bit`.

Screen text can include work content. The database stays in `~/.dayglass/` and is gitignored. Do not commit it.
