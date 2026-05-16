Sync project documentation to match what was recently shipped.

**Steps:**

1. Run `git log --oneline -20` to see recent commits. Identify which commits are new (unreflected in docs) and which source areas they touch: story format, display layer, engine, save/gallery, config, scripts.

2. Read `ROADMAP.md` in full.

3. For each commit that changed source files, run `git show <hash> -- <file>` to read the exact diff. Do this for source files only — skip test files and story JSON.

4. Based on what actually changed, read only the relevant CLAUDE.md sections:
   - Story JSON fields changed → read the **Story JSON Format** section only
   - Display method added/changed → read the **Display Layer** table only
   - Engine behavior changed → read the **Flag System** or **Save System** sections only
   - Validation rules changed → read the **Validation Rules** section only
   - If nothing in CLAUDE.md needs updating, skip reading it entirely

**ROADMAP.md updates:**
- For each item in Near-term, Medium-term, or Longer-term that matches a recent commit, move it into the **Shipped** section — insert at the top, above existing Shipped entries.
- Replace the `**Plan:**` block with a concise `**Implemented:**` one-liner naming the key files, classes, and fields changed. Match the style of existing Shipped entries exactly.
- Leave all other sections and entries untouched.

**CLAUDE.md updates — only edit what actually changed:**
- New story JSON fields → add a row to the correct field table (Required column, Notes column — match existing row style).
- New validation rules → add a bullet to the Validation Rules list.
- New or changed `Display` methods or signatures → update the Display Layer table.
- New Engine behaviors → update the relevant prose section.
- No new sections, no narrative prose, no reformatting of untouched content.

After editing, print a brief summary: which ROADMAP item(s) moved to Shipped and which CLAUDE.md sections were updated (or "no CLAUDE.md changes needed").
