# Dayglass

Local screen memory and ask. Capture stays on this Mac. Answers come from a local model (LM Studio). There is no weekly cloud AI meter.

## Why

Screenpipe’s capture is useful and its cloud ask hits a credit cap. Dayglass is our own product: screenshot + OCR into a local database, then ask that history through whatever model is already running on localhost.

This is original code. It is not a Screenpipe fork.

## Features

- **Dayglass.app** — Mac app (Dock and menu bar say Dayglass). Chat, Meetings, Timeline, and Automations.
- **Menu Bar App (`dayglass-menubar`)** — Native macOS AppKit `NSStatusItem` in your top menu bar with hotkeys (`⌘⇧C` to capture, `⌘⇧D` to open desktop).
- **Screen Memory (`capture` / `watch`)** — On-device OCR into SQLite FTS5 database (`~/.dayglass/dayglass.sqlite`).
- **Meetings & Audio (`meeting`)** — Microphone capture and transcription into SQLite with on-demand local summaries.
- **Local Automations (`automate`)** — Safe, deterministic local models replacing Screenpipe's credit-burning pipes (`standup-prep`, `day-recap`, `missed-todos`, `blockers`, `time-breakdown`, `automate-my-work`).
- **100% Free & Local** — Zero cloud limits. Zero monthly subscriptions ($0.00/mo). Zero corporate transcript leakage.

## Acceptance

- [x] Capture writes OCR into `~/.dayglass/dayglass.sqlite` with no network call
- [x] `ask` posts only to `127.0.0.1` (LM Studio), never to a hosted chat API
- [x] Mac app at `/Applications/Dayglass.app` (menu bar name is Dayglass)
- [x] Menu-bar companion (`~/.local/bin/dayglass-menubar`)
- [x] Mic / meeting audio & transcription (`python3 -m dayglass meeting`)
- [x] Local deterministic automations (`python3 -m dayglass automate`)

## Run

```bash
# 1. Launch the Mac app
open -a Dayglass

# 2. Start the native macOS Menu Bar Companion
dayglass-menubar &

# 3. CLI Screen Capture & Search
python3 -m dayglass capture
python3 -m dayglass watch --interval 45
python3 -m dayglass search "stock"

# 4. Ask Local LM Studio
python3 -m dayglass ask "what was I looking at this morning?"

# 5. Run Local Automations (Zero token caps)
python3 -m dayglass automate standup-prep
python3 -m dayglass automate day-recap
python3 -m dayglass automate missed-todos
python3 -m dayglass automate blockers

# 6. Record & Summarize a Meeting
python3 -m dayglass meeting "PSN StockService Sync" --duration 60

# 7. Check Database & Local Status
python3 -m dayglass stats
```

Needs `tesseract` and LM Studio on `http://127.0.0.1:1234/v1` (falls back to `:1235`). Default model: `qwen3.8-27b-mlx@4bit` (fallback: `qwen3-4b-instruct-2507-mlx`).

Screen text and transcripts stay in `~/.dayglass/` and are gitignored. Never committed or sent to cloud.

