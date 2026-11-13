#!/usr/bin/env python3
"""AI Analyst Showdown, v0.

Sends one fixed earnings snippet + one fixed question to every model in
models.toml via OpenRouter, saves each raw response (model, provider, tokens,
cost, latency) under runs/<UTC-stamp>/, and writes runs/<UTC-stamp>/comparison.md.
Decisions behind every choice here: docs/adr/0001-v0-harness-one-earnings-snippet-three-models-via-openrouter.md

Usage:
    uv run showdown.py --dry-run   # budget check + estimate, no API calls, no key needed
    uv run showdown.py             # live run (costs money; est. < $0.01)

Key hygiene (the repo is public): OPENROUTER_API_KEY is read from the
environment only, sent only in the Authorization header, never printed, and
never saved. Every file this script writes passes through safe_write(), which
refuses to write anything containing the key or a key-shaped string.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_URL = "https://openrouter.ai/api/v1/chat/completions"
KEY_ENV = "OPENROUTER_API_KEY"
# The shape of an OpenRouter key: a second net for when the key itself is unknown.
KEY_PATTERN = re.compile(r"sk-or-[A-Za-z0-9_-]{20,}")
TIMEOUT_S = 180


class BudgetExceeded(Exception):
    """A run could push total spend past the stop line."""


class SecretLeak(Exception):
    """Text about to be written contains the API key or a key-shaped string."""


# ── config & inputs ──────────────────────────────────────────────────────────

def load_config(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def build_prompt(snippet: str, question: str) -> str:
    """One user message: the snippet, a blank line, the question. Identical for every model."""
    return f"{snippet.strip()}\n\n{question.strip()}\n"


def request_body(model: dict, prompt: str) -> dict:
    """The JSON body sent for one model. Vendor defaults (QST-RUN-SETTINGS = A):
    no temperature / max_tokens / reasoning. `usage.include` asks OpenRouter for
    accounting (cost in the response); it does not change generation."""
    body = {
        "model": model["id"],
        "messages": [{"role": "user", "content": prompt}],
        "usage": {"include": True},
    }
    if "provider" in model:
        body["provider"] = dict(model["provider"])
    return body


# ── budget ───────────────────────────────────────────────────────────────────

def spent_so_far(runs_dir: Path) -> float:
    """Sum of cost_usd over every saved call record in every run. A failed call
    records cost_usd = null and counts as 0."""
    total = 0.0
    for path in sorted(runs_dir.glob("*/*.json")):
        cost = json.loads(path.read_text()).get("cost_usd")
        if cost:
            total += float(cost)
    return total


def estimate_run_cost(models: list[dict], prompt: str, est_output_tokens: int) -> float:
    """Conservative upper estimate: ~3 chars per prompt token (real tokenizers
    average ~4) and a fixed output allowance, since max_tokens is not sent."""
    prompt_tokens = math.ceil(len(prompt) / 3)
    return sum(
        (prompt_tokens * m["price_in_per_m"] + est_output_tokens * m["price_out_per_m"]) / 1e6
        for m in models
    )


def check_budget(spent: float, estimate: float, stop_line: float) -> None:
    if spent + estimate > stop_line:
        raise BudgetExceeded(
            f"Refusing to run: ${spent:.4f} spent + ${estimate:.4f} estimated "
            f"would exceed the ${stop_line:.2f} stop line (ADR-0001)."
        )


# ── secrets ──────────────────────────────────────────────────────────────────

def find_secrets(text: str, key: str | None) -> list[str]:
    """Reasons `text` is unsafe to write. Never returns the secret itself."""
    reasons = []
    if key and key in text:
        reasons.append(f"contains the value of {KEY_ENV}")
    if KEY_PATTERN.search(text):
        reasons.append("contains an OpenRouter-key-shaped string (sk-or-...)")
    return reasons


def safe_write(path: Path, text: str, key: str | None) -> None:
    reasons = find_secrets(text, key)
    if reasons:
        raise SecretLeak(f"Refusing to write {path}: {'; '.join(reasons)}")
    path.write_text(text)


# ── the call ─────────────────────────────────────────────────────────────────

def call_openrouter(body: dict, key: str, timeout: float = TIMEOUT_S) -> dict:
    """POST one chat completion. Returns {http_status, payload, error, latency_s};
    never raises for HTTP/network failures, so one bad model can't sink the run."""
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    status, raw, error = None, None, None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, raw = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read().decode("utf-8", "replace")
        error = f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        error = f"{type(e).__name__}: {getattr(e, 'reason', e)}"
    latency = time.monotonic() - t0

    payload = None
    if raw is not None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"unparsed_body": raw}
            error = error or "response was not JSON"
    # OpenRouter can report an upstream failure inside a 200 body.
    if isinstance(payload, dict) and payload.get("error"):
        err = payload["error"]
        msg = err.get("message", err) if isinstance(err, dict) else err
        error = f"{error or 'error'}: {msg}"
    return {"http_status": status, "payload": payload, "error": error, "latency_s": latency}


