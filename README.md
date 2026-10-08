# VZ-Tool

**A GitHub project cloner and compatibility assistant for iSH on iPhone.**

VZ-Tool helps bring GitHub projects into your iSH workspace, inspect their structure, identify common platform blockers, and review likely setup steps before running them. It is a practical mobile-development helper—not a promise that every repository will run.

> **Important:** standard iSH provides an Alpine Linux userland with an emulated 32-bit x86 environment. It is not native ARM64 Linux, and iOS sandboxing limits kernel and privileged features. See the [official iSH project](https://github.com/ish-app/ish).

## Features

- Clone GitHub repositories over HTTPS or SSH.
- Select a branch/tag, shallow-clone with a depth, and optionally fetch submodules.
- Detect common Python, Node.js, Rust, Go, Ruby, PHP, Java, C/C++, and shell manifests.
- Flag common platform blockers such as Docker, systemd, non-Alpine package managers, kernel modules, and privileged networking.
- Identify a small set of risky installer patterns for manual review.
- Print readable reports or machine-readable JSON.
- Check local command availability with `doctor`.
- Suggest setup commands without executing them by default.
- Use only the Python standard library; Git is required for cloning.

## Install in iSH

```sh
apk update
apk add python3 git
git clone https://github.com/nagatoara4/VZ-Tool.git
cd VZ-Tool
python3 vztool.py --help
```

## Quick start

### Clone a repository

```sh
python3 vztool.py clone https://github.com/OWNER/PROJECT.git
python3 vztool.py clone https://github.com/OWNER/PROJECT.git --dir my-project
python3 vztool.py clone https://github.com/OWNER/PROJECT.git --branch main --depth 1
python3 vztool.py clone https://github.com/OWNER/PROJECT.git --recursive
```

The destination must not already exist; VZ-Tool refuses to overwrite it. HTTPS and SSH repository URLs must point to GitHub. SSH cloning requires working SSH configuration. For private repositories, configure Git authentication securely—never embed tokens in URLs or source code.

### Check the environment

```sh
python3 vztool.py doctor
```

This read-only check reports available commands and explains relevant iSH constraints. It does not install packages or change settings.

### Analyze a project

```sh
python3 vztool.py analyze my-project
python3 vztool.py analyze my-project --json
```

Analysis is local and does not execute project code. It reports detected manifests, likely compatibility concerns, and selected installer patterns that deserve manual review.

### Review setup suggestions

```sh
python3 vztool.py prepare my-project
```

Suggestions are displayed without execution. To request execution of one unambiguous detected command:

```sh
python3 vztool.py prepare my-project --execute
```

VZ-Tool asks for interactive confirmation and refuses to choose automatically when multiple candidate commands are detected. Review the repository's README, dependency manifests, and scripts before approving commands from an unfamiliar project.

## Compatibility guide

| Project/dependency | Practical expectation |
|---|---|
| Pure Python | Often a good starting point if dependencies support the environment |
| Shell scripts | Depends on shell features and installed commands |
| Node.js, Rust, Go, C/C++ | Depends on available runtimes, compilers, packages, and native dependencies |
| Docker/Podman and systemd | Generally unavailable as on a conventional Linux host |
| Kernel modules, privileged networking, mounts | Require capabilities standard iSH does not provide |
| Prebuilt ARM64 or x86_64 Linux binaries | May not match standard iSH's emulated x86 32-bit environment |
| Desktop GUI apps, Windows executables, Android APKs | Not directly runnable as ordinary iSH commands |

Compatibility findings are heuristics, not guarantees. Some projects require manual porting or a full Linux VM/remote host.

## Security model

- Cloning and analysis do not execute project scripts.
- Existing clone destinations are never overwritten.
- Setup commands are shown before any optional execution.
- Execution requires an explicit flag and interactive confirmation.
- Pattern matches are review signals, not proof of malicious behavior or safety.
- Keep Git credentials and API tokens out of command history, logs, source files, and commits.
- Dependency installation can execute third-party code; inspect it first.

## Tests

```sh
python3 -m unittest -v test_vztool.py
```

GitHub Actions runs the unit tests on pushes and pull requests.

## Scope and limitations

VZ-Tool is a **cloner and triage assistant**, not a universal code converter, emulator, sandbox, or security certification tool. It cannot grant unrestricted root, escape iOS sandboxing, add kernel features, make incompatible binaries executable, or guarantee that arbitrary repositories will run.

## License

MIT. See [LICENSE](LICENSE).
