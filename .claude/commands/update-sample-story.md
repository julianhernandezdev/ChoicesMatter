Update the engine feature showcase story so every documented feature is demonstrated at least once.

**Goal:** Keep `stories/test_scene_color.json` as a living reference that authors and contributors can play through to see all engine features in action. Whenever new features are added to the engine, this story should be updated to showcase them.

**Steps:**

1. Read `CLAUDE.md` in full. Build a checklist of every feature that story JSON can express:
   - Meta: `est_time`, `warnings`
   - Node: `scene` (explicit + inherited carry-forward), `choice_number_color`, `insets` (before/after, each named style, `requires`), `overlays` (before/after, each named style, `requires`), `is_ending` + `ending_type` (good, bad, neutral)
   - Choice: `requires`, `sets`, `color` (per-choice number color override), `obfuscated`

2. Read `stories/test_scene_color.json`. For each item on the checklist, note whether it is currently demonstrated with a comment like `[x] scene (intro node)` or `[ ] obfuscated`.

3. Read two or three of the richer story files (e.g. `stories/dead_air.json`, `stories/the_locked_room.json`) to understand the authoring style and tone for inset/overlay copy.

4. Rewrite `stories/test_scene_color.json` in place so that:
   - Every checklist item is demonstrated at least once
   - The story remains short (8–12 nodes max) and playable top-to-bottom
   - At least one path exercises the flag system end-to-end: a choice that `sets` a flag, an inset and an overlay gated on that flag, and a choice gated on that flag
   - All three `ending_type` values appear (good, bad, neutral) across the possible endings
   - One choice uses `obfuscated: true`
   - `scene` changes at least once mid-story to show the carry-forward behavior; at least one node inherits the scene silently
   - `warnings` is non-empty in meta so the warning screen is exercised
   - Prose is tight and functional — this is a tech demo, not a story; clarity beats atmosphere

5. Validate the finished JSON mentally against the rules in the `Validation Rules` section of CLAUDE.md before writing. Check: all `next` values reference real node IDs, flag dicts have string keys and boolean values, `ending_type` is one of the three valid values, `position` fields are `before` or `after`.

6. Write the updated file to `stories/test_scene_color.json`.

7. Print a summary: list each checklist item and confirm it is now covered, noting the node ID where it appears.
