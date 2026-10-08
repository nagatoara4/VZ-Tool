#!/usr/bin/env python3
"""VZ-Tool: GitHub cloner and project compatibility triage for iSH."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

VERSION = "0.2.0"
MAX_FILE_BYTES = 256_000
MAX_SCANNED_FILES = 5_000
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "target", "dist", "__pycache__", ".tox"}

MANIFESTS = {
    "Python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
    "Node.js": ["package.json"],
    "Rust": ["Cargo.toml"],
    "Go": ["go.mod"],
    "Ruby": ["Gemfile"],
    "PHP": ["composer.json"],
    "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "C/C++": ["Makefile", "CMakeLists.txt"],
    "Shell": ["install.sh", "run.sh", "setup.sh"],
}
BLOCKERS = [
    (r"\b(docker|docker-compose|podman)\b", "Container tooling may require kernel features unavailable in iSH."),
    (r"\b(systemctl|systemd)\b", "Assumes systemd, which standard iSH does not provide."),
    (r"\b(apt-get|apt|pacman|dnf|yum)\b", "Uses a package manager other than Alpine apk."),
    (r"\b(sudo|mount|modprobe|iptables|ip6tables)\b", "May require privileged host/kernel access unavailable in standard iSH."),
    (r"\b(nvidia-smi|cuda|/dev/kvm|kvm)\b", "May depend on hardware/kernel features not exposed by iOS/iSH."),
]
RISK_PATTERNS = [
    (r"\bcurl\b[^\n|]*\|\s*(?:sh|bash|ash)\b", "Downloads content and pipes it directly into a shell."),
    (r"\bwget\b[^\n|]*\|\s*(?:sh|bash|ash)\b", "Downloads content and pipes it directly into a shell."),
    (r"\b(?:eval\s+\$\(|base64\s+--?decode[^\n]*\|\s*(?:sh|bash|ash))", "Uses a dynamic or encoded shell execution pattern."),
]
GITHUB_SCP = re.compile(r"^git@github\.com:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$")
REPO_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


def run(command: list[str], cwd: Path | None = None) -> str:
    """Run a command without shell interpolation and return combined output."""
    try:
        result = subprocess.run(
            command, cwd=str(cwd) if cwd else None, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True,
        )
        return result.stdout.strip()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stdout.strip() or f"Command failed: {command[0]}") from exc


def validate_github_url(url: str) -> str:
    """Accept only standard GitHub HTTPS or SSH repository URL forms."""
    if not isinstance(url, str) or not url or any(ch.isspace() for ch in url):
        raise ValueError("Repository URL is empty or contains whitespace.")
    if GITHUB_SCP.fullmatch(url):
        return url
    parsed = urlparse(url)
    if parsed.scheme == "https":
        if parsed.hostname != "github.com" or parsed.username or parsed.password:
            raise ValueError("HTTPS URLs must use github.com and must not embed credentials.")
        if parsed.query or parsed.fragment:
            raise ValueError("Repository URLs must not contain query strings or fragments.")
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2 or not all(REPO_PART.fullmatch(part.removesuffix(".git")) for part in parts):
            raise ValueError("Expected a GitHub repository URL like https://github.com/OWNER/REPO.git")
        return url
    if parsed.scheme == "ssh":
        if parsed.hostname != "github.com" or parsed.username != "git" or parsed.password:
            raise ValueError("SSH URLs must use git@github.com.")
        if parsed.query or parsed.fragment:
            raise ValueError("Repository URLs must not contain query strings or fragments.")
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2 or not all(REPO_PART.fullmatch(part.removesuffix(".git")) for part in parts):
            raise ValueError("Expected an SSH GitHub repository URL.")
        return url
    raise ValueError("Use a GitHub HTTPS URL, git@github.com:OWNER/REPO.git, or ssh://git@github.com/OWNER/REPO.git.")


def _manifest_report(path: Path) -> list[dict]:
    detected = []
    for kind, filenames in MANIFESTS.items():
        matches = [name for name in filenames if (path / name).is_file()]
        if matches:
            detected.append({"kind": kind, "files": matches})
    return detected


def analyze(path: Path) -> dict:
    """Inspect manifests and selected compatibility/risk patterns without executing code."""
    detected = _manifest_report(path)
    blockers, risk_flags = [], []
    scanned = 0
    truncated = False
    for base, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for filename in sorted(files):
            scanned += 1
            if scanned > MAX_SCANNED_FILES:
                truncated = True
                break
            file_path = Path(base) / filename
            try:
                if file_path.stat().st_size > MAX_FILE_BYTES:
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            relative = str(file_path.relative_to(path))
            for pattern, reason in BLOCKERS:
                if re.search(pattern, content, re.I):
                    blockers.append({"file": relative, "reason": reason})
                    break
            for pattern, reason in RISK_PATTERNS:
                match = re.search(pattern, content, re.I)
                if match:
                    line = content.count("\n", 0, match.start()) + 1
                    risk_flags.append({"file": relative, "line": line, "reason": reason})
                    break
        if truncated:
            break

    has_python_or_shell = any(item["kind"] in ("Python", "Shell") for item in detected)
    return {
        "tool": "VZ-Tool",
        "version": VERSION,
        "project": path.name or str(path),
        "path": str(path.resolve()),
        "detected": detected,
        "compatibility_estimate": "promising starting point" if has_python_or_shell else ("manual review needed" if detected else "unknown"),
        "blockers": blockers,
        "risk_flags": risk_flags,
        "scan": {"files_examined": min(scanned, MAX_SCANNED_FILES), "truncated": truncated},
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "limitations": [
            "Analysis is heuristic and does not execute or certify project code.",
            "Standard iSH emulates a 32-bit x86 Linux userland; iPhone host architecture does not imply native ARM64 Linux support.",
            "iOS sandboxing and kernel capabilities restrict privileged Linux features.",
        ],
    }


def doctor() -> dict:
    commands = {name: shutil.which(name) for name in ("python3", "git", "pip3", "apk", "ssh", "npm", "make")}
    return {
        "tool": "VZ-Tool",
        "version": VERSION,
        "python": sys.version.split()[0],
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "commands": commands,
        "clone_ready": bool(commands["git"]),
        "notes": [
            "Standard iSH emulates a 32-bit x86 Linux userland; it is not native ARM64 Linux.",
            "Install only packages available for your iSH environment with apk.",
            "This check is read-only; it does not install packages or alter settings.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vztool",
        description="Clone GitHub repositories and triage project compatibility for iSH.",
        epilog="VZ-Tool cannot guarantee that arbitrary projects run in iSH.",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    clone = sub.add_parser("clone", help="clone a GitHub repository")
    clone.add_argument("url", help="GitHub HTTPS or SSH repository URL")
    clone.add_argument("--dir", help="destination directory (must not already exist)")
    clone.add_argument("--branch", help="branch, tag, or remote ref to check out")
    clone.add_argument("--depth", type=int, help="optional positive shallow-clone depth")
    clone.add_argument("--recursive", action="store_true", help="initialize submodules recursively")

    scan = sub.add_parser("analyze", help="inspect a local project without executing it")
    scan.add_argument("path", nargs="?", default=".")
    scan.add_argument("--json", action="store_true", help="print the complete JSON report")

    sub.add_parser("doctor", help="check local command availability and iSH constraints")

    prepare = sub.add_parser("prepare", help="suggest setup commands for a local project")
    prepare.add_argument("path", nargs="?", default=".")
    prepare.add_argument("--execute", action="store_true", help="request execution after an interactive confirmation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "clone":
            url = validate_github_url(args.url)
            if args.depth is not None and args.depth < 1:
                raise ValueError("--depth must be a positive integer.")
            if not shutil.which("git"):
                raise RuntimeError("git is missing. In iSH try: apk update && apk add git")
            repo_name = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
            if ":" in repo_name:
                repo_name = repo_name.rsplit(":", 1)[-1].removesuffix(".git")
            destination = Path(args.dir or repo_name).expanduser()
            if destination.exists():
                raise RuntimeError(f"Destination already exists: {destination}. Refusing to overwrite it.")
            if destination.name in ("", ".", ".."):
                raise ValueError("Choose a valid destination directory.")
            command = ["git", "clone"]
            if args.branch:
                command.extend(["--branch", args.branch])
            if args.depth is not None:
                command.extend(["--depth", str(args.depth)])
            if args.recursive:
                command.append("--recurse-submodules")
            command.extend(["--", url, str(destination)])
            output = run(command)
            if output:
                print(output)
            print(f"\nClone complete: {destination}")
            print(f"Next step: python3 vztool.py analyze {destination}")
            return 0

        if args.command == "doctor":
            report = doctor()
            print(json.dumps(report, indent=2))
            return 0 if report["clone_ready"] else 1

        path = Path(args.path).expanduser()
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        if args.command == "analyze":
            report = analyze(path)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(f"VZ-TOOL {VERSION} | {report['project']}")
                print(f"Compatibility estimate: {report['compatibility_estimate']}")
                print("Detected:", ", ".join(item["kind"] for item in report["detected"]) or "no known manifest")
                print(f"Files examined: {report['scan']['files_examined']}" + (" (scan capped)" if report["scan"]["truncated"] else ""))
                print("\nPlatform blockers:")
                for item in report["blockers"]:
                    print(f"  - {item['file']}: {item['reason']}")
                if not report["blockers"]:
                    print("  - No known blocker patterns found.")
                print("\nReview flags:")
                for item in report["risk_flags"]:
                    print(f"  - {item['file']}:{item['line']}: {item['reason']}")
                if not report["risk_flags"]:
                    print("  - No configured patterns found; this is not proof of safety.")
                for note in report["limitations"]:
                    print("NOTE:", note)
            return 0

        choices = []
        if (path / "requirements.txt").is_file():
            choices.append(("Install Python dependencies", [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]))
        elif (path / "pyproject.toml").is_file():
            choices.append(("Install Python project", [sys.executable, "-m", "pip", "install", "."]))
        if (path / "package.json").is_file():
            choices.append(("Install Node.js dependencies", ["npm", "install"]))
        if (path / "Makefile").is_file():
            choices.append(("Build with make", ["make"]))
        if not choices:
            print("No default setup command detected. Review the project's documentation and scripts manually.")
            return 0
        for index, (label, command) in enumerate(choices, 1):
            print(f"{index}. {label}: {' '.join(command)} (not run)")
        print("Review upstream scripts before approving setup; dependency installation may execute third-party code.")
        if args.execute:
            if len(choices) != 1:
                raise RuntimeError("Multiple commands detected; refusing ambiguous execution.")
            label, command = choices[0]
            if input(f"Execute {label} in {path.resolve()}? [y/N] ").strip().lower() != "y":
                print("Cancelled.")
                return 0
            output = run(command, cwd=path)
            if output:
                print(output)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"vztool: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
