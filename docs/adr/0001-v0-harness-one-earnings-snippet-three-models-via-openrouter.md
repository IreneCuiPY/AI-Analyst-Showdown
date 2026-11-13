<!-- adr template version: "adr 3.12.0" -->
<!--
adr teaching map: the example is not the teaching — these are the up-links from this file to what teaches its form; load them rather than winging it. (Sibling: the template-version marker dates the mold this file was minted from.)
  skill: adr-authoring
  mcp: adrs4ai
  plugin: adr@adrs4ai
-->

# v0 harness: one earnings snippet, four models via OpenRouter

- **Date**: 2026-11-12
- **Iteration**: 3
- **Status**: Partially Implemented
- **Deciders**: Irene Cui (human), Ledger 5.5 (Claude Opus 5.5, Claude Code)

**TL;DR**: v0 sends one fixed, fictional, source-labelled earnings snippet and one fixed question to four cheap models through OpenRouter, with vendor-default settings: Claude Haiku 5.5, GPT-6 Luna, Gemini 3.1 Flash Lite, and DeepSeek V4.1 Flash pinned to one provider. It saves each raw response with provider, tokens and cost, and commits the runs plus a Markdown comparison, but only behind a key-leak test.

*(Filename keeps "three models" from Iteration 1. The count changed when Irene answered QST-MODEL-TRIO, and filenames don't get renamed after they're cited.)*

---

## Originating Context

**Source**: Human brief (Irene Cui, 2026-11-12, first session), excerpted:

> A harness that compares how different LLMs analyze the same company earnings information. Start with the simplest possible version (v0); we'll grow it step by step.
>
> v0 scope only:
> - One fixed input: a short hand-written earnings snippet (a few figures like revenue, net income, margin, guidance), with each fact labeled [S1], [S2]...
> - One fixed question, e.g. "Summarize this quarter's results and cite the source label for every number."
> - Send the exact same input and prompt to 3 models through OpenRouter (one API, just different model IDs). Look up current model IDs and prices from OpenRouter's model list rather than guessing.
> - Save each raw response with model ID, token counts, and cost, then write a side-by-side comparison file I can read myself.
> - Python 3.12, runs locally on my Mac. Keep it small: one script plus a config listing the models.
>
> Constraints:
> - OPENROUTER_API_KEY is already set in the environment. Read it from the environment only — never print, log, hard-code, or commit it. The repo is public.
> - $10 total budget: choose cheap models and show the cost of each run.
> - Not in scope yet: automatic scoring, SEC EDGAR fetching, price prediction. Note them as later steps, don't build them.
>
> Before writing any code, bring me the 2–3 decisions to settle first as QST cards, each with a recommendation.

**Agency Grant**: Structure the decisions and recommend; no code until the questions below are answered.

---

## Explicitation

**What I understand**:

1. **The input is fixed and labelled.** The labels ([S1]…) make citation checkable, and citation is what a later scoring step will grade. v0 only has to keep the labels intact and put them in front of a human.
2. **"Exact same input" is about fairness.** The models differ, so everything else in the request should be held constant and recorded. Otherwise a difference in output can't be attributed to the model.
3. **Cost is a first-class output, not a footnote.** Each run reports its own cost and the running total against the $10 budget.
4. **The repo is public.** This affects both the key (env-only, never logged) and anything the harness writes to disk and might commit.

**Assumptions** (defaults I will build unless a question below or an objection overrides them):

- **The company is fictional.** I'll write the snippet for an invented company so that (a) no model can answer from memorized real figures, which would hide citation failures, and (b) nobody mistakes the snippet for real financial data in a public repo. The figures are internally consistent (margins match revenue and income), so a later scoring step can check arithmetic. Draft below: `COD: earnings-snippet-draft`.
- **Cost comes from OpenRouter's reported per-request cost** (`usage.cost` in the response body), not from our own arithmetic. Config prices are kept only for a pre-run estimate. *Unverified until the first call*; if the field is absent, I fall back to a lookup by generation ID and note it in Iteration 2.
- **Budget guard**: before calling, the script sums the cost of every saved run. It refuses to start a run if the total plus this run's estimate would exceed $9.00, which leaves $1 of headroom under the $10 cap.
- **Key hygiene**: the key is read with `os.environ["OPENROUTER_API_KEY"]`, sent only in the `Authorization` header, never stored in any saved request record, and never echoed in errors (exception text is scrubbed of headers).
- **Tooling**: `uv` for Python 3.12 + one dependency (`httpx`, or stdlib `urllib` if you prefer zero dependencies). Layout: `showdown.py` + `models.toml` + `inputs/`.

