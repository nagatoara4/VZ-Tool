import tempfile
import unittest
from pathlib import Path
from shadowphish import analyze_url, analyze_email_headers, run_training_server, write_reports

class UrlTests(unittest.TestCase):
    def test_https_not_flagged_for_http(self):
        self.assertNotIn("http_without_tls",{x["id"] for x in analyze_url("https://example.org/docs")["findings"]})
    def test_http_and_terms_flagged(self):
        ids={x["id"] for x in analyze_url("http://example.org/login")["findings"]}
        self.assertIn("http_without_tls",ids); self.assertIn("suspicious_terms",ids)
    def test_userinfo_flagged(self):
        self.assertIn("userinfo_present",{x["id"] for x in analyze_url("https://trusted.example@evil.example/")["findings"]})
    def test_ip_flagged(self):
        self.assertIn("ip_literal_host",{x["id"] for x in analyze_url("http://192.0.2.1/login")["findings"]})
    def test_punycode_flagged(self):
        self.assertIn("punycode_host",{x["id"] for x in analyze_url("https://xn--example-ova.test/")["findings"]})
    def test_empty_high_risk(self):
        self.assertEqual(analyze_url("")["risk_level"],"high")
    def test_bad_port_is_handled(self):
        self.assertIn("malformed_url",{x["id"] for x in analyze_url("https://example.org:bad/")["findings"]})
    def test_public_bind_refused(self):
        with self.assertRaises(ValueError): run_training_server("0.0.0.0",8080)

class HeaderTests(unittest.TestCase):
    def test_reply_to_mismatch(self):
        r=analyze_email_headers("From: Billing <billing@example.com>\nReply-To: help@attacker.test\nDate: Thu, 1 Jan 2026 00:00:00 +0000\n")
        self.assertIn("reply_to_domain_mismatch",{x["id"] for x in r["findings"]})
    def test_authentication_failures(self):
        r=analyze_email_headers("From: a@example.com\nAuthentication-Results: mx; spf=fail; dkim=pass; dmarc=fail\n")
        ids={x["id"] for x in r["findings"]}; self.assertIn("spf_failure",ids); self.assertIn("dmarc_failure",ids)
    def test_missing_auth_is_flagged(self):
        self.assertIn("missing_auth_results",{x["id"] for x in analyze_email_headers("From: a@example.com\n")["findings"]})
    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"report.csv"; write_reports([analyze_url("https://example.org")],path,"csv")
            self.assertIn("risk_score",path.read_text(encoding="utf-8"))

if __name__=="__main__": unittest.main()
