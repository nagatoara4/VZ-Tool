import tempfile
import unittest
from pathlib import Path
import vztool


class VZToolTests(unittest.TestCase):
    def test_github_https_url(self):
        self.assertEqual(vztool.validate_url("https://github.com/a/b.git"), "https://github.com/a/b.git")

    def test_rejects_external_https(self):
        with self.assertRaises(ValueError):
            vztool.validate_url("https://example.com/a/b")

    def test_detects_python_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "requirements.txt").write_text("requests\n")
            self.assertEqual(vztool.analyze(Path(directory))["compatibility_estimate"], "best chance")

    def test_detects_docker_blocker(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "README.md").write_text("docker compose up")
            self.assertTrue(vztool.analyze(Path(directory))["blockers"])

    def test_existing_destination_not_overwritten_by_design(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "keep")
            target.mkdir()
            (target / "important.txt").write_text("keep")
            self.assertEqual((target / "important.txt").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
