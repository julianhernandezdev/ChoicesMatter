const app = document.getElementById("app");

const STORE_PREFIX = "choices-matter";
var RULE_WIDTH = 74;
var PANEL_RULE_WIDTH = 70;

function makeRule(text, width) {
  if (!text) return '─'.repeat(width);
  var inner = ' ' + text + ' ';
  if (inner.length >= width) return inner;
  var dashes = width - inner.length;
  var left = Math.floor(dashes / 2);
  return '─'.repeat(left) + inner + '─'.repeat(dashes - left);
}

function renderRule(text, colorClass, width) {
  var w = (width !== undefined) ? width : RULE_WIDTH;
  var cls = colorClass ? 'terminal-rule ' + escapeHtml(colorClass) : 'terminal-rule';
  return '<span class="' + cls + '">' + escapeHtml(makeRule(text, w)) + '</span>';
}

var COLOR_MAP = {
  cyan: 'var(--cyan)', green: 'var(--green)', red: 'var(--red)',
  yellow: 'var(--yellow)', magenta: 'var(--magenta)', blue: 'var(--blue)',
  white: 'var(--bright)', dim: 'var(--dim)',
  bright_red: 'var(--red)', bright_green: 'var(--green)', bright_yellow: 'var(--yellow)',
  bright_cyan: 'var(--cyan)', bright_magenta: 'var(--magenta)', bright_blue: 'var(--blue)',
  bright_white: 'var(--bright)',
};

function resolveColor(name) {
  if (!name) return 'var(--cyan)';
  if (name.charAt(0) === '#') return name;
  return COLOR_MAP[name] || 'var(--cyan)';
}

var SETTINGS_KEY = STORE_PREFIX + ':typewriter-settings';

var TYPEWRITER_DEFAULTS = {
  enabled: true,
  delay_ms: 20,
  pauses: { '.': 150, '!': 150, '?': 150, '…': 200, '—': 100 },
};

function loadTypewriterSettings() {
  var stored = loadJson(SETTINGS_KEY, null);
  if (!stored) return {
    enabled: TYPEWRITER_DEFAULTS.enabled,
    delay_ms: TYPEWRITER_DEFAULTS.delay_ms,
    pauses: Object.assign({}, TYPEWRITER_DEFAULTS.pauses),
  };
  return {
    enabled: typeof stored.enabled === 'boolean' ? stored.enabled : TYPEWRITER_DEFAULTS.enabled,
    delay_ms: typeof stored.delay_ms === 'number' ? stored.delay_ms : TYPEWRITER_DEFAULTS.delay_ms,
    pauses: Object.assign({}, TYPEWRITER_DEFAULTS.pauses, stored.pauses || {}),
  };
}

function saveTypewriterSettings(settings) {
  storeJson(SETTINGS_KEY, settings);
}

// Session-only toggle — null means "use stored setting"
var sessionTwEnabled = null;

function isTypewriterOn() {
  var settings = loadTypewriterSettings();
  return sessionTwEnabled !== null ? sessionTwEnabled : settings.enabled;
}

function toggleTypewriter() {
  sessionTwEnabled = !isTypewriterOn();
  if (currentScreen === 'library') renderPicker();
  else if (currentScreen === 'folder') renderFolder(currentFolder);
}

// Screen-state variables (used by keyboard handler and all renderers)
var currentScreen = 'library';
var currentFolder = null;
var activeMenuEntries = [];
var warningEntry = null;
var warningResume = false;
var settingsDraft = null;
var settingsEditRow = null;
var twAnimation = null;

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

function renderPickerEntry(entry, num) {
  var story = entry.story;
  var save = loadSave(story.meta.id);
  var gallery = loadGallery(story.meta.id);
  var endings = endingCount(story);
  var found = gallery.endings_found ? gallery.endings_found.length : 0;
  var resumeBadge = save ? ' <span class="badge-resume">● RESUME</span>' : '';
  var warnBadge = story.meta.warnings && story.meta.warnings.length ? ' <span class="badge-warning">[!]</span>' : '';
  var meta = nodeList(story).length + ' nodes · ' + found + '/' + (endings || '?') + ' endings · ' + escapeHtml(estimateTime(story));
  return '<div class="terminal-list-item" data-action="pick-story" data-path="' + escapeHtml(entry.path) + '">' +
    '<span class="item-num">' + num + '.</span>' +
    '<div><div class="item-name">' + escapeHtml(storyTitle(entry)) + warnBadge + resumeBadge + '</div>' +
    '<div class="item-meta">' + meta + '</div></div>' +
    '</div>';
}

function renderLibrary() {
  currentRun = null;
  lastSaved = '';
  currentFolder = null;
  renderPicker();
}

