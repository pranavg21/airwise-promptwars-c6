"""Fast CI gate for challenge submission constraints and common accidental leaks."""
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
INCLUDE={'.py','.js','.css','.html','.md','.txt','.yaml','.yml','.example','.toml'}
AVOID={'node_modules','.git','.venv','__pycache__','.pytest_cache'}
files=[p for p in ROOT.rglob('*') if p.is_file() and not (set(p.parts) & AVOID)]
size=sum(p.stat().st_size for p in files)
errors=[]
if size >= 10_000_000:errors.append(f"Repository over 10MB (before .git): {size} bytes")
if (ROOT/'.env').exists():errors.append('A .env file exists in repository root')
for p in files:
    if p.suffix not in INCLUDE:continue
    t=p.read_text(encoding='utf-8',errors='replace')
    if p.name != 'audit_repo.py' and '-----BEGIN PRIVATE KEY-----' in t:errors.append(f"Possible private key in {p.relative_to(ROOT)}")
    if re.search(r'\bAIza[0-9A-Za-z_-]{35}\b|\bsk-proj-[0-9A-Za-z_-]{30,}\b', t):errors.append(f"Possible embedded API key in {p.relative_to(ROOT)}")
if errors:
    for error in errors:print('FAIL:',error)
    sys.exit(1)
print(f"PASS: {len(files)} source/docs files; {size:,} total bytes (< 10 MB); basic secret scan clean")
print('Reminder: verify final pushed GitHub repository history, public access, single branch and deployed AI separately.')
