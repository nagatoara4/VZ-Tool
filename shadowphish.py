#!/usr/bin/env python3
"""SHADOWPHISH LAB v2: offline URL/email triage and loopback-only awareness demo."""
from __future__ import annotations
import argparse, csv, ipaddress, json, sys
from datetime import datetime, timezone
from email.parser import Parser
from pathlib import Path
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, HTTPServer

SHORTENERS = {"bit.ly","t.co","tinyurl.com","is.gd","cutt.ly","rb.gy","ow.ly","buff.ly"}
TERMS = {"verify","account","secure","login","signin","password","confirm","wallet","update","urgent","support"}
WEIGHTS = {"http_without_tls":10,"ip_literal_host":25,"userinfo_present":30,"punycode_host":20,
           "many_subdomains":10,"url_shortener":15,"suspicious_terms":10,"unusual_port":10}

def finding(code, severity, message, weight):
    return {"id":code,"severity":severity,"message":message,"weight":weight}

def make_report(raw, findings, kind):
    score = min(100, sum(x["weight"] for x in findings))
    return {"tool":"SHADOWPHISH LAB","version":"2.0.0","generated_at":datetime.now(timezone.utc).isoformat(),
            "input_type":kind,"input":raw,"risk_score":score,
            "risk_level":"high" if score>=50 else "medium" if score>=25 else "low",
            "finding_count":len(findings),"findings":findings,
            "note":"Heuristic triage only. No target was contacted; no reputation lookup was performed."}

def analyze_url(value):
    raw = value.strip()
    if not raw: return make_report(raw,[finding("empty_url","high","No URL was provided.",100)],"url")
    try:
        parts = urlsplit(raw if "://" in raw else "https://" + raw)
        host, port = parts.hostname, parts.port
    except ValueError:
        return make_report(raw,[finding("malformed_url","high","Malformed authority or port data.",40)],"url")
    f=[]; scheme=parts.scheme.lower()
    if scheme not in {"http","https"}: f.append(finding("unsupported_scheme","high","Only HTTP and HTTPS are expected.",25))
    if not host: return make_report(raw,f+[finding("missing_host","high","No hostname could be parsed.",40)],"url")
    host=host.lower().rstrip(".")
    if scheme=="http": f.append(finding("http_without_tls","medium","HTTP does not protect the connection with TLS.",10))
    if parts.username is not None or parts.password is not None: f.append(finding("userinfo_present","high","Text before @ can disguise the destination.",30))
    try: ipaddress.ip_address(host); is_ip=True
    except ValueError: is_ip=False
    if is_ip: f.append(finding("ip_literal_host","high","The URL uses an IP literal rather than a domain name.",25))
    if "xn--" in host: f.append(finding("punycode_host","high","Hostname contains IDN punycode; inspect for lookalikes.",20))
    if len(host.split("."))>=5: f.append(finding("many_subdomains","medium","Many hostname labels can obscure the registered domain.",10))
    if host in SHORTENERS: f.append(finding("url_shortener","medium","A shortening service obscures the final destination.",15))
    matched=sorted(t for t in TERMS if t in (host+" "+parts.path.lower()+" "+parts.query.lower()).replace("-"," "))
    if matched: f.append(finding("suspicious_terms","low","Account-related terms found: "+", ".join(matched),10))
    if port is not None and port not in {80,443}: f.append(finding("unusual_port","low",f"Non-standard web port {port}.",10))
    return make_report(raw,f,"url")

def address_domain(value):
    value=(value or "").strip()
    if "<" in value and ">" in value: value=value.rsplit("<",1)[1].split(">",1)[0]
    return value.rsplit("@",1)[1].strip().strip(">").lower().rstrip(".") if "@" in value else ""

def analyze_email_headers(raw_headers):
    """Analyze locally supplied headers only; no body parsing or network access."""
    msg=Parser().parsestr(raw_headers,headersonly=True); f=[]
    fd=address_domain(msg.get("From","")); rd=address_domain(msg.get("Reply-To","")); ret=address_domain(msg.get("Return-Path",""))
    if not msg.get("From"): f.append(finding("missing_from","medium","No From header was found.",15))
    if msg.get("Reply-To") and fd and rd and rd!=fd:
        f.append(finding("reply_to_domain_mismatch","high",f"Reply-To domain ({rd}) differs from From domain ({fd}).",25))
    if ret and fd and ret!=fd:
        f.append(finding("return_path_domain_mismatch","medium",f"Return-Path domain ({ret}) differs from From domain ({fd}); legitimate senders can also do this.",10))
    auth=" ".join(msg.get_all("Authentication-Results",[])).lower()
    if not auth: f.append(finding("missing_auth_results","low","No Authentication-Results header found; forwarding or header removal may explain this.",5))
    else:
        for method in ("spf","dkim","dmarc"):
            if method+"=fail" in auth or method+"=softfail" in auth:
                f.append(finding(method+"_failure","high",f"Authentication-Results indicates {method.upper()} failure.",20))
            elif method+"=pass" not in auth:
                f.append(finding(method+"_not_pass","low",f"No explicit {method.upper()} pass result was found.",5))
    if not msg.get("Date"): f.append(finding("missing_date","low","No Date header was found.",3))
    return make_report(raw_headers[:1200],f,"email_headers")

