"""Tests for showdown.py: the behaviors ADR-0001 says must not fail.

- The budget guard refuses a run that could cross the $9.00 stop line.
- No API key reaches anything written to disk, and nothing committed under runs/.
- A model that fails (e.g. the pinned DeepSeek provider is down) stays visible.
- The request is identical across models apart from the DeepSeek pin, and
  carries no generation parameters (vendor defaults).
"""
import json
import os
from pathlib import Path

import pytest

import showdown

ROOT = Path(showdown.__file__).resolve().parent
# Built at runtime so no key-shaped literal ever sits in this source file
# (GitHub secret scanning would flag it, and so would our own scan).
FAKE_KEY = "sk-or-" + "v1-" + "0123456789abcdef" * 4


def _save_call(runs_dir: Path, run: str, model_slug: str, cost):
    d = runs_dir / run
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{model_slug}.json").write_text(json.dumps({"cost_usd": cost}))


# ── budget ───────────────────────────────────────────────────────────────────

def test_spent_sums_every_call_across_runs_and_counts_failures_as_zero(tmp_path):
    _save_call(tmp_path, "2026-11-12T000000Z", "a", 0.0012)
    _save_call(tmp_path, "2026-11-12T000000Z", "b", None)  # failed call: no cost
    _save_call(tmp_path, "2026-11-13T000000Z", "a", 0.0030)
    (tmp_path / "2026-11-13T000000Z" / "comparison.md").write_text("# not a call record")
    assert showdown.spent_so_far(tmp_path) == pytest.approx(0.0042)


def test_dry_run_refuses_when_next_run_could_cross_stop_line(tmp_path, capsys):
    # $8.999 already spent: any real run's estimate pushes past $9.00.
    _save_call(tmp_path, "2026-11-12T000000Z", "a", 8.999)
    assert showdown.main(["--dry-run", "--runs-dir", str(tmp_path)]) == 2
    assert "stop line" in capsys.readouterr().err


def test_dry_run_allows_fresh_budget_and_estimate_stays_tiny(tmp_path):
    assert showdown.main(["--dry-run", "--runs-dir", str(tmp_path)]) == 0
    cfg = showdown.load_config(ROOT / "models.toml")
    prompt = showdown.build_prompt((ROOT / "inputs/snippet.txt").read_text(),
                                   (ROOT / "inputs/question.txt").read_text())
    est = showdown.estimate_run_cost(cfg["models"], prompt, cfg["budget"]["est_output_tokens_per_model"])
    # ADR-0001 promised a conservative estimate of at most ~$0.01 per four-model run.
    assert 0 < est <= 0.012


# ── key hygiene ──────────────────────────────────────────────────────────────

def test_safe_write_refuses_text_containing_the_key(tmp_path):
    # Real scenario: an error body or a debug dump that echoes the Authorization header.
    target = tmp_path / "x.json"
    with pytest.raises(showdown.SecretLeak) as e:
        showdown.safe_write(target, f'{{"echo": "Bearer {FAKE_KEY}"}}', FAKE_KEY)
    assert not target.exists()
    assert FAKE_KEY not in str(e.value)  # the refusal message must not leak it either


def test_safe_write_refuses_key_shaped_text_even_when_key_unknown(tmp_path):
    target = tmp_path / "x.json"
    with pytest.raises(showdown.SecretLeak):
        showdown.safe_write(target, f"token {FAKE_KEY}", key=None)
    assert not target.exists()


def test_committed_runs_contain_no_api_key():
    """Irene's gate condition (ADR-0001, QST-OUTPUT): no run is committed unless this
    passes. Scans every file under runs/ for the live key's value (when set) and for
    any key-shaped string."""
    key = os.environ.get(showdown.KEY_ENV)
    runs = ROOT / "runs"
    leaks = [
        f"{p.relative_to(ROOT)}: {', '.join(reasons)}"
        for p in sorted(runs.rglob("*")) if p.is_file()
        if (reasons := showdown.find_secrets(p.read_text(errors="replace"), key))
    ] if runs.exists() else []
    assert leaks == []


