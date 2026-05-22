# Contributing to Choices Matter

Thanks for your interest. Here's how to get involved.

---

## Suggesting a Feature

Two lanes — pick whichever fits:

**Lane 1 — GitHub Issue** (lowest friction)
Got a rough idea, a question, or want to float something before writing it up? [Open an issue](https://github.com/julianhernandezdev/ChoicesMatter/issues/new) with the `suggestion` label. No fork needed.

**Lane 2 — PR to `SUGGESTIONS.md`** (considered proposal)
Idea clear enough to describe in a sentence or two? Fork the repo, add an entry to `SUGGESTIONS.md` using the template at the bottom of that file, and open a PR titled `suggestion: your title`. Include what the feature does and why it's valuable — you don't need to spec the implementation, that happens internally once an idea is accepted.

The maintainer reviews both lanes regularly. Promising issues get graduated into `SUGGESTIONS.md`; accepted entries move into the internal roadmap.

---

## Reporting a Bug

[Open an issue](https://github.com/julianhernandezdev/ChoicesMatter/issues/new). Include:
- What you did
- What you expected
- What actually happened
- OS and Python version

---

## Contributing Code

Before opening a code PR:
1. **Check first** — if the feature isn't in `SUGGESTIONS.md` under Accepted or an open issue, a code PR is likely to be closed without review. Get the idea accepted first.
2. **One thing per PR** — one feature or fix, not a bundle. Large refactors should be discussed in an issue before any code is written.
3. **Tests required** — run `pytest` before opening. It must pass clean. New behaviour needs new tests; see the existing test files in `/tests/` for patterns.
4. **Follow existing conventions** — read `CLAUDE.md` for engine architecture, story format rules, and the display/config boundary. The short version: story content never belongs in code, `rich` is only imported in `display.py`, validation fails fast at load time.
5. **No speculative additions** — don't add error handling, abstractions, or features beyond what the PR description says it does.

---

## Writing a Story

Drop any `.json` file into `/stories/` — no code changes needed. See `README.md` for the full story format reference, or use an existing story in `/stories/` as a starting point.

---

## AI Tooling

This project uses Claude (Anthropic) extensively — for engine development and most story content. Contributors are welcome to use AI tools in their own workflow. Story contributions should disclose if AI-generated content is included.
