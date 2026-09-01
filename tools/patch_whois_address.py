#!/usr/bin/env python3
"""Add public RDAP contact addresses to WHOIS Slack details."""

from datetime import datetime
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if "WHOIS住所:" in text:
    print("Already patched.")
    raise SystemExit(0)
if "WHOIS電話番号:" not in text:
    raise SystemExit("WHOIS phone patch is not installed yet.")

old = '    phone = "記載なし"\n\n    try:\n'
new = '    phone = "記載なし"\n    address = "記載なし"\n\n    try:\n'
if old not in text:
    raise SystemExit("Could not locate WHOIS contact defaults.")
text = text.replace(old, new, 1)

old = '''        for entity in data.get("entities") or []:
            vcard = entity.get("vcardArray") or []
            fields = vcard[1] if len(vcard) > 1 and isinstance(vcard[1], list) else []
            for field in fields:
                if len(field) >= 4 and field[0] == "tel" and field[3]:
                    phone = str(field[3]).replace("tel:", "").strip()
                    break
            if phone != "記載なし":
                break
'''
new = '''        for entity in data.get("entities") or []:
            vcard = entity.get("vcardArray") or []
            fields = vcard[1] if len(vcard) > 1 and isinstance(vcard[1], list) else []
            for field in fields:
                if len(field) < 4 or not field[3]:
                    continue
                if field[0] == "tel" and phone == "記載なし":
                    phone = str(field[3]).replace("tel:", "").strip()
                elif field[0] == "adr" and address == "記載なし":
                    value = field[3]
                    if isinstance(value, list):
                        address = " ".join(str(part).strip() for part in value if str(part).strip())
                    else:
                        address = str(value).strip()
            if phone != "記載なし" and address != "記載なし":
                break
'''
if old not in text:
    raise SystemExit("Could not locate RDAP contact parsing.")
text = text.replace(old, new, 1)

old = '        f"WHOIS電話番号: {phone}\\n"\n        f"国: {country}\\n"\n'
new = (
    '        f"WHOIS電話番号: {phone}\\n"\n'
    '        f"WHOIS住所: {address}\\n"\n'
    '        f"国: {country}\\n"\n'
)
if old not in text:
    raise SystemExit("Could not locate WHOIS Slack contact output.")
text = text.replace(old, new, 1)

compile(text, str(target), "exec")
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-address-{timestamp}")
shutil.copy2(target, backup)
target.write_text(text, encoding="utf-8")

print(f"Patched: {target}")
print(f"Backup:  {backup}")
print("WHOIS address field added.")
