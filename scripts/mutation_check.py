"""Planted-bug check: each mutation below breaks one rule, and the test suites must notice.

Run from the project root: python -m scripts.mutation_check
Every file is restored afterwards, even if a run is interrupted.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTEST = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "--no-cov"]
NODE = ["node", "--test", "tests/js/pure-modules.test.js"]


@dataclass(frozen=True)
class Mutant:
    path: str
    original: str
    mutated: str
    rule: str
    command: tuple[str, ...] = tuple(PYTEST)


MUTANTS = (
    Mutant(
        "airwise/aqi.py",
        'AqiBand("good", "Good", "low", 50)',
        'AqiBand("good", "Good", "low", 51)',
        "Good/Moderate AQI boundary",
    ),
    Mutant(
        "airwise/policy.py",
        "MIN_SHIFT_DIFFERENCE_PCT = 5.0",
        "MIN_SHIFT_DIFFERENCE_PCT = 50.0",
        "5% timing-shift threshold",
    ),
    Mutant("airwise/policy.py", "total / duration", "total / (duration + 1)", "duration-weighted PM2.5 mean"),
    Mutant(
        "airwise/forecast.py",
        "<= datetime.fromisoformat(hour.time) < end",
        "<= datetime.fromisoformat(hour.time) <= end",
        "24-hour outlook excludes the hour 24 h ahead",
    ),
    Mutant(
        "airwise/ai.py",
        "if any(char.isnumeric() for char in prose) or PERCENT_WORDS.search(prose):",
        "if PERCENT_WORDS.search(prose):",
        "AI prose may not contain digits",
    ),
    Mutant(
        "airwise/ai.py",
        "    if cached is not None:\n        return cached\n",
        "",
        "identical AI requests reuse the cached answer",
    ),
    Mutant("airwise/data.py", "result < 0", "result < -1", "negative upstream values are discarded"),
    Mutant("airwise/security.py", '== "cross-site"', '== "never"', "cross-site API writes are rejected"),
    Mutant(
        "airwise/security.py",
        '"Strict-Transport-Security": "max-age=31536000; includeSubDomains",\n',
        "",
        "HSTS header on every response",
    ),
    Mutant(
        "airwise/main.py",
        '@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)',
        '@app.api_route("/favicon-missing.ico", methods=["GET", "HEAD"], include_in_schema=False)',
        "/favicon.ico is served",
    ),
    Mutant(
        "static/js/transport.js",
        "const API_PATH = /^\\/api\\/",
        "const API_PATH = /\\/api\\/",
        "browser only calls same-origin API paths",
        tuple(NODE),
    ),
    Mutant(
        "static/js/city-search.js",
        "return `/api/geo?${new URLSearchParams({ q: query })}`;",
        "return `/api/geo?q=${encodeURIComponent(query)}`;",
        "city names with apostrophes",
        tuple(NODE),
    ),
    Mutant(
        "static/js/brief.js",
        "Not India's official CPCB AQI or a local station reading.",
        "",
        "community brief states the AQI scale",
        tuple(NODE),
    ),
)


def survives(mutant: Mutant) -> bool:
    path = ROOT / mutant.path
    source = path.read_text(encoding="utf-8")
    if source.count(mutant.original) != 1:
        raise SystemExit(f"Mutation target not found exactly once in {mutant.path}: {mutant.original!r}")
    path.write_text(source.replace(mutant.original, mutant.mutated), encoding="utf-8")
    try:
        result = subprocess.run(mutant.command, cwd=ROOT, capture_output=True, text=True, check=False)
    finally:
        path.write_text(source, encoding="utf-8")
    return result.returncode == 0


def main() -> int:
    survivors = []
    for mutant in MUTANTS:
        survived = survives(mutant)
        print(f"{'SURVIVED' if survived else 'caught  '}  {mutant.path}: {mutant.rule}")
        if survived:
            survivors.append(mutant)
    print(f"{len(MUTANTS) - len(survivors)} of {len(MUTANTS)} planted bugs caught")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
