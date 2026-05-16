import { createRun, currentView, applySets } from "./engine.js";
import { loadSave, writeSave, deleteSave, loadGallery, recordEnding, clearAllProgress } from "./storage.js";
import { isTypewriterOn, setSessionTw, isTwAnimating, startTypewriter, skipTypewriter, loadTypewriterSettings, saveTypewriterSettings, TYPEWRITER_DEFAULTS } from "./typewriter.js";

const app = document.getElementById("app");

// --- Rendering constants ---

var RULE_WIDTH = 74;
var PANEL_RULE_WIDTH = 70;

var COLOR_MAP = {
  cyan: 'var(--cyan)', green: 'var(--green)', red: 'var(--red)',
  yellow: 'var(--yellow)', magenta: 'var(--magenta)', blue: 'var(--blue)',
  white: 'var(--bright)', dim: 'var(--dim)',
  bright_red: 'var(--red)', bright_green: 'var(--green)', bright_yellow: 'var(--yellow)',
  bright_cyan: 'var(--cyan)', bright_magenta: 'var(--magenta)', bright_blue: 'var(--blue)',
  bright_white: 'var(--bright)',
};

// --- Screen state ---

var currentScreen = 'library';
var currentFolder = null;
var activeMenuEntries = [];
var warningEntry = null;
var warningResume = false;
var resumeEntry = null;
var resumeSkipWarnings = false;
var settingsDraft = null;
var settingsEditRow = null;
var speedCustomEdit = false;
var pendingInput = '';

// --- App state ---

let library = [];
let currentRun = null;
let lastSaved = "";

// --- HTML utilities ---

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function slugClass(value) {
  return String(value || "").trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "_");
}

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

function resolveColor(name) {
  if (!name) return 'var(--cyan)';
  if (name.charAt(0) === '#') return name;
  return COLOR_MAP[name] || 'var(--cyan)';
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

// --- Story metadata helpers ---

function nodeList(story) {
  return Object.values(story.nodes || {});
}

function endingCount(story) {
  return nodeList(story).filter((node) => node.is_ending || !node.choices?.length).length;
}

function estimateTime(story) {
  if (story.meta?.est_time) return story.meta.est_time;
  const words = nodeList(story).map((n) => n.text || "").join(" ").trim().split(/\s+/).filter(Boolean).length;
  const minutes = Math.max(5, Math.round(((words / 130) * 1.3) / 5) * 5);
  return `~${minutes} min`;
}

function storyTitle(entry) {
  return entry.story.meta?.title || entry.path.split("/").pop()?.replace(".json", "") || "Untitled Story";
}

function findEntry(path) {
  return library.find((entry) => entry.path === path);
}

// --- Settings UI helpers ---

var SPEED_PRESETS = [
  { label: 'Slowest', ms: 60 },
  { label: 'Slow',    ms: 40 },
  { label: 'Normal',  ms: 35 },
  { label: 'Fast',    ms: 15 },
  { label: 'Fastest', ms:  5 },
];

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

// --- Prompt ---

function promptPrefix() {
  if (currentScreen === 'game')           return 'Your choice (or <span class="key-back">Q</span> to menu): ';
  if (currentScreen === 'resume')         return 'Continue? (<span class="key-fwd">C</span> continue &middot; <span class="key-back">N</span> new game): ';
  if (currentScreen === 'warning')        return 'Proceed? (<span class="key-fwd">Y</span> continue &middot; <span class="key-back">N</span> back): ';
  if (currentScreen === 'ending')         return 'Play again? (<span class="key-fwd">Y</span> yes &middot; <span class="key-back">N</span> library): ';
  if (currentScreen === 'settings-speed') return speedCustomEdit ? 'Enter ms (5&ndash;200): ' : '&gt; ';
  return '&gt; ';
}

function updatePrompt() {
  var el = document.querySelector('.terminal-prompt-line');
  if (!el) return;
  el.innerHTML = promptPrefix() + escapeHtml(pendingInput) + '<span class="terminal-cursor">█</span>';
}

// --- Renderers ---

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
    '<div class="footer-hint">Enter a number, <span class="key-back">Q</span> to visit repo, C to clear saves, or <span class="key-fwd">S</span> for settings. Press Enter to confirm.</div>' +
    '<div class="footer-typewriter">T · Toggle typewriter (session only) <span class="' + (twOn ? 'tw-state-on' : 'tw-state-off') + '">' + (twOn ? 'ON' : 'OFF') + '</span></div>' +
    '<div class="terminal-prompt-line"></div>' +
    '</div></div>';
  updatePrompt();
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
    '<div class="footer-hint">Enter a number, <span class="key-back">B</span> to go back, or <span class="key-back">Q</span> to quit. Press Enter to confirm.</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '</div></div>';
  updatePrompt();
}

