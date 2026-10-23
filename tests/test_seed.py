import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from do_something import SeedWorld, peel_windows_scr  # noqa: E402


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

    def test_contact_format(self):
        w = SeedWorld("System Check")
        contact = w.contact(0)
        # Must match ^[A-Z0-9]{1,8}-[0-9A-F]{4}$
        self.assertRegex(contact, r"^[A-Z0-9]{1,8}-[0-9A-F]{4}$")

    def test_contact_stable(self):
        w = SeedWorld("System Check")
        self.assertEqual(w.contact(0), w.contact(0))
        self.assertEqual(w.contact(0), w.contact(0))

    def test_ident_truncation(self):
        # Short phrase
        w1 = SeedWorld("abc")
        self.assertLessEqual(len(w1.ident), 24)
        # Long phrase
        w2 = SeedWorld("this is a very long phrase that should be truncated")
        self.assertLessEqual(len(w2.ident), 24)

    def test_slug_keeps_words(self):
        w = SeedWorld("System Check")
        self.assertIn("system", w.slug)
        self.assertIn("check", w.slug)


if __name__ == "__main__":
    unittest.main()
