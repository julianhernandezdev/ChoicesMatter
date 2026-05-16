const app = document.getElementById("app");

const STORE_PREFIX = "choices-matter";
const STYLE_PREFIXES = {
  whisper: "✦ ",
  echo: "~ ",
  warning: "⚠ ",
  memory: "◈ ",
  system: "",
};

let library = [];
let currentRun = null;
let lastSaved = "";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function slugClass(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_");
}

function saveKey(storyId) {
  return `${STORE_PREFIX}:save:${storyId}`;
}

function galleryKey(storyId) {
  return `${STORE_PREFIX}:gallery:${storyId}`;
}

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function storeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

function removeStoredItem(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // Storage can be unavailable in locked-down browser contexts.
  }
}

function storedKeys() {
  try {
    return Object.keys(localStorage);
  } catch {
    return [];
  }
}

function loadSave(storyId) {
  return loadJson(saveKey(storyId), null);
}

function writeSave(story, run) {
  const saved = storeJson(saveKey(story.meta.id), {
    story_id: story.meta.id,
    current_node: run.nodeId,
    history: run.history,
    state: run.state,
    timestamp: new Date().toISOString(),
  });
  lastSaved = saved
    ? "✓ Progress saved."
    : "Progress could not be saved in this browser.";
}

function deleteSave(storyId) {
  removeStoredItem(saveKey(storyId));
}

function loadGallery(storyId) {
  return loadJson(galleryKey(storyId), { story_id: storyId, endings_found: [] });
}

function recordEnding(story, nodeId) {
  const gallery = loadGallery(story.meta.id);
  gallery.endings_found = Array.from(new Set([...(gallery.endings_found || []), nodeId])).sort();
  storeJson(galleryKey(story.meta.id), gallery);
}

function clearAllProgress() {
  for (const key of storedKeys()) {
    if (key.startsWith(`${STORE_PREFIX}:`)) {
      removeStoredItem(key);
    }
  }
}

function nodeList(story) {
  return Object.values(story.nodes || {});
}

function endingCount(story) {
  return nodeList(story).filter((node) => node.is_ending || !node.choices?.length).length;
}

function estimateTime(story) {
  if (story.meta?.est_time) {
    return story.meta.est_time;
  }
  const words = nodeList(story)
    .map((node) => node.text || "")
    .join(" ")
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
  const minutes = Math.max(5, Math.round(((words / 130) * 1.3) / 5) * 5);
  return `~${minutes} min`;
}

