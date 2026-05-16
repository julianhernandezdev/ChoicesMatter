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
var resumeEntry = null;
var resumeSkipWarnings = false;
var settingsDraft = null;
var settingsEditRow = null;
var twAnimation = null;
var pendingInput = '';

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

var SETTINGS_ROWS = [
  { key: 'enabled',   label: 'Enabled',        type: 'boolean' },
  { key: 'delay_ms',  label: 'Speed',           type: 'number', unit: 'ms' },
  { key: 'pauses..',  label: 'Pause after  .',  type: 'number', unit: 'ms' },
  { key: 'pauses.!',  label: 'Pause after  !',  type: 'number', unit: 'ms' },
  { key: 'pauses.?',  label: 'Pause after  ?',  type: 'number', unit: 'ms' },
  { key: 'pauses.…', label: 'Pause after  …', type: 'number', unit: 'ms' },
  { key: 'pauses.—', label: 'Pause after  —', type: 'number', unit: 'ms' },
];

function getSettingValue(draft, key) {
  if (key.indexOf('pauses.') === 0) return draft.pauses[key.slice('pauses.'.length)];
  return draft[key];
}

function setSettingValue(draft, key, value) {
  if (key.indexOf('pauses.') === 0) draft.pauses[key.slice('pauses.'.length)] = value;
  else draft[key] = value;
}

function updatePrompt() {
  var el = document.querySelector('.terminal-prompt-line');
  if (!el) return;
  var prefix = currentScreen === 'game' ? 'Your choice (or Q to return to menu): ' : '&gt; ';
  el.innerHTML = prefix + escapeHtml(pendingInput) + '<span class="terminal-cursor">█</span>';
}

function renderSettings() {
  pendingInput = '';
  currentScreen = 'settings';
  if (!settingsDraft) {
    var s = loadTypewriterSettings();
    settingsDraft = { enabled: s.enabled, delay_ms: s.delay_ms, pauses: Object.assign({}, s.pauses) };
  }
  settingsEditRow = null;

  var rows = SETTINGS_ROWS.map(function(row, i) {
    var val = getSettingValue(settingsDraft, row.key);
    var display = row.type === 'boolean' ? (val ? 'on' : 'off') : val + (row.unit ? ' ' + row.unit : '');
    return '<div class="terminal-settings-row" data-action="settings-row" data-row="' + i + '">' +
      '<span class="setting-num">' + (i + 1) + '.</span>' +
      '<span class="setting-name">' + escapeHtml(row.label) + '</span>' +
      '<span class="setting-value">' + escapeHtml(String(display)) + '</span>' +
      '</div>';
  }).join('');

  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Settings – Typewriter', 'green') +
    '<div class="terminal-list">' + rows + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Enter a number to edit · <span style="color:var(--green)">S</span> save · <span style="color:var(--red)">X</span> discard</div>' +
    '<div class="terminal-prompt-line">&gt; <span class="terminal-cursor">█</span></div>' +
    '</div></div>';
}

function startSettingsEdit(rowIndex) {
  var row = SETTINGS_ROWS[rowIndex];
  if (!row) return;
  var val = getSettingValue(settingsDraft, row.key);
  if (row.type === 'boolean') {
    setSettingValue(settingsDraft, row.key, !val);
    renderSettings();
    return;
  }
  var rowEl = document.querySelector('.terminal-settings-row[data-row="' + rowIndex + '"]');
  if (!rowEl) return;
  settingsEditRow = rowIndex;
  var valEl = rowEl.querySelector('.setting-value');
  valEl.innerHTML = '<input class="setting-input" id="settings-edit-input" type="text" value="' + escapeHtml(String(val)) + '" autocomplete="off">';
  var input = document.getElementById('settings-edit-input');
  if (input) { input.focus(); input.select(); }
}