function renderResume(entry, skipWarnings) {
  pendingInput = '';
  currentScreen = 'resume';
  resumeEntry = entry;
  resumeSkipWarnings = skipWarnings;
  app.innerHTML =
    '<div class="terminal-screen">' +
    '<div class="terminal-prose">A save was found for this story.</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '</div>';
  updatePrompt();
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
    '<div class="terminal-prompt-line"></div>' +
    '</div>';
  updatePrompt();
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
    '<div class="terminal-prompt-line"></div>' +
    '</div>';
  updatePrompt();

  if (isTypewriterOn()) startTypewriter(document.getElementById('prose-text'), node.text);
}

function renderEnding(view) {
  pendingInput = '';
  currentScreen = 'ending';
  recordEnding(currentRun.story, currentRun.nodeId);
  deleteSave(currentRun.story.meta.id);

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
    '<div class="terminal-prompt-line"></div>' +
    '</div>';
  updatePrompt();

  if (isTypewriterOn()) startTypewriter(document.getElementById('prose-text'), view.node.text);
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
    '<div class="footer-hint">Enter a number to edit · <span class="key-fwd">S</span> save · <span class="key-back">X</span> discard. Press Enter to confirm.</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '</div></div>';
  updatePrompt();
}

function renderSpeedPresets() {
  pendingInput = '';
  currentScreen = 'settings-speed';
  speedCustomEdit = false;
  var current = settingsDraft.delay_ms;
  var isPreset = SPEED_PRESETS.some(function(p) { return p.ms === current; });

  var rows = SPEED_PRESETS.map(function(p, i) {
    var active = p.ms === current;
    var markerHtml = active
      ? '<span class="key-fwd">›</span>'
      : '<span class="setting-marker"> </span>';
    return '<div class="terminal-settings-row" data-action="speed-preset" data-index="' + i + '">' +
      markerHtml +
      '<span class="setting-num">' + (i + 1) + '.</span>' +
      '<span class="setting-name">' + escapeHtml(p.label) + '</span>' +
      '<span class="setting-value">' + p.ms + ' ms</span>' +
      '</div>';
  }).join('');

  var customVal = isPreset ? '' : current + ' ms';
  var customActive = !isPreset;
  rows +=
    '<div class="terminal-settings-row" data-action="speed-custom">' +
    (customActive ? '<span class="key-fwd">›</span>' : '<span class="setting-marker"> </span>') +
    '<span class="setting-num">6.</span>' +
    '<span class="setting-name">Custom</span>' +
    '<span class="setting-value" id="speed-custom-val">' + escapeHtml(customVal) + '</span>' +
    '</div>';

  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Settings – Typewriter Speed', 'green') +
    '<div class="terminal-list">' + rows + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">1–5 to pick preset &middot; <span class="key-fwd">6</span> for custom &middot; <span class="key-back">B</span> back. Press Enter to confirm.</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '</div></div>';
  updatePrompt();
}

function startSettingsEdit(rowIndex) {
  var row = SETTINGS_ROWS[rowIndex];
  if (!row) return;
  if (row.key === 'delay_ms') { renderSpeedPresets(); return; }
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

// --- Library dispatch ---

function renderLibrary() {
  currentRun = null;
  lastSaved = '';
  currentFolder = null;
  renderPicker();
}

function toggleTypewriter() {
  setSessionTw(!isTypewriterOn());
  if (currentScreen === 'library') renderPicker();
  else if (currentScreen === 'folder') renderFolder(currentFolder);
}

// --- Story flow ---

function startStory(entry, { resume = false, skipWarnings = false, skipResume = false } = {}) {
  if (!entry) return;
  if (!skipWarnings && entry.story.meta.warnings?.length) {
    renderWarnings(entry, resume);
    return;
  }
  if (resume && !skipResume && loadSave(entry.story.meta.id)) {
    renderResume(entry, skipWarnings);
    return;
  }
  const saved = resume ? loadSave(entry.story.meta.id) : null;
  if (!resume) deleteSave(entry.story.meta.id);
  currentRun = createRun(entry, saved);
  lastSaved = resume ? "Restored saved progress." : "";
  renderGame();
}

function choose(index) {
  if (!currentRun) return;
  var view = currentView(currentRun);
  var choice = view.choices[index];
  if (!choice) return;
  currentRun.state = applySets(choice.sets || {}, currentRun.state);
  currentRun.history.push(currentRun.nodeId);
  currentRun.nodeId = choice.next;
  if (currentRun.story.meta.auto_visited_flags !== false) {
    currentRun.state[`visited_${currentRun.nodeId}`] = true;
  }
  lastSaved = writeSave(currentRun.story, currentRun);
  renderGame();
}

// --- Event handlers ---

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
    if (!isTwAnimating()) choose(Number(button.dataset.index));
  } else if (action === 'settings-row') {
    startSettingsEdit(Number(button.dataset.row));
  } else if (action === 'speed-preset') {
    settingsDraft.delay_ms = SPEED_PRESETS[Number(button.dataset.index)].ms;
    renderSettings();
  } else if (action === 'speed-custom') {
    speedCustomEdit = true;
    updatePrompt();
  }
});

