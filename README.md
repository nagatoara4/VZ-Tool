# VZ-Tool

**A GitHub project cloner and compatibility assistant for iSH on iPhone.**

VZ-Tool helps you bring public GitHub projects into your iSH workspace, inspect their structure, identify common platform blockers, and review likely setup steps before running them.

It is designed for practical mobile development—not to promise impossible compatibility.

> **Platform note:** the standard iSH app uses an Alpine Linux userland and emulates a 32-bit x86 Linux environment. An ARM64 iPhone does not mean standard iSH runs native ARM64 Linux binaries. iSH is also constrained by iOS sandboxing and does not provide unrestricted host-root or kernel access. See the [official iSH project](https://github.com/ish-app/ish).

## Highlights

- **GitHub cloning:** HTTPS and SSH GitHub repository URLs, optional branch selection, shallow clones, and recursive submodules.
- **Project inspection:** detect common manifests for Python, Node.js, Rust, Go, Ruby, PHP, Java, C/C++, and shell projects.
- **Compatibility triage:** flag common assumptions such as Docker, systemd, non-Alpine package managers, kernel modules, privileged networking, and architecture-specific dependencies.
- **Supply-chain warnings:** identify a small set of risky installation patterns for manual review; findings are indicators, not proof of malicious behavior.
- **Machine-readable reports:** export analysis as JSON for scripts or further review.
- **Conservative setup assistance:** print likely setup commands first. Execution is opt-in, confirmed interactively, and blocked when multiple candidate commands make the choice ambiguous.
- **No Python dependencies:** VZ-Tool uses the Python standard library. Git is required for cloning.

## Install

In iSH, install the available packages:

```sh
apk update
apk add python3 git
```

Clone VZ-Tool and open its directory:

```sh
git clone https://github.com/nagatoara4/VZ-Tool.git
cd VZ-Tool
python3 vztool.py --help
```

## Quick start

### 1. Clone a project

```sh
python3 vztool.py clone https://github.com/OWNER/PROJECT.git
```

Choose a directory name, branch, or shallow clone when needed:

```sh
python3 vztool.py clone https://github.com/OWNER/PROJECT.git --dir my-project
python3 vztool.py clone https://github.com/OWNER/PROJECT.git --branch main
python3 vztool.py clone https://github.com/OWNER/PROJECT.git --depth 1
python3 vztool.py clone https://github.com/OWNER/PROJECT.git --recursive
```

VZ-Tool refuses to clone into an existing destination. HTTPS and SSH URLs must point to GitHub; SSH cloning requires a working SSH key/configuration. Private repositories require credentials already configured with Git—never paste tokens into URLs or source files.

### 2. Check the environment

```sh
python3 vztool.py doctor
```

This reports available local commands and explains relevant iSH constraints. It does not install packages or change system settings.

### 3. Analyze a project

```sh
python3 vztool.py analyze my-project
python3 vztool.py analyze my-project --json
```

The report includes detected manifests, platform details, likely compatibility concerns, and review flags. Analysis is local and does not execute the project's scripts.

### 4. Review setup suggestions

```sh
python3 vztool.py prepare my-project
```

Commands are suggestions only. To request execution for a single unambiguous detected command:

```sh
python3 vztool.py prepare my-project --execute
```

VZ-Tool asks for interactive confirmation. It refuses to choose automatically if several setup commands are detected. Review the project's README, dependency manifests, and scripts before approving any third-party command.

## What may work in iSH?

| Project type or dependency | Practical expectation |
|---|---|
| Pure Python | Often a good starting point if all dependencies support the environment |
| Shell scripts | Depends on shell features and installed commands |
| Node.js, Rust, Go, C/C++ | Depends on package availability, compiler/runtime support, and native dependencies |
| Docker/Podman and systemd | Usually not available as they are on a conventional Linux host |
| Kernel modules, privileged networking, mounts | Require capabilities standard iSH does not provide |
| Prebuilt ARM64 or x86_64 Linux binaries | May not match standard iSH's emulated x86 32-bit environment |
| Desktop GUI applications, Windows executables, Android APKs | Not directly runnable as ordinary iSH commands |

A compatibility score cannot be inferred reliably from a repository name alone. Some projects need manual porting; others require a full Linux VM or remote Linux host.

## Security model

- Cloning and analysis do not execute project code.
- Existing destination paths are not overwritten by the clone command.
- Setup commands are displayed before execution.
- Execution requires an explicit flag and interactive confirmation.
- URL analysis is heuristic; it does not establish that a project is safe.
- Keep Git credentials and API tokens out of command history, logs, source files, and commits.
- Treat unfamiliar dependency install scripts as executable third-party code.

## Tests

Run the test suite with Python's built-in test runner:

```sh
python3 -m unittest -v
```

The repository also includes a GitHub Actions workflow that runs the unit tests on pushes and pull requests.

## Scope and limitations

VZ-Tool is a **cloner and triage assistant**, not a universal project converter, emulator, sandbox, or security certification tool. It cannot grant unrestricted root, escape iOS app sandboxing, add kernel features, make incompatible binaries executable, or guarantee that arbitrary repositories will run.

## License

MIT. See [LICENSE](LICENSE).
