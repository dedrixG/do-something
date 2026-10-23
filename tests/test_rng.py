import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from do_something import Rng  # noqa: E402


class RngTests(unittest.TestCase):
    def test_same_seed_gives_same_sequence(self):
        rng1 = Rng(42)
        rng2 = Rng(42)
        for _ in range(10):
            self.assertEqual(rng1(), rng2())

    def test_rng_output_range(self):
        rng = Rng(123)
        for _ in range(100):
            val = rng()
            self.assertGreaterEqual(val, 0.0)
            self.assertLess(val, 1.0)

    def test_irand_stays_within_bounds(self):
        rng = Rng(99)
        for _ in range(1000):
            val = rng.irand(10, 20)
            self.assertGreaterEqual(val, 10)
            self.assertLessEqual(val, 20)

    def test_pick_returns_element_of_list(self):
        rng = Rng(7)
        choices = ["a", "b", "c"]
        for _ in range(50):
            val = rng.pick(choices)
            self.assertIn(val, choices)

    def test_seed_zero_behaves_like_seed_one(self):
        rng0 = Rng(0)
        rng1 = Rng(1)
        for _ in range(10):
            self.assertEqual(rng0(), rng1())


if __name__ == "__main__":
    unittest.main()
