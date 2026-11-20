import os
import signal
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import do_something as ds  # noqa: E402

APP = QApplication.instance() or QApplication([])


def ev(kind, key=None):
    e = MagicMock()
    e.type.return_value = kind
    if key is not None:
        e.key.return_value = key
        e.isAutoRepeat.return_value = False
    return e


class SkipScreensTests(unittest.TestCase):
    def test_default_skips_virtual_outputs(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DO_SOMETHING_SKIP_SCREENS", None)
            pats = ds.skip_patterns(None)
        self.assertTrue(ds.screen_skipped("Virtual-stream", pats))
        self.assertFalse(ds.screen_skipped("DP-1", pats))

    def test_env_and_flag(self):
        with patch.dict(os.environ, {"DO_SOMETHING_SKIP_SCREENS": "HDMI-*, DP-2"}):
            pats = ds.skip_patterns(None)
        self.assertTrue(ds.screen_skipped("HDMI-A-1", pats))
        self.assertTrue(ds.screen_skipped("DP-2", pats))
        self.assertFalse(ds.screen_skipped("Virtual-x", pats))
        self.assertEqual(ds.skip_patterns(""), [])

    def test_parse_args(self):
        a = ds.parse_args(["--stream-lock", "--skip-screens", "X-*"])
        self.assertTrue(a.stream_lock)
        self.assertEqual(a.skip_screens, "X-*")
        self.assertFalse(ds.parse_args([]).stream_lock)


class StreamLockTests(unittest.TestCase):
    def make(self, locked=False):
        g = ds.ScreensaverGuard(grace_s=0, locked=locked)
        g._arm()
        return g

    def test_locked_swallows_everything_and_stays_up(self):
        g = self.make(locked=True)
        with patch.object(ds.QApplication, "quit") as q:
            from PySide6.QtCore import Qt
            self.assertTrue(g.eventFilter(None, ev(QEvent.Type.KeyPress, Qt.Key.Key_Escape)))
            self.assertTrue(g.eventFilter(None, ev(QEvent.Type.MouseButtonPress)))
            q.assert_not_called()
        self.assertFalse(g._done)

    def test_unlocked_escape_quits(self):
        g = self.make(locked=False)
        from PySide6.QtCore import Qt
        with patch.object(ds.QApplication, "quit") as q:
            g.eventFilter(None, ev(QEvent.Type.KeyPress, Qt.Key.Key_Escape))
            q.assert_called_once()

    @unittest.skipUnless(hasattr(signal, "SIGUSR1"), "POSIX only")
    def test_signals_toggle_lock(self):
        g = self.make()
        ds.install_lock_signals(APP, g)
        marker = ds.lockable_marker()
        if marker is not None:
            self.assertTrue(marker.exists())
        os.kill(os.getpid(), signal.SIGUSR1)
        self.assertTrue(g.locked)
        os.kill(os.getpid(), signal.SIGUSR2)
        self.assertFalse(g.locked)
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)
        signal.signal(signal.SIGUSR2, signal.SIG_DFL)


if __name__ == "__main__":
    unittest.main()
