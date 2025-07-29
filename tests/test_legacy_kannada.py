import unittest
from modules.legacy_kannada import convert_legacy_to_unicode

class TestLegacyKannada(unittest.TestCase):
    def test_simple_conversion(self):
        legacy_text = "ªÀ£ÀPÀAiÀÄ"
        expected = "ಅನಡಆ"
        self.assertEqual(convert_legacy_to_unicode(legacy_text), expected)

if __name__ == "__main__":
    unittest.main()
