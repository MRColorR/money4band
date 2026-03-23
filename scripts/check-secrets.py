#!/usr/bin/env python3
"""Pre-commit hook to detect hardcoded credentials in staged files.

Install:
    cp scripts/check-secrets.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit

Or use with the pre-commit framework (see .pre-commit-config.yaml).
"""

from __future__ import annotations

import re
import subprocess
import sys

# Patterns that indicate real credentials (not placeholders).
# Each tuple: (compiled_regex, human_readable_description)
CREDENTIAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"""(?:password|passwd|secret|token|apikey|api_key|cid)"""
            r"""[\s]*[=:]\s*["']?(?!your)[a-zA-Z0-9/+_.@-]{3,}""",
            re.IGNORECASE,
        ),
        "Possible hardcoded credential (non-placeholder value)",
    ),
    (
        re.compile(r"PACKETSTREAM_CID=(?!yourPACKETSTREAMCID)(?!$)\S+"),
        "Real PacketStream CID detected",
    ),
]

# Files/patterns to skip (binary, generated, docs that discuss credentials)
SKIP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\.env\.example$"),
    re.compile(r"\.env$"),
    re.compile(r"docker-compose\.yaml$"),
    re.compile(r"docs/"),
    re.compile(r"\.github/copilot-instructions\.md$"),
    re.compile(r"\.md$"),  # Documentation files may reference credential patterns
    re.compile(r"tests/"),
    re.compile(r"\.pyc$"),
    re.compile(r"\.png$|\.jpg$|\.gif$|\.ico$"),
    re.compile(r"scripts/check-secrets\.py$"),  # This file itself
    re.compile(r"\.pre-commit-config\.yaml$"),
]


def get_staged_files() -> list[str]:
    """Return list of files staged for commit."""
    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def should_skip(filepath: str) -> bool:
    """Check if a file should be skipped."""
    return any(pat.search(filepath) for pat in SKIP_PATTERNS)


def check_file(filepath: str) -> list[tuple[int, str, str]]:
    """Check a single file for credential patterns.

    Returns list of (line_number, line_content, description) tuples.
    """
    findings: list[tuple[int, str, str]] = []
    try:
        # Read the staged version of the file
        result = subprocess.run(  # noqa: S603
            ["git", "show", f":{filepath}"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
        for line_num, line in enumerate(result.stdout.splitlines(), start=1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith(("#", "//")):
                continue
            for pattern, description in CREDENTIAL_PATTERNS:
                if pattern.search(line):
                    findings.append((line_num, stripped, description))
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        pass  # Binary file or not in index
    return findings


def main() -> int:
    staged = get_staged_files()
    all_findings: list[tuple[str, int, str, str]] = []

    for filepath in staged:
        if should_skip(filepath):
            continue
        findings = check_file(filepath)
        for line_num, line_content, desc in findings:
            all_findings.append((filepath, line_num, line_content, desc))

    if all_findings:
        print("\n❌ Potential credentials detected in staged files:\n")
        for filepath, line_num, line_content, desc in all_findings:
            print(f"  {filepath}:{line_num}")
            print(f"    {desc}")
            print(f"    > {line_content[:120]}")
            print()
        print(
            "If these are intentional (e.g., placeholder patterns), "
            "use: git commit --no-verify"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