**Confirm**: Irene. Is anything above wrong, especially the fictional company and the $9 stop line?

---

## Questions

### QST-MODEL-TRIO: Which three models does v0 compare?
- Status: answered
- Why asking: The trio sets what "different LLMs" means for every later version. Prices are from OpenRouter's public model list, pulled 2026-11-12 (`scripts/ephemeral/2026-11-12-openrouter-price-scan.py`). One v0 run is about 350 input and ≤1,500 output tokens per model, so **every option below costs well under $0.01 per three-model run**. The $10 budget does not decide this; the comparison you want to see does. Prices are $ per 1M tokens, input / output.
- Need: pick a letter (or override — any shape answers; you can also name your own three)

Options:
- **A — three labs, small tier**: `anthropic/claude-haiku-5.5` ($0.10 / $0.50), `openai/gpt-6-luna` ($0.10 / $0.50), `google/gemini-3.1-flash-lite` ($0.25 / $1.50). These are the current small models from the three largest closed-model vendors. ≈ $0.004 per three-model run.
- **B — two closed + one open-weight**: `anthropic/claude-haiku-5.5`, `openai/gpt-6-luna`, `deepseek/deepseek-v4.1-flash` ($0.022 / $0.40). This adds an open-weight model as a comparison axis. Caveat: OpenRouter may serve open-weight models from several hosting providers with different quantization, so two runs may not hit the same weights. ≈ $0.002 per run.
- **C — rock-bottom**: `mistralai/mistral-nemo` ($0.029 / $0.030), `meta-llama/llama-3.1-8b-instruct` ($0.02 / $0.04), `z-ai/glm-5.3-flash` ($0.04 / $0.078). These are the cheapest and oldest/smallest models. They are the most likely to drop citations, which makes differences vivid but says little about the models people actually use for analysis. ≈ $0.0003 per run.

**Recommendation**: (by Ledger 5.5, Claude Opus 5.5, 2026-11-12)

**A — three labs, small tier.** *Rationale*: All three are current-generation models at nearly the same price point (the scan shows them within 3× of each other on output price). A difference in citation behaviour is then more about the vendor's training than about model size or age, which is the comparison this project exists to make. B's open-weight axis is genuinely interesting, but its provider-routing variance adds a confound on day one. **Disclosure**: I am an Anthropic model recommending a slate that includes an Anthropic model. I included it for vendor coverage, and you should weigh that. *Confidence*: 0.65 — because I chose this from price and recency in the model list, not from having seen any of these models run this task. *If wrong*: if you care more about open vs. closed weights than about vendor spread, this flips to **B**. If the first run shows all three acing citation, so there is nothing to compare, consider swapping one model for a weaker C model to calibrate the scale.

**ANS:** (by Irene Cui)
Override: four models — A's three plus deepseek/deepseek-v4.1-flash — because I want both the vendor comparison and an open-weight comparison, and the extra cost is negligible. Pin DeepSeek to one provider.

---

### QST-RUN-SETTINGS: What request settings make "the exact same input" fair?
- Status: answered
- Why asking: The same messages alone don't give the same treatment. All the newer candidate models are reasoning-capable (the model list flags `reasoning` support), and each vendor applies its own default temperature and thinking budget. OpenRouter also silently drops parameters a model doesn't support. So "same request" can still mean "different conditions," and whatever I pick has to be recorded in every saved response so the comparison file can show it.
- Need: pick a letter (or override — any shape answers)

Options:
- **A — vendor defaults**: send only the system and user messages. Each model behaves as it would for a typical user. This is the most "natural," but differences mix model quality with vendor default settings.
- **B — pinned and recorded**: send the same `temperature: 0`, `max_tokens: 1500`, and `reasoning: {effort: "low"}` to all three, with one run per model. Save the request parameters plus the provider OpenRouter actually routed to. Parameters a model ignores are noted, not hidden.
- **C — pinned + repeats**: B, but 3 runs per model, to show run-to-run variance next to model-to-model differences. This triples cost, which is still under $0.02 per batch with option A models.

**Recommendation**: (by Ledger 5.5, Claude Opus 5.5, 2026-11-12)

