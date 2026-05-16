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

export function createRun(entry, saved = null) {
  const story = entry.story;
  return {
    entry,
    story,
    nodeId: saved?.current_node && story.nodes[saved.current_node]
      ? saved.current_node
      : story.meta.start_node,
    history: Array.isArray(saved?.history) ? [...saved.history] : [],
    state: saved?.state && typeof saved.state === "object" ? { ...saved.state } : {},
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
  return {
    node,
    choices,
    overlays,
    insets,
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
