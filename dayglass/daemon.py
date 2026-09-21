"""Autonomous capture daemon for Dayglass.

Runs continuous screen capture + audio monitoring in background.
Automatically detects meetings (speech) and records them.
Zero manual intervention required.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from dayglass.ask import complete
from dayglass.capture import grab
from dayglass.meetings import AUDIO_DIR, record_chunk, transcribe_audio
from dayglass.store import (
    connect,
    insert_audio_chunk,
    insert_frame,
    insert_meeting,
)


class MeetingDetector:
    """Detects meetings by monitoring audio for speech patterns."""

    def __init__(self, chunk_duration: int = 15, silence_threshold: int = 2):
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold
        self.silent_chunks = 0
        self.in_meeting = False
        self.meeting_audio: list[tuple[str, float]] = []
        self.meeting_start: datetime | None = None

    def process_chunk(self, transcript: str, duration: float) -> dict | None:
        """Process an audio chunk and return meeting event if detected."""
        has_speech = len(transcript.strip()) > 20

        if has_speech:
            self.silent_chunks = 0
            if not self.in_meeting:
                self.in_meeting = True
                self.meeting_start = datetime.now(timezone.utc)
                self.meeting_audio = []
            self.meeting_audio.append((transcript, duration))
        else:
            if self.in_meeting:
                self.silent_chunks += 1
                if self.silent_chunks >= self.silence_threshold:
                    meeting_data = self._end_meeting()
                    return meeting_data

        return None

    def _end_meeting(self) -> dict:
        """End current meeting and return aggregated data."""
        full_transcript = "\n\n".join(t for t, _ in self.meeting_audio)
        total_duration = sum(d for _, d in self.meeting_audio)
        start = self.meeting_start
        end = datetime.now(timezone.utc)

        self.in_meeting = False
        self.meeting_audio = []
        self.meeting_start = None
        self.silent_chunks = 0

        return {
            "transcript": full_transcript,
            "duration": total_duration,
            "started_at": start.strftime("%Y-%m-%dT%H:%M:%SZ") if start else None,
            "ended_at": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def _summarize_meeting_auto(transcript: str) -> tuple[str, str]:
    """Auto-generate meeting title, summary, and action items."""
    if not transcript.strip():
        return "Untitled Meeting", "No audio transcribed.", "None"

    prompt = (
        f"Analyze this meeting transcript and provide:\n"
        f"1. TITLE: A concise 3-5 word title\n"
        f"2. SUMMARY: 2-3 sentence executive summary\n"
        f"3. ACTION_ITEMS: Bulleted list of action items with owners if mentioned\n\n"
        f"Format exactly as:\n"
        f"TITLE: [title]\n"
        f"SUMMARY: [summary]\n"
        f"ACTION_ITEMS:\n"
        f"- [item]\n"
        f"- [item]\n\n"
        f"--- TRANSCRIPT ---\n{transcript[:16000]}\n------------------"
    )

    try:
        response = complete(prompt)
        lines = response.strip().split("\n")
        title = "Untitled Meeting"
        summary = response
        action_items = ""

        for i, line in enumerate(lines):
            if line.startswith("TITLE:"):
                title = line[6:].strip()
            elif line.startswith("SUMMARY:"):
                summary = line[8:].strip()
            elif line.startswith("ACTION_ITEMS:"):
                action_items = "\n".join(lines[i+1:]).strip()

        return title, summary, action_items
    except Exception:
        return "Untitled Meeting", transcript[:500], ""


def _screen_capture_loop(interval: int, stop_event: threading.Event) -> None:
    """Continuous screen capture loop."""
    conn = connect()
    while not stop_event.is_set():
        try:
            text, path = grab(keep_image=False)
            if text.strip():
                insert_frame(conn, text, path)
        except Exception as exc:
            print(f"[daemon] screen capture error: {exc}", flush=True)

        stop_event.wait(interval)


def _audio_monitor_loop(detector: MeetingDetector, stop_event: threading.Event) -> None:
    """Continuous audio monitoring and meeting detection."""
    conn = connect()
    AUDIO_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)

    while not stop_event.is_set():
        try:
            transcript, audio_path = record_chunk(
                duration_sec=detector.chunk_duration,
                keep_audio=False
            )

            if transcript.strip():
                insert_audio_chunk(
                    conn,
                    duration_sec=detector.chunk_duration,
                    source="microphone",
                    transcript=transcript,
                    audio_path=None,
                )

            event = detector.process_chunk(transcript, detector.chunk_duration)
            if event:
                print(f"[daemon] Meeting detected: {event['duration']}s", flush=True)
                title, summary, action_items = _summarize_meeting_auto(event["transcript"])
                insert_meeting(
                    conn,
                    title=title,
                    transcript=event["transcript"],
                    summary=summary,
                    action_items=action_items,
                    started_at=event["started_at"],
                    ended_at=event["ended_at"],
                )
                print(f"[daemon] Meeting saved: {title}", flush=True)

        except Exception as exc:
            print(f"[daemon] audio monitor error: {exc}", flush=True)

        stop_event.wait(1)


def run_daemon(screen_interval: int = 45, audio_chunk: int = 15) -> None:
    """Run autonomous capture daemon (screen + audio + meeting detection)."""
    print("[daemon] Starting Dayglass autonomous capture...", flush=True)
    print(f"[daemon] Screen capture: every {screen_interval}s", flush=True)
    print(f"[daemon] Audio monitoring: {audio_chunk}s chunks", flush=True)
    print("[daemon] Press Ctrl+C to stop.", flush=True)

    stop_event = threading.Event()
    detector = MeetingDetector(chunk_duration=audio_chunk, silence_threshold=2)

    screen_thread = threading.Thread(
        target=_screen_capture_loop,
        args=(screen_interval, stop_event),
        daemon=True,
    )
    audio_thread = threading.Thread(
        target=_audio_monitor_loop,
        args=(detector, stop_event),
        daemon=True,
    )

    screen_thread.start()
    audio_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[daemon] Stopping...", flush=True)
        stop_event.set()
        screen_thread.join(timeout=5)
        audio_thread.join(timeout=5)
        print("[daemon] Stopped.", flush=True)
