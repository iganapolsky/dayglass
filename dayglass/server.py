"""Dayglass local API and static server.

Runs on 127.0.0.1:3333 with 0 dependencies.
Provides REST API for screen history, local LM Studio chat, and automations.
"""

from __future__ import annotations

import json
import mimetypes
import os
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dayglass.ask import complete
from dayglass.automations import run_automation
from dayglass.capture import grab
from dayglass.store import (
    connect,
    get_stats,
    insert_frame,
    list_automations,
    list_meetings,
    list_recent_frames,
    recent_text,
    search,
)

WEB_DIR = Path(__file__).parent / "web"


class DayglassHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict | list, status: int = HTTPStatus.OK):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int = HTTPStatus.INTERNAL_SERVER_ERROR):
        self._send_json({"error": message}, status=status)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        conn = connect()

        if path == "/api/status":
            try:
                stats = get_stats(conn)
                self._send_json({"status": "ok", **stats})
            except Exception as exc:
                self._send_error(str(exc))
            return

        if path == "/api/frames":
            try:
                limit = int(query.get("limit", ["25"])[0])
                frames = list_recent_frames(conn, limit=limit)
                self._send_json(frames)
            except Exception as exc:
                self._send_error(str(exc))
            return

        if path == "/api/search":
            q = query.get("q", [""])[0]
            if not q:
                self._send_json([])
                return
            try:
                rows = search(conn, q, limit=int(query.get("limit", ["15"])[0]))
                results = [{"id": r["id"], "captured_at": r["captured_at"], "snippet": r["snip"]} for r in rows]
                self._send_json(results)
            except Exception as exc:
                self._send_error(str(exc))
            return

        if path == "/api/meetings":
            try:
                meetings = [dict(m) for m in list_meetings(conn)]
                self._send_json(meetings)
            except Exception as exc:
                self._send_error(str(exc))
            return

        if path == "/api/automations":
            try:
                autos = [dict(a) for a in list_automations(conn)]
                self._send_json(autos)
            except Exception as exc:
                self._send_error(str(exc))
            return

        # Static files
        if path == "/" or path == "/index.html":
            target = WEB_DIR / "index.html"
        else:
            rel = path.lstrip("/")
            target = WEB_DIR / rel

        if target.exists() and target.is_file():
            mime, _ = mimetypes.guess_type(str(target))
            mime = mime or "application/octet-stream"
            content = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except json.JSONDecodeError:
            body = {}

        conn = connect()

        if path == "/api/capture":
            try:
                text, img_path = grab(keep_image=body.get("keep_image", False))
                rowid = insert_frame(conn, text, img_path)
                self._send_json({"id": rowid, "chars": len(text), "status": "captured"})
            except Exception as exc:
                self._send_error(f"Capture error: {exc}")
            return

        if path == "/api/ask":
            question = body.get("question", "").strip()
            if not question:
                self._send_error("question is required", HTTPStatus.BAD_REQUEST)
                return
            try:
                context = recent_text(conn, limit=16)
                prompt = (
                    f"Screen & Activity Notes:\n{context[:24000]}\n\n"
                    f"User Question: {question}\n\n"
                    f"Answer accurately and directly based on what was observed on screen."
                )
                answer = complete(prompt)
                self._send_json({"answer": answer})
            except Exception as exc:
                self._send_error(f"Inference error: {exc}")
            return

        if path.startswith("/api/automate/"):
            auto_name = path.replace("/api/automate/", "").strip()
            try:
                name, result = run_automation(auto_name, conn=conn)
                self._send_json({"automation": name, "result": result})
            except Exception as exc:
                self._send_error(f"Automation '{auto_name}' error: {exc}")
            return

        self._send_error("Endpoint not found", HTTPStatus.NOT_FOUND)

    def log_message(self, format, *args):
        # Keep terminal clean unless debugging
        pass


def serve(port: int = 3333, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), DayglassHandler)
    return server