**B — pinned and recorded.** *Rationale*: The project's question is "how do models differ on the same task," and B removes the largest controllable confound, vendor default settings, while recording what it couldn't control. Low reasoning effort keeps output tokens and cost predictable for the budget guard. C is the more rigorous design, but at v0 there's no scoring to tell whether variance matters, so its extra output is three times more text for you to read by hand. *Confidence*: 0.7 — because I know temperature is sometimes ignored by reasoning models, but I haven't yet seen how OpenRouter maps `effort: "low"` for each of these three vendors. *If wrong*: if two back-to-back runs of the same model disagree on substance (different numbers cited, different conclusions), variance is real and this flips to **C**. If you want to see each model "as it ships," this flips to **A**.

**ANS:** (by Irene Cui)
A — because I want to compare models the way a normal user experiences them, defaults included. Still record the parameters and provider each response actually used.

---

### QST-OUTPUT: Where do run outputs live, and do they get committed to this public repo?
- Status: answered
- Why asking: Each run writes one raw JSON per model (response body, our request body *without headers*, model ID, provider, token counts, cost, latency) plus a comparison file. The repo is public, so whether those files are committed decides whether runs become a reviewable public record or stay on your Mac. Markdown can't show three long answers in readable columns, so the format choice is also a choice about how "side-by-side" looks.
- Need: pick a letter (or override — any shape answers)

Options:
- **A — committed Markdown**: `runs/<UTC-stamp>/` holds `<model>.json` ×3 + `comparison.md`. The comparison file has a side-by-side **metrics table** (model, provider, input/output/reasoning tokens, cost, latency, run total vs. budget) followed by each full response under its own heading. Committed to git. It renders on GitHub, and diffs between runs are readable.
- **B — local-only Markdown**: same files and format as A, but `runs/` is gitignored. Nothing a model writes ever reaches the public repo. The budget ledger also stays local, so a fresh clone starts at $0 spent.
- **C — committed HTML columns**: same JSON, but the comparison is a single self-contained `comparison.html` with three true columns (you open it in a browser). It's more literally side-by-side, but GitHub shows it as source, not rendered.

**Recommendation**: (by Ledger 5.5, Claude Opus 5.5, 2026-11-12)

**A — committed Markdown.** *Rationale*: The input is fictional (see Assumptions), and the saved request deliberately excludes headers, so there's nothing secret to leak. The key lives only in the `Authorization` header, which is never written. Committing turns every run into evidence that later versions (scoring, v1 inputs) can be checked against, which is what this methodology wants from substrate. A metrics table plus stacked responses is readable at v0's scale of three answers. *Confidence*: 0.75 — because the leak argument rests on code I haven't written yet. I'll add a test that scans every saved file for the key's value before anything is committed. *If wrong*: if you'd rather no model output be public at all (e.g. a model produces something embarrassing or off-topic), this flips to **B**. If reading stacked responses proves tiring after the first run, it flips to **C**, or to A plus an HTML view.

**ANS:** (by Irene Cui)
A — because committed runs give later versions (scoring, real filings) a record to check against, and the input is fictional. Required: the test that scans every saved file for the key must exist and pass before any run is committed.

---

## Supporting Materials

### COD: earnings-snippet-draft
Fictional company. Figures are internally consistent: 412.6 / 380.6 = +8.4%, 52.3 / 412.6 = 12.7%.

```text
Halvern Instruments, Inc. (fictional) — Q3 FY2026 results

[S1] Revenue was $412.6 million, up 8.4% from $380.6 million in Q3 FY2025.
[S2] Gross margin was 41.2%, compared with 39.8% a year earlier.
[S3] Operating income was $52.3 million, an operating margin of 12.7%.
[S4] Operating expenses include a one-time restructuring charge of $4.1 million.
[S5] Net income was $38.9 million, or $1.17 per diluted share, versus $33.1 million, or $0.99, a year earlier.
[S6] Free cash flow was $41.0 million.
[S7] Guidance: Q4 FY2026 revenue of $420–$435 million; full-year diluted EPS of $4.40–$4.55.
```

[S4] is deliberate: a careful analyst should mention it when interpreting [S3]. It gives the comparison something beyond copying numbers.

### COD: question-draft
```text
Using only the earnings snippet above, summarize this quarter's results.
Cite the source label (e.g. [S1]) for every number you state.
If you compute a number that is not in the snippet, show the inputs and cite their labels.
```

