import unittest

from videodock.core import friendly_error


class NetworkErrorTests(unittest.TestCase):
    def test_dns_error_identifies_name_resolution_and_preserves_details(self):
        raw = "Unable to download API page: Failed to resolve www.youtube.com ([Errno 11001] getaddrinfo failed)"
        result = friendly_error(raw)
        self.assertIn("DNS", result)
        self.assertIn("для этого запуска", result)
        self.assertTrue(result.endswith(raw))

    def test_http_forbidden_is_not_reported_as_no_internet(self):
        result = friendly_error("Unable to download webpage: HTTP Error 403: Forbidden")
        self.assertIn("HTTP 403", result)
        self.assertNotIn("Проверьте интернет", result)

    def test_certificate_error_is_specific(self):
        result = friendly_error("Unable to download webpage: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
        self.assertIn("сертификат HTTPS", result)

    def test_unknown_download_error_preserves_actual_cause(self):
        raw = "Unable to download webpage: HTTP Error 418"
        self.assertEqual(friendly_error(raw), raw)

    def test_rate_limit_is_specific(self):
        self.assertIn("HTTP 429", friendly_error("HTTP Error 429: Too Many Requests"))


if __name__ == "__main__":
    unittest.main()
