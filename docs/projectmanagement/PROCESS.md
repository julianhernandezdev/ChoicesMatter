# PROCESS

---

## Development Lifecycle

```
Discovery → Planning → Execution → Testing → Reflect → repeat
```

### Discovery
Identify the feature or fix. Source: PIPELINE.md (active queue), BACKLOG.md, open GitHub issues with the `suggestion` label, or ad-hoc observations during play-testing.

**Exit criteria:** The problem or goal is clearly stated. Known constraints and affected files are noted. Ready to plan.

### Planning
Write a spec (`docs/superpowers/specs/`) and/or implementation plan (`docs/superpowers/plans/`) for anything non-trivial. Trivial bug fixes skip straight to execution.

For engine features: identify which of the two engines (Python CLI, JS web) the change affects and whether a conformance fixture update is needed. Features that touch `engine.py` almost always need a JS port in `web/engine.js`.

If the work involves an RFC (`docs/rfcs/`), see **RFC / Spec Closing Discipline** below — a session touching an RFC has its own exit requirement in addition to this one.

**Exit criteria:** Affected files listed. Test plan exists. If a story format change: validator coverage is planned. Ready to code.

### Execution
Create a feature branch. Implement in this order for engine features: (1) story.py / model changes, (2) engine.py logic, (3) display.py rendering, (4) web/engine.js port, (5) web/app.js rendering, (6) CLAUDE.md update. Validate stories if the format changed.

**Exit criteria:** Tests pass (`pytest`; `node tests/test_web_engine.js` if JS changed). Story validator clean on all public stories. CLAUDE.md updated for any format or API changes.

### Testing
Manual play-test the golden path and any edge cases. For web changes: test both terminal and accessible modes. Check typewriter on/off. If stories were added or moved: run `scripts/sync_stories.py` and verify the manifest.

**Exit criteria:** Feature works end-to-end in both CLI and web player. No regressions observed. Manifest synced if stories changed.

### Reflect
Update CHANGELOG.md, BOARD.md (move to Done), and any stale roadmap/PIPELINE entries. Write a postmortem if something went wrong. Update this file if the process improved.

**Exit criteria:** Docs match what shipped. Branch merged. Commit message follows `type(scope): description` convention.

---

## RFC / Spec Closing Discipline

`docs/rfcs/` had no equivalent of `SUGGESTIONS.md`'s accept/reject/close cycle — RFCs 0001 and 0002 both sat at `Status: Draft` for months (2026-05 → 2026-09) with no forcing function, until an unrelated retrospective caught it. This is the fix.

**Rule:** any session that creates or substantively edits an RFC (`docs/rfcs/NNNN-*.md`) must not end with the RFC still at `Status: Draft`. Before the session closes, do one of:

1. **Move its Status** to `Accepted` or `Rejected`, with a linked implementation plan (`docs/superpowers/plans/`) if accepted, **or**
2. **Park it explicitly** — set `Status: Parked` and add a one-line `**Revisit by:** <date>` under the status line, stating what's blocking the decision.

A Draft RFC with no plan and no park date is the failure mode this rule exists to prevent — it reads as "someone will get to this" when nothing is actually tracking it.

**Prior-art check:** before accepting an RFC or writing a spec, search unmerged branches and remotes for existing design work on the same feature (`git branch -a`, `git log --all -i --grep=<feature>`) and record what was reconciled. RFC 0001 was accepted on 2026-09-19 without seeing a conflicting Chapters spec that lived only on a remote branch (POSTMORTEMS 2026-09-20).

**Weekly Triage Checklist** (below) picks up anything that slips through: scan `docs/rfcs/` for `Parked` entries past their `Revisit by` date and re-triage them.

---

## Contribution Pipeline

---

## The Two Lanes

| Lane | Format | Friction | Use for |
|---|---|---|---|
| GitHub Issue | Free-form, `suggestion` label | Lowest — no fork | Rough ideas, questions, discussions |
| PR to `SUGGESTIONS.md` | Structured entry template | Fork + PR | Clear, fleshed-out proposals |

Both funnel toward the same place: the internal roadmap (kept outside this repo).

---

## Triage Flow

```
GitHub Issue
    └─→ SUGGESTIONS.md (Under Consideration)
            └─→ internal roadmap (accepted + planned)
                    └─→ Shipped (code merged, entry removed from SUGGESTIONS.md)
```

---

## Weekly Triage Checklist

- [ ] Scan open issues with `suggestion` label
- [ ] Scan open PRs targeting `SUGGESTIONS.md`
- [ ] Move anything clearly off-scope: close with a brief comment, no explanation debt
- [ ] Move anything promising: see graduation steps below
- [ ] Scan `docs/rfcs/` for `Status: Draft` entries with no linked plan — should have closed same-session per RFC / Spec Closing Discipline above; re-triage now if one slipped through
- [ ] Scan `docs/rfcs/` for `Status: Parked` entries past their `Revisit by` date — re-triage: accept, reject, or re-park with a new date

---

## Graduating an Issue → SUGGESTIONS.md

1. Write the entry yourself (or ask the contributor to PR it)
2. Credit with `**Suggested by:** @their-username`
3. Open a PR titled `suggestion: [title]`, merge it
4. Close the original issue linking to the merged PR: *"Graduated to SUGGESTIONS.md — tracking here now."*

---

## Accepting a Suggestion

1. Edit `SUGGESTIONS.md`: move the entry from **Under Consideration** → **Accepted**
2. Add the implementation plan to the internal roadmap (not tracked in this repo)
3. Comment on the originating issue/PR so the contributor knows: *"Accepted — queued for implementation."*

---

## Marking Something Shipped

1. Remove the entry from `SUGGESTIONS.md` (clean) — or leave it in Accepted with a `*(shipped in vX.X)*` note if you want a public changelog feel
2. Close the originating issue/PR with a link to the commit or release

---

## Closing Without Accepting

Just close the issue or PR with a brief comment. You don't need to add anything to `SUGGESTIONS.md`. Examples:
- *"Outside the scope of where I want to take the engine right now."*
- *"Covered by [other issue/suggestion]."*
- *"This belongs in story authoring, not the engine."*

---

## Recommended GitHub Labels to Create

| Label | Color | Use |
|---|---|---|
| `suggestion` | `#0075ca` | Feature proposals (both lanes) |
| `bug` | `#d73a4a` | Confirmed bugs |
| `under consideration` | `#e4e669` | Triaged, evaluating |
| `accepted` | `#0e8a16` | Approved, in the internal roadmap |
| `wontfix` | `#ffffff` | Closed, out of scope |

---

## Seeded Entries

These three were seeded from the internal roadmap at launch and are already planned — public PRs for them are welcome but not required:

- **Node Reachability Validator** — extend `scripts/validate_story.py`
- **Node Revisit Flags** — auto-set `visited_<node_id>` flags in the engine
- **Variable Text Substitution** — `{var}` interpolation in node text

---

## Files

| File | Committed | Purpose |
|---|---|---|
| `SUGGESTIONS.md` | Yes | Public-facing curated list |
| `CONTRIBUTING.md` | Yes | Contributor instructions |
| Internal roadmap | No (kept outside this repo) | Internal planning, full implementation detail |
| `docs/projectmanagement/PROCESS.md` | Yes | This file |
| `docs/rfcs/` | No (local only) | Format/architecture RFCs; subject to the RFC / Spec Closing Discipline rule above |