def _message_text(message: dict) -> str | None:
    content = message.get("content")
    if isinstance(content, list):  # some providers return content parts
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content


def make_record(model: dict, body: dict, result: dict, started_at: str) -> dict:
    """Everything saved for one call: the request BODY (never headers), the raw
    response, and the fields the comparison needs, pulled out for reading."""
    payload = result["payload"] if isinstance(result["payload"], dict) else {}
    usage = payload.get("usage") or {}
    choices = payload.get("choices") or [{}]
    choice = choices[0]
    details = usage.get("completion_tokens_details") or {}

    cost, cost_source = usage.get("cost"), None
    if cost is not None:
        cost_source = "openrouter usage.cost"
    elif usage.get("prompt_tokens") is not None:
        # Fallback: list price × reported tokens, flagged so nobody mistakes it for billed cost.
        cost = (usage.get("prompt_tokens", 0) * model["price_in_per_m"]
                + usage.get("completion_tokens", 0) * model["price_out_per_m"]) / 1e6
        cost_source = "computed from list price (usage.cost missing)"

    error = result["error"]
    text = _message_text(choice.get("message") or {})
    if not error and not text:
        error = "empty response"
    return {
        "model_requested": model["id"],
        "model_served": payload.get("model"),
        "provider": payload.get("provider"),
        "started_at": started_at,
        "latency_s": round(result["latency_s"], 2),
        "http_status": result["http_status"],
        "error": error,
        "finish_reason": choice.get("finish_reason"),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": details.get("reasoning_tokens"),
        },
        "cost_usd": cost,
        "cost_source": cost_source,
        "text": text,
        "request": body,
        "response": result["payload"],
    }


# ── the comparison ───────────────────────────────────────────────────────────

def _fmt(v, fmt="{}"):
    return "—" if v is None else fmt.format(v)


