import unittest
from shadowphish import analyze_url, run_training_server

class AnalyzeUrlTests(unittest.TestCase):
    def test_https_url_has_no_http_finding(self):
        self.assertNotIn("http_without_tls", {x["id"] for x in analyze_url("https://example.org/docs")["findings"]})
    def test_http_and_account_terms_flagged(self):
        ids = {x["id"] for x in analyze_url("http://example.org/login")["findings"]}
        self.assertIn("http_without_tls", ids); self.assertIn("suspicious_terms", ids)
    def test_userinfo_flagged(self):
        self.assertIn("userinfo_present", {x["id"] for x in analyze_url("https://trusted.example@evil.example/")["findings"]})
    def test_ip_literal_flagged(self):
        self.assertIn("ip_literal_host", {x["id"] for x in analyze_url("http://192.0.2.1/login")["findings"]})
    def test_punycode_flagged(self):
        self.assertIn("punycode_host", {x["id"] for x in analyze_url("https://xn--example-ova.test/")["findings"]})
    def test_empty_url_high_risk(self):
        self.assertEqual(analyze_url("")["risk_level"], "high")
    def test_report_says_no_fetch(self):
        self.assertIn("no URL was fetched", analyze_url("https://example.org/")["note"])
    def test_public_bind_refused(self):
        with self.assertRaises(ValueError): run_training_server("0.0.0.0", 8080)

if __name__ == "__main__": unittest.main()