function confirmSettingsEdit() {
  var input = document.getElementById('settings-edit-input');
  if (!input || settingsEditRow === null) return;
  var num = parseInt(input.value, 10);
  if (!isNaN(num) && num >= 0) setSettingValue(settingsDraft, SETTINGS_ROWS[settingsEditRow].key, num);
  settingsEditRow = null;
  renderSettings();
}

function cancelSettingsEdit() {
  settingsEditRow = null;
  renderSettings();
}

function renderLibrary() {
  currentRun = null;
  lastSaved = '';
  currentFolder = null;
  renderPicker();
}

function renderPicker() {
  pendingInput = '';
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
    '<div class="footer-hint">Enter a number, <span style="color:var(--red)">Q</span> to quit, C to clear saves, or <span style="color:var(--green)">S</span> for settings:</div>' +
    '<div class="footer-typewriter">T · Toggle typewriter (session only) <span class="' + (twOn ? 'tw-state-on' : 'tw-state-off') + '">' + (twOn ? 'ON' : 'OFF') + '</span></div>' +
    '<div class="terminal-prompt-line">&gt; <span class="terminal-cursor">█</span></div>' +
    '</div></div>';
}

function renderFolder(folderName) {
  pendingInput = '';
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
    '<div class="footer-hint">Enter a number, <span style="color:var(--red)">B</span> to go back, or <span style="color:var(--red)">Q</span> to quit:</div>' +
    '<div class="terminal-prompt-line">&gt; <span class="terminal-cursor">█</span></div>' +
    '</div></div>';
}

function findEntry(path) {
  return library.find((entry) => entry.path === path);
}

function renderResume(entry, skipWarnings) {
  pendingInput = '';
  currentScreen = 'resume';
  resumeEntry = entry;
  resumeSkipWarnings = skipWarnings;

  app.innerHTML =
    '<div class="terminal-screen">' +
    '<div class="terminal-prose">A save was found for this story.</div>' +
    '<div class="terminal-prompt-line">Continue saved game? ' +
    '(<span style="color:var(--green)">C</span> to continue, ' +
    '<span style="color:var(--red)">N</span> for new): ' +
    '<span class="terminal-cursor">█</span></div>' +
    '</div>';
}

