# SHADOWPHISH LAB
### Defensive phishing triage + privacy-first awareness simulation for Kali Linux

<p align="center">
  <strong>Inspect suspicious URLs locally. Run a safe awareness exercise. Export JSON reports.</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="Dependencies" src="https://img.shields.io/badge/dependencies-standard%20library-2ea44f">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Kali%20Linux%20%7C%20Linux-black">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
</p>

SHADOWPHISH LAB is an auditable security-awareness toolkit for students, analysts, and blue teams. It combines a local URL heuristic analyzer with a loopback-only training page. It does not fetch submitted URLs, harvest credentials, or transmit form data.

> [!IMPORTANT]
> This is a defensive training project, not a credential-harvesting framework. The training server accepts only loopback bind addresses, ignores submitted form bodies, and suppresses access logs. Never enter real credentials into a training page.

## Features

- **Offline URL triage:** no requests to target hosts or reputation APIs.
- **Explainable findings:** HTTP, embedded user-info, IP-literal hosts, punycode, deep subdomains, known shorteners, suspicious terms, and non-standard ports.
- **JSON reporting:** single-URL and batch reports.
- **Local awareness exercise:** generic training page on 127.0.0.1 by default.
- **Privacy by design:** POST body is never read; submitted values are not logged or saved.
- **No third-party dependencies:** Python standard library only.
- **Unit tests:** key detection logic and loopback guard.

## Project layout

~~~text
VZ-Tool/
├── shadowphish.py
├── test_shadowphish.py
├── requirements.txt
├── LICENSE
└── README.md
~~~

## Requirements

- Kali Linux or another Linux distribution
- Python 3.10+
- Terminal access

Check Python:

~~~bash
python3 --version
~~~

## Installation

~~~bash
git clone https://github.com/nagatoara4/VZ-Tool.git
cd VZ-Tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
~~~

No external packages are needed. On a minimal Kali installation:

~~~bash
sudo apt update
sudo apt install -y python3 python3-venv
~~~

## Quick start

### 1. Analyze one URL

~~~bash
python3 shadowphish.py scan-url 'https://example.org/account/verify'
~~~

The JSON result contains a score, risk band, timestamp, findings, and a note that the URL was not fetched.

Save a report:

~~~bash
python3 shadowphish.py scan-url 'http://192.0.2.1/login' --json report.json
cat report.json
~~~

### 2. Batch analysis

Create a file with one URL per line. Blank lines and lines beginning with # are ignored.

~~~bash
cat > urls.txt <<'EOF'
https://example.org/
http://192.0.2.1/login
https://trusted.example@evil.example/
https://xn--example-ova.test/
EOF

python3 shadowphish.py scan-file urls.txt --json batch-report.json
~~~

### 3. Run the awareness exercise

~~~bash
python3 shadowphish.py serve-training
~~~

Open **http://127.0.0.1:8080/** on the same machine. Stop with Ctrl+C.

The server rejects non-loopback addresses such as 0.0.0.0. The page is clearly labeled as a training simulation. The form has no field names; the server does not read the request body, and default access logging is disabled.

## Run tests

~~~bash
python3 -m unittest -v test_shadowphish.py
~~~

## How scoring works

The score is a heuristic triage indicator, not a probability that a URL is malicious.

| Signal | Reason | Weight |
|---|---|---:|
| HTTP scheme | No TLS protection | 10 |
| IP-literal host | Destination is an IP address | 25 |
| User-info field | Text before @ can disguise the host | 30 |
| Punycode hostname | Possible IDN lookalike needs inspection | 20 |
| Many hostname labels | Domain boundary may be confusing | 10 |
| Known URL shortener | Final destination is obscured | 15 |
| Suspicious terms | Urgent account-related wording | 10 |
| Non-standard port | Web service uses an unusual port | 10 |

Weights are added and capped at 100. Risk labels are low (0–24), medium (25–49), and high (50–100). Signals can produce false positives or miss sophisticated threats. Inspect the registered domain, context, sender, redirects, and independent threat intelligence where appropriate.

## Design and safety notes

- **No URL fetching:** URL parsing and string heuristics only.
- **No credential collection:** the training endpoint ignores submitted form values.
- **Loopback-only:** public/interface bind addresses are rejected.
- **No stealth, persistence, evasion, or third-party impersonation.**
- **No guaranteed verdict:** not a replacement for a browser, sandbox, mail gateway, or threat-intelligence platform.

## Troubleshooting

**Python is missing:** install it with the Kali command above.

**Port already in use:** choose another local port, for example:

~~~bash
python3 shadowphish.py serve-training --port 8090
~~~

**Loopback safety guard:** use the default 127.0.0.1 host; the restriction is intentional.

**A URL is flagged but seems legitimate:** review each finding. The tool reports signals, not a definitive malicious verdict.

## Roadmap

- CSV report export
- Configurable local allow/deny patterns
- Mail-header triage helpers
- SARIF-style export for pipeline integration
- Additional malformed and internationalized URL tests

## Responsible use

Use this project for awareness training, defensive analysis, and controlled lab learning. Do not use it to collect credentials, impersonate third-party services, or target people without permission.

## License

MIT — see LICENSE.
