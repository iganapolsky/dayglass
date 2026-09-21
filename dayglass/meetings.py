"""Meetings & Audio Intelligence for Dayglass.

Captures microphone or system audio locally and writes transcription
into SQLite (meetings and audio_chunks tables) with FTS5 search.
Zero cloud costs, 100% private.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from dayglass.ask import complete
from dayglass.store import HOME, connect, insert_audio_chunk, insert_meeting

AUDIO_DIR = HOME / "audio"


def _get_ffmpeg() -> str:
    which = shutil.which("ffmpeg")
    if which:
        return which
    local_ff = Path.home() / ".local" / "bin" / "ffmpeg"
    if local_ff.exists():
        return str(local_ff)
    screenpipe_ff = Path("/Applications/screenpipe.app/Contents/MacOS/ffmpeg")
    if screenpipe_ff.exists():
        return str(screenpipe_ff)
    raise RuntimeError("ffmpeg not found in PATH or ~/.local/bin/ffmpeg")


def record_chunk(duration_sec: int = 30, keep_audio: bool = False) -> tuple[str, str | None]:
    """Records an audio chunk from the default microphone and transcribes it."""
    AUDIO_DIR.mkdir(parents=True, mode=0o700, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    wav_path = AUDIO_DIR / f"mic_{stamp}.wav"
    ffmpeg = _get_ffmpeg()

    # Record from default macOS input device (avfoundation ":0")
    cmd = [
        ffmpeg,
        "-y",
        "-f", "avfoundation",
        "-i", ":0",
        "-t", str(duration_sec),
        "-ar", "16000",
        "-ac", "1",
        str(wav_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=duration_sec + 10)
    except subprocess.CalledProcessError as err:
        stderr = (err.stderr or b"").decode(errors="replace")
        # If input 0 fails, could be device permission or missing input
        raise RuntimeError(f"Audio capture failed: {stderr[:200]}") from err

    transcript = transcribe_audio(wav_path)

    saved_path: str | None = str(wav_path)
    if not keep_audio:
        wav_path.unlink(missing_ok=True)
        saved_path = None

    return transcript, saved_path


def transcribe_audio(audio_path: Path) -> str:
    """Transcribes an audio file on-device."""
    # Check if whisper CLI is available
    whisper_bin = shutil.which("whisper")
    if whisper_bin:
        res = subprocess.run(
            [whisper_bin, str(audio_path), "--output_format", "txt", "--model", "tiny.en"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if res.returncode == 0 and res.stdout:
            return res.stdout.strip()

    # Fallback: macOS SFSpeechRecognizer via inline swift script
    swift_script = f"""
    import Foundation
    import Speech

    let url = URL(fileURLWithPath: "{audio_path}")
    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US")) else {{
        exit(1)
    }}
    let request = SFSpeechURLRecognitionRequest(url: url)
    let sema = DispatchSemaphore(value: 0)
    var transcribedText = ""

    recognizer.recognitionTask(with: request) {{ result, error in
        if let result = result {{
            transcribedText = result.bestTranscription.formattedString
            if result.isFinal {{
                sema.signal()
            }}
        }}
        if error != nil {{
            sema.signal()
        }}
    }}
    _ = sema.wait(timeout: .now() + 30.0)
    print(transcribedText)
    """

    res = subprocess.run(
        ["swift", "-e", swift_script],
        capture_output=True,
        text=True,
        timeout=40,
    )
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()

    return ""


def summarize_meeting(title: str, transcript: str) -> tuple[str, str]:
    """Uses local LM Studio to generate meeting summary and action items."""
    if not transcript.strip():
        return "No audio transcribed.", "None"

    prompt = (
        f"Summarize this meeting transcript concisely:\n\n"
        f"--- TRANSCRIPT ---\n{transcript[:16000]}\n------------------\n\n"
        f"Provide:\n"
        f"1. Executive Summary (2-3 sentences)\n"
        f"2. Key Decisions Made\n"
        f"3. Action Items (Owner and task list)"
    )
    response = complete(prompt)
    return response, ""