def test_saved_record_holds_request_body_but_not_headers():
    model = {"id": "anthropic/claude-haiku-5.5", "price_in_per_m": 0.1, "price_out_per_m": 0.5}
    body = showdown.request_body(model, "prompt")
    result = {"http_status": 200, "error": None, "latency_s": 1.0, "payload": {
        "model": model["id"], "provider": "Anthropic",
        "choices": [{"message": {"content": "Revenue was $412.6M [S1]."}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 300, "completion_tokens": 40, "cost": 0.00005}}}
    text = json.dumps(showdown.make_record(model, body, result, "t"))
    assert "Authorization" not in text and "Bearer" not in text


# ── recording what came back ─────────────────────────────────────────────────

def test_record_prefers_billed_cost_and_flags_list_price_fallback():
    model = {"id": "openai/gpt-6-luna", "price_in_per_m": 0.10, "price_out_per_m": 0.50}
    body = showdown.request_body(model, "p")
    payload = {"model": model["id"], "provider": "OpenAI",
               "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
               "usage": {"prompt_tokens": 1000, "completion_tokens": 2000,
                         "completion_tokens_details": {"reasoning_tokens": 1500},
                         "cost": 0.0011}}
    billed = showdown.make_record(model, body, {"http_status": 200, "error": None,
                                                "latency_s": 2.0, "payload": payload}, "t")
    assert billed["cost_usd"] == 0.0011 and billed["cost_source"] == "openrouter usage.cost"
    assert billed["usage"]["reasoning_tokens"] == 1500 and billed["provider"] == "OpenAI"

    del payload["usage"]["cost"]  # if OpenRouter ever omits it, the budget must still count the call
    computed = showdown.make_record(model, body, {"http_status": 200, "error": None,
                                                  "latency_s": 2.0, "payload": payload}, "t")
    assert computed["cost_usd"] == pytest.approx((1000 * 0.10 + 2000 * 0.50) / 1e6)
    assert "list price" in computed["cost_source"]


def test_failed_model_stays_visible_in_comparison():
    # Real scenario: DeepInfra is down and allow_fallbacks=false makes the pinned call fail.
    ok_model = {"id": "anthropic/claude-haiku-5.5", "price_in_per_m": 0.1, "price_out_per_m": 0.5}
    ds_model = {"id": "deepseek/deepseek-v4.1-flash", "price_in_per_m": 0.14, "price_out_per_m": 0.42}
    ok = showdown.make_record(ok_model, {}, {"http_status": 200, "error": None, "latency_s": 1.2, "payload": {
        "provider": "Anthropic", "choices": [{"message": {"content": "Revenue $412.6M [S1]."},
                                              "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 300, "completion_tokens": 20, "cost": 0.00004}}}, "t")
    down = showdown.make_record(ds_model, {}, {
        "http_status": 404, "error": "HTTP 404", "latency_s": 0.3,
        "payload": {"error": {"message": "No endpoints found matching your data policy"}}}, "t")
    md = showdown.render_comparison("STAMP", [ok, down], "snippet", "question", 0.00004,
                                    {"total_usd": 10.0, "stop_line_usd": 9.0})
    assert md.count("deepseek/deepseek-v4.1-flash") == 2  # table row and its own section
    assert "**FAILED**: HTTP 404" in md
    assert "Revenue $412.6M [S1]." in md


# ── the ADR-0001 request contract ────────────────────────────────────────────

def test_every_model_gets_the_same_prompt_and_no_generation_params():
    cfg = showdown.load_config(ROOT / "models.toml")
    bodies = [showdown.request_body(m, "PROMPT") for m in cfg["models"]]
    assert len(bodies) == 4
    assert all(b["messages"] == bodies[0]["messages"] for b in bodies)
    for b in bodies:  # vendor defaults: QST-RUN-SETTINGS = A
        assert not {"temperature", "max_tokens", "reasoning", "top_p"} & b.keys()
    pinned = [b for b in bodies if "provider" in b]
    assert [b["model"] for b in pinned] == ["deepseek/deepseek-v4.1-flash"]
    assert pinned[0]["provider"] == {"order": ["deepinfra"], "quantizations": ["fp8"],
                                     "allow_fallbacks": False}
