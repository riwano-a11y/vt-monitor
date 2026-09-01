#!/usr/bin/env python3
"""Add RDAP/ASN ownership details to ip_monitor.py Slack notifications."""

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if "def get_whois_info(" in text:
    print("Already patched.")
    raise SystemExit(0)

function = r'''
def get_whois_info(ip):
    """Return compact WHOIS/RDAP and ASN ownership details for Slack."""
    organization = "取得できませんでした"
    country = "不明"
    network_range = "不明"
    asn = "不明"
    asn_holder = "不明"

    try:
        response = requests.get(f"https://rdap.org/ip/{ip}", timeout=20)
        response.raise_for_status()
        data = response.json()
        organization = data.get("name") or data.get("handle") or organization
        country = data.get("country") or country
        start = data.get("startAddress")
        end = data.get("endAddress")
        if start and end:
            network_range = f"{start} - {end}"
    except requests.RequestException as error:
        print(f"WHOIS/RDAP error for {ip}: {error}", flush=True)

    try:
        response = requests.get(
            "https://stat.ripe.net/data/prefix-overview/data.json",
            params={"resource": ip},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        asns = data.get("asns") or []
        if asns:
            asn = "AS" + ", AS".join(str(value) for value in asns)
        asn_holder = data.get("holder") or asn_holder
    except requests.RequestException as error:
        print(f"ASN lookup error for {ip}: {error}", flush=True)

    return (
        f"WHOIS組織: {organization}\n"
        f"国: {country}\n"
        f"ASN: {asn}\n"
        f"ASN管理元: {asn_holder}\n"
        f"IP範囲: {network_range}"
    )


'''

main_match = re.search(r"(?m)^def main\(\):", text)
if not main_match:
    raise SystemExit("Could not locate main() in ip_monitor.py.")
text = text[:main_match.start()] + function + text[main_match.start():]

domains_pattern = re.compile(
    r'(?m)^(?P<indent>\s*)domains\s*=\s*get_resolutions\(ip\)\s*$'
)
text, domains_count = domains_pattern.subn(
    lambda match: (
        match.group(0)
        + "\n"
        + match.group("indent")
        + "whois_info = get_whois_info(ip)"
    ),
    text,
    count=1,
)
if domains_count != 1:
    raise SystemExit("Could not locate the get_resolutions(ip) call.")

ip_pattern = re.compile(r'(?m)^(?P<indent>\s*)f"IP: \{ip\}\\n"\s*$')
text, notification_count = ip_pattern.subn(
    lambda match: (
        match.group(0)
        + "\n"
        + match.group("indent")
        + 'f"{whois_info}\\n"'
    ),
    text,
)
if notification_count < 1:
    raise SystemExit("Could not locate Slack IP notification lines.")

compile(text, str(target), "exec")
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-whois-{timestamp}")
shutil.copy2(target, backup)
target.write_text(text, encoding="utf-8")

print(f"Patched: {target}")
print(f"Backup:  {backup}")
print(f"Updated notifications: {notification_count}")
