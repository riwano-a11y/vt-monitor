#!/usr/bin/env python3
"""Normalize WHOIS phone numbers to digits only."""

from datetime import datetime
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if "raw_phone = str(field[3])" in text:
    print("Already patched.")
    raise SystemExit(0)

old = '                    phone = str(field[3]).replace("tel:", "").strip()\n'
new = (
    '                    raw_phone = str(field[3]).replace("tel:", "").strip()\n'
    '                    phone = "".join(char for char in raw_phone if char.isdigit()) or "記載なし"\n'
)
if old not in text:
    raise SystemExit("Could not locate WHOIS phone parsing.")
text = text.replace(old, new, 1)

compile(text, str(target), "exec")
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-phone-digits-{timestamp}")
shutil.copy2(target, backup)
target.write_text(text, encoding="utf-8")

print(f"Patched: {target}")
print(f"Backup:  {backup}")
print("Phone numbers are now digits only.")