The third line is my addition to your example. Without it, a model that computes, say, operating-margin expansion either cites nothing or cites misleadingly, and v0 would hide that difference instead of showing it.

### FIL: price-scan
- `scripts/ephemeral/2026-11-12-openrouter-price-scan.py`: reads the public `/api/v1/models` listing (no key) and prints the cheapest models per vendor plus details for named IDs. Re-run it before changing the trio, because prices drift. `--endpoints <file>` mode lists the providers for one model; that's how the DeepSeek pin below was chosen.

### DOC: deepseek-v4.1-flash-providers (2026-11-12)
OpenRouter's public `/api/v1/models/deepseek/deepseek-v4.1-flash/endpoints` lists **38 endpoints and no first-party DeepSeek endpoint**. Quantization ranges over fp4, mxfp4, fp8 and "unknown"; output price ranges from $0.336 to $12.00 per 1M. The headline price on the model list ($0.022 / $0.40) is simply the cheapest endpoint (Morph, fp8). Unpinned, consecutive runs could hit different precisions of "the same model," which is exactly the confound Irene's pin removes.

---

## Decision

### Context
v0 has to answer one question cheaply and legibly: given identical, labelled inputs, do models differ in how they summarize and cite? Scope is fixed by the brief. Irene answered all three questions on 2026-11-12.

### Chosen

1. **Models (QST-MODEL-TRIO, override: four instead of three)**:
   - `anthropic/claude-haiku-5.5`
   - `openai/gpt-6-luna`
   - `google/gemini-3.1-flash-lite`
   - `deepseek/deepseek-v4.1-flash`, **pinned to DeepInfra fp8** (`provider: {order: ["deepinfra"], quantizations: ["fp8"], allow_fallbacks: false}`)

   **Why DeepInfra fp8** (Ledger's pick within Irene's "pin to one provider"; override freely): fp8 is the precision DeepSeek's models are released in, so it's the closest thing to the reference weights when no first-party endpoint exists. DeepInfra is a long-running provider with a declared (not "unknown") quantization, and its standard tier, unlike `flex`, isn't preemptible. Cost is $0.14 / $0.42 per 1M, still under $0.001 per call. With `allow_fallbacks: false`, if DeepInfra is down the DeepSeek call **fails visibly** instead of silently landing on another precision. A failed call is recorded in the comparison as a failure, not dropped.
