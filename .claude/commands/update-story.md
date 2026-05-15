Bring an existing story up to date with all current engine features, weaving new mechanics into the narrative rather than bolting them on.

**Input:** The argument is a story name or path — e.g. `dead_air`, `the_locked_room`, or `stories/dead_air.json`. Resolve it to the correct file under `stories/`.

**Steps:**

1. Read `CLAUDE.md` in full. Extract the complete feature set available to story authors.

2. Read the target story in full. Understand:
   - Its tone, setting, and genre (horror, thriller, sci-fi, etc.)
   - The emotional register of each node (dread, relief, ambiguity, etc.)
   - Which flags are already in use and what they track
   - The branching structure and all possible paths

3. Audit the story against the feature checklist below. For each item, note whether it's present and, if absent, whether it would *serve* this specific story:

   **Meta**
   - [ ] `est_time` — is the read time documented?
   - [ ] `warnings` — does the content warrant any trigger warnings?

   **Nodes**
   - [ ] `scene` — are locations established and carried forward naturally?
   - [ ] `choice_number_color` — does the color reinforce the node's emotional register (e.g. red for danger, green for safety, dim for ambiguity)?
   - [ ] `insets` (before) — is there data, logs, or internal monologue that belongs *before* the prose?
   - [ ] `insets` (after) — is there data, logs, or internal monologue that belongs *after* the prose?
   - [ ] `insets` with `requires` — are there insets that should only appear when the player has made certain choices?
   - [ ] `overlays` (before) — is there whispering context or intrusive memory that belongs *before* the choices?
   - [ ] `overlays` (after) — is there lingering atmosphere that belongs *after* the choices?
   - [ ] `overlays` with `requires` — are there echoes or callbacks that should only surface after certain flags are set?

   **Choices**
   - [ ] `color` (per-choice override) — should any individual choice stand out from the node's default color?
   - [ ] `obfuscated` — is there a choice whose true nature the player shouldn't know in advance?
   - [ ] `requires` — are there choices that should only appear after certain prior decisions?

4. For every absent feature that *would serve the story*, design how to add it. Prioritize narrative fit over mechanical coverage — a feature that would feel forced should be left out with a note. Consider:

   - **`scene`:** Where does each scene take place? Even sparse scene labels ("The Corridor", "Your Office", "Somewhere Else") ground the reader. Look for natural location shifts in the existing node structure.
   - **`choice_number_color`:** Match the palette to the emotional weight. Horror nodes lean red or dim. Safe nodes lean green or cyan. Uncertain nodes lean yellow or white.
   - **`insets`:** What is happening *around* the prose that the player notices but doesn't act on? System logs, overheard fragments, bodily sensations, memories. These should feel like marginal annotations to the main text.
   - **`overlays`:** What haunts the space *around* the choices? Recurring phrases, intrusive thoughts, environmental sounds. `after` overlays linger in the reader's mind as they decide.
   - **`obfuscated`:** Is there a choice that the character would make blindly — something they cannot name or fully understand? This works best on pivotal or irreversible choices.
   - **`requires`:** Which choices or insets or overlays should only exist if the player has taken a specific path? Use flag gating to reward attentive players with callbacks or restrict options that would be narratively incoherent.
   - **`warnings`:** Read for content themes — death, violence, psychological distress, etc.

5. Write the updated story JSON. Preserve all existing prose and structure exactly — do not rewrite the story's voice or plot. Only add:
   - New fields on existing nodes/choices (scene, color, insets, overlays, obfuscated)
   - Flag gates on existing choices/insets/overlays where they make narrative sense
   - Meta fields that were missing

   If a flag gate requires a new `sets` on an upstream choice, add it — but do not add nodes, reroute `next` values, or alter any existing prose text.

6. Validate the finished JSON against CLAUDE.md's validation rules before writing: all `next` values point to real nodes, flag dicts have string keys + boolean values, `ending_type` is valid, `position` is `before`/`after` only.

7. Write the updated file back to the same path.

8. Print a summary: for each feature added, name it, the node(s) it was added to, and one sentence on the narrative reason for the placement. For any feature deliberately skipped, say why.
