#!/usr/bin/env python3
"""VZ-Tool: conservative GitHub project helper for iSH on iOS."""
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

VERSION = "0.1.0"
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
    (r"\b(docker|docker-compose|podman)\b", "Container engine/kernel capabilities generally unavailable in iSH."),
    (r"\b(systemctl|systemd)\b", "Assumes systemd, which iSH does not provide."),
    (r"\b(apt-get|apt|pacman|dnf|yum)\b", "Uses a distro package manager other than Alpine apk."),
    (r"\b(sudo|mount|modprobe|iptables|ip6tables)\b", "Requests privileged system/kernel access unavailable to ordinary iSH processes."),
    (r"\b(nvidia-smi|cuda|/dev/kvm|kvm)\b", "Depends on hardware/kernel features not exposed by iOS/iSH."),
]


def run(cmd, cwd=None):
    try:
        return subprocess.run(
            cmd, cwd=cwd, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, check=True
        ).stdout
    except FileNotFoundError as exc:
        raise RuntimeError(f"{cmd[0]} not found. Install available packages with iSH apk.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stdout.strip() or "Command failed") from exc


def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "ssh") or not parsed.netloc:
        raise ValueError("Use a GitHub HTTPS or SSH repository URL.")
    if parsed.scheme == "https" and (parsed.hostname or "").lower() not in ("github.com", "www.github.com"):
        raise ValueError("HTTPS cloning is restricted to github.com.")
    return url


def analyze(path):
    found = []
    blockers = []
    for kind, names in MANIFESTS.items():
        matches = [name for name in names if (path / name).exists()]
        if matches:
            found.append({"kind": kind, "files": matches})
    for base, dirs, files in os.walk(path):
        dirs[:] = [name for name in dirs if name not in {".git", "node_modules", ".venv", "venv", "target", "dist"}]
        for name in files:
            file_path = Path(base) / name
            try:
                if file_path.stat().st_size > 256000:
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern, reason in BLOCKERS:
                if re.search(pattern, content, re.I):
                    blockers.append({"file": str(file_path.relative_to(path)), "reason": reason})
                    break
            if len(blockers) >= 100:
                break
        if len(blockers) >= 100:
            break
    best = any(item["kind"] in ("Python", "Shell") for item in found)
    return {
        "project": path.name,
        "path": str(path.resolve()),
        "detected": found,
        "compatibility_estimate": "best chance" if best else ("needs review" if found else "unknown"),
        "blockers": blockers,
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "limitations": [
            "iSH is an Alpine Linux userland, not a full Linux kernel or unrestricted root environment.",
            "ARM64 iPhone hardware does not make x86_64 binaries runnable.",
            "This heuristic cannot guarantee compatibility or establish that code is safe.",
            "Review third-party scripts before executing them.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        prog="vztool",
        description="GitHub project cloner and compatibility assistant for iSH on iPhone",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="cmd", required=True)

    clone_parser = sub.add_parser("clone", help="clone a GitHub repository")
    clone_parser.add_argument("url")
    clone_parser.add_argument("--dir")

    analyze_parser = sub.add_parser("analyze", help="analyze a local project")
    analyze_parser.add_argument("path", nargs="?", default=".")
    analyze_parser.add_argument("--json", action="store_true")

    prepare_parser = sub.add_parser("prepare", help="show likely setup commands without running them")
    prepare_parser.add_argument("path", nargs="?", default=".")
    prepare_parser.add_argument("--execute", action="store_true")

    args = parser.parse_args()
    try:
        if args.cmd == "clone":
            url = validate_url(args.url)
            if not shutil.which("git"):
                raise RuntimeError("git is missing. In iSH try: apk update && apk add git")
            name = args.dir or Path(urlparse(url).path.rstrip("/").removesuffix(".git")).name
            destination = Path(name)
            if destination.exists():
                raise RuntimeError(f"{destination} already exists; refusing to overwrite it.")
            print(run(["git", "clone", "--", url, str(destination)]))
            print(f"Cloned to {destination.resolve()}\nNext: python3 vztool.py analyze {destination}")
        else:
            path = Path(args.path).expanduser()
            if not path.is_dir():
                raise ValueError(f"Not a directory: {path}")
            report = analyze(path)
            if args.cmd == "analyze":
                if args.json:
                    print(json.dumps(report, indent=2))
                else:
                    detected = ", ".join(item["kind"] for item in report["detected"]) or "no known manifest"
                    print(f"VZ-TOOL {VERSION} | {report['project']}\nCompatibility estimate: {report['compatibility_estimate']}\nDetected: {detected}")
                    print("Potential blockers:")
                    for blocker in report["blockers"]:
                        print(f" - {blocker['file']}: {blocker['reason']}")
                    if not report["blockers"]:
                        print(" - No known blocker patterns found (not proof of compatibility).")
                    for note in report["limitations"]:
                        print("NOTE:", note)
            else:
                choices = []
                if (path / "requirements.txt").exists():
                    choices.append(("Install Python dependencies", [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]))
                elif (path / "pyproject.toml").exists():
                    choices.append(("Install Python project", [sys.executable, "-m", "pip", "install", "."]))
                if (path / "package.json").exists():
                    choices.append(("Install Node dependencies", ["npm", "install"]))
                if (path / "Makefile").exists():
                    choices.append(("Build with make", ["make"]))
                if not choices:
                    print("No safe default command detected. Review README.md and project scripts manually.")
                    return 0
                for index, (label, command) in enumerate(choices, 1):
                    print(f"{index}. {label}: {' '.join(command)} (not run)")
                print("Review upstream scripts first; setup commands can execute third-party code.")
                if args.execute:
                    if len(choices) != 1:
                        raise RuntimeError("Multiple commands detected; refusing ambiguous execution.")
                    label, command = choices[0]
                    if input(f"Execute {label} in {path.resolve()}? [y/N] ").strip().lower() != "y":
                        print("Cancelled.")
                        return 0
                    print(run(command, cwd=path))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"vztool: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