2. **Settings (QST-RUN-SETTINGS, A: vendor defaults)**: the request carries only `model`, `messages`, and (for DeepSeek only) the provider pin. No temperature, max_tokens, or reasoning parameters are sent. Each saved JSON records what was sent and everything OpenRouter reports back: the model and provider actually served, finish reason, prompt, completion and reasoning token counts, cost, and latency.
3. **Output (QST-OUTPUT, A: committed Markdown)**: `runs/<UTC-stamp>/<model-slug>.json` ×4 + `comparison.md` (metrics table, then each full response). Committed to git. **Gate condition (Irene's requirement)**: a test that scans every file under `runs/` for the live key's value must exist and pass before any run is committed. It joins `just gate`, so the Fifth Directive enforces it.

**Rationale**: Irene's override keeps option A's vendor spread *and* adds B's open-weight axis. She weighed the confound I raised against B and neutralized it with the provider pin instead of dropping the model. Vendor defaults put the "how a normal user experiences it" question ahead of my controlled-conditions framing. That's a legitimate research question, and recording what each response reports keeps it auditable.

**Trade-offs accepted**:
- Output differences mix model capability with each vendor's default settings (temperature, whether reasoning is on). That's the price of option A, accepted deliberately.
- The DeepSeek pin is an asymmetry: it's the only model with a routing constraint. It's justified because the closed models are served from the vendor's own weights wherever OpenRouter routes them, while open-weight hosts differ in precision.

### Consequences
- **"Parameters actually used" is only partly observable.** With vendor defaults we send no parameters, and providers don't report the effective temperature. We *can* record what we sent, the provider and model actually served, the reasoning token count (which shows whether thinking happened), and the finish reason. The comparison table will say this rather than imply more.
- The budget guard can't bound output with `max_tokens` (not sent, under A). It estimates conservatively instead: 4,000 output tokens per model at list price, which comes to $0.0118 per four-model run (`--dry-run`, 2026-11-12; Iteration 2 said "≤ $0.01", but the real arithmetic is slightly higher). The $9.00 stop line is unchanged.
- The `runs/` key-leak test is part of the gate from the first commit that adds `runs/`.

---

## Open Follow-ups

- [ ] Later step (not v0): **automatic scoring**. Every number cited, every citation correct, computed numbers derivable from cited inputs, [S4] mentioned.
- [ ] Later step (not v0): **SEC EDGAR fetching**, replacing the fictional snippet with real filings. This needs a labelling step that turns a filing into [S#] facts.
- [ ] Later step (not v0): **price prediction**. It's a different question from summarization and will need its own ADR on evaluation, since look-ahead leakage is the classic trap.
- [ ] Unverified assumption: OpenRouter returns `usage.cost` in the response body. Verify on the first live call.
- [ ] Unverified assumption: the DeepSeek provider pin (`order: ["deepinfra"]` + `quantizations: ["fp8"]`) lands on the `deepinfra/fp8` endpoint, not `deepinfra/fp8/flex` or `/priority`. Check the reported provider on the first call. If it's ambiguous, pin by endpoint tag instead.
- [x] ~~Unconfirmed: the $9.00 budget stop line~~ Approved by Irene, 2026-11-12. The fictional company was confirmed in her QST-OUTPUT answer. The DeepInfra fp8 pin was also confirmed the same day.
- [ ] Concern: model IDs and prices drift. The price scan is dated, so re-check before each new trio.

---

## Action Items

- [x] Answer QST-MODEL-TRIO, QST-RUN-SETTINGS, QST-OUTPUT - Owner: Irene (done 2026-11-12)
- [x] Approve the $9.00 stop line and the DeepInfra pin - Owner: Irene (approved 2026-11-12)
- [ ] Review the snippet and question drafts (Supporting Materials). **Blocks the first live run**; the code can be built meanwhile - Owner: Irene
- [x] Build `showdown.py` + `models.toml` (4 models, DeepSeek pin) + `inputs/` - Owner: Ledger 5.5 (2026-11-12)
- [x] Tests: budget guard refuses past $9.00; key-leak scan over `runs/`; add `uv run pytest` to `just gate` - Owner: Ledger 5.5 (2026-11-12, 10 tests)
- [ ] First live run (est. < $0.01); verify `usage.cost` and the DeepSeek provider; record actual costs in Iteration 3 - Owner: Ledger 5.5

---

## Validation

- [ ] Irene Cui: Decision captured matches intent
- [ ] Irene Cui: Snippet and question drafts are acceptable

---

## Iterations

### Iteration 1 (2026-11-12)
- Trigger: initial brief from Irene Cui, first session
- Contributors: Irene Cui, Ledger 5.5 (Claude Opus 5.5)
- Changes: scope captured; live OpenRouter price scan; three decisions raised with recommendations; snippet and question drafted
- Outcome: Draft, awaiting answers

### Iteration 2 (2026-11-12)
- Trigger: Irene answered all three questions via the ADR Manager
- Contributors: Irene Cui (answers), Ledger 5.5 (processing)
- Changes: four models instead of three (Irene's override of my A recommendation, adding B's DeepSeek); vendor defaults instead of my recommended pinned settings (her A over my B); committed Markdown with a mandatory key-leak test (A, as recommended, plus her gate condition). I chose the DeepSeek provider after listing its 38 OpenRouter endpoints (DOC: deepseek-v4.1-flash-providers). Decision section filled.
- Outcome: `Draft → Accepted`; implementation next

### Iteration 3 (2026-11-12)
- Trigger: Irene: "start building"
- Contributors: Ledger 5.5
- Changes: `showdown.py` (stdlib only: urllib + tomllib), `models.toml`, `inputs/snippet.txt` + `inputs/question.txt` (verbatim from the COD drafts above), `tests/test_showdown.py` (10 tests), `pytest` wired into `just gate`. Every file the script writes goes through `safe_write()`, which refuses any text containing the key's value or a key-shaped string. That is defense in depth on top of the committed-runs scan Irene required. `--dry-run` checks the budget without a key or any API call.
- Outcome: `Accepted → Partially Implemented`; the live run waits on Irene's snippet/question review

---

## Links

- Related code: `scripts/ephemeral/2026-11-12-openrouter-price-scan.py`
- OpenRouter model list (public): https://openrouter.ai/api/v1/models