function handleSubmit(input) {
  if (!input) return;

  if (currentScreen === 'library') {
    if (input === 'q') { window.location.href = 'https://github.com/julianhernandezdev/ChoicesMatter'; return; }
    if (input === 't') { toggleTypewriter(); return; }
    if (input === 'c') {
      if (confirm('Clear all browser saves and ending progress?')) { clearAllProgress(); renderLibrary(); }
      return;
    }
    if (input === 's') { settingsDraft = null; renderSettings(); return; }
    var n = parseInt(input, 10);
    if (n >= 1 && n <= activeMenuEntries.length) {
      var me = activeMenuEntries[n - 1];
      if (me.type === 'folder') renderFolder(me.name);
      else startStory(me.entry, { resume: !!loadSave(me.entry.story.meta.id) });
    }

  } else if (currentScreen === 'folder') {
    if (input === 'q' || input === 'b') { renderLibrary(); return; }
    var nf = parseInt(input, 10);
    if (nf >= 1 && nf <= activeMenuEntries.length) {
      startStory(activeMenuEntries[nf - 1].entry, { resume: !!loadSave(activeMenuEntries[nf - 1].entry.story.meta.id) });
    }

  } else if (currentScreen === 'resume') {
    if (input === 'c') startStory(resumeEntry, { resume: true,  skipWarnings: resumeSkipWarnings, skipResume: true });
    if (input === 'n') startStory(resumeEntry, { resume: false, skipWarnings: resumeSkipWarnings, skipResume: true });

  } else if (currentScreen === 'warning') {
    if (input === 'y') startStory(warningEntry, { resume: warningResume, skipWarnings: true });
    if (input === 'n') renderLibrary();

  } else if (currentScreen === 'game') {
    if (input === 'q') { renderLibrary(); return; }
    var ng = parseInt(input, 10);
    var vg = currentView(currentRun);
    if (ng >= 1 && ng <= vg.choices.length) choose(ng - 1);

  } else if (currentScreen === 'ending') {
    if (input === 'y') startStory(currentRun.entry, { resume: false, skipWarnings: true });
    if (input === 'n') renderLibrary();

  } else if (currentScreen === 'settings') {
    if (input === 'x') { renderLibrary(); return; }
    if (input === 's') { saveTypewriterSettings(settingsDraft); renderLibrary(); return; }
    var ns = parseInt(input, 10);
    if (ns >= 1 && ns <= SETTINGS_ROWS.length) startSettingsEdit(ns - 1);

  } else if (currentScreen === 'settings-speed') {
    if (input === 'b') { renderSettings(); return; }
    if (speedCustomEdit) {
      var ms = parseInt(input, 10);
      if (!isNaN(ms) && ms >= 5 && ms <= 200) settingsDraft.delay_ms = ms;
      speedCustomEdit = false;
      renderSpeedPresets();
      return;
    }
    var sp = parseInt(input, 10);
    if (sp >= 1 && sp <= SPEED_PRESETS.length) {
      settingsDraft.delay_ms = SPEED_PRESETS[sp - 1].ms;
      renderSettings();
      return;
    }
    if (input === '6') {
      speedCustomEdit = true;
      updatePrompt();
      return;
    }
  }
}

document.addEventListener('keydown', function(e) {
  var key = e.key;
  var keyUp = key.toUpperCase();

  if (isTwAnimating()) {
    e.preventDefault();
    skipTypewriter();
    return;
  }

  // Settings row edit — real <input> is focused; Enter confirms, Escape cancels
  if (currentScreen === 'settings' && settingsEditRow !== null) {
    if (keyUp === 'ENTER')  { confirmSettingsEdit(); return; }
    if (keyUp === 'ESCAPE') { cancelSettingsEdit();  return; }
    return;
  }
  // Speed custom edit uses pendingInput (no real <input>), so falls through normally

  if (keyUp === 'BACKSPACE') {
    pendingInput = pendingInput.slice(0, -1);
    updatePrompt();
    e.preventDefault();
    return;
  }

  if (keyUp === 'ENTER') {
    var input = pendingInput.trim().toLowerCase();
    pendingInput = '';
    updatePrompt();
    handleSubmit(input);
    return;
  }

  if (key.length === 1) {
    pendingInput += key;
    updatePrompt();
    e.preventDefault();
  }
});

// --- Boot ---

async function loadLibrary() {
  const manifestResponse = await fetch("web/stories.json");
  if (!manifestResponse.ok) throw new Error("Could not load story manifest.");
  const manifest = await manifestResponse.json();
  const entries = await Promise.all((manifest.stories || []).map(async (item) => {
    const storyResponse = await fetch(item.path);
    if (!storyResponse.ok) throw new Error(`Could not load ${item.path}`);
    return { ...item, story: await storyResponse.json() };
  }));
  library = entries.sort((a, b) => storyTitle(a).localeCompare(storyTitle(b)));
  renderLibrary();
}

loadLibrary().catch((error) => {
  app.innerHTML =
    '<section class="error-card">' +
    '<h1>Could not load Choices Matter</h1>' +
    '<p>' + escapeHtml(error.message) + '</p>' +
    '<p class="muted">If you downloaded the files, run them from a small web server so the browser can fetch the story JSON.</p>' +
    '</section>';
});
