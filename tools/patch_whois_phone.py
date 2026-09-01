#!/usr/bin/env python3
"""Add public RDAP contact phone numbers to WHOIS Slack details."""

from datetime import datetime
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if "WHOIS電話番号:" in text:
    print("Already patched.")
    raise SystemExit(0)
if "def get_whois_info(" not in text:
    raise SystemExit("WHOIS patch is not installed yet.")

old = '    asn_holder = "不明"\n\n    try:\n'
new = '    asn_holder = "不明"\n    phone = "記載なし"\n\n    try:\n'
if old not in text:
    raise SystemExit("Could not locate WHOIS defaults.")
text = text.replace(old, new, 1)

old = '''        country = data.get("country") or country
        start = data.get("startAddress")
'''
new = '''        country = data.get("country") or country
        for entity in data.get("entities") or []:
            vcard = entity.get("vcardArray") or []
            fields = vcard[1] if len(vcard) > 1 and isinstance(vcard[1], list) else []
            for field in fields:
                if len(field) >= 4 and field[0] == "tel" and field[3]:
                    phone = str(field[3]).replace("tel:", "").strip()
                    break
            if phone != "記載なし":
                break
        start = data.get("startAddress")
'''
if old not in text:
    raise SystemExit("Could not locate RDAP response handling.")
text = text.replace(old, new, 1)

old = '        f"WHOIS組織: {organization}\\n"\n        f"国: {country}\\n"\n'
new = (
    '        f"WHOIS組織: {organization}\\n"\n'
    '        f"WHOIS電話番号: {phone}\\n"\n'
    '        f"国: {country}\\n"\n'
)
if old not in text:
    raise SystemExit("Could not locate WHOIS Slack output.")
text = text.replace(old, new, 1)

compile(text, str(target), "exec")
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-phone-{timestamp}")
shutil.copy2(target, backup)
target.write_text(text, encoding="utf-8")

print(f"Patched: {target}")
print(f"Backup:  {backup}")
print("WHOIS phone field added.")
