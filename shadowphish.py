#!/usr/bin/env python3
"""SHADOWPHISH LAB: offline URL triage and loopback-only awareness demo."""
from __future__ import annotations
import argparse, ipaddress, json, sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "is.gd", "cutt.ly", "rb.gy", "ow.ly", "buff.ly"}
TERMS = {"verify", "account", "secure", "login", "signin", "password", "confirm", "wallet", "update", "urgent", "support"}
WEIGHTS = {"http_without_tls": 10, "ip_literal_host": 25, "userinfo_present": 30,
           "punycode_host": 20, "many_subdomains": 10, "url_shortener": 15,
           "suspicious_terms": 10, "unusual_port": 10}

def finding(code, severity, message, weight):
    return {"id": code, "severity": severity, "message": message, "weight": weight}

def report(raw, findings):
    score = min(100, sum(x["weight"] for x in findings))
    return {"tool": "SHADOWPHISH LAB", "generated_at": datetime.now(timezone.utc).isoformat(),
            "input": raw, "risk_score": score,
            "risk_level": "high" if score >= 50 else "medium" if score >= 25 else "low",
            "finding_count": len(findings), "findings": findings,
            "note": "Heuristic triage only; no URL was fetched and no reputation service was queried."}

def analyze_url(value: str) -> dict:
    raw = value.strip()
    if not raw:
        return report(raw, [finding("empty_url", "high", "No URL was provided.", 100)])
    candidate = raw if "://" in raw else "https://" + raw
    try:
        parts = urlsplit(candidate)
        host, port = parts.hostname, parts.port
    except ValueError:
        return report(raw, [finding("malformed_url", "high", "Malformed authority or port data.", 40)])
    findings = []
    if parts.scheme.lower() not in {"http", "https"}:
        findings.append(finding("unsupported_scheme", "high", "Only HTTP and HTTPS are expected.", 25))
    if not host:
        findings.append(finding("missing_host", "high", "No hostname could be parsed.", 40))
        return report(raw, findings)
    host = host.lower().rstrip(".")
    if parts.scheme.lower() == "http":
        findings.append(finding("http_without_tls", "medium", "HTTP does not protect the connection with TLS.", WEIGHTS["http_without_tls"]))
    if parts.username is not None or parts.password is not None:
        findings.append(finding("userinfo_present", "high", "Text before @ can disguise the actual destination.", WEIGHTS["userinfo_present"]))
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    if is_ip:
        findings.append(finding("ip_literal_host", "high", "The URL uses an IP literal rather than a domain name.", WEIGHTS["ip_literal_host"]))
    if "xn--" in host:
        findings.append(finding("punycode_host", "high", "Hostname contains IDN punycode; inspect for lookalike characters.", WEIGHTS["punycode_host"]))
    if len(host.split(".")) >= 5:
        findings.append(finding("many_subdomains", "medium", "Many hostname labels can obscure the registered domain.", WEIGHTS["many_subdomains"]))
    if host in SHORTENERS:
        findings.append(finding("url_shortener", "medium", "A shortening service obscures the final destination.", WEIGHTS["url_shortener"]))
    searchable = (host + " " + parts.path.lower() + " " + parts.query.lower()).replace("-", " ")
    matched = sorted(term for term in TERMS if term in searchable)
    if matched:
        findings.append(finding("suspicious_terms", "low", "Account-related terms found: " + ", ".join(matched), WEIGHTS["suspicious_terms"]))
    if port is not None and port not in {80, 443}:
        findings.append(finding("unusual_port", "low", f"Non-standard web port {port}.", WEIGHTS["unusual_port"]))
    return report(raw, findings)

TRAINING_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>SHADOWPHISH LAB</title>
<style>body{font:16px system-ui;background:#0b1020;color:#f3f6ff;min-height:100vh;display:grid;place-items:center;margin:0;padding:20px}main{max-width:500px;background:#151d32;border:1px solid #293650;border-radius:20px;padding:28px}p{color:#aab7cf}label,input,button{display:block;width:100%;box-sizing:border-box;margin:12px 0}input,button{padding:12px;border-radius:9px;border:1px solid #293650}button{background:#74f0c0;font-weight:800}</style>
<main><small>LOCAL TRAINING SIMULATION</small><h1>Recognize the warning signs</h1>
<p>Generic security-awareness exercise. Never enter real credentials.</p>
<form method="post" action="/submit"><label>Demo username (optional)<input autocomplete="off" placeholder="Training-only example"></label>
<label>Demo password (leave blank)<input type="password" autocomplete="off" placeholder="Never use a real password"></label>
<button type="submit">Run awareness check</button></form>
<p>Privacy by design: form values are not read, logged, transmitted, or stored. Loopback only.</p></main>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in {"/", "/index.html"}:
            self.send_error(404); return
        body = TRAINING_HTML.encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path != "/submit":
            self.send_error(404); return
        # Intentionally do not read the request body or access Content-Length.
        body = b"<!doctype html><meta charset=utf-8><title>Exercise complete</title><main style='font:16px system-ui;max-width:640px;margin:3rem auto'><h1>Exercise complete</h1><p>No form values were collected. Verify domains independently and report suspicious messages.</p><a href='/'>Return</a></main>"
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, fmt, *args):
        return

def run_training_server(host, port):
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("Safety guard: bind only to loopback (127.0.0.1, ::1, localhost).")
    server = HTTPServer((host, port), Handler)
    print(f"[SHADOWPHISH] Awareness exercise: http://{host}:{port}/")
    print("[SHADOWPHISH] Loopback only; submitted values are ignored. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SHADOWPHISH] Stopping.")
    finally:
        server.server_close()

def main(argv=None):
    parser = argparse.ArgumentParser(prog="shadowphish", description="Defensive URL triage and local awareness simulation.")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("scan-url", help="Analyze one URL without fetching it.")
    one.add_argument("url"); one.add_argument("--json", dest="json_path")
    batch = sub.add_parser("scan-file", help="Analyze one URL per line.")
    batch.add_argument("path", type=Path); batch.add_argument("--json", dest="json_path", required=True)
    serve = sub.add_parser("serve-training", help="Start the loopback awareness page.")
    serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    try:
        if args.command == "scan-url":
            result = json.dumps(analyze_url(args.url), indent=2, ensure_ascii=False)
            if args.json_path: Path(args.json_path).write_text(result + "\n", encoding="utf-8")
            print(result); return 0
        if args.command == "scan-file":
            urls = [x.strip() for x in args.path.read_text(encoding="utf-8").splitlines()
                    if x.strip() and not x.lstrip().startswith("#")]
            payload = {"tool": "SHADOWPHISH LAB", "count": len(urls), "reports": [analyze_url(x) for x in urls]}
            Path(args.json_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"[SHADOWPHISH] Analyzed {len(urls)} URL(s); report saved to {args.json_path}"); return 0
        if args.command == "serve-training":
            if not 1 <= args.port <= 65535: parser.error("--port must be between 1 and 65535")
            run_training_server(args.host, args.port); return 0
    except (OSError, ValueError) as exc:
        print(f"[error] {exc}", file=sys.stderr); return 2
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
