#!/usr/bin/env python3
"""Keep only company, phone and address in WHOIS Slack details."""

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if 'f"会社名: {organization}' in text:
    print("Already patched.")
    raise SystemExit(0)
if "def get_whois_info(" not in text:
    raise SystemExit("WHOIS patch is not installed.")

asn_block = re.compile(
    r'''\n    try:\n        response = requests\.get\(\n            "https://stat\.ripe\.net/data/prefix-overview/data\.json",.*?\n    except requests\.RequestException as error:\n        print\(f"ASN lookup error for \{ip\}: \{error\}", flush=True\)\n''',
    re.DOTALL,
)
text, removed = asn_block.subn("\n", text, count=1)
if removed != 1:
    raise SystemExit("Could not locate ASN lookup block.")

output_block = re.compile(
    r'''    return \(\n        f"WHOIS組織: \{organization\}\\n"\n        f"WHOIS電話番号: \{phone\}\\n"\n        f"WHOIS住所: \{address\}\\n"\n        f"国: \{country\}\\n"\n        f"ASN: \{asn\}\\n"\n        f"ASN管理元: \{asn_holder\}\\n"\n        f"IP範囲: \{network_range\}"\n    \)'''
)
replacement = '''    return (
        f"会社名: {organization}\\n"
        f"電話番号: {phone}\\n"
        f"住所: {address}"
    )'''
text, changed = output_block.subn(lambda _: replacement, text, count=1)
if changed != 1:
    raise SystemExit("Could not locate WHOIS Slack output block.")

compile(text, str(target), "exec")
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-whois-compact-{timestamp}")
shutil.copy2(target, backup)
target.write_text(text, encoding="utf-8")

print(f"Patched: {target}")
print(f"Backup:  {backup}")
print("WHOIS notification now contains company, phone and address only.")
