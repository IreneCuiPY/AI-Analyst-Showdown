#!/usr/bin/env python3
"""OpenRouter price scan — pick cheap v0 candidate models from the live list.

Context: v0 of the earnings-analysis harness (ADR-0001) must choose 3 cheap
models from distinct vendors. The user asked us to look up current model IDs
and prices instead of guessing. This reads a saved copy of the PUBLIC endpoint
https://openrouter.ai/api/v1/models (no API key needed or sent) and prints, per
vendor family, the cheapest text models with $/1M prompt + completion tokens.

Usage:  python3 -I scripts/ephemeral/2026-11-12-openrouter-price-scan.py <models.json>
"""
import json
import sys

FAMILIES = ["openai", "anthropic", "google", "meta-llama", "mistralai",
            "deepseek", "qwen", "x-ai", "moonshotai", "z-ai"]


def per_million(v):
    try:
        return float(v) * 1_000_000
    except (TypeError, ValueError):
        return None


def main(path):
    data = json.load(open(path))["data"]
    rows = []
    for m in data:
        mid = m["id"]
        fam = mid.split("/")[0]
        if fam not in FAMILIES or mid.endswith(":free"):
            continue
        arch = m.get("architecture", {})
        if "text" not in arch.get("output_modalities", ["text"]):
            continue
        p = m.get("pricing", {})
        pin, pout = per_million(p.get("prompt")), per_million(p.get("completion"))
        if pin is None or pout is None or pin <= 0:
            continue
        rows.append((fam, pin, pout, mid, m.get("context_length"), m.get("created", 0)))
    print(f"{len(data)} models total; {len(rows)} paid text models in tracked families\n")
    for fam in FAMILIES:
        fr = sorted((r for r in rows if r[0] == fam), key=lambda r: r[1] + r[2])
        if not fr:
            continue
        print(f"== {fam}")
        for _, pin, pout, mid, ctx, created in fr[:6]:
            print(f"   ${pin:7.3f} in / ${pout:7.3f} out per 1M   ctx={ctx}  {mid}")
    # Rough cost of one v0 run: ~600 prompt tokens + ~600 completion tokens.
    print("\nEst. cost of ONE call (~600 in + ~600 out) for the cheapest per family:")
    for fam in FAMILIES:
        fr = sorted((r for r in rows if r[0] == fam), key=lambda r: r[1] + r[2])
        if fr:
            _, pin, pout, mid, _, _ = fr[0]
            print(f"   ${(600 * pin + 600 * pout) / 1e6:.5f}  {mid}")


def detail(path, ids):
    """Second mode: price + reasoning support for named candidate IDs."""
    by_id = {m["id"]: m for m in json.load(open(path))["data"]}
    for mid in ids:
        m = by_id.get(mid)
        if not m:
            print(f"   MISSING  {mid}")
            continue
        p = m["pricing"]
        sp = m.get("supported_parameters", [])
        print(f"   ${per_million(p['prompt']):6.3f} in / ${per_million(p['completion']):6.3f} out"
              f"  reasoning={'reasoning' in sp}  {mid}  ({m.get('name')})")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        detail(sys.argv[1], sys.argv[2:])
    else:
        main(sys.argv[1])

# Outcome (2026-11-12): 475 models listed. One v0 call (~600 in / ~600 out) costs
# $0.00004–$0.002 for the cheapest per vendor, so the $10 budget does not
# constrain model choice at v0; ":batch" variants are excluded from consideration
# (asynchronous batch pricing, not a plain chat call). Fed QST-MODEL-TRIO in ADR-0001.
