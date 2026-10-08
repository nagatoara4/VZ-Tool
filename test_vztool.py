import tempfile
import unittest
from pathlib import Path

import vztool


class URLValidationTests(unittest.TestCase):
    def test_github_https_url(self):
        self.assertEqual(
            vztool.validate_github_url("https://github.com/example/project.git"),
            "https://github.com/example/project.git",
        )

    def test_github_ssh_scp_style(self):
        self.assertEqual(
            vztool.validate_github_url("git@github.com:example/project.git"),
            "git@github.com:example/project.git",
        )

    def test_github_ssh_scheme(self):
        self.assertEqual(
            vztool.validate_github_url("ssh://git@github.com/example/project.git"),
            "ssh://git@github.com/example/project.git",
        )

    def test_rejects_external_https_host(self):
        with self.assertRaises(ValueError):
            vztool.validate_github_url("https://example.com/example/project")

    def test_rejects_external_ssh_host(self):
        with self.assertRaises(ValueError):
            vztool.validate_github_url("ssh://git@example.com/example/project.git")

    def test_rejects_embedded_https_credentials(self):
        with self.assertRaises(ValueError):
            vztool.validate_github_url("https://token@github.com/example/project.git")

    def test_rejects_query_strings(self):
        with self.assertRaises(ValueError):
            vztool.validate_github_url("https://github.com/example/project?token=secret")


class AnalysisTests(unittest.TestCase):
    def test_detects_python_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("requests\n", encoding="utf-8")
            self.assertEqual(vztool.analyze(root)["compatibility_estimate"], "promising starting point")

    def test_detects_docker_blocker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("docker compose up\n", encoding="utf-8")
            self.assertTrue(vztool.analyze(root)["blockers"])

    def test_detects_piped_remote_shell_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "install.sh").write_text("curl https://example.invalid/install.sh | sh\n", encoding="utf-8")
            report = vztool.analyze(root)
            self.assertTrue(report["risk_flags"])
            self.assertEqual(report["risk_flags"][0]["line"], 1)

    def test_ignores_dependency_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "node_modules"
            nested.mkdir()
            (nested / "README.md").write_text("docker systemctl", encoding="utf-8")
            self.assertFalse(vztool.analyze(root)["blockers"])

    def test_scan_is_read_only_and_reports_limitations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("Example project", encoding="utf-8")
            report = vztool.analyze(root)
            self.assertIn("limitations", report)
            self.assertTrue((root / "README.md").exists())


class CLIArgumentTests(unittest.TestCase):
    def test_help_parser_builds(self):
        parser = vztool.build_parser()
        parsed = parser.parse_args(["clone", "https://github.com/example/project.git", "--depth", "1"])
        self.assertEqual(parsed.command, "clone")
        self.assertEqual(parsed.depth, 1)

    def test_rejects_nonpositive_depth(self):
        with self.assertRaises(SystemExit):
            vztool.build_parser().parse_args(["clone", "https://github.com/example/project.git", "--depth", "0"])


if __name__ == "__main__":
    unittest.main()
