# Suggestions

Community-proposed features for Choices Matter. Two ways to get an idea in:

- **Rough idea or discussion** → [open a GitHub Issue](https://github.com/julianhernandezdev/ChoicesMatter/issues/new) with the `suggestion` label — no fork needed
- **Fleshed-out proposal** → PR this file using the template at the bottom

The maintainer reviews Issues and PRs regularly. Promising Issues get graduated into this file. Accepted entries move into the internal roadmap and get implemented.

---

## Under Consideration

### Variable Text Substitution
**What:** Authors write `{player_name}` or `{item}` inside node `text` and the engine substitutes the matching value from the player's current flag state.
**Why:** Enables personalisation and callbacks to earlier choices without full node branching — one node can address the player by a name they chose three scenes ago.
**Suggested by:** maintainer

---

### Conditional Inline Text
**What:** Authors write `{flag?shown if set|shown if unset}` spans directly inside node `text` — the fallback is optional and collapses to nothing when omitted.
**Why:** Small conditional variations (a name, a detail, a tone shift) without branching to a whole new node — keeps the story graph lean.
**Suggested by:** maintainer

---

### Story Graph Visualizer
**What:** A CLI script (`scripts/graph_story.py`) that reads a story JSON and outputs a Mermaid diagram of the full node graph — nodes, choices, flags, and endings.
**Why:** Authors can audit their story structure visually and catch unreachable branches or dead ends that the validator doesn't surface.
**Suggested by:** maintainer

---

### Themes
**What:** Named color scheme presets (`noir`, `amber`, `paper`) selectable in `settings.json` — all contained in `display.py` and `config.py`, no engine changes.
**Why:** Different stories have different tones; a horror story in amber reads differently than the same text in the default teal.
**Suggested by:** maintainer

---

### Chapters / Multi-File Stories
**What:** Ending nodes can declare `"next_story": "chapter_2"` — the engine chains into the next story, carrying flag state across the boundary.
**Why:** Enables serialised episodic fiction where choices in chapter one echo in chapter three, without requiring one giant story file.
**Suggested by:** maintainer

---

### Achievements
**What:** Cross-run, cross-story unlocks defined in story `meta` and stored in `saves/achievements.json` — survive save deletion and persist across playthroughs.
**Why:** Rewards exploration beyond the gallery: completing all endings, finding a hidden path, or reaching a specific flag state.
**Suggested by:** maintainer

---

### Choice Graph / Replay
**What:** An in-game map of the full story choice tree, unlocked only after all endings are found. Players can inspect every branch and jump into replay from any node.
**Why:** A completion reward rather than a navigation aid — gives gallery hunters a payoff without making the map a crutch during a first run.
**Suggested by:** maintainer

---

### Web Export (Single-File)
**What:** A CLI script (`scripts/export_web.py`) generates a self-contained `.html` file from a story JSON — no server, no repo, shareable as a single attachment.
**Why:** Authors can share a story with anyone who has a browser, distinct from the GitHub Pages player which requires the full repo.
**Suggested by:** maintainer

---

### Corrupted Text Rendering
**What:** A `"corrupted"` named style on insets and overlays renders text with glitch substitutions — random `█`, `▓`, `░` swaps and stutter repeats. Intensity is configurable.
**Why:** A pure display effect for institutional horror or degraded-signal aesthetics — the underlying text is unchanged, so it degrades gracefully.
**Suggested by:** maintainer

---

## In-Flight

### Dev / Author Mode
**What:** `python main.py --debug` renders the current flag state in a dim panel below each node — display-only, zero engine changes.
**Why:** Invaluable for playtesting: authors can see exactly which flags are set without adding temporary `sets`/`requires` entries to probe state.
**Suggested by:** maintainer

---

### Accessibility Options
**What:** Reduced motion mode, high-contrast color scheme, and font-size hints — selectable in `settings.json` or the settings screen.
**Why:** Makes the game usable for players with motion sensitivity or low-vision needs without touching story content.
**Suggested by:** maintainer

---

## Shipped

### Web Player (GitHub Pages) *(shipped)*
**What:** A browser-based play mode hosted on GitHub Pages — same story JSON format, same flag system, same named styles. No Python or terminal required.
**Why:** Players click a link and play; authors can share stories with anyone regardless of technical setup.
**Suggested by:** maintainer

---

### Non-Boolean State (Counters & Strings) *(shipped)*
**What:** The flag system supports integer counters, strings, delta increments (`"+1"`), and threshold `requires` checks (`"trust": 3` means ≥ 3).
**Why:** Enables relationship scores, inventory counts, and stat-gated branches without separate tracking logic.
**Suggested by:** maintainer

---

### Settings Screen *(shipped)*
**What:** An in-game settings screen (`S` at the story picker) covering typewriter toggle, speed presets, and punctuation pause values — writes to `settings.json`.
**Why:** Players can tune the reading experience without editing a config file by hand.
**Suggested by:** maintainer

---

### Obfuscated Choices *(shipped)*
**What:** Choices marked `"obfuscated": true` render as `[REDACTED ██████]` — the player can still select them but doesn't see the label until after.
**Why:** Perfect for institutional horror or mystery: the option exists, you just don't know what it does.
**Suggested by:** maintainer

---

### Content Warnings *(shipped)*
**What:** Stories declare `meta.warnings` (a list of strings) shown in a yellow panel before launch; the story picker marks affected stories with `[!]`.
**Why:** Lets players opt out of content before they encounter it — a basic duty-of-care for sensitive themes.
**Suggested by:** maintainer

---

### Scene Context Headers *(shipped)*
**What:** An optional `"scene"` key on any node renders a dim location label above the story panel and carries forward until overridden.
**Why:** Spatial anchoring without repeating location prose — readers always know where they are.
**Suggested by:** maintainer

---

### Choice Number Color *(shipped)*
**What:** A `"color"` key on individual choices and a `"choice_number_color"` fallback on nodes control the color of choice number prefixes.
**Why:** Signals tone, faction, or mechanical state through color — danger in red, safety in green — without altering the prose.
**Suggested by:** maintainer

---

### Node Reachability Validator *(shipped)*
**What:** `scripts/validate_story.py` detects nodes unreachable from `start_node` and non-ending leaf nodes missing `is_ending`.
**Why:** Authors find out about dead zones at validate time, not mid-playtest.
**Suggested by:** maintainer

---

### Node Revisit Flags *(shipped)*
**What:** The engine automatically sets `visited_<node_id>: true` each time a node is entered. Authors use it in `requires` without any `sets` boilerplate.
**Why:** Enables "you've been here before" writing patterns without manual flag management.
**Suggested by:** maintainer

---

### Subfolder Directory Navigation *(shipped)*
**What:** The story picker supports subfolders inside `/stories/`. Top-level shows root stories alongside named folder entries; selecting a folder drills into it with a back option.
**Why:** As a story library grows, a flat list becomes unwieldy — authors can organise by genre, series, or status without any engine changes.
**Suggested by:** maintainer

---

## Propose Something

Fork the repo, add an entry below the last one in **Under Consideration**, and open a PR titled `suggestion: your title`. Keep it brief — you don't need to spec the implementation, just the what and why.

```
### Your Feature Title
**What:** one sentence describing the feature
**Why:** the problem it solves or value it adds for players or story authors
**Suggested by:** @your-github-username
```
