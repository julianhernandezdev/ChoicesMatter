Sync project documentation to match what was recently shipped.

**Steps:**

1. Run `git log --oneline -20` to see recent commits.
2. Read `ROADMAP.md` and `CLAUDE.md` in full.
3. Read the diff for any source files touched in those commits (`git show <hash> -- <file>`) to understand exactly what changed.

**ROADMAP.md updates:**
- For each item in Near-term, Medium-term, or Longer-term that matches a recent commit, move the entire entry into the **Shipped** section — insert it at the top of that section, above existing Shipped entries.
- Replace the `**Plan:**` block with a concise `**Implemented:**` one-liner naming the key files, classes, and fields changed. Match the style of the existing Shipped entries exactly (single line, no bullets).
- Leave all other sections and entries untouched.

**CLAUDE.md updates — only edit what actually changed:**
- New story JSON fields on nodes, choices, overlays, or insets → add a row to the correct field table (Required column, Notes column — match existing row style).
- New validation rules → add a bullet to the Validation Rules list.
- New or changed `Display` methods or signatures → update the Display Layer table.
- New Engine behaviors → update the relevant prose section.
- No new sections, no narrative prose, no reformatting of untouched content.

After editing, print a brief summary: which ROADMAP item(s) moved to Shipped and which CLAUDE.md sections were updated.
