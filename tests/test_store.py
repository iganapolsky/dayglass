import os
import tempfile
import unittest
from pathlib import Path

from dayglass.ask import complete
from dayglass.store import connect, get_stats, insert_frame, search


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def test_search_finds_ocr(self):
        conn = connect(self.db_path)
        insert_frame(conn, "StockService health is green", None)
        rows = search(conn, "StockService")
        self.assertTrue(len(rows) > 0)
        self.assertIn("StockService", rows[0]["snip"])

    def test_stats_counts_properly(self):
        conn = connect(self.db_path)
        insert_frame(conn, "frame 1", None)
        insert_frame(conn, "frame 2", None)
        stats = get_stats(conn)
        self.assertEqual(stats["frames_count"], 2)

    def test_ask_refuses_non_localhost(self):
        old = os.environ.get("DAYGLASS_BASE_URL")
        try:
            os.environ["DAYGLASS_BASE_URL"] = "https://api.openai.com/v1"
            with self.assertRaises(RuntimeError) as ctx:
                complete("hello")
            self.assertTrue("localhost" in str(ctx.exception).lower() or "refusing" in str(ctx.exception).lower())
        finally:
            if old is not None:
                os.environ["DAYGLASS_BASE_URL"] = old
            else:
                os.environ.pop("DAYGLASS_BASE_URL", None)


if __name__ == "__main__":
    unittest.main()

