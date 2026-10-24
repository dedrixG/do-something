import unittest
from do_something import pad, hx


class FormatHelpersTests(unittest.TestCase):
    def test_pad_default_width(self):
        self.assertEqual(pad(5), "05")

    def test_pad_larger_number(self):
        self.assertEqual(pad(123, 2), "123")

    def test_pad_custom_width(self):
        self.assertEqual(pad(7, 4), "0007")

    def test_hx_zero(self):
        self.assertEqual(hx(0), "00")

    def test_hx_max_byte(self):
        self.assertEqual(hx(255), "ff")

    def test_hx_large_value(self):
        # Verify it produces a lowercase hex string of correct length (8 chars for 32-bit)
        val = 0xDEADBEEF
        result = hx(val)
        self.assertEqual(result, "deadbeef")


if __name__ == "__main__":
    unittest.main()
