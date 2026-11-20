"""Fast CI gate for challenge submission constraints and common accidental leaks.

Measures what the repository actually contains (git-tracked files), so local tool caches
such as .mypy_cache or node_modules never count toward the 10 MB limit.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZE_LIMIT_BYTES = 10_000_000
TEXT_SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".txt", ".yaml", ".yml", ".example", ".toml", ".json"}
KEY_PATTERN = re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b|\bsk-proj-[0-9A-Za-z_-]{30,}\b")
PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"


def tracked_files() -> list[Path]:
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout
    return [ROOT / name for name in listing.split("\0") if name and (ROOT / name).is_file()]


def problems(files: list[Path]) -> list[str]:
    found = []
    size = sum(path.stat().st_size for path in files)
    if size >= SIZE_LIMIT_BYTES:
        found.append(f"Tracked files total {size:,} bytes (limit 10 MB)")
    if (ROOT / ".env").exists():
        found.append("A .env file exists in the repository root")
    for path in files:
        if path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if PRIVATE_KEY_MARKER in text:
            found.append(f"Possible private key in {path.relative_to(ROOT)}")
        if KEY_PATTERN.search(text):
            found.append(f"Possible embedded API key in {path.relative_to(ROOT)}")
    return found


def main() -> int:
    files = tracked_files()
    found = problems(files)
    for problem in found:
        print("FAIL:", problem)
    if found:
        return 1
    size = sum(path.stat().st_size for path in files)
    print(f"PASS: {len(files)} tracked files; {size:,} bytes (< 10 MB); basic secret scan clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
