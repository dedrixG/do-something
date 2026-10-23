import os
import sys
import unittest
import unittest.mock
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from do_something import (
    SeedWorld,
    config_dir,
    load_saved_seed,
    peel_windows_scr,
    save_seed,
)  # noqa: E402


class SeedWorldTests(unittest.TestCase):
    def test_same_phrase_is_stable(self):
        a = SeedWorld("System Check")
        b = SeedWorld("System Check")
        self.assertEqual(a.hex, b.hex)
        self.assertEqual(a.shape, b.shape)
        self.assertEqual(a.ip_a, b.ip_a)
        self.assertEqual(a.pal.fg.name(), b.pal.fg.name())

    def test_different_phrases_diverge(self):
        a = SeedWorld("System Check")
        b = SeedWorld("Bed time")
        self.assertNotEqual(a.hex, b.hex)
        self.assertTrue(
            a.pal.fg.name() != b.pal.fg.name()
            or a.pal.accent.name() != b.pal.accent.name()
        )
        self.assertTrue(a.ip_a != b.ip_a or a.ip_b != b.ip_b)
        self.assertIn("system-check", a.hosts[0])
        self.assertIn("bed-time", b.hosts[0])

    def test_empty_falls_back(self):
        w = SeedWorld("   ")
        self.assertEqual(w.phrase, "do something")
        self.assertTrue(w.hex)


class WindowsScrArgsTests(unittest.TestCase):
    def test_fullscreen(self):
        mode, rest = peel_windows_scr(["/s"])
        self.assertEqual(mode, "fullscreen")
        self.assertEqual(rest, [])

    def test_config(self):
        mode, rest = peel_windows_scr(["/c"])
        self.assertEqual(mode, "config")

    def test_preview_eats_hwnd(self):
        mode, rest = peel_windows_scr(["/p", "12345", "--seed", "x"])
        self.assertEqual(mode, "preview")
        self.assertEqual(rest, ["--seed", "x"])


if __name__ == "__main__":
    unittest.main()


class SeedPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_env = {}
        self.orig_xdg = os.environ.get("XDG_CONFIG_HOME")

    def tearDown(self):
        if self.orig_xdg is not None:
            os.environ["XDG_CONFIG_HOME"] = self.orig_xdg
        else:
            os.environ.pop("XDG_CONFIG_HOME", None)

    @unittest.skipIf(sys.platform == "win32", "Skip on win32")
    def test_save_load_round_trip(self):
        with unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/test_xdg"}):
            phrase = "Hello World"
            save_seed(phrase)
            loaded = load_saved_seed()
            self.assertEqual(loaded, phrase)

    @unittest.skipIf(sys.platform == "win32", "Skip on win32")
    def test_missing_file_returns_none(self):
        with unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/test_xdg"}):
            # Ensure the file doesn't exist by removing it if it was created in a previous run
            path = config_dir() / "seed.txt"
            if path.exists():
                path.unlink()

            loaded = load_saved_seed()
            self.assertIsNone(loaded)

    @unittest.skipIf(sys.platform == "win32", "Skip on win32")
    def test_whitespace_file_returns_none(self):
        with unittest.mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/test_xdg"}):
            path = config_dir() / "seed.txt"
            path.write_text("   \n\t\n", encoding="utf-8")

            loaded = load_saved_seed()
            self.assertIsNone(loaded)
