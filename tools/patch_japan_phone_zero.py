#!/usr/bin/env python3
"""Convert Japanese +81 WHOIS phones to domestic leading-zero format."""

from datetime import datetime
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if 'phone = "0" + phone[2:]' in text:
    print("Already patched.")
    raise SystemExit(0)

old = '        phone = "".join(char for char in raw_phone if char.isdigit()) or "記載なし"\n'
new = (
    '        phone = "".join(char for char in raw_phone if char.isdigit()) or "記載なし"\n'
    '        if phone.startswith("81") and len(phone) >= 10:\n'
    '            phone = "0" + phone[2:]\n'
)
if old not in text:
    raise SystemExit("Could not locate domain WHOIS phone normalization.")
text = text.replace(old, new, 1)

compile(text, str(target), "exec")
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-jp-phone-{timestamp}")
shutil.copy2(target, backup)
target.write_text(text, encoding="utf-8")

print(f"Patched: {target}")
print(f"Backup:  {backup}")
print("Japanese WHOIS phone numbers now start with 0.")
