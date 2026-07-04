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

const _CORRUPT_RE = /\{corrupt(?::([0-9]*\.?[0-9]+))?(?::(consistent|random))?\}([\s\S]*?)\{\/corrupt\}/g;

function _textSeed(text, index) {
  const combined = text + String(index);
  let sum = 0;
  for (let i = 0; i < combined.length; i++) {
    sum = (sum + combined.charCodeAt(i) * (i + 1)) % 4294967296;
  }
  return sum;
}

export function resolveCorruption(text, nodeCorruption) {
  let nodeIntensity = 1.0;
  let nodeMode = "consistent";
  if (typeof nodeCorruption === "number") {
    nodeIntensity = nodeCorruption;
  } else if (nodeCorruption && typeof nodeCorruption === "object") {
    nodeIntensity = nodeCorruption.intensity ?? 1.0;
    nodeMode = nodeCorruption.mode ?? "consistent";
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
    const spanText = match[3];
    const intensity = rawIntensity !== undefined ? parseFloat(rawIntensity) : nodeIntensity;
    const mode = rawMode !== undefined ? rawMode : nodeMode;
    const seed = _textSeed(spanText, spanIndex);
    segments.push({ text: spanText, intensity, mode, seed });
    lastEnd = match.index + match[0].length;
    spanIndex++;
  }

  if (lastEnd < text.length) {
    segments.push(text.slice(lastEnd));
  }
  return segments.length ? segments : [text];
}

export function checkRequires(requires = {}, state = {}) {
  return Object.entries(requires).every(([key, condition]) => {
    const current = state[key];
    if (typeof condition === "boolean") {
      return current === condition;
    }
    if (Number.isInteger(condition)) {
      return Number.isInteger(current) && current >= condition;
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

export function applySets(sets = {}, state = {}) {
  const next = { ...state };
  for (const [key, value] of Object.entries(sets)) {
    if (typeof value === "string" && /^[+-]\d+$/.test(value)) {
      const current = Number.isInteger(next[key]) ? next[key] : 0;
      next[key] = current + Number(value);
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
