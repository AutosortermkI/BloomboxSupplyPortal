import unittest

from scrape.core.fetcher import FetchResult


class FetchBlockDetectionTests(unittest.TestCase):
    def test_sitewide_recaptcha_script_alone_is_not_blocked(self):
        html = """
        <html>
          <body>
            <script src="https://www.google.com/recaptcha/api.js"></script>
            <a href="/my-account/customer-logout/">Log out</a>
            <a href="/my-account/edit-account/">Account details</a>
          </body>
        </html>
        """

        result = FetchResult(
            url="https://www.americannativeplants.com/my-account/",
            status=200,
            html=html,
            tier="playwright",
        )

        self.assertFalse(result.blocked)

    def test_explicit_captcha_challenge_is_blocked(self):
        html = "<html><body>reCAPTCHA challenge required before continuing</body></html>"

        result = FetchResult(
            url="https://example.com/login",
            status=200,
            html=html,
            tier="playwright",
        )

        self.assertTrue(result.blocked)


if __name__ == "__main__":
    unittest.main()