def render_comparison(stamp: str, records: list[dict], snippet: str, question: str,
                      spent_after: float, budget: dict) -> str:
    run_total = sum(r["cost_usd"] or 0 for r in records)
    lines = [
        f"# Showdown run {stamp}",
        "",
        "Same input, same question, every model. Settings are **vendor defaults**: no temperature, "
        "max_tokens or reasoning parameters were sent, and providers do not report the effective "
        "temperature. The reasoning-token count shows whether the model thought before answering. "
        "Decisions: ADR-0001.",
        "",
        "| Model | Served by | Prompt tok | Output tok | Reasoning tok | Cost (USD) | Latency | Finish |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in records:
        u = r["usage"]
        status = f"**FAILED**: {r['error']}" if r["error"] else _fmt(r["finish_reason"])
        lines.append(
            f"| `{r['model_requested']}` | {_fmt(r['provider'])} | {_fmt(u['prompt_tokens'])} "
            f"| {_fmt(u['completion_tokens'])} | {_fmt(u['reasoning_tokens'])} "
            f"| {_fmt(r['cost_usd'], '${:.6f}')} | {r['latency_s']:.1f}s | {status} |"
        )
    lines += [
        "",
        f"**This run**: ${run_total:.6f}  ·  **Spent to date**: ${spent_after:.4f} of "
        f"${budget['total_usd']:.2f} (stop line ${budget['stop_line_usd']:.2f})",
    ]
    if any(r["cost_source"] and r["cost_source"] != "openrouter usage.cost" for r in records):
        lines.append("")
        lines.append("⚠️ Some costs were computed from list prices because OpenRouter reported none; see each JSON's `cost_source`.")
    lines += [
        "",
        "<details><summary>Input and question sent to every model</summary>",
        "",
        "```text",
        snippet.strip(),
        "",
        question.strip(),
        "```",
        "",
        "</details>",
    ]
    for r in records:
        lines += ["", "---", "", f"## `{r['model_requested']}`", ""]
        if r["error"]:
            lines.append(f"**FAILED**: {r['error']}. No answer from this model in this run.")
        else:
            lines.append(r["text"].strip())
    return "\n".join(lines) + "\n"


# ── main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="budget check and estimate only; no API calls")
    ap.add_argument("--config", type=Path, default=ROOT / "models.toml")
    ap.add_argument("--inputs-dir", type=Path, default=ROOT / "inputs")
    ap.add_argument("--runs-dir", type=Path, default=ROOT / "runs")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    models, budget = cfg["models"], cfg["budget"]
    snippet = (args.inputs_dir / "snippet.txt").read_text()
    question = (args.inputs_dir / "question.txt").read_text()
    prompt = build_prompt(snippet, question)

    spent = spent_so_far(args.runs_dir)
    estimate = estimate_run_cost(models, prompt, budget["est_output_tokens_per_model"])
    print(f"Spent so far ${spent:.4f} of ${budget['total_usd']:.2f} · this run est. ≤ ${estimate:.4f} "
          f"· stop line ${budget['stop_line_usd']:.2f}")
    try:
        check_budget(spent, estimate, budget["stop_line_usd"])
    except BudgetExceeded as e:
        print(e, file=sys.stderr)
        return 2

    if args.dry_run:
        for m in models:
            pin = f"  (pinned: {m['provider']})" if "provider" in m else ""
            print(f"  would call {m['id']}{pin}")
        return 0

    key = os.environ.get(KEY_ENV)
    if not key:
        print(f"{KEY_ENV} is not set; export it in your shell (never in a file in this repo).", file=sys.stderr)
        return 1

    stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H%M%SZ")
    run_dir = args.runs_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=False)

    records = []
    for m in models:
        body = request_body(m, prompt)
        started = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
        print(f"→ {m['id']} …", end=" ", flush=True)
        rec = make_record(m, body, call_openrouter(body, key), started)
        safe_write(run_dir / f"{m['id'].replace('/', '__')}.json",
                   json.dumps(rec, indent=2, ensure_ascii=False) + "\n", key)
        records.append(rec)
        if rec["error"]:
            print(f"FAILED ({rec['error']})")
        else:
            print(f"{_fmt(rec['cost_usd'], '${:.6f}')} · {rec['usage']['completion_tokens']} out tok "
                  f"· via {rec['provider']} · {rec['latency_s']:.1f}s")

    spent_after = spent_so_far(args.runs_dir)
    safe_write(run_dir / "comparison.md",
               render_comparison(stamp, records, snippet, question, spent_after, budget), key)
    run_total = sum(r["cost_usd"] or 0 for r in records)
    print(f"Run total ${run_total:.6f} · spent to date ${spent_after:.4f} of ${budget['total_usd']:.2f}")
    print(f"Comparison: {(run_dir / 'comparison.md').relative_to(ROOT) if run_dir.is_relative_to(ROOT) else run_dir / 'comparison.md'}")
    return 0 if any(not r["error"] for r in records) else 1


if __name__ == "__main__":
    sys.exit(main())
