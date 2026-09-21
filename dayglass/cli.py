"""Dayglass CLI."""

from __future__ import annotations

import argparse
import sys
import time

from dayglass.ask import complete
from dayglass.capture import grab
from dayglass.store import connect, insert_frame, recent_text, search, today_text


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dayglass", description="Local screen memory and ask")
    sub = parser.add_subparsers(dest="cmd", required=True)

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
    parser.error("unknown command")
    return 2
