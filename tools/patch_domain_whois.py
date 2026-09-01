#!/usr/bin/env python3
"""Use domain WHOIS for company, phone and address Slack fields."""

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if "def get_domain_whois_info(" in text:
    print("Already patched.")
    raise SystemExit(0)

function = r'''
def get_domain_whois_info(domain, ip):
    """Look up public registrant contact details for a domain."""
    try:
        response = requests.post(
            "https://tech-unlimited.com/proc/whois.php",
            data={"params": f"target_domain={domain}"},
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DomainWhoisMonitor/1.0)",
                "Referer": "https://tech-unlimited.com/whois.html",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        raw = str(payload.get("data") or "")

        def field(*labels):
            for label in labels:
                match = re.search(
                    rf"^\[{re.escape(label)}\]\s+(.+?)\s*$",
                    raw,
                    re.MULTILINE,
                )
                if match and match.group(1).strip():
                    return match.group(1).strip()
            return ""

        company = field("登録者名", "Registrant") or "記載なし"
        raw_phone = field("電話番号", "Phone")
        phone = "".join(char for char in raw_phone if char.isdigit()) or "記載なし"
        address = field("住所", "Postal Address") or "記載なし"

        if company != "記載なし" or phone != "記載なし" or address != "記載なし":
            return (
                f"会社名: {company}\n"
                f"電話番号: {phone}\n"
                f"住所: {address}"
            )
    except (requests.RequestException, ValueError) as error:
        print(f"Domain WHOIS error for {domain}: {error}", flush=True)

    return get_whois_info(ip)


'''

main_match = re.search(r"(?m)^def main\(\):", text)
if not main_match:
    raise SystemExit("Could not locate main() in ip_monitor.py.")
text = text[:main_match.start()] + function + text[main_match.start():]

text, removed = re.subn(
    r'(?m)^\s*whois_info\s*=\s*get_whois_info\(ip\)\s*\n',
    "",
    text,
    count=1,
)
if removed != 1:
    raise SystemExit("Could not locate the existing IP WHOIS call.")

live_pattern = re.compile(r'(?m)^(?P<indent>\s*)if live_url:\s*$')
text, live_count = live_pattern.subn(
    lambda match: (
        match.group(0)
        + "\n"
        + match.group("indent")
        + "    whois_info = get_domain_whois_info(domain, ip)"
    ),
    text,
    count=1,
)

candidate_pattern = re.compile(
    r'(?m)^(?P<indent>\s*)if domain not in state\["candidate_seen"\]\[ip\]:\s*$'
)
text, candidate_count = candidate_pattern.subn(
    lambda match: (
        match.group(0)
        + "\n"
        + match.group("indent")
        + "    whois_info = get_domain_whois_info(domain, ip)"
    ),
    text,
    count=1,
)
if live_count != 1 or candidate_count != 1:
    raise SystemExit("Could not locate both Slack notification branches.")

compile(text, str(target), "exec")
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-domain-whois-{timestamp}")
shutil.copy2(target, backup)
target.write_text(text, encoding="utf-8")

print(f"Patched: {target}")
print(f"Backup:  {backup}")
print("Domain WHOIS lookup is now used for Slack contact details.")
