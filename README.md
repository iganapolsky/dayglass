# Dayglass

Local screen memory and autonomous meeting capture. Everything stays on this Mac. Answers come from a local model (LM Studio). No cloud, no subscription, no credit cap.

## Why

Screenpipe's capture is useful but its cloud AI hits a credit cap and copies its UI everywhere. Dayglass is different: autonomous background capture, original timeline-first UI, and $0/mo forever.

This is original code. It is not a Screenpipe fork.

## Features

- **Autonomous Daemon (`dayglass daemon`)** — Runs in background, captures screen + monitors audio continuously. Automatically detects meetings (speech), records them, transcribes, and summarizes when they end. Zero manual intervention.
- **Original Timeline UI (`dayglass desktop`)** — Timeline-first design with command bar. No sidebar clone. All activity (screens, meetings, audio) flows chronologically with inline search and quick actions.
- **Screen Memory (`capture` / `watch`)** — On-device OCR into SQLite FTS5 database (`~/.dayglass/dayglass.sqlite`).
- **Meetings & Audio** — Microphone capture and transcription with automatic meeting detection, local summaries, and action item extraction.
- **Local Automations** — Standup prep, day recap, missed to-dos, blockers, time breakdown, and more. All run locally with zero token caps.
- **100% Free & Local** — Zero cloud limits. Zero monthly subscriptions. Zero corporate transcript leakage.

## Acceptance

- [x] Capture writes OCR into `~/.dayglass/dayglass.sqlite` with no network call
- [x] `ask` posts only to `127.0.0.1` (LM Studio), never to a hosted chat API
- [x] Autonomous daemon with automatic meeting detection
- [x] Original timeline-first desktop UI (not a Screenpipe copy)
- [x] Mic / meeting audio & transcription
- [x] Local deterministic automations
- [x] Menu-bar companion (`~/.local/bin/dayglass-menubar`)

## Run

```bash
# 1. Start autonomous daemon (screen + audio + meeting detection)
python3 -m dayglass daemon
python3 -m dayglass daemon --screen-interval 30 --audio-chunk 15

# 2. Launch the Desktop Client (timeline-first UI)
python3 -m dayglass desktop

# 3. CLI Screen Capture & Search
python3 -m dayglass capture
python3 -m dayglass watch --interval 45
python3 -m dayglass search "stock"

# 4. Ask Local LM Studio
python3 -m dayglass ask "what was I looking at this morning?"

# 5. Run Local Automations
python3 -m dayglass automate standup-prep
python3 -m dayglass automate day-recap
python3 -m dayglass automate missed-todos
python3 -m dayglass automate blockers

# 6. Manual Meeting Record (daemon does this automatically)
python3 -m dayglass meeting "PSN StockService Sync" --duration 60

# 7. Check Database & Local Status
python3 -m dayglass stats
```

## Daemon Mode

The daemon runs two background threads:

1. **Screen capture** — Takes screenshots every N seconds, OCRs them, stores in SQLite
2. **Audio monitoring** — Records 15-second audio chunks, transcribes, detects speech
3. **Meeting detection** — When speech is detected in consecutive chunks, it's a meeting. When silence persists, the meeting ends and is auto-summarized.

```bash
# Start daemon with custom intervals
python3 -m dayglass daemon --screen-interval 30 --audio-chunk 15

# The daemon will:
# - Capture screen every 30 seconds
# - Monitor audio in 15-second chunks
# - Auto-detect meetings (speech in consecutive chunks)
# - Auto-summarize meetings when they end
# - Store everything in ~/.dayglass/dayglass.sqlite
```

## UI Design

Dayglass uses an original timeline-first design:

- **Command bar** — Ask questions, search, or run commands from one input
- **Stats dashboard** — Frames, meetings, audio chunks, database size at a glance
- **Activity timeline** — All captured activity (screens, meetings, audio) in chronological order
- **Quick actions** — One-click automations (standup prep, day recap, missed to-dos, etc.)
- **No sidebar** — Everything flows in the timeline, filterable by type

This is not a Screenpipe UI clone. The design prioritizes chronological flow and command-driven interaction over sidebar navigation.

## Requirements

- `tesseract` for OCR (`brew install tesseract`)
- `ffmpeg` for audio capture (`brew install ffmpeg`)
- LM Studio on `http://127.0.0.1:1234/v1` (falls back to `:1235`)
- Default model: `qwen3.8-27b-mlx@4bit` (fallback: `qwen3-4b-instruct-2507-mlx`)

## Privacy

Screen text, audio transcripts, and meeting summaries stay in `~/.dayglass/` and are gitignored. Never committed or sent to cloud. All inference runs on localhost.

## Cost

$0.00 / month forever. All inference runs locally on your hardware.
