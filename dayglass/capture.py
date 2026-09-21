"""One screenshot + local OCR. No upload."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dayglass.store import HOME

FRAMES = HOME / "frames"


def grab(keep_image: bool = False) -> tuple[str, str | None]:
    FRAMES.mkdir(parents=True, mode=0o700, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    image = FRAMES / f"{stamp}.png"
    subprocess.run(
        ["screencapture", "-x", str(image)],
        check=True,
        timeout=30,
    )
    proc = subprocess.run(
        ["tesseract", str(image), "stdout", "--psm", "6"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    text = (proc.stdout or "").strip()
    if proc.returncode != 0 and not text:
        err = (proc.stderr or "tesseract failed").strip()
        raise RuntimeError(err)
    path: str | None = str(image)
    if not keep_image:
        image.unlink(missing_ok=True)
        path = None
    return text, path
