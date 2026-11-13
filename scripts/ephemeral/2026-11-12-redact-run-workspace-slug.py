#!/usr/bin/env python3
"""Redact the OpenRouter workspace slug from an already-written run directory.

Context: the first live run (runs/2026-11-13T010936Z) was written before
showdown.safe_write() learned to redact account identifiers. A rate-limit error
for openai/gpt-6-luna embedded "openrouter.ai/workspaces/<slug>/byok" in the
model's JSON and in comparison.md. This applies the same redaction the fixed
writer now applies, in place, so the run can be committed to the public repo.
Everything else in the files is left byte-for-byte unchanged.

Usage:  uv run python scripts/ephemeral/2026-11-12-redact-run-workspace-slug.py runs/<stamp>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import showdown  # noqa: E402

for path in sorted(Path(sys.argv[1]).iterdir()):
    text = path.read_text()
    clean = showdown.redact_account_ids(text)
    if clean != text:
        path.write_text(clean)
        print(f"redacted: {path}")

# Outcome (2026-11-12): run on runs/2026-11-13T010936Z; redacted
# openai__gpt-6-luna.json and comparison.md (2 occurrences each). The
# committed-runs scan in tests/test_showdown.py passed afterwards.
