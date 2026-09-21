"""Dayglass CLI."""

from __future__ import annotations

import argparse
import sys
import time

import os
import subprocess

from dayglass.ask import complete
from dayglass.automations import PROMPTS, run_automation
from dayglass.capture import grab
from dayglass.meetings import record_chunk, summarize_meeting
from dayglass.server import serve
from dayglass.store import (
    connect,
    get_stats,
    insert_frame,
    insert_meeting,
    list_meetings,
    recent_text,
    search,
    today_text,
)


def _capture_once(keep_image: bool) -> int:
    text, path = grab(keep_image=keep_image)
    conn = connect()
    rowid = insert_frame(conn, text, path)
    chars = len(text)
    print(f"stored frame {rowid} ({chars} chars)")
    return 0 if chars else 2


def _ask(question: str) -> int:
    conn = connect()
    context = recent_text(conn)
    if not context.strip():
        print("No screen notes yet. Run: python3 -m dayglass capture")
        return 2
    prompt = f"Screen notes:\n{context[:24000]}\n\nQuestion: {question}"
    print(complete(prompt))
    return 0


def _recap() -> int:
    conn = connect()
    context = today_text(conn)
    if not context.strip():
        print("Nothing captured today.")
        return 2
    prompt = (
        "Write a short day recap from these screen notes: what got done, "
        "what was on screen, what looks unfinished. Plain sentences.\n\n"
        + context[:24000]
    )
    print(complete(prompt))
    return 0


def _run_automate(name: str) -> int:
    conn = connect()
    try:
        _, result = run_automation(name, conn=conn)
        print(f"=== AUTOMATION: {name} ===\n")
        print(result)
        return 0
    except Exception as exc:
        print(f"Automation failed: {exc}", file=sys.stderr)
        return 2


def _record_meeting(title: str, duration: int) -> int:
    print(f"Recording meeting '{title}' for {duration} seconds...")
    try:
        transcript, _ = record_chunk(duration_sec=duration)
        if not transcript.strip():
            print("No speech detected in audio.")
            return 2
        print(f"Transcript captured ({len(transcript)} chars). Summarizing with local LM Studio...")
        summary, action_items = summarize_meeting(title, transcript)
        conn = connect()
        rowid = insert_meeting(conn, title, transcript, summary, action_items)
        print(f"Meeting stored (id: {rowid}).")
        print(f"\n--- Summary ---\n{summary}")
        return 0
    except Exception as exc:
        print(f"Meeting capture error: {exc}", file=sys.stderr)
        return 2


def _show_stats() -> int:
    conn = connect()
    stats = get_stats(conn)
    print("=== Dayglass Local Status ===")
    print(f"Frames stored:      {stats['frames_count']}")
    print(f"Audio chunks:       {stats['audio_chunks_count']}")
    print(f"Meetings recorded:  {stats['meetings_count']}")
    print(f"Automations run:    {stats['automations_count']}")
    print(f"Latest capture:     {stats['latest_capture']}")
    print(f"Database size:      {stats['db_size_mb']} MB")
    print("Cost to date:       $0.00 / month (100% on-device)")
    return 0


NATIVE_APP = "/Applications/Dayglass.app"


def _start_desktop(port: int = 3333, daemon: bool = False) -> int:
    if not os.path.isdir(NATIVE_APP):
        print("Dayglass.app is not installed.", file=sys.stderr)
        return 1
    subprocess.Popen(["open", "-a", NATIVE_APP])
    print("Opened Dayglass")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dayglass", description="Local screen memory, desktop UI, and ask")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Core CLI
    cap = sub.add_parser("capture", help="Screenshot + OCR once")
    cap.add_argument("--keep-image", action="store_true")

    watch = sub.add_parser("watch", help="Keep capturing")
    watch.add_argument("--interval", type=int, default=45)
    watch.add_argument("--keep-image", action="store_true")

    find = sub.add_parser("search", help="Search OCR text")
    find.add_argument("query")
    find.add_argument("--limit", type=int, default=8)

    ask = sub.add_parser("ask", help="Ask recent screen notes via local LM Studio")
    ask.add_argument("question")

    sub.add_parser("recap", help="Summarize today's screen notes locally")
    sub.add_parser("stats", help="Display local database and capture statistics")

    # Automations
    auto = sub.add_parser("automate", help="Run a named local automation")
    auto.add_argument("name", choices=list(PROMPTS.keys()), help="Automation name")

    # Meetings
    meet = sub.add_parser("meeting", help="Record and summarize a meeting")
    meet.add_argument("title", help="Meeting title or subject")
    meet.add_argument("--duration", type=int, default=30, help="Duration in seconds (default: 30)")

    # Desktop & Server
    desk = sub.add_parser("desktop", help="Launch Dayglass Desktop client window")
    desk.add_argument("--port", type=int, default=3333)

    ui = sub.add_parser("ui", help="Alias for desktop")
    ui.add_argument("--port", type=int, default=3333)

    srv = sub.add_parser("serve", help="Start Dayglass API server")
    srv.add_argument("--port", type=int, default=3333)

    args = parser.parse_args(argv)

    if args.cmd == "capture":
        return _capture_once(args.keep_image)
    if args.cmd == "watch":
        while True:
            try:
                _capture_once(args.keep_image)
            except Exception as exc:  # noqa: BLE001 — keep the loop alive
                print(f"capture failed: {exc}", file=sys.stderr)
            time.sleep(max(10, args.interval))
    if args.cmd == "search":
        conn = connect()
        rows = search(conn, args.query, args.limit)
        if not rows:
            print("No matches.")
            return 2
        for row in rows:
            print(f"{row['captured_at']}  {row['snip']}")
        return 0
    if args.cmd == "ask":
        return _ask(args.question)
    if args.cmd == "recap":
        return _recap()
    if args.cmd == "stats":
        return _show_stats()
    if args.cmd == "automate":
        return _run_automate(args.name)
    if args.cmd == "meeting":
        return _record_meeting(args.title, args.duration)
    if args.cmd in ("desktop", "ui"):
        return _start_desktop(args.port)
    if args.cmd == "serve":
        s = serve(port=args.port)
        print(f"Dayglass server running at http://127.0.0.1:{args.port}")
        s.serve_forever()
        return 0

    parser.error("unknown command")
    return 2