function renderWarnings(entry, resume) {
  pendingInput = '';
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

function startStory(entry, { resume = false, skipWarnings = false, skipResume = false } = {}) {
  if (!entry) { return; }
  if (!skipWarnings && entry.story.meta.warnings?.length) {
    renderWarnings(entry, resume);
    return;
  }
  if (resume && !skipResume && loadSave(entry.story.meta.id)) {
    renderResume(entry, skipWarnings);
    return;
  }
  const saved = resume ? loadSave(entry.story.meta.id) : null;
  if (!resume) { deleteSave(entry.story.meta.id); }
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

function startTypewriter(element, text) {
  var settings = loadTypewriterSettings();
  var pauses = settings.pauses || {};
  var delay = settings.delay_ms || 20;

  element.textContent = '';
  var toReveal = Array.from(
    document.querySelectorAll('.terminal-choice, .terminal-overlay, .terminal-prompt-line')
  );
  toReveal.forEach(function(el) { el.style.visibility = 'hidden'; });

  var chars = Array.from(text);
  var i = 0;
  function step() {
    if (i >= chars.length) {
      twAnimation = null;
      revealChoices(toReveal);
      return;
    }
    var ch = chars[i++];
    element.textContent += ch;
    var extra = pauses[ch] || 0;
    twAnimation = { id: setTimeout(step, delay + extra), text: text, element: element, toReveal: toReveal };
  }
  twAnimation = { id: setTimeout(step, 0), text: text, element: element, toReveal: toReveal };
}

function skipTypewriter() {
  if (!twAnimation) return;
  clearTimeout(twAnimation.id);
  twAnimation.element.textContent = twAnimation.text;
  var toReveal = twAnimation.toReveal;
  twAnimation = null;
  revealChoices(toReveal);
}

function revealChoices(elements) {
  setTimeout(function() {
    elements.forEach(function(el, i) {
      setTimeout(function() { el.style.visibility = 'visible'; }, i * 60);
    });
  }, 250);
}

function renderGame() {
  pendingInput = '';
  if (!currentRun) { renderLibrary(); return; }
  var view = currentView(currentRun);
  if (view.isEnding) { renderEnding(view); return; }

  currentScreen = 'game';
  var node = view.node;

  var sceneRule = currentRun.currentScene ? renderRule(currentRun.currentScene, 'green') : '';

  var sep = '<span class="terminal-separator">' + '─'.repeat(PANEL_RULE_WIDTH) + '</span>';
  var beforeInsets = view.insets.before.map(function(i) {
    return '<span class="terminal-inset">' + renderStyledLine(i, '') + '</span>';
  }).join('');
  var afterInsets = view.insets.after.map(function(i) {
    return '<span class="terminal-inset">' + renderStyledLine(i, '') + '</span>';
  }).join('');

  var fallbackColor = node.choice_number_color || 'cyan';
  var choiceHtml = view.choices.map(function(choice, i) {
    var label = choice.obfuscated ? '[REDACTED ██████]' : choice.label;
    var colorVar = resolveColor(choice.color || fallbackColor);
    return '<div class="terminal-choice" data-action="choice" data-index="' + i + '">' +
      '<span class="choice-num" style="color:' + colorVar + '">' + (i + 1) + '.</span>' +
      '<span class="choice-label">' + escapeHtml(label) + '</span></div>';
  }).join('');

  var beforeOverlays = view.overlays.before.map(function(o) {
    return '<span class="terminal-overlay">' + renderStyledLine(o, '') + '</span>';
  }).join('');
  var afterOverlays = view.overlays.after.map(function(o) {
    return '<span class="terminal-overlay">' + renderStyledLine(o, '') + '</span>';
  }).join('');

  app.innerHTML =
    '<div class="terminal-screen">' +
    sceneRule +
    '<div class="terminal-panel">' +
    '<span class="terminal-panel-title">' + escapeHtml(makeRule(storyTitle(currentRun.entry), PANEL_RULE_WIDTH)) + '</span>' +
    beforeInsets +
    (view.insets.before.length ? sep : '') +
    '<div class="terminal-prose" id="prose-text">' + escapeHtml(node.text) + '</div>' +
    (view.insets.after.length ? sep : '') +
    afterInsets +
    '</div>' +
    beforeOverlays +
    '<div class="terminal-choices">' + choiceHtml + '</div>' +
    afterOverlays +
    '<div class="terminal-prompt-line">Your choice (or <span style="color:var(--red)">Q</span> to return to menu): <span class="terminal-cursor">█</span></div>' +
    '</div>';

  if (isTypewriterOn()) startTypewriter(document.getElementById('prose-text'), node.text);
}

function renderEnding(view) {
  pendingInput = '';
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
    '<span class="terminal-ending-label ' + escapeHtml(type) + '">' + escapeHtml(makeRule(type.toUpperCase() + ' ENDING', PANEL_RULE_WIDTH)) + '</span>' +
    '<div class="terminal-prose ending-prose" id="prose-text">' + escapeHtml(view.node.text) + '</div>' +
    '</div>' +
    '<div class="terminal-prompt-line">Play again? (<span style="color:var(--green)">Y</span> to play again, <span style="color:var(--red)">N</span> to return to library): <span class="terminal-cursor">█</span></div>' +
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

document.addEventListener('keydown', function(e) {
  var key = e.key.toUpperCase();

  if (twAnimation) {
    e.preventDefault();
    skipTypewriter();
    return;
  }

  if (currentScreen === 'library') {
    if (key === 'T') { toggleTypewriter(); return; }
    if (key === 'C') {
      if (confirm('Clear all browser saves and ending progress?')) { clearAllProgress(); renderLibrary(); }
      return;
    }
    if (key === 'S') { settingsDraft = null; renderSettings(); return; }
    if (key === 'BACKSPACE') { pendingInput = pendingInput.slice(0, -1); updatePrompt(); e.preventDefault(); return; }
    if (key === 'ENTER' && pendingInput) {
      var n = parseInt(pendingInput, 10); pendingInput = '';
      if (n >= 1 && n <= activeMenuEntries.length) {
        var me = activeMenuEntries[n - 1];
        if (me.type === 'folder') renderFolder(me.name);
        else startStory(me.entry, { resume: !!loadSave(me.entry.story.meta.id) });
      }
      return;
    }
    var nd = parseInt(e.key, 10);
    if (!isNaN(nd)) { pendingInput += e.key; updatePrompt(); e.preventDefault(); return; }

  } else if (currentScreen === 'folder') {
    if (key === 'Q' || key === 'B') { renderLibrary(); return; }
    if (key === 'BACKSPACE') { pendingInput = pendingInput.slice(0, -1); updatePrompt(); e.preventDefault(); return; }
    if (key === 'ENTER' && pendingInput) {
      var nf = parseInt(pendingInput, 10); pendingInput = '';
      if (nf >= 1 && nf <= activeMenuEntries.length) {
        var mef = activeMenuEntries[nf - 1];
        startStory(mef.entry, { resume: !!loadSave(mef.entry.story.meta.id) });
      }
      return;
    }
    var nfd = parseInt(e.key, 10);
    if (!isNaN(nfd)) { pendingInput += e.key; updatePrompt(); e.preventDefault(); return; }

  } else if (currentScreen === 'resume') {
    if (key === 'C' || key === 'ENTER') startStory(resumeEntry, { resume: true,  skipWarnings: resumeSkipWarnings, skipResume: true });
    if (key === 'N')                    startStory(resumeEntry, { resume: false, skipWarnings: resumeSkipWarnings, skipResume: true });

  } else if (currentScreen === 'warning') {
    if (key === 'Y') startStory(warningEntry, { resume: warningResume, skipWarnings: true });
    if (key === 'N') renderLibrary();

  } else if (currentScreen === 'game') {
    if (key === 'Q') { renderLibrary(); return; }
    if (key === 'BACKSPACE') { pendingInput = pendingInput.slice(0, -1); updatePrompt(); e.preventDefault(); return; }
    if (key === 'ENTER' && pendingInput) {
      var ng = parseInt(pendingInput, 10); pendingInput = '';
      var vg = currentView(currentRun);
      if (ng >= 1 && ng <= vg.choices.length) choose(ng - 1);
      return;
    }
    var ngd = parseInt(e.key, 10);
    if (!isNaN(ngd)) { pendingInput += e.key; updatePrompt(); e.preventDefault(); return; }

  } else if (currentScreen === 'ending') {
    if (key === 'Y') startStory(currentRun.entry, { resume: false, skipWarnings: true });
    if (key === 'N') renderLibrary();

  } else if (currentScreen === 'settings') {
    if (key === 'X') { renderLibrary(); return; }
    if (key === 'S') { saveTypewriterSettings(settingsDraft); renderLibrary(); return; }
    if (key === 'ESCAPE' && settingsEditRow !== null) { cancelSettingsEdit(); return; }
    if (key === 'ENTER' && settingsEditRow !== null) { confirmSettingsEdit(); return; }
    if (settingsEditRow === null) {
      if (key === 'BACKSPACE') { pendingInput = pendingInput.slice(0, -1); updatePrompt(); e.preventDefault(); return; }
      if (key === 'ENTER' && pendingInput) {
        var ns = parseInt(pendingInput, 10); pendingInput = '';
        if (ns >= 1 && ns <= SETTINGS_ROWS.length) startSettingsEdit(ns - 1);
        return;
      }
      var nsd = parseInt(e.key, 10);
      if (!isNaN(nsd)) { pendingInput += e.key; updatePrompt(); e.preventDefault(); return; }
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
