from __future__ import annotations

import importlib
import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

import helix_core.auth as auth_module


class _DummySidebar:
    def __init__(self) -> None:
        self.last_error = ""

    def markdown(self, *_args, **_kwargs) -> None:
        pass

    def error(self, message: str) -> None:
        self.last_error = message

    def text_input(self, *_args, **_kwargs) -> str:
        return ""

    def button(self, *_args, **_kwargs) -> bool:
        return False

    def success(self, *_args, **_kwargs) -> None:
        pass


class _DummyStreamlit:
    def __init__(self) -> None:
        self.sidebar = _DummySidebar()
        self.session_state = {}

    def rerun(self) -> None:
        raise AssertionError("rerun should not be called in this test")


class AuthTests(unittest.TestCase):
    def test_env_file_is_loaded_on_import(self) -> None:
        tmp = Path("tests/.tmp_auth")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        Path(tmp, ".env").write_text("HELIX_USER=admin\nHELIX_PASS=helix\n", encoding="utf-8")
        cwd = os.getcwd()
        try:
            os.chdir(tmp)
            with mock.patch.dict(os.environ, {}, clear=True):
                reloaded = importlib.reload(auth_module)
                self.assertEqual(reloaded.DEFAULT_USER, "admin")
                self.assertEqual(reloaded.DEFAULT_PASS, "helix")
        finally:
            os.chdir(cwd)
            importlib.reload(auth_module)
            shutil.rmtree(tmp)

    def test_login_fails_closed_when_credentials_missing(self) -> None:
        dummy = _DummyStreamlit()
        with mock.patch.object(auth_module, "st", dummy):
            with mock.patch.object(auth_module, "DEFAULT_USER", ""):
                with mock.patch.object(auth_module, "DEFAULT_PASS", ""):
                    ok, user = auth_module.login()
        self.assertFalse(ok)
        self.assertEqual(user, "")
        self.assertIn("Authentication is not configured", dummy.sidebar.last_error)


if __name__ == "__main__":
    unittest.main()
