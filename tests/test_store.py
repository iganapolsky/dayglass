from pathlib import Path

from dayglass.ask import complete
from dayglass.store import connect, insert_frame, search


def test_search_finds_ocr(tmp_path: Path) -> None:
    conn = connect(tmp_path / "dayglass.sqlite")
    insert_frame(conn, "StockService health is green", None)
    rows = search(conn, "StockService")
    assert rows
    assert "StockService" in rows[0]["snip"]


def test_ask_refuses_non_localhost(monkeypatch) -> None:
    monkeypatch.setenv("DAYGLASS_BASE_URL", "https://api.openai.com/v1")
    try:
        complete("hello")
    except RuntimeError as exc:
        assert "localhost" in str(exc).lower() or "refusing" in str(exc).lower()
    else:
        raise AssertionError("non-localhost base was accepted")
