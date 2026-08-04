"""Tests for the local browser interface.

Two of these are security properties rather than features, and they are the
reason this file exists. The server renders somebody's complete financial
position with no authentication, which is safe on loopback and unsafe anywhere
else. If a later change flips the bind address or drops the escaping, that
should fail a test rather than be discovered by someone on shared wifi.
"""

import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from portfolio_accountant import web
from portfolio_accountant.config import ConfigError


class TestBindingIsLoopbackOnly(unittest.TestCase):
    def test_bind_host_is_loopback(self):
        """Guards against a well-meaning change to 0.0.0.0.

        Serving on all interfaces would publish an unauthenticated view of the
        user's finances to every device on the network.
        """
        self.assertEqual(web.BIND_HOST, "127.0.0.1")
        self.assertNotIn(web.BIND_HOST, ("0.0.0.0", "::", ""))


class TestEngagementResolution(unittest.TestCase):
    def test_finds_the_bundled_example(self):
        names = [p.parent.name for p in web.find_engagements()]
        self.assertIn("example", names)

    def test_resolves_a_known_folder(self):
        self.assertTrue(web.resolve_engagement("example").exists())

    def test_rejects_path_traversal(self):
        """The folder name arrives from a query string and is treated as hostile."""
        for hostile in (
            "../../etc",
            "../example",
            "/etc/passwd",
            "example/../../..",
            "",
        ):
            with self.assertRaises(ConfigError, msg=f"accepted {hostile!r}"):
                web.resolve_engagement(hostile)

    def test_rejects_an_unknown_name(self):
        with self.assertRaises(ConfigError):
            web.resolve_engagement("no-such-portfolio")


class TestEscaping(unittest.TestCase):
    def test_escapes_html(self):
        self.assertEqual(web.esc("<script>"), "&lt;script&gt;")
        self.assertEqual(web.esc('"x"'), "&quot;x&quot;")

    def test_page_escapes_its_title(self):
        body = web.page("<script>alert(1)</script>", "<p>ok</p>").decode()
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("&lt;script&gt;", body)


class TestViews(unittest.TestCase):
    def test_home_renders(self):
        body = web.view_home().decode()
        self.assertIn("Portfolio Accountant", body)
        self.assertIn("example", body)
        # The scope limitation must be on the landing page, not buried.
        self.assertIn("It is not", body)

    def test_rates_page_shows_unverified_state(self):
        body = web.view_rates().decode()
        self.assertIn("Rates not verified", body)
        self.assertIn("Deliberately not implemented", body)

    def test_refusals_page_lists_refusals(self):
        body = web.view_refusals().decode()
        self.assertIn("will not assist with", body)
        self.assertIn("Let Property Campaign", body)

    def test_run_renders_the_example(self):
        body = web.view_run("example").decode()
        for expected in (
            "Rates not verified",      # unverified banner comes first
            "Not ready",               # readiness gate is honest
            "Section 24 gap",
            "Forensic review",
            "Income tax computation",
            "Compliance calendar",
        ):
            self.assertIn(expected, body, f"missing: {expected}")

    def test_run_shows_the_unclassified_queue(self):
        body = web.view_run("example").decode()
        self.assertIn("needs a human decision", body)
        self.assertIn("TRANSFER MAINTENANCE SERVICES", body)


class TestStaticExport(unittest.TestCase):
    """The export is how a period's workings reach an accountant or a lender.

    It has to survive being emailed and opened offline, so it must carry no
    external references at all.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = web.export_static("example").decode()

    def test_is_a_complete_document(self):
        self.assertTrue(self.html.startswith("<!doctype html>"))
        self.assertIn("</html>", self.html)

    def test_makes_no_external_requests(self):
        """A CDN font or remote image would break offline and leak the fact of
        opening the file to a third party."""
        import re

        self.assertIsNone(re.search(r'(src|href)="https?://', self.html))
        self.assertNotIn("@import", self.html)

    def test_tags_are_balanced(self):
        for tag in ("section", "div", "table", "ul"):
            self.assertEqual(
                self.html.count(f"<{tag}") - self.html.count(f"</{tag}>"),
                0,
                f"unbalanced <{tag}>",
            )

    def test_every_nav_anchor_has_a_target(self):
        import re

        for anchor in set(re.findall(r'href="#([\w-]+)"', self.html)):
            self.assertIn(f'id="{anchor}"', self.html, f"dead anchor #{anchor}")

    def test_supports_both_themes_and_an_explicit_toggle(self):
        self.assertIn("prefers-color-scheme: dark", self.html)
        self.assertIn(':root[data-theme="dark"]', self.html)
        self.assertIn(':root[data-theme="light"]', self.html)

    def test_leads_with_verification_and_readiness_not_with_figures(self):
        """Ordering is a correctness property, not a layout preference."""
        rates = self.html.index("Rates not verified")
        readiness = self.html.index("Not ready")
        tax = self.html.index("Income tax computation")
        self.assertLess(rates, tax)
        self.assertLess(readiness, tax)

    def test_scope_limitation_survives_export(self):
        self.assertIn("not tax advice", self.html)
        self.assertIn("must review these workings", self.html)

    def test_guide_can_be_omitted(self):
        plain = web.export_static("example", include_guide=False).decode()
        self.assertNotIn('id="guide"', plain)
        self.assertIn('id="readiness"', plain)


class TestServerRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer((web.BIND_HOST, 0), web.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def get(self, path):
        url = f"http://{web.BIND_HOST}:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.status, response.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    def test_pages_return_200(self):
        for path in ("/", "/rates", "/refusals", "/retention", "/run?config=example"):
            status, _ = self.get(path)
            self.assertEqual(status, 200, f"{path} returned {status}")

    def test_unknown_route_is_404(self):
        status, _ = self.get("/nonsense")
        self.assertEqual(status, 404)

    def test_bad_config_is_400_not_500(self):
        status, body = self.get("/run?config=../../etc")
        self.assertEqual(status, 400)
        self.assertIn("Configuration problem", body)

    def test_errors_do_not_echo_unescaped_input(self):
        status, body = self.get("/run?config=%3Cimg%20src=x%20onerror=alert(1)%3E")
        self.assertEqual(status, 400)
        self.assertNotIn("<img src=x", body)

    def test_response_sets_framing_headers(self):
        url = f"http://{web.BIND_HOST}:{self.port}/"
        with urllib.request.urlopen(url, timeout=30) as response:
            self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")


if __name__ == "__main__":
    unittest.main()
