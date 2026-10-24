import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from do_something import (  # noqa: E402
    SeedWorld,
    load_saved_seed,
    main,
    parse_args,
    peel_windows_scr,
    save_seed,
)


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

    def test_contact_format_and_stable(self):
        world = SeedWorld("System Check")
        contact = world.contact(0)
        self.assertRegex(contact, r"^[A-Z0-9]{1,8}-[0-9A-F]{4}$")
        self.assertEqual(contact, world.contact(0))

    def test_ident_truncates_and_slug_keeps_every_word(self):
        short = SeedWorld("abc")
        self.assertLessEqual(len(short.ident), 24)
        phrase = "this is a very long phrase that should be truncated"
        world = SeedWorld(phrase)
        self.assertLessEqual(len(world.ident), 24)
        for word in phrase.split():
            self.assertIn(word, world.slug)


class CoverWindowGracePeriodTests(unittest.TestCase):
    def test_non_esc_key_does_not_quit(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from do_something import CoverWindow, SeedWorld  # noqa: E402
        from PySide6.QtWidgets import QApplication  # noqa: E402
        from PySide6.QtGui import QKeyEvent  # noqa: E402
        from PySide6.QtCore import QEvent, Qt  # noqa: E402

        app = QApplication.instance() or QApplication([])
        world = SeedWorld("Test Phrase")
        
        # Mock quit to verify it's not called
        original_quit = QApplication.quit
        quit_called = False
        
        def mock_quit():
            nonlocal quit_called
            quit_called = True
            # Don't actually quit in test
            
        QApplication.quit = mock_quit

        try:
            # Create a dummy screen object for CoverWindow initialization
            class DummyScreen:
                def geometry(self):
                    from PySide6.QtCore import QRect
                    return QRect(0, 0, 1920, 1080)
                def name(self):
                    return "test"
            
            cover = CoverWindow(DummyScreen(), world, salt=0)
            
            # Simulate a non-Escape key press (e.g., 'A')
            event_a = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
            cover.keyPressEvent(event_a)
            
            self.assertFalse(quit_called, "QApplication.quit should not be called for non-Escape keys")

            # Simulate Escape key press
            event_esc = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
            cover.keyPressEvent(event_esc)
            
            self.assertTrue(quit_called, "QApplication.quit should be called for Escape key")
        finally:
            QApplication.quit = original_quit


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

    def test_uppercase_s(self):
        mode, rest = peel_windows_scr(["/S"])
        self.assertEqual(mode, "fullscreen")
        self.assertEqual(rest, [])

    def test_config_colon(self):
        mode, rest = peel_windows_scr(["/c:1234"])
        self.assertEqual(mode, "config")
        self.assertEqual(rest, [])

    def test_preview_colon(self):
        mode, rest = peel_windows_scr(["/p:5678", "--seed", "x"])
        self.assertEqual(mode, "preview")
        self.assertEqual(rest, ["--seed", "x"])

    def test_dash_s(self):
        mode, rest = peel_windows_scr(["-s"])
        self.assertEqual(mode, "fullscreen")
        self.assertEqual(rest, [])

    def test_dash_p_with_arg(self):
        mode, rest = peel_windows_scr(["-p", "99", "--seed", "x"])
        self.assertEqual(mode, "preview")
        self.assertEqual(rest, ["--seed", "x"])

    def test_passthrough_non_flags(self):
        mode, rest = peel_windows_scr(["/s", "--seed", "abc", "--windowed"])
        self.assertEqual(mode, "fullscreen")
        self.assertEqual(rest, ["--seed", "abc", "--windowed"])

    def test_no_flag_argv(self):
        mode, rest = peel_windows_scr(["--seed", "abc"])
        self.assertIsNone(mode)
        self.assertEqual(rest, ["--seed", "abc"])


class ParseArgsTests(unittest.TestCase):
    def test_defaults(self):
        args = parse_args([])
        self.assertEqual(args.width, 1600)
        self.assertEqual(args.height, 900)
        self.assertIsNone(args.seed)
        self.assertFalse(args.windowed)

    def test_seed_window_and_width(self):
        args = parse_args(["--seed", "Bed time", "--window", "--width", "800"])
        self.assertEqual(args.seed, "Bed time")
        self.assertTrue(args.windowed)
        self.assertEqual(args.width, 800)


def _seed_env(root: str) -> dict[str, str]:
    env = {"XDG_CONFIG_HOME": root}
    if sys.platform == "win32":
        env["APPDATA"] = root
    return env


class SavedSeedTests(unittest.TestCase):
    def test_load_saved_seed_does_not_create_config_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-config"
            with patch.dict(os.environ, _seed_env(str(missing))):
                self.assertIsNone(load_saved_seed())
            self.assertFalse(missing.exists())

    def test_load_saved_seed_returns_none_on_oserror(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / (
                "DoSomething" if sys.platform == "win32" else "do-something"
            )
            folder.mkdir()
            (folder / "seed.txt").write_text("hello\n", encoding="utf-8")
            with patch.dict(os.environ, _seed_env(tmp)):
                with patch.object(Path, "read_text", side_effect=PermissionError("nope")):
                    self.assertIsNone(load_saved_seed())

    def test_save_seed_creates_dir_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "fresh"
            with patch.dict(os.environ, _seed_env(str(fresh))):
                self.assertIs(save_seed("x"), True)
                self.assertEqual(load_saved_seed(), "x")

    def test_save_then_load_returns_the_stripped_phrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, _seed_env(tmp)):
                self.assertIs(save_seed("  Hello World  "), True)
                self.assertEqual(load_saved_seed(), "Hello World")

    def test_whitespace_only_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / (
                "DoSomething" if sys.platform == "win32" else "do-something"
            )
            folder.mkdir()
            (folder / "seed.txt").write_text("   \n\t\n", encoding="utf-8")
            with patch.dict(os.environ, _seed_env(tmp)):
                self.assertIsNone(load_saved_seed())

    def test_save_seed_returns_false_when_unwritable(self):
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with patch.dict(os.environ, _seed_env(tmp)):
                with patch.object(Path, "write_text", side_effect=PermissionError("nope")):
                    with patch("do_something.sys.stderr", err):
                        self.assertIs(save_seed("x"), False)
            self.assertIn("could not save seed", err.getvalue())


class LaunchSeedTests(unittest.TestCase):
    def _run(self, argv, prompt):
        app = MagicMock()
        app.exec.return_value = 0
        app.primaryScreen.return_value = None
        with patch("do_something.QApplication", return_value=app), \
             patch("do_something.QGuiApplication.screens", return_value=[]), \
             patch("do_something.Windowed"), \
             patch("do_something.CoverWindow"), \
             patch("do_something.QTimer.singleShot"), \
             patch("do_something.prompt_seed", side_effect=prompt):
            return main(argv)

    def test_smoke_and_seed_flag_leave_the_saved_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / (
                "DoSomething" if sys.platform == "win32" else "do-something"
            )
            folder.mkdir()
            seed = folder / "seed.txt"
            seed.write_text("Mine\n", encoding="utf-8")

            def answer(preset):
                return SeedWorld(preset or "Typed")

            with patch.dict(os.environ, _seed_env(tmp)):
                self._run(["--smoke", str(Path(tmp) / "shot.png")], answer)
                self.assertEqual(seed.read_text(encoding="utf-8"), "Mine\n")
                self._run(["--seed", "Other"], answer)
                self.assertEqual(seed.read_text(encoding="utf-8"), "Mine\n")

    def test_prompt_and_config_still_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            def typed(preset):
                self.assertIsNone(preset)
                return SeedWorld("Typed")

            def from_settings(preset):
                self.assertIsNone(preset)
                return SeedWorld("From settings")

            with patch.dict(os.environ, _seed_env(tmp)):
                self._run([], typed)
                self.assertEqual(load_saved_seed(), "Typed")
                self._run(["/c"], from_settings)
                self.assertEqual(load_saved_seed(), "From settings")

    def test_fullscreen_without_saved_seed_uses_system_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen = []

            def answer(preset):
                seen.append(preset)
                return SeedWorld(preset or "should-not-prompt")

            with patch.dict(os.environ, _seed_env(tmp)), \
                 patch("do_something.SeedDialog") as dialog:
                self._run(["/s"], answer)
            self.assertEqual(seen, ["System Check"])
            dialog.assert_not_called()
            folder = Path(tmp) / (
                "DoSomething" if sys.platform == "win32" else "do-something"
            )
            self.assertFalse((folder / "seed.txt").exists())

    def test_fullscreen_keeps_a_saved_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / (
                "DoSomething" if sys.platform == "win32" else "do-something"
            )
            folder.mkdir()
            seed = folder / "seed.txt"
            seed.write_text("Mine\n", encoding="utf-8")
            seen = []

            def answer(preset):
                seen.append(preset)
                return SeedWorld(preset or "should-not-prompt")

            with patch.dict(os.environ, _seed_env(tmp)), \
                 patch("do_something.SeedDialog") as dialog:
                self._run(["/s"], answer)
            self.assertEqual(seen, ["Mine"])
            dialog.assert_not_called()
            self.assertEqual(seed.read_text(encoding="utf-8"), "Mine\n")


if __name__ == "__main__":
    unittest.main()
