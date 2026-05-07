from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from helix_core.db import list_sessions, load_session, save_session


class SessionStoreTests(unittest.TestCase):
    def test_save_and_load_session_roundtrip(self) -> None:
        tmp = Path("tests/.tmp_db")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        db_path = tmp / "helix.db"
        try:
            session_id = save_session(
                {"sequence": "ACGT", "win": [0, 4]},
                username="admin",
                session_name="demo",
                mode="sandbox",
                path=db_path,
            )

            sessions = list_sessions(username="admin", mode="sandbox", path=db_path)
            loaded = load_session(session_id, path=db_path)

            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["session_name"], "demo")
            self.assertEqual(loaded["payload"]["sequence"], "ACGT")
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
