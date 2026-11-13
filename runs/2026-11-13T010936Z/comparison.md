# Showdown run 2026-11-13T010936Z

Same input, same question, every model. Settings are **vendor defaults**: no temperature, max_tokens or reasoning parameters were sent, and providers do not report the effective temperature. The reasoning-token count shows whether the model thought before answering. Decisions: ADR-0001.

| Model | Served by | Prompt tok | Output tok | Reasoning tok | Cost (USD) | Latency | Finish |
|---|---|---:|---:|---:|---:|---:|---|
| `anthropic/claude-haiku-5.5` | Claude Platform on AWS | 360 | 1236 | 640 | $0.000654 | 5.5s | stop |
| `openai/gpt-6-luna` | — | — | — | — | — | 0.6s | **FAILED**: error: openai/gpt-6-luna is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/<redacted>/byok |
| `google/gemini-3.1-flash-lite` | Google | 291 | 291 | 0 | $0.000509 | 1.4s | stop |
| `deepseek/deepseek-v4.1-flash` | DeepInfra | 275 | 1886 | 1675 | $0.000831 | 12.0s | stop |

**This run**: $0.001994  ·  **Spent to date**: $0.0020 of $10.00 (stop line $9.00)

<details><summary>Input and question sent to every model</summary>

```text
Halvern Instruments, Inc. (fictional) — Q3 FY2026 results

[S1] Revenue was $412.6 million, up 8.4% from $380.6 million in Q3 FY2025.
[S2] Gross margin was 41.2%, compared with 39.8% a year earlier.
[S3] Operating income was $52.3 million, an operating margin of 12.7%.
[S4] Operating expenses include a one-time restructuring charge of $4.1 million.
[S5] Net income was $38.9 million, or $1.17 per diluted share, versus $33.1 million, or $0.99, a year earlier.
[S6] Free cash flow was $41.0 million.
[S7] Guidance: Q4 FY2026 revenue of $420–$435 million; full-year diluted EPS of $4.40–$4.55.

Using only the earnings snippet above, summarize this quarter's results.
Cite the source label (e.g. [S1]) for every number you state.
If you compute a number that is not in the snippet, show the inputs and cite their labels.
```

</details>

---

## `anthropic/claude-haiku-5.5`

**Halvern Instruments, Q3 FY2026 summary**

- **Revenue** grew 8.4% year over year to $412.6 million, from $380.6 million a year earlier [S1].
- **Gross margin** was 41.2%, up from 39.8% a year earlier [S2]. That is an improvement of 1.4 percentage points (41.2% − 39.8%) [S2].
- **Operating income** was $52.3 million, a 12.7% operating margin [S3]. Operating expenses include a one-time restructuring charge of $4.1 million [S4]. Excluding that charge, operating income would be $56.4 million ($52.3M + $4.1M) [S3, S4], or a 13.7% margin ($56.4M ÷ $412.6M) [S1, S3, S4]. This is a non-GAAP-style adjustment I computed, not a figure the company reported.
- **Net income** was $38.9 million, or $1.17 per diluted share, compared with $33.1 million, or $0.99, a year earlier [S5]. That is growth of about 17.5% in net income ($38.9M ÷ $33.1M − 1) and about 18.2% in diluted EPS ($1.17 ÷ $0.99 − 1) [S5].
- **Free cash flow** was $41.0 million [S6]. This is about 105% of net income ($41.0M ÷ $38.9M) [S5, S6].
- **Guidance:** Q4 FY2026 revenue is expected at $420–$435 million, and full-year diluted EPS at $4.40–$4.55 [S7].

The snippet does not give prior-year operating income or margin, so I can't compare operating profitability year over year. It also lacks year-to-date figures, so I can't check the full-year EPS guidance against results to date.

---

## `openai/gpt-6-luna`

**FAILED**: error: openai/gpt-6-luna is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/<redacted>/byok. No answer from this model in this run.

---

## `google/gemini-3.1-flash-lite`

Halvern Instruments, Inc. reported strong growth for Q3 FY2026:

*   **Revenue:** Totaled $412.6 million [S1], representing an 8.4% increase from the $380.6 million reported in Q3 FY2025 [S1].
*   **Profitability:** Gross margin improved to 41.2%, up from 39.8% in the prior-year period [S2]. Operating income reached $52.3 million [S3], reflecting a 12.7% operating margin [S3]. This performance included a $4.1 million one-time restructuring charge [S4].
*   **Net Income and EPS:** Net income rose to $38.9 million ($1.17 per diluted share) from $33.1 million ($0.99 per diluted share) in Q3 FY2025 [S5].
*   **Cash Flow:** The company generated $41.0 million in free cash flow [S6].
*   **Forward-Looking Guidance:** Halvern projects Q4 FY2026 revenue to be between $420 million and $435 million [S7], with full-year diluted EPS expected in the range of $4.40 to $4.55 [S7].

---

## `deepseek/deepseek-v4.1-flash`

- Revenue was $412.6 million [S1], up 8.4% [S1] from $380.6 million in Q3 FY2025 [S1].
- Gross margin was 41.2% [S2], compared with 39.8% a year earlier [S2].
- Operating income was $52.3 million [S3], an operating margin of 12.7% [S3]; operating expenses included a one-time restructuring charge of $4.1 million [S4].
- Net income was $38.9 million [S5], or $1.17 per diluted share [S5], versus $33.1 million [S5], or $0.99 [S5], a year earlier.
- Free cash flow was $41.0 million [S6].
- Guidance: Q4 FY2026 revenue of $420–$435 million [S7]; full-year diluted EPS of $4.40–$4.55 [S7].
