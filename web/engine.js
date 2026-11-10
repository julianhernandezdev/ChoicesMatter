const _INLINE_RE = /\{(\w+)\?([^|{}]*?)(?:\|([^{}]*?))?\}/g;

export function resolveInline(text, state = {}) {
  return text.replace(_INLINE_RE, (_, key, trueBranch, falseBranch) => {
    return state[key] ? trueBranch : (falseBranch ?? "");
  });
}

const _SUBST_RE = /\{(\w+)\}/g;

export function substituteVars(text, state = {}) {
  return text.replace(_SUBST_RE, (match, key) => {
    const val = state[key];
    return val !== undefined && val !== null ? String(val) : match;
  });
}

const _CORRUPT_RE = /\{corrupt(?::([0-9]*\.?[0-9]+))?(?::(consistent|random))?(?::(decay|cascade))?\}([\s\S]*?)\{\/corrupt\}/g;

function _textSeed(text, index) {
  const combined = text + String(index);
  let sum = 0;
  for (let i = 0; i < combined.length; i++) {
    sum = (sum + combined.charCodeAt(i) * (i + 1)) % 4294967296;
  }
  return sum;
}

export function resolveCorruption(text, nodeCorruption) {
  let nodeIntensity = null;
  let nodeMode = null;
  let nodeResolveStyle = null;
  if (typeof nodeCorruption === "number") {
    nodeIntensity = nodeCorruption;
  } else if (nodeCorruption && typeof nodeCorruption === "object") {
    if (nodeCorruption.intensity !== undefined) nodeIntensity = nodeCorruption.intensity;
    if (nodeCorruption.mode !== undefined) nodeMode = nodeCorruption.mode;
    if (nodeCorruption.resolve_style !== undefined) nodeResolveStyle = nodeCorruption.resolve_style;
  }

  const segments = [];
  let lastEnd = 0;
  let spanIndex = 0;
  let match;
  _CORRUPT_RE.lastIndex = 0;

  while ((match = _CORRUPT_RE.exec(text)) !== null) {
    if (match.index > lastEnd) {
      segments.push(text.slice(lastEnd, match.index));
    }
    const rawIntensity = match[1];
    const rawMode = match[2];
    const rawResolveStyle = match[3];
    const spanText = match[4];
    const intensity = rawIntensity !== undefined ? parseFloat(rawIntensity) : nodeIntensity;
    const mode = rawMode !== undefined ? rawMode : nodeMode;
    const resolveStyle = rawResolveStyle !== undefined ? rawResolveStyle : nodeResolveStyle;
    const seed = _textSeed(spanText, spanIndex);
    segments.push({ text: spanText, intensity, mode, seed, resolve_style: resolveStyle });
    lastEnd = match.index + match[0].length;
    spanIndex++;
  }

  if (lastEnd < text.length) {
    segments.push(text.slice(lastEnd));
  }
  return segments.length ? segments : [text];
}

// A flag's integer value: itself if it is an integer, otherwise 0 (missing, boolean, string).
function intValue(value) {
  return Number.isInteger(value) ? value : 0;
}

// Strictly typed matching, pinned by conformance/requires.json.
export function checkRequires(requires = {}, state = {}) {
  return Object.entries(requires).every(([key, condition]) => {
    const current = state[key];
    if (typeof condition === "boolean") {
      return current === condition;
    }
    if (Number.isInteger(condition)) {
      return intValue(current) >= condition;
    }
    if (typeof condition === "string") {
      return current === condition;
    }
    if (Array.isArray(condition)) {
      return condition.includes(current);
    }
    return false;
  });
}

// Pinned by conformance/sets.json.
export function applySets(sets = {}, state = {}) {
  const next = { ...state };
  for (const [key, value] of Object.entries(sets)) {
    if (typeof value === "string" && /^[+-][0-9]+$/.test(value)) {
      next[key] = intValue(next[key]) + Number(value);
    } else {
      next[key] = value;
    }
  }
  return next;
}

export function visibleItems(items = [], state = {}) {
  return items.filter((item) => checkRequires(item.requires || {}, state));
}

export function partitionByPosition(items = [], fallback = "after") {
  return {
    before: items.filter((item) => (item.position || fallback) === "before"),
    after: items.filter((item) => (item.position || fallback) === "after"),
  };
}

export function createRun(entry, saved = null, initialState = {}) {
  const story = entry.story;
  return {
    entry,
    story,
    nodeId: saved?.current_node && story.nodes[saved.current_node]
      ? saved.current_node
      : story.meta.start_node,
    history: Array.isArray(saved?.history) ? [...saved.history] : [],
    state: saved?.state && typeof saved.state === "object"
      ? { ...saved.state }
      : { ...initialState },
    currentScene: null,
  };
}

export function currentView(run) {
  const node = run.story.nodes[run.nodeId];
  if (node.scene) {
    run.currentScene = node.scene;
  }
  const choices = visibleItems(node.choices || [], run.state);
  const overlays = partitionByPosition(visibleItems(node.overlays || [], run.state), "after");
  const insets = partitionByPosition(visibleItems(node.insets || [], run.state), "before");
  const pt = (text) => resolveCorruption(
    resolveInline(substituteVars(text, run.state), run.state),
    run.story.nodes[run.nodeId].corruption ?? null
  );
  return {
    node: { ...node, text: pt(node.text) },
    choices,
    overlays: {
      before: overlays.before.map((o) => ({ ...o, text: pt(o.text) })),
      after: overlays.after.map((o) => ({ ...o, text: pt(o.text) })),
    },
    insets: {
      before: insets.before.map((i) => ({ ...i, text: pt(i.text) })),
      after: insets.after.map((i) => ({ ...i, text: pt(i.text) })),
    },
    isEnding: Boolean(node.is_ending || choices.length === 0),
  };
}