TRAINING_HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SHADOWPHISH LAB</title><style>body{font:16px system-ui;background:#0b1020;color:#f3f6ff;min-height:100vh;display:grid;place-items:center;margin:0;padding:20px}main{max-width:500px;background:#151d32;border:1px solid #293650;border-radius:20px;padding:28px}p{color:#aab7cf}label,input,button{display:block;width:100%;box-sizing:border-box;margin:12px 0}input,button{padding:12px;border-radius:9px;border:1px solid #293650}button{background:#74f0c0;font-weight:800}</style><main><small>LOCAL TRAINING SIMULATION</small><h1>Recognize the warning signs</h1><p>Generic awareness exercise. Never enter real credentials.</p><form method="post" action="/submit"><label>Demo username (optional)<input autocomplete="off" placeholder="Training-only example"></label><label>Demo password (leave blank)<input type="password" autocomplete="off" placeholder="Never use a real password"></label><button type="submit">Run awareness check</button></form><p>Privacy by design: form values are not read, logged, transmitted, or stored. Loopback only.</p></main>"""

class TrainingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in {"/","/index.html"}: self.send_error(404); return
        body=TRAINING_HTML.encode("utf-8"); self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        if self.path!="/submit": self.send_error(404); return
        # Never read the request body or access Content-Length.
        body=b"<!doctype html><meta charset=utf-8><title>Exercise complete</title><main style='font:16px system-ui;max-width:640px;margin:3rem auto'><h1>Exercise complete</h1><p>No form values were collected. Verify domains independently and report suspicious messages.</p><a href='/'>Return</a></main>"
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store")
        self.end_headers(); self.wfile.write(body)
    def log_message(self,fmt,*args): return

def run_training_server(host,port):
    if host not in {"127.0.0.1","::1","localhost"}: raise ValueError("Safety guard: bind only to loopback.")
    server=HTTPServer((host,port),TrainingHandler)
    print(f"[SHADOWPHISH] Awareness exercise: http://{host}:{port}/")
    print("[SHADOWPHISH] Loopback only; submitted values are ignored. Ctrl+C to stop.")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\n[SHADOWPHISH] Stopping.")
    finally: server.server_close()

def write_reports(reports,path,fmt):
    path=Path(path)
    if fmt=="json":
        payload=reports[0] if len(reports)==1 else {"tool":"SHADOWPHISH LAB","count":len(reports),"reports":reports}
        path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return
    with path.open("w",newline="",encoding="utf-8") as handle:
        fields=["input_type","input","risk_score","risk_level","finding_count","finding_ids","generated_at"]
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
        for item in reports:
            row={k:item.get(k,"") for k in fields}; row["finding_ids"]=";".join(x["id"] for x in item["findings"]); writer.writerow(row)

def main(argv=None):
    p=argparse.ArgumentParser(prog="shadowphish",description="Offline URL/email triage and local awareness simulation.")
    sub=p.add_subparsers(dest="command",required=True)
    one=sub.add_parser("scan-url",help="Analyze one URL without fetching it."); one.add_argument("url"); one.add_argument("--json",dest="json_path")
    batch=sub.add_parser("scan-file",help="Analyze one URL per line."); batch.add_argument("path",type=Path); batch.add_argument("--json",dest="json_path"); batch.add_argument("--csv",dest="csv_path")
    mail=sub.add_parser("scan-headers",help="Analyze saved email headers offline."); mail.add_argument("path",type=Path); mail.add_argument("--json",dest="json_path"); mail.add_argument("--csv",dest="csv_path")
    serve=sub.add_parser("serve-training",help="Start loopback-only awareness page."); serve.add_argument("--host",default="127.0.0.1"); serve.add_argument("--port",type=int,default=8080)
    a=p.parse_args(argv)
    try:
        if a.command=="scan-url":
            r=analyze_url(a.url)
            if a.json_path: write_reports([r],a.json_path,"json")
            print(json.dumps(r,indent=2,ensure_ascii=False)); return 0
        if a.command in {"scan-file","scan-headers"}:
            if a.command=="scan-file":
                lines=[x.strip() for x in a.path.read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#")]
                reports=[analyze_url(x) for x in lines]
            else: reports=[analyze_email_headers(a.path.read_text(encoding="utf-8"))]
            fmt="csv" if a.csv_path else "json"; output=a.csv_path or a.json_path
            if output:
                write_reports(reports,output,fmt); print(f"[SHADOWPHISH] {len(reports)} report(s) written to {output}")
            else: print(json.dumps(reports[0] if len(reports)==1 else {"count":len(reports),"reports":reports},indent=2,ensure_ascii=False))
            return 0
        if a.command=="serve-training":
            if not 1<=a.port<=65535: p.error("--port must be between 1 and 65535")
            run_training_server(a.host,a.port); return 0
    except (OSError,ValueError) as exc: print(f"[error] {exc}",file=sys.stderr); return 2
    return 1

if __name__=="__main__": raise SystemExit(main())
