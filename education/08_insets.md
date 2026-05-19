# 08 — Insets

**Story:** `stories/examples/08_insets.json`
**Feature:** Styled text blocks inside the story panel, positioned before or after the prose, with optional flag gating.

## What the story does

The first node has two insets: one `"before"` with `style: "system"` and one `"after"` with `style: "memory"`. The second node has a conditional inset (`requires: { "read_note": true }`) that only appears after the player has passed through the first node.

## Engine code path

**Data model** — `Inset` is a dataclass in `src/story.py:40`:

```python
@dataclass
class Inset:
    text: str
    position: str = "before"   # "before" | "after" relative to node text
    style: str = ""             # named style key; "" = dim italic default
    requires: dict = field(default_factory=dict)
```

Parsed by `StoryLoader._parse_insets()` (`src/story.py:347`). Position defaults to `"before"` and must be `"before"` or `"after"`.

**Filtering in `Engine.run()`** (`src/engine.py:49`):

```python
visible_insets = [i for i in node.insets if self._check_requires(i.requires)]
before_insets = [i for i in visible_insets if i.position == "before"]
after_insets  = [i for i in visible_insets if i.position == "after"]
```

Insets with unmet `requires` are excluded before splitting into before/after lists. The two lists are passed to `display.show_node()`.

**Rendering — `Display._node_panel()`** (`src/display.py:246`):

```python
parts: list = []
for inset in (before_insets or []):
    parts.append(self._inset_renderable(inset))
    parts.append(Rule(style="dim white"))   # separator rule
parts.append(Text(text))                   # main prose
for inset in (after_insets or []):
    parts.append(Rule(style="dim white"))   # separator rule
    parts.append(self._inset_renderable(inset))
content = Group(*parts) if len(parts) > 1 else Text(text)
```

Each inset gets a dim `Rule` separator on the side facing the prose — before-insets get a rule after them, after-insets get a rule before them. If there are no insets, `content` is just `Text(text)` with no `Group` overhead.

**`Display._inset_renderable()`** (`src/display.py:280`) — when `inset.style` is non-empty, it calls `_style_cfg()` to resolve the config for that named style (see example 10). When `inset.style == ""`, it falls back to `style="dim italic"` with no prefix.

**Insets on ending nodes** — `Engine.run()` computes `before_insets` and `after_insets` but only passes them to `display.show_node()` for non-ending nodes. On ending nodes, `display.show_ending()` is called instead, which accepts `overlays` but not insets. **Insets on an ending node are silently dropped.** Use `overlays` to attach conditional content to ending nodes.

## Key references

| Symbol | Location |
|---|---|
| `Inset` dataclass | `src/story.py:40` |
| `_parse_insets()` | `src/story.py:347` |
| Inset filtering in `Engine.run()` | `src/engine.py:49` |
| `Display._node_panel()` | `src/display.py:246` |
| `Display._inset_renderable()` | `src/display.py:280` |
