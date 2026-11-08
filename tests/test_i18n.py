import string
import unittest

from videodock.core import friendly_error, validate_range
from videodock.i18n import ENGLISH, translate


class TranslationTests(unittest.TestCase):
    def test_template_arguments_match_in_both_languages(self):
        formatter = string.Formatter()
        for source, english in ENGLISH.items():
            with self.subTest(source=source):
                original_fields = {field for _, field, _, _ in formatter.parse(source) if field is not None}
                english_fields = {field for _, field, _, _ in formatter.parse(english) if field is not None}
                self.assertEqual(original_fields, english_fields)

    def test_formatted_validation_error_translates(self):
        with self.assertRaises(ValueError) as caught:
            validate_range("1:00", "3:00", 120)
        self.assertEqual(translate(str(caught.exception), "en"), "The clip end exceeds the video duration (2:00).")

    def test_extractor_details_remain_unchanged(self):
        diagnostic = "HTTPSConnection: getaddrinfo failed; original title: Пример"
        error = friendly_error(diagnostic)
        translated = translate(error, "en")
        self.assertIn("DNS error", translated)
        self.assertEqual(translated.split("\n\n", 1)[1], diagnostic)
        self.assertEqual(translate(error, "ru"), error)

    def test_unknown_text_is_not_interpreted_as_a_format_string(self):
        diagnostic = "Extractor error: {'key': 'value'}"
        self.assertEqual(translate(diagnostic, "en"), diagnostic)


if __name__ == "__main__":
    unittest.main()
