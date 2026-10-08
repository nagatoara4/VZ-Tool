# VZ-Tool

**GitHub project cloner and iSH compatibility assistant for iPhone.**

VZ-Tool helps iSH Shell users clone GitHub repositories, inspect project types, identify common Linux/system assumptions that may not work on iOS, and review likely setup commands before executing them.

> **Honest promise:** no tool can make every GitHub project run on iSH. iSH provides an Alpine Linux userland with kernel, privilege, architecture, and package limitations. VZ-Tool helps classify and prepare projects; it cannot turn iOS into an unrestricted Linux machine or grant real kernel root access.

## Features

- Clone GitHub repositories without overwriting an existing destination.
- Detect common Python, Node.js, Rust, Go, Ruby, PHP, Java, C/C++, and shell manifests.
- Flag common blockers: Docker/Podman, systemd, non-Alpine package managers, kernel modules, privileged networking, and hardware-specific dependencies.
- Generate human-readable or JSON compatibility reports.
- Suggest setup commands without running them automatically.
- Optional explicit setup execution with an interactive confirmation; refuses ambiguous multi-command execution.
- Python standard library only; no third-party Python packages required.

## Install in iSH

    apk update
    apk add python3 py3-pip git

    git clone https://github.com/nagatoara4/VZ-Tool.git
    cd VZ-Tool
    python3 vztool.py --help

## Commands

### Clone a repository

    python3 vztool.py clone https://github.com/OWNER/PROJECT.git
    python3 vztool.py clone https://github.com/OWNER/PROJECT.git --dir my-project

The destination must not already exist. VZ-Tool refuses to overwrite it. HTTPS cloning is restricted to github.com; SSH URLs are accepted if SSH is configured.

### Analyze a project

    cd PROJECT
    python3 /path/to/VZ-Tool/vztool.py analyze .
    python3 /path/to/VZ-Tool/vztool.py analyze . --json

Reports detected manifests, likely compatibility, blocker patterns, and platform limitations. This is a heuristic—not a sandbox, security audit, or guarantee of successful execution.

### Prepare setup

    python3 /path/to/VZ-Tool/vztool.py prepare .

This shows likely commands but does not execute them. To request execution for one unambiguous command:

    python3 /path/to/VZ-Tool/vztool.py prepare . --execute

VZ-Tool asks for confirmation. Review the project's README, dependency manifests, and scripts before approving commands from an unfamiliar repository.

## Compatibility reality check

| Project/dependency | Likely iSH situation |
|---|---|
| Pure Python | Often the best starting point if dependencies support the environment |
| Shell scripts | May work after checking shell and command assumptions |
| Node.js, Rust, Go, C/C++ | Depends on runtime/compiler/package availability and native dependencies |
| Docker/Podman | Container engine and kernel capabilities generally unavailable in iSH |
| systemd/services | Not provided like a conventional Linux host |
| kernel modules, mount, privileged firewall tools | iOS/iSH does not grant unrestricted host-kernel access |
| x86_64 prebuilt binaries | ARM64 hardware does not make x86_64 binaries runnable |
| Windows executables, Android APKs, desktop GUI applications | Not directly runnable as ordinary iSH commands |

## Security principles

- Clone/analyze does not execute project scripts.
- Existing directories are never overwritten by the clone command.
- Setup execution is opt-in and requires confirmation.
- Never put access tokens in clone URLs or commit secrets to Git.
- Review dependencies and install scripts before running them.

## What VZ-Tool cannot do

VZ-Tool cannot grant access outside iOS's app sandbox, provide unrestricted root, install a custom Linux kernel, emulate every CPU architecture, add Docker/systemd/kernel modules, or guarantee every repository can be ported. Some projects require manual code changes or a full Linux VM/host. iSH is useful for lightweight shell, Git, and Python experiments, but it is not equivalent to a full Linux VM.

## Tests

    python3 -m unittest -v

## License

MIT. See LICENSE.