function checkRequires(requires = {}, state = {}) {
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

function applySets(sets = {}, state = {}) {
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

function visibleItems(items = [], state = {}) {
  return items.filter((item) => checkRequires(item.requires || {}, state));
}

function partitionByPosition(items = [], fallback = "after") {
  return {
    before: items.filter((item) => (item.position || fallback) === "before"),
    after: items.filter((item) => (item.position || fallback) === "after"),
  };
}

function createRun(entry, saved = null) {
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

function currentView(run) {
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

function storyTitle(entry) {
  return entry.story.meta?.title || entry.path.split("/").pop()?.replace(".json", "") || "Untitled Story";
}

function renderLibrary() {
  currentRun = null;
  lastSaved = "";
  const cards = library.map((entry) => {
    const story = entry.story;
    const save = loadSave(story.meta.id);
    const gallery = loadGallery(story.meta.id);
    const endings = endingCount(story);
    const found = gallery.endings_found?.length || 0;
    const warningBadge = story.meta.warnings?.length ? '<span class="badge warning">[!] content warning</span>' : "";
    const resumeBadge = save ? '<span class="badge resume">● resume</span>' : "";
    const author = story.meta.author ? ` by ${escapeHtml(story.meta.author)}` : "";
    return `
      <article class="story-card">
        <h2>${escapeHtml(storyTitle(entry))}</h2>
        <p>${escapeHtml(entry.category || "story")}${author}</p>
        <div class="badges">
          <span class="badge">${nodeList(story).length} nodes</span>
          <span class="badge">${found}/${endings || "?"} endings</span>
          <span class="badge">${escapeHtml(estimateTime(story))}</span>
          ${warningBadge}
          ${resumeBadge}
        </div>
        <div class="card-actions">
          ${save ? `<button data-action="resume" data-path="${escapeHtml(entry.path)}">Continue</button>` : ""}
          <button data-action="start" data-path="${escapeHtml(entry.path)}">${save ? "New Game" : "Play"}</button>
        </div>
      </article>
    `;
  }).join("");

  app.innerHTML = `
    <section class="library-header">
      <img src="assets/banner.png" alt="Choices Matter" class="hero-banner">
      <h1>Choices Matter</h1>
      <p>Pick a story. Your browser saves progress automatically on this device.</p>
      <div class="top-actions">
        <button class="secondary" data-action="clear-progress">Clear all browser saves</button>
      </div>
    </section>
    <section class="story-grid" aria-label="Story library">
      ${cards}
    </section>
  `;
}

function findEntry(path) {
  return library.find((entry) => entry.path === path);
}

function renderWarnings(entry, resume) {
  const warnings = entry.story.meta.warnings || [];
  app.innerHTML = `
    <section class="warning-card">
      <h1>Content Warning</h1>
      <p>${escapeHtml(storyTitle(entry))} contains:</p>
      <ul>${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>
      <div class="warning-actions">
        <button data-action="confirm-start" data-path="${escapeHtml(entry.path)}" data-resume="${resume ? "yes" : "no"}">Continue</button>
        <button class="secondary" data-action="library">Back to library</button>
      </div>
    </section>
  `;
}

function startStory(entry, { resume = false, skipWarnings = false } = {}) {
  if (!entry) {
    return;
  }
  if (!skipWarnings && entry.story.meta.warnings?.length) {
    renderWarnings(entry, resume);
    return;
  }
  const saved = resume ? loadSave(entry.story.meta.id) : null;
  if (!resume) {
    deleteSave(entry.story.meta.id);
  }
  currentRun = createRun(entry, saved);
  lastSaved = resume ? "Restored saved progress." : "";
  renderGame();
}

function renderStyledLine(item, className) {
  const styleName = item.style || "whisper";
  const prefix = STYLE_PREFIXES[styleName] ?? STYLE_PREFIXES.whisper;
  return `<p class="${className} ${escapeHtml(slugClass(styleName))}">${escapeHtml(prefix)}${escapeHtml(item.text)}</p>`;
}

function renderGame() {
  if (!currentRun) {
    renderLibrary();
    return;
  }
  const view = currentView(currentRun);
  const { story } = currentRun;
  if (view.isEnding) {
    renderEnding(view);
    return;
  }

  const beforeInsets = view.insets.before.map((item) => renderStyledLine(item, "inset before")).join("");
  const afterInsets = view.insets.after.map((item) => renderStyledLine(item, "inset after")).join("");
  const beforeOverlays = view.overlays.before.map((item) => renderStyledLine(item, "overlay")).join("");
  const afterOverlays = view.overlays.after.map((item) => renderStyledLine(item, "overlay")).join("");
  const fallbackColor = view.node.choice_number_color || "cyan";
  const choices = view.choices.map((choice, index) => {
    const label = choice.obfuscated ? "[REDACTED ██████]" : choice.label;
    const color = slugClass(choice.color || fallbackColor);
    return `
      <button class="choice-button color-${escapeHtml(color)}" data-action="choice" data-index="${index}">
        <span class="choice-number">${index + 1}.</span>
        <span>${escapeHtml(label)}</span>
      </button>
    `;
  }).join("");

  app.innerHTML = `
    <section class="game-card">
      <header class="game-title">
        <div>
          <p class="muted">${escapeHtml(currentRun.entry.category || "story")}</p>
          <h1>${escapeHtml(storyTitle(currentRun.entry))}</h1>
        </div>
        <button class="secondary" data-action="library">Back to library</button>
      </header>
      ${currentRun.currentScene ? `<div class="scene-rule">${escapeHtml(currentRun.currentScene)}</div>` : ""}
      <article class="prose-panel">
        ${beforeInsets}
        <div class="prose">${escapeHtml(view.node.text)}</div>
        ${afterInsets}
      </article>
      ${beforeOverlays}
      <div class="choices">${choices}</div>
      ${afterOverlays}
      <p class="save-line">${escapeHtml(lastSaved)}</p>
    </section>
  `;
}

function renderEnding(view) {
  const { story } = currentRun;
  recordEnding(story, currentRun.nodeId);
  deleteSave(story.meta.id);
  const endingType = view.node.ending_type || "neutral";
  const overlays = [...view.overlays.before, ...view.overlays.after]
    .map((item) => renderStyledLine(item, "overlay"))
    .join("");
  app.innerHTML = `
    <section class="game-card">
      <header class="game-title">
        <div>
          <p class="muted">${escapeHtml(storyTitle(currentRun.entry))}</p>
          <h1>Ending Reached</h1>
        </div>
        <button class="secondary" data-action="library">Back to library</button>
      </header>
      ${overlays}
      <article class="ending-panel ${escapeHtml(slugClass(endingType))}">
        <p class="ending-label ${escapeHtml(slugClass(endingType))}">— ${escapeHtml(endingType.toUpperCase())} ENDING —</p>
        <div class="prose">${escapeHtml(view.node.text)}</div>
      </article>
      <div class="ending-actions">
        <button data-action="play-again">Play again</button>
        <button class="secondary" data-action="library">Choose another story</button>
      </div>
    </section>
  `;
}

function choose(index) {
  const view = currentView(currentRun);
  const choice = view.choices[index];
  if (!choice) {
    return;
  }
  currentRun.state = applySets(choice.sets || {}, currentRun.state);
  currentRun.history.push(currentRun.nodeId);
  currentRun.nodeId = choice.next;
  if (currentRun.story.meta.auto_visited_flags !== false) {
    currentRun.state[`visited_${currentRun.nodeId}`] = true;
  }
  writeSave(currentRun.story, currentRun);
  renderGame();
}

app.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }
  const action = button.dataset.action;
  if (action === "library") {
    renderLibrary();
  } else if (action === "start") {
    startStory(findEntry(button.dataset.path), { resume: false });
  } else if (action === "resume") {
    startStory(findEntry(button.dataset.path), { resume: true });
  } else if (action === "confirm-start") {
    startStory(findEntry(button.dataset.path), {
      resume: button.dataset.resume === "yes",
      skipWarnings: true,
    });
  } else if (action === "choice") {
    choose(Number(button.dataset.index));
  } else if (action === "play-again") {
    startStory(currentRun.entry, { resume: false, skipWarnings: true });
  } else if (action === "clear-progress") {
    if (confirm("Clear all browser saves and ending progress for Choices Matter?")) {
      clearAllProgress();
      renderLibrary();
    }
  }
});

async function loadLibrary() {
  const manifestResponse = await fetch("web/stories.json");
  if (!manifestResponse.ok) {
    throw new Error("Could not load story manifest.");
  }
  const manifest = await manifestResponse.json();
  const entries = await Promise.all((manifest.stories || []).map(async (item) => {
    const storyResponse = await fetch(item.path);
    if (!storyResponse.ok) {
      throw new Error(`Could not load ${item.path}`);
    }
    return {
      ...item,
      story: await storyResponse.json(),
    };
  }));
  library = entries.sort((a, b) => storyTitle(a).localeCompare(storyTitle(b)));
  renderLibrary();
}

loadLibrary().catch((error) => {
  app.innerHTML = `
    <section class="error-card">
      <h1>Could not load Choices Matter</h1>
      <p>${escapeHtml(error.message)}</p>
      <p class="muted">If you downloaded the files, run them from a small web server so the browser can fetch the story JSON.</p>
    </section>
  `;
});