function renderPicker() {
  currentScreen = 'library';
  var twOn = isTypewriterOn();

  var folders = {};
  var rootStories = [];
  library.forEach(function(entry) {
    var cat = entry.category || null;
    if (cat) { if (!folders[cat]) folders[cat] = []; folders[cat].push(entry); }
    else rootStories.push(entry);
  });

  var items = [];
  var menuEntries = [];
  var idx = 1;

  Object.keys(folders).sort().forEach(function(name) {
    var count = folders[name].length;
    items.push(
      '<div class="terminal-list-item" data-action="open-folder" data-folder="' + escapeHtml(name) + '">' +
      '<span class="item-num">' + idx + '.</span>' +
      '<div><div class="item-name">📁 ' + escapeHtml(name) + '/</div>' +
      '<div class="item-meta">' + count + ' ' + (count === 1 ? 'story' : 'stories') + '</div></div>' +
      '</div>'
    );
    menuEntries.push({ type: 'folder', name: name });
    idx++;
  });

  rootStories.forEach(function(entry) {
    items.push(renderPickerEntry(entry, idx));
    menuEntries.push({ type: 'story', entry: entry });
    idx++;
  });

  activeMenuEntries = menuEntries;

  app.innerHTML =
    '<div class="terminal-screen">' +
    '<div class="terminal-title-box">Choices Matter</div>' +
    renderRule('A text adventure engine', 'green') +
    renderRule('Select a Story', 'green') +
    '<div class="terminal-list">' + items.join('') + '</div>' +
    renderRule('', 'dim') +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Enter a number, Q to quit, C to clear saves, or S for settings:</div>' +
    '<div class="footer-typewriter">T · Toggle typewriter (session only) <span class="' + (twOn ? 'tw-state-on' : 'tw-state-off') + '">' + (twOn ? 'ON' : 'OFF') + '</span></div>' +
    '<div class="terminal-prompt-line">&gt; <span class="terminal-cursor">█</span></div>' +
    '</div></div>';
}

function renderFolder(folderName) {
  currentScreen = 'folder';
  currentFolder = folderName;
  var folderEntries = library.filter(function(e) { return e.category === folderName; });
  activeMenuEntries = folderEntries.map(function(entry) { return { type: 'story', entry: entry }; });
  var items = folderEntries.map(function(entry, i) { return renderPickerEntry(entry, i + 1); });
  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('📁 ' + folderName + '/', 'green') +
    '<div class="terminal-list">' + items.join('') + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Enter a number, B to go back, or Q to quit:</div>' +
    '<div class="terminal-prompt-line">&gt; <span class="terminal-cursor">█</span></div>' +
    '</div></div>';
}

function findEntry(path) {
  return library.find((entry) => entry.path === path);
}

function renderWarnings(entry, resume) {
  currentScreen = 'warning';
  warningEntry = entry;
  warningResume = resume;
  var warnings = entry.story.meta.warnings || [];
  var items = warnings.map(function(w) { return '<li>' + escapeHtml(w) + '</li>'; }).join('');
  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('[!] Content Warnings', 'yellow') +
    '<div class="terminal-panel warning-panel">' +
    '<span class="warning-bold">This story contains:</span>' +
    '<ul class="warning-list">' + items + '</ul>' +
    '</div>' +
    renderRule(storyTitle(entry), 'dim') +
    '<div class="terminal-prompt-line">Proceed? (<span style="color:var(--green)">Y</span> to continue, <span style="color:var(--red)">N</span> to go back): <span class="terminal-cursor">█</span></div>' +
    '</div>';
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

function renderStyledLine(item, extraClass) {
  var style = item.style;
  var cssClass, prefix;
  if (style === "") {
    cssClass = 'style-empty'; prefix = '';
  } else if (style === 'system') {
    cssClass = 'style-system'; prefix = '';
  } else if (style === 'warning') {
    cssClass = 'style-warning-tag'; prefix = '⚠ ';
  } else if (style === 'memory') {
    cssClass = 'style-memory'; prefix = '◈ ';
  } else if (style === 'echo') {
    cssClass = 'style-echo'; prefix = '~ ';
  } else {
    cssClass = 'style-whisper'; prefix = '✦ ';
  }
  var cls = [extraClass || '', cssClass].filter(Boolean).join(' ');
  return '<span class="' + escapeHtml(cls) + '">' + escapeHtml(prefix + (item.text || '')) + '</span>';
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
  currentScreen = 'ending';
  var story = currentRun.story;
  recordEnding(story, currentRun.nodeId);
  deleteSave(story.meta.id);

  var type = view.node.ending_type || 'neutral';
  var overlays = [].concat(view.overlays.before, view.overlays.after)
    .map(function(o) { return '<span class="terminal-overlay">' + renderStyledLine(o, '') + '</span>'; })
    .join('');

  app.innerHTML =
    '<div class="terminal-screen">' +
    overlays +
    '<div class="terminal-panel ' + escapeHtml(type) + '">' +
    '<span class="terminal-ending-label ' + escapeHtml(type) + '">' + makeRule(type.toUpperCase() + ' ENDING', PANEL_RULE_WIDTH) + '</span>' +
    '<div class="terminal-prose ending-prose" id="prose-text">' + escapeHtml(view.node.text) + '</div>' +
    '</div>' +
    '<div class="terminal-prompt-line">Play again? (<span style="color:var(--green)">Y</span> to play again, <span style="color:var(--dim)">N</span> to return to library): <span class="terminal-cursor">█</span></div>' +
    '</div>';

  if (isTypewriterOn()) startTypewriter(document.getElementById('prose-text'), view.node.text);
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

app.addEventListener('click', function(event) {
  var button = event.target.closest('[data-action]');
  if (!button) return;
  var action = button.dataset.action;
  if (action === 'open-folder') {
    renderFolder(button.dataset.folder);
  } else if (action === 'pick-story') {
    var entry = findEntry(button.dataset.path);
    if (entry) startStory(entry, { resume: !!loadSave(entry.story.meta.id) });
  } else if (action === 'choice') {
    if (!twAnimation) choose(Number(button.dataset.index));
  } else if (action === 'settings-row') {
    startSettingsEdit(Number(button.dataset.row));
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
