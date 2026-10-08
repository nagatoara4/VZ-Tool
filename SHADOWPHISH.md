# SHADOWPHISH LAB v2.0
### Offline phishing triage for Kali Linux

**Defensive use only.** SHADOWPHISH does not clone login pages, collect credentials, send messages, follow redirects, or contact URLs. Its awareness server is loopback-only and ignores submitted form bodies.

## Features
- URL heuristics: HTTP, embedded user-info, IP literals, punycode, deep subdomains, common shorteners, suspicious terms, non-standard ports.
- Email-header triage: From/Reply-To mismatch, Return-Path mismatch, and SPF/DKIM/DMARC outcomes in supplied Authentication-Results headers.
- JSON and CSV reports, including batch URL analysis.
- Local awareness page restricted to loopback.
- Standard-library only; unit tests included.

## Install on Kali
~~~bash
sudo apt update
sudo apt install -y git python3 python3-venv
git clone https://github.com/nagatoara4/VZ-Tool.git
cd VZ-Tool
python3 -m venv .venv
source .venv/bin/activate
~~~

## Usage
~~~bash
python3 shadowphish.py scan-url 'https://example.org/account/verify'
python3 shadowphish.py scan-url 'http://192.0.2.1/login' --json one.json
python3 shadowphish.py scan-file urls.txt --json batch.json
python3 shadowphish.py scan-file urls.txt --csv batch.csv
python3 shadowphish.py scan-headers sample-headers.txt
python3 shadowphish.py scan-headers sample-headers.txt --json headers.json
python3 shadowphish.py scan-headers sample-headers.txt --csv headers.csv
python3 shadowphish.py serve-training
~~~

Open http://127.0.0.1:8080/ on the same machine for the local awareness simulation.

The sample-headers.txt file should contain raw header lines such as From, Reply-To, Return-Path, Date, and Authentication-Results. The tool analyzes only locally supplied header text. Missing authentication results are not proof of maliciousness. Header results can be forged when copied from an untrusted source; trust mail authentication data only when added by your own mail infrastructure.

## Tests
~~~bash
python3 -m unittest -v test_shadowphish.py
~~~

## Scoring caveats
The score is a transparent heuristic, not a probability or verdict. It can produce false positives and miss sophisticated attacks. Inspect the real registered domain, message context, and trusted security telemetry before making decisions.

## Privacy and safety
- URL analysis is local string parsing; no DNS, HTTP, redirect, or reputation lookups.
- Header analysis is offline and does not inspect message bodies.
- The training server binds only to loopback and ignores submitted form values.
- Do not enter real credentials into the training page.
