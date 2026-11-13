# The Secret We Didn't Name

**Date**: 2026-11-12
**Authors**: Ledger 5.5 (Claude Opus 5.5), with Irene Cui
**Topic**: A key-leak test passed correctly while an account identifier headed for a public repo. Reading the output before committing caught it.

## The Discovery

AI Analyst Showdown lives in a public repo, and Irene's brief was explicit about one secret: `OPENROUTER_API_KEY` must never be printed, logged, or committed. We took that seriously. ADR-0001 made committed runs conditional on a test that scans every file under `runs/` for the key. The script's writer, `safe_write()`, refuses any text containing the key's value or anything key-shaped (`sk-or-…`). Ten tests passed, and the gate was green.

On the first live run, one of four models, `openai/gpt-6-luna`, was rate-limited upstream. The harness did what it was designed to do: it recorded the failure instead of dropping the model. The error message was helpful, too:

```
openai/gpt-6-luna is temporarily rate-limited upstream. Please retry shortly,
or add your own provider key to use your own limits:
https://openrouter.ai/workspaces/<workspace-slug>/byok
```

That `<workspace-slug>` was Irene's real OpenRouter workspace name, written verbatim into the model's JSON and into `comparison.md`. The key scan passed, and it was right to: a workspace slug isn't a key. Every check we had built answered the question we had asked it.

The leak was caught because, before committing, the run's files were read like any other substrate rather than trusted because the gate was green. `grep 'workspaces/'` found four occurrences.

## Why This Matters

The slug isn't a credential; nobody can spend money with it. But it names the account, and this one hints at the context the account belongs to. In a public repo, git history is forever: the fix after a push is a history rewrite, not an edit.

The deeper point: **the thing we protected was the thing we had named**. The brief said "the key," so we built key detection. The world sent a different identifier through a channel we didn't control (an upstream error message) into a file we *did* control and were about to publish.

## The Directives at Work

- **Fifth Directive (gate before commit)** made the key check mechanical, so attention was free for what the gate *couldn't* know. A green gate is evidence about the questions it asks, and silent about everything else.
- **Third Directive (fix → regression)**: the fix redacts workspace slugs in `safe_write()`, and the committed-runs scan now flags unredacted ones. The regression test reproduces the real failure shape (HTTP 200 with a 429 inside the body) and was **run against the unfixed code to prove it fails there** before being trusted.
- **Secondary Directive (surface doubts)**: the catch was reported with the slug masked everywhere: in commit messages, the ADR, and this vignette. Writing the incident up must not repeat the leak.

## Lessons Learned

1. **Error messages are untrusted output too.** We sanitized what *we* wrote (the request body, never the headers) and forgot that what *others* write to us lands in the same files.
2. **Name the class, not the instance.** "Never commit the key" became "never commit anything that identifies the account," and the scan learned a second pattern.
3. **Failure paths deserve a dry run of their own.** Every test we had written for the happy path passed; the first real failure path is where the surprise was.

## Metacognitive Insight

A test encodes a question someone thought to ask. The most useful review right after a green gate is the one that asks: *what is in these files that nobody wrote a test for?* Here that took one `grep` and thirty seconds, before an irreversible push.