export function advance(run, choiceIndex) {
  const view = currentView(run);
  const choice = view.choices[choiceIndex];
  if (!choice) return false;
  run.state = applySets(choice.sets || {}, run.state);
  run.history.push(run.nodeId);
  run.nodeId = choice.next;
  if (run.story.meta.auto_visited_flags !== false) {
    run.state[`visited_${run.nodeId}`] = true;
  }
  return true;
}

// --- Settings clamping (mirrors src/config.py SETTINGS_SECTIONS ranges) ---

export const SETTING_RANGES = {
  page_size: [1, 50],
  "pauses..": [0, 2000],
  "pauses.!": [0, 2000],
  "pauses.?": [0, 2000],
  "pauses.…": [0, 2000],
  "pauses.—": [0, 2000],
  "corruption.intensity": [0, 1],
  "corruption.intensity_multiplier": [0, 1],
  "corruption.scramble_frames": [1, 200],
  "corruption.scramble_delay_ms": [0, 1000],
  "corruption.resolve_frames": [1, 200],
  "corruption.resolve_delay_ms": [0, 1000],
  "corruption.cascade_stagger_ms": [0, 1000],
};

const _FLOAT_SETTING_KEYS = new Set(["corruption.intensity", "corruption.intensity_multiplier"]);

// Clamp a numeric setting to its range. Unknown keys use [0, 9999], like Python's default.
// Non-finite input collapses to the range minimum.
export function clampSetting(key, value) {
  const [lo, hi] = SETTING_RANGES[key] ?? [0, 9999];
  const n = Number(value);
  if (!Number.isFinite(n)) return lo;
  return Math.min(Math.max(n, lo), hi);
}

// Parse and range-check a value typed into a settings row. Number rows accept only
// plain digits and clamp to range; float rows reject anything outside their range.
export function commitSettingValue(row, raw) {
  const text = String(raw).trim();
  if (row.type === "float") {
    const [lo, hi] = SETTING_RANGES[row.key] ?? [0, 1];
    const f = parseFloat(text);
    if (!Number.isFinite(f) || f < lo || f > hi) return { ok: false };
    return { ok: true, value: f };
  }
  if (!/^\d+$/.test(text)) return { ok: false };
  return { ok: true, value: clampSetting(row.key, parseInt(text, 10)) };
}

// Frame counts and delays (ms) for corruption animation, clamped like Python's
// config.corruption_timing(). resolve_* / cascade_stagger_ms fall back to the
// (clamped) scramble values when unset.
export function corruptionTiming(cfg) {
  const scrambleFrames = clampSetting("corruption.scramble_frames", cfg.scramble_frames);
  const scrambleDelay = clampSetting("corruption.scramble_delay_ms", cfg.scramble_delay_ms);
  const orScramble = (key, fallback) =>
    clampSetting("corruption." + key, cfg[key] != null ? cfg[key] : fallback);
  return {
    scrambleFrames,
    scrambleDelay,
    resolveFrames: orScramble("resolve_frames", scrambleFrames),
    resolveDelay: orScramble("resolve_delay_ms", scrambleDelay),
    cascadeStagger: orScramble("cascade_stagger_ms", scrambleDelay),
  };
}

// How many of nCorruptible characters to corrupt. Non-positive / NaN intensity
// corrupts nothing (Python's corrupt_string returns the text unchanged).
export function corruptionCount(nCorruptible, intensity) {
  if (!(intensity > 0)) return 0;
  return Math.floor(nCorruptible * Math.min(intensity, 1));
}

// Coerce the range-checked keys of a stored corruption settings object. Unknown
// keys (e.g. custom_chars) and non-range keys pass through untouched.
export function sanitizeCorruptionSettings(stored, defaults) {
  const out = Object.assign({}, defaults, stored && typeof stored === "object" ? stored : {});
  for (const key of Object.keys(defaults)) {
    const rangeKey = "corruption." + key;
    if (!(rangeKey in SETTING_RANGES)) continue;
    const value = out[key];
    if (value === null && defaults[key] === null) continue; // nullable "Auto" stays null
    if (typeof value !== "number" || !Number.isFinite(value)) {
      out[key] = defaults[key];
      continue;
    }
    const clamped = clampSetting(rangeKey, value);
    out[key] = _FLOAT_SETTING_KEYS.has(rangeKey) ? clamped : Math.trunc(clamped);
  }
  return out;
}

// Coerce stored per-character punctuation pauses; invalid entries keep the default.
export function sanitizePauses(stored, defaults) {
  const out = Object.assign({}, defaults);
  if (stored && typeof stored === "object") {
    for (const [ch, ms] of Object.entries(stored)) {
      if (typeof ms === "number" && Number.isFinite(ms)) {
        out[ch] = Math.trunc(clampSetting("pauses." + ch, ms));
      }
    }
  }
  return out;
}
