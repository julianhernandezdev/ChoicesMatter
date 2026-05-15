# Suggestions

Community-proposed features for Choices Matter. Two ways to get an idea in:

- **Rough idea or discussion** → [open a GitHub Issue](https://github.com/julianhernandezdev/ChoicesMatter/issues/new) with the `suggestion` label — no fork needed
- **Fleshed-out proposal** → PR this file using the template at the bottom

The maintainer reviews Issues and PRs regularly. Promising Issues get graduated into this file. Accepted entries move into the internal roadmap and get implemented.

---

## Under Consideration

### Node Reachability Validator
**What:** Extend `validate_story.py` to detect nodes that are defined but can never be reached from `start_node`, and non-ending leaf nodes that have no `is_ending` marker.
**Why:** Authors find out about dead zones at validate time, not mid-playtest — a broken branch is caught before the story ships.
**Suggested by:** maintainer

---

### Node Revisit Flags
**What:** The engine automatically sets a `visited_<node_id>: true` flag the first time a node is entered. Authors can use it in `requires` without adding manual `sets` entries to every choice that leads there.
**Why:** Enables "you've been here before" writing patterns — subtle acknowledgments and unlockable callbacks — without boilerplate flag management.
**Suggested by:** maintainer

---

### Variable Text Substitution
**What:** Authors write `{player_name}` or `{item}` inside node `text` and the engine substitutes the matching value from the player's current flag state.
**Why:** Enables personalisation and callbacks to earlier choices without full node branching — one node can address the player by a name they chose three scenes ago.
**Suggested by:** maintainer

---

## Accepted

*Nothing here yet — accepted suggestions move into the internal roadmap and get implemented.*

---

## Propose Something

Fork the repo, add an entry below the last one in **Under Consideration**, and open a PR titled `suggestion: your title`. Keep it brief — you don't need to spec the implementation, just the what and why.

```
### Your Feature Title
**What:** one sentence describing the feature
**Why:** the problem it solves or value it adds for players or story authors
**Suggested by:** @your-github-username
```
