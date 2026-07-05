import { createRun, currentView, applySets } from "./engine.js";
import { loadSave, writeSave, deleteSave, loadGallery, recordEnding, clearAllProgress } from "./storage.js";
import { isTypewriterOn, setSessionTw, isTwAnimating, startTypewriter, skipTypewriter, loadTypewriterSettings, saveTypewriterSettings, TYPEWRITER_DEFAULTS } from "./typewriter.js";

const app = document.getElementById("app");
const mobileCapture = document.getElementById("mobile-capture");

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
var currentPage = 0;
var activeMenuEntries = [];
var warningEntry = null;
var warningResume = false;
var resumeEntry = null;
var resumeSkipWarnings = false;
var namePromptEntry = null;
var settingsDraft = null;
var settingsEditRow = null;
var speedCustomEdit = false;
var pendingInput = '';
var debugMode = false; // false | "author" | "all"
var sessionAccessible = null; // null | true | false — never written to disk
var currentSectionScreen = null;
var sectionDraftSnapshot = null;
var sectionEditRow = null;
var speedPresetsReturn = null;
var resetChecked = {};
var resetFeedback = '';

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

function setPageTitle(...parts) {
  document.title = [...parts, 'Choices Matter'].filter(Boolean).join(' — ');
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
  if (style === undefined || style === null || style === "") {
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

function debugTag(style) {
  // style === undefined/null: key absent (no tag); style === "": [empty] tag
  if (style === undefined || style === null) return '';
  var label = style === '' ? 'empty' : style;
  return '<span class="debug-tag">[' + escapeHtml(label) + ']</span>';
}

// --- Corruption rendering ---

var _CHARSET_MAP = {
  blocks:    ["█", "▓", "▒", "░"],
  symbols:   ["#", "@", "!", "?", "&", "*", "~"],
  diacritics: ["̈", "̊", "̃", "̂", "̄"],
};
var _PUNCT = new Set([...".,!?…—;:'\"()-\n "]);

function _lcgSelect(nTotal, nSelect, seed) {
  var a = 1664525, c = 1013904223, m = 4294967296;
  var state = seed % m;
  var indices = Array.from({ length: nTotal }, function(_, i) { return i; });
  for (var i = nTotal - 1; i >= nTotal - nSelect; i--) {
    state = (a * state + c) % m;
    var j = state % (i + 1);
    var tmp = indices[i]; indices[i] = indices[j]; indices[j] = tmp;
  }
  return new Set(indices.slice(nTotal - nSelect));
}

function _corruptString(span, cfg) {
  var charset = cfg.charset === "custom"
    ? [...(cfg.custom_chars || "█▓▒░")]
    : (_CHARSET_MAP[cfg.charset] || _CHARSET_MAP.blocks);
  if (!charset.length) return span.text;
  var corruptible = [...span.text].map(function(c, i) { return _PUNCT.has(c) ? null : i; }).filter(function(i) { return i !== null; });
  var count = Math.floor(corruptible.length * Math.min(span.intensity * (cfg.intensity != null ? cfg.intensity : 1.0), 1.0));
  if (count === 0) return span.text;
  var positions = span.mode === "consistent"
    ? _lcgSelect(corruptible.length, count, span.seed)
    : new Set([...Array(corruptible.length).keys()].sort(function() { return Math.random() - 0.5; }).slice(0, count));
  var a = 1664525, c = 1013904223, m = 4294967296;
  var state = span.seed % m;
  var chars = [...span.text];
  corruptible.forEach(function(charIdx, posIdx) {
    if (positions.has(posIdx)) {
      if (span.mode === "consistent") {
        state = (a * state + c) % m;
        chars[charIdx] = charset[state % charset.length];
      } else {
        chars[charIdx] = charset[Math.floor(Math.random() * charset.length)];
      }
    }
  });
  return chars.join("");
}

function _assembleText(segments, cfg) {
  if (!Array.isArray(segments)) return segments; // plain string fallback
  var corruption = (cfg && cfg.corruption) || {};
  return segments.map(function(seg) {
    if (typeof seg === "string") return seg.replace(/\{pause\}/g, "");
    if (!corruption.enabled) return seg.text;
    return _corruptString(seg, corruption);
  }).join("");
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

var SETTINGS_SECTIONS = [
  {
    id: 'typewriter', label: 'Typewriter',
    preserveOnGlobalReset: false, hasSubscreen: true,
    defaultKeys: ['enabled', 'delay_ms', 'pauses', 'pause_ms'],
    rows: [
      { key: 'enabled',   label: 'Enabled',        type: 'boolean',                             subsection: 'Typewriter' },
      { key: 'delay_ms',  label: 'Speed',           type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses..',  label: 'Pause after  .', type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses.!',  label: 'Pause after  !', type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses.?',  label: 'Pause after  ?', type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses.…', label: 'Pause after  …', type: 'number', unit: 'ms',        subsection: null },
      { key: 'pauses.—', label: 'Pause after  —', type: 'number', unit: 'ms',        subsection: null },
    ],
  },
  {
    id: 'display', label: 'Display',
    preserveOnGlobalReset: false, hasSubscreen: false,
    defaultKeys: ['page_size'],
    rows: [
      { key: 'page_size', label: 'Stories per page', type: 'number', unit: '', subsection: 'Display' },
    ],
  },
  {
    id: 'corruption', label: 'Corruption',
    preserveOnGlobalReset: false, hasSubscreen: true,
    defaultKeys: ['corruption'],
    rows: [
      { key: 'corruption.enabled',           label: 'Enabled',         type: 'boolean',                                              subsection: 'Corruption' },
      { key: 'corruption.intensity',         label: 'Intensity',       type: 'float',   unit: '×',                             subsection: null },
      { key: 'corruption.mode',              label: 'Mode',            type: 'cycle',   values: ['consistent', 'random'],            subsection: null },
      { key: 'corruption.charset',           label: 'Character set',   type: 'cycle',   values: ['blocks', 'symbols', 'diacritics', 'custom'], subsection: null },
      { key: 'corruption.animate',           label: 'Animate',         type: 'boolean',                                             subsection: null },
      { key: 'corruption.scramble_frames',   label: 'Scramble frames', type: 'number',  unit: '',                                   subsection: null },
      { key: 'corruption.scramble_delay_ms', label: 'Scramble delay',  type: 'number',  unit: 'ms',                                 subsection: null },
    ],
  },
  {
    id: 'player', label: 'Player',
    preserveOnGlobalReset: true, hasSubscreen: false,
    defaultKeys: ['player_name'],
    rows: [
      { key: 'player_name', label: 'Player name', type: 'text', subsection: 'Player' },
    ],
  },
  {
    id: 'accessibility', label: 'Accessibility',
    preserveOnGlobalReset: true, hasSubscreen: true,
    defaultKeys: ['accessible_mode'],
    rows: [
      { key: 'accessible_mode', label: 'Accessible mode', type: 'a11y', subsection: 'Accessibility' },
    ],
  },
];

var SETTINGS_ROWS = SETTINGS_SECTIONS.reduce(function(acc, section) {
  if (section.hasSubscreen) {
    acc.push({
      key: '__nav__' + section.id,
      label: section.label,
      type: 'nav',
      section: section.label,
      _section: section,
    });
  } else {
    section.rows.forEach(function(row, i) {
      acc.push(Object.assign({}, row, { section: i === 0 ? (row.subsection || section.label) : null }));
    });
  }
  return acc;
}, []);

function applyDefaults(draft, section) {
  section.defaultKeys.forEach(function(key) {
    if (key === 'pauses') {
      draft.pauses = Object.assign({}, TYPEWRITER_DEFAULTS.pauses);
    } else if (key === 'corruption') {
      draft.corruption = Object.assign({}, TYPEWRITER_DEFAULTS.corruption);
    } else {
      draft[key] = TYPEWRITER_DEFAULTS[key];
    }
  });
}

function getPageSize() { return loadTypewriterSettings().page_size || 5; }
function getTotalPages(entries) { return Math.max(1, Math.ceil(entries.length / getPageSize())); }
function getPagedEntries(entries) { var ps = getPageSize(); return entries.slice(currentPage * ps, (currentPage + 1) * ps); }

function changePage(delta) {
  var total = getTotalPages(activeMenuEntries);
  currentPage = delta === -Infinity ? 0 : Math.max(0, Math.min(total - 1, currentPage + delta));
  if (currentScreen === 'library') renderPicker();
  else if (currentScreen === 'folder') renderFolder(currentFolder);
}

function getSettingValue(draft, key) {
  if (key.indexOf('pauses.') === 0) return draft.pauses[key.slice('pauses.'.length)];
  if (key.indexOf('corruption.') === 0) return (draft.corruption || {})[key.slice('corruption.'.length)];
  return draft[key];
}

function setSettingValue(draft, key, value) {
  if (key.indexOf('pauses.') === 0) draft.pauses[key.slice('pauses.'.length)] = value;
  else if (key.indexOf('corruption.') === 0) {
    if (!draft.corruption) draft.corruption = {};
    draft.corruption[key.slice('corruption.'.length)] = value;
  } else {
    draft[key] = value;
  }
}

// --- Prompt ---

function promptPrefix() {
  if (currentScreen === 'settings' && settingsEditRow !== null) {
    var row = SETTINGS_ROWS[settingsEditRow];
    return 'Edit ' + (row ? row.label : 'value') + ': ';
  }
  if (currentScreen === 'settings-section' && sectionEditRow !== null) {
    var srow = currentSectionScreen ? currentSectionScreen.rows[sectionEditRow] : null;
    return 'Edit ' + (srow ? srow.label : 'value') + ': ';
  }
  if (currentScreen === 'name-prompt') {
    var pn = loadTypewriterSettings().player_name;
    return 'Name' + (pn ? ' [' + escapeHtml(pn) + ']' : '') + ': ';
  }
  if (currentScreen === 'game')           return 'Your choice (or <span class="key-back">Q</span> to menu): ';
  if (currentScreen === 'resume')         return 'Continue? (<span class="key-fwd">C</span> continue &middot; <span class="key-back">N</span> new game): ';
  if (currentScreen === 'warning')        return 'Proceed? (<span class="key-fwd">Y</span> continue &middot; <span class="key-back">N</span> back): ';
  if (currentScreen === 'ending')         return 'Play again? (<span class="key-fwd">Y</span> yes &middot; <span class="key-back">N</span> library): ';
  if (currentScreen === 'settings-speed') return speedCustomEdit ? 'Enter ms (5&ndash;200): ' : '&gt; ';
  if (currentScreen === 'settings-section') return '&gt; ';
  if (currentScreen === 'settings-section-reset') return '&gt; ';
  return '&gt; ';
}

function updatePrompt() {
  var el = document.querySelector('.terminal-prompt-line');
  if (!el) return;
  el.innerHTML = promptPrefix() + escapeHtml(pendingInput) + '<span class="terminal-cursor">█</span>';
  mobileCapture.value = pendingInput;
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
  if (isAccessibleMode()) { renderAccessiblePicker(); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'library';
  setPageTitle();
  var twOn = isTypewriterOn();

  var folders = {};
  var rootStories = [];
  library.forEach(function(entry) {
    var cat = entry.category || null;
    if (cat) { if (!folders[cat]) folders[cat] = []; folders[cat].push(entry); }
    else rootStories.push(entry);
  });

  var menuEntries = [];

  Object.keys(folders).sort().forEach(function(name) {
    menuEntries.push({ type: 'folder', name: name });
  });

  rootStories.forEach(function(entry) {
    menuEntries.push({ type: 'story', entry: entry });
  });

  activeMenuEntries = menuEntries;
  var totalPages = getTotalPages(menuEntries);
  var pagedEntries = getPagedEntries(menuEntries);
  var pagedItems = pagedEntries.map(function(me, i) {
    return me.type === 'folder'
      ? (function(name) {
          var count = folders[name].length;
          return '<div class="terminal-list-item" data-action="open-folder" data-folder="' + escapeHtml(name) + '">' +
            '<span class="item-num">' + (i + 1) + '.</span>' +
            '<div><div class="item-name">📁 ' + escapeHtml(name) + '/</div>' +
            '<div class="item-meta">' + count + ' ' + (count === 1 ? 'story' : 'stories') + '</div></div>' +
            '</div>';
        })(me.name)
      : renderPickerEntry(me.entry, i + 1);
  });

  var pageHint = totalPages > 1
    ? '<div class="footer-page-hint">Page ' + (currentPage + 1) + ' of ' + totalPages + '  ·  ↑/↓ or W/D to navigate · 0 for first page</div>'
    : '';

  app.innerHTML =
    '<div class="terminal-screen">' +
    '<div class="terminal-title-box">Choices Matter</div>' +
    renderRule('A text adventure engine', 'green') +
    renderRule('Select a Story', 'green') +
    '<div class="terminal-list">' + pagedItems.join('') + '</div>' +
    renderRule('', 'dim') +
    '<div class="terminal-footer">' +
    pageHint +
    '<div class="footer-hint">Enter a number, <span class="key-back">Q</span> to visit repo, C to clear saves, or <span class="key-fwd">S</span> for settings. Press Enter to confirm.</div>' +
    '<div class="footer-typewriter">' +
    'T · Typewriter <span class="' + (twOn ? 'tw-state-on' : 'tw-state-off') + '">' + (twOn ? 'ON' : 'OFF') + '</span>' +
    ' &nbsp;&nbsp; A · Accessible mode <span class="' + (isAccessibleMode() ? 'tw-state-on' : 'tw-state-off') + '">' + (isAccessibleMode() ? 'ON' : 'OFF') + '</span>' +
    '</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderFolder(folderName) {
  if (isAccessibleMode()) { renderAccessibleFolder(folderName); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'folder';
  setPageTitle(folderName);
  if (folderName !== currentFolder) currentPage = 0;
  currentFolder = folderName;
  var folderEntries = library.filter(function(e) { return e.category === folderName; });
  activeMenuEntries = folderEntries.map(function(entry) { return { type: 'story', entry: entry }; });
  var totalPages = getTotalPages(activeMenuEntries);
  var pagedEntries = getPagedEntries(activeMenuEntries);
  var items = pagedEntries.map(function(me, i) { return renderPickerEntry(me.entry, i + 1); });
  var pageHint = totalPages > 1
    ? '<div class="footer-page-hint">Page ' + (currentPage + 1) + ' of ' + totalPages + '  ·  ↑/↓ or W/D to navigate · 0 for first page</div>'
    : '';
  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('📁 ' + folderName + '/', 'green') +
    '<div class="terminal-list">' + items.join('') + '</div>' +
    '<div class="terminal-footer">' +
    pageHint +
    '<div class="footer-hint">Enter a number, <span class="key-back">B</span> to go back, or <span class="key-back">Q</span> to quit. Press Enter to confirm.</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderResume(entry, skipWarnings) {
  if (isAccessibleMode()) { renderAccessibleResume(entry, skipWarnings); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'resume';
  setPageTitle(storyTitle(entry));
  resumeEntry = entry;
  resumeSkipWarnings = skipWarnings;
  app.innerHTML =
    '<div class="terminal-screen">' +
    '<div class="terminal-prose">A save was found for this story.</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div>';
  updatePrompt();
}

function renderWarnings(entry, resume) {
  if (isAccessibleMode()) { renderAccessibleWarnings(entry, resume); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'warning';
  setPageTitle(storyTitle(entry));
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
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div>';
  updatePrompt();
}

function _resolvePlayerName(entered, meta) {
  if (entered !== '') return entered;
  if (meta.name_default) return meta.name_default;
  var savedName = loadTypewriterSettings().player_name;
  if (savedName) return savedName;
  return null; // reject — no fallback available
}

function renderNamePrompt() {
  if (isAccessibleMode()) { renderAccessibleNamePrompt(); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'name-prompt';
  setPageTitle('Protagonist');
  var meta = namePromptEntry.story.meta;
  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Protagonist', 'cyan') +
    '<p class="terminal-prose">' + escapeHtml(meta.name_prompt) + '</p>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint"><span class="key-back">Esc</span> to go back. Press Enter to confirm.</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div>' +
    '</div>';
  updatePrompt();
}

function renderAccessibleNamePrompt() {
  document.body.classList.add('reader-mode');
  currentScreen = 'name-prompt';
  setPageTitle('Protagonist');
  var meta = namePromptEntry.story.meta;
  var savedName = loadTypewriterSettings().player_name;
  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Protagonist</h1>' +
    '<p class="r-prose">' + escapeHtml(meta.name_prompt) + '</p>' +
    '<div class="r-name-form">' +
    '<label for="r-name-input" class="r-name-label">Your name</label>' +
    '<input id="r-name-input" type="text" class="r-name-input" value="' + escapeHtml(savedName || '') + '"' +
    (meta.name_default ? ' placeholder="' + escapeHtml(meta.name_default) + '"' : '') +
    ' autocomplete="off">' +
    '</div>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-submit-btn">Continue</button>' +
    '<button class="r-btn ghost r-back-btn">&#8592; Back</button>' +
    '</div>' +
    '</main>';

  var input = document.getElementById('r-name-input');
  if (input) input.focus();

  app.querySelector('.r-submit-btn').addEventListener('click', function() {
    var entered = input ? input.value.trim() : '';
    var resolvedName = _resolvePlayerName(entered, meta);
    if (resolvedName === null) {
      var errEl = app.querySelector('.r-name-error');
      if (!errEl) {
        errEl = document.createElement('p');
        errEl.className = 'r-name-error';
        errEl.textContent = 'Please enter a name, or set one in Settings.';
        if (input) input.parentNode.insertBefore(errEl, input.nextSibling);
      }
      if (input) input.focus();
      return;
    }
    startStory(namePromptEntry, { resume: false, skipWarnings: true, skipNamePrompt: true, playerName: resolvedName });
  });
  app.querySelector('.r-back-btn').addEventListener('click', renderLibrary);
}

function renderGame() {
  if (isAccessibleMode()) { renderAccessibleGame(); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  if (!currentRun) { renderLibrary(); return; }
  var view = currentView(currentRun);
  if (view.isEnding) { renderEnding(view); return; }

  currentScreen = 'game';
  setPageTitle(storyTitle(currentRun.entry));
  var node = view.node;
  var sceneRule = currentRun.currentScene ? renderRule(currentRun.currentScene, 'green') : '';
  var sep = '<span class="terminal-separator">' + '─'.repeat(PANEL_RULE_WIDTH) + '</span>';

  var cfg = loadTypewriterSettings();
  var beforeInsets = view.insets.before.map(function(inset) {
    var tag = debugMode ? debugTag(inset.style) : '';
    var item = Object.assign({}, inset, { text: _assembleText(inset.text, cfg) });
    return '<span class="terminal-inset">' + renderStyledLine(item, '') + tag + '</span>';
  }).join('');
  var afterInsets = view.insets.after.map(function(inset) {
    var tag = debugMode ? debugTag(inset.style) : '';
    var item = Object.assign({}, inset, { text: _assembleText(inset.text, cfg) });
    return '<span class="terminal-inset">' + renderStyledLine(item, '') + tag + '</span>';
  }).join('');

  var fallbackColor = node.choice_number_color || 'cyan';
  var choiceHtml = view.choices.map(function(choice, i) {
    var label = choice.obfuscated ? '[REDACTED ██████]' : choice.label;
    var colorVar = resolveColor(choice.color || fallbackColor);
    var redactTag = (debugMode && choice.obfuscated) ? '<span class="debug-tag">[redacted]</span>' : '';
    return '<div class="terminal-choice" data-action="choice" data-index="' + i + '">' +
      '<span class="choice-num" style="color:' + colorVar + '">' + (i + 1) + '.</span>' +
      '<span class="choice-label">' + escapeHtml(label) + redactTag + '</span></div>';
  }).join('');

  var beforeOverlays = view.overlays.before.map(function(o) {
    var tag = debugMode ? debugTag(o.style) : '';
    var ov = Object.assign({}, o, { text: _assembleText(o.text, cfg) });
    return '<span class="terminal-overlay">' + renderStyledLine(ov, '') + tag + '</span>';
  }).join('');
  var afterOverlays = view.overlays.after.map(function(o) {
    var tag = debugMode ? debugTag(o.style) : '';
    var ov = Object.assign({}, o, { text: _assembleText(o.text, cfg) });
    return '<span class="terminal-overlay">' + renderStyledLine(ov, '') + tag + '</span>';
  }).join('');

  var debugPanel = '';
  if (debugMode) {
    var state = currentRun.state || {};
    var flagPairs = Object.entries(state).filter(function(pair) {
      return debugMode === 'all' || !pair[0].startsWith('visited_');
    });
    var hint = debugMode === 'all'
      ? '(showing all flags)'
      : '(visited_* hidden &mdash; press - to show all)';
    var flagsInner;
    if (flagPairs.length === 0) {
      flagsInner = '<span class="debug-empty">(no flags set)</span>';
    } else {
      flagsInner = flagPairs.map(function(pair) {
        return '<span class="debug-flag"><span class="debug-key">' + escapeHtml(pair[0]) + ':</span> ' +
          '<span class="debug-val">' + escapeHtml(String(pair[1])) + '</span></span>';
      }).join('');
    }
    debugPanel = '<div class="debug-panel">' +
      '<div class="debug-panel-title">debug: flags</div>' +
      '<div class="debug-flags">' + flagsInner + '</div>' +
      '<div class="debug-hint">' + hint + '</div>' +
      '</div>';
  }

  app.innerHTML =
    '<div class="terminal-screen">' +
    sceneRule +
    '<div class="terminal-panel">' +
    '<span class="terminal-panel-title">' + escapeHtml(makeRule(storyTitle(currentRun.entry), PANEL_RULE_WIDTH)) + '</span>' +
    beforeInsets +
    (view.insets.before.length ? sep : '') +
    '<div class="terminal-prose" id="prose-text">' + escapeHtml(_assembleText(node.text, cfg)) + '</div>' +
    (view.insets.after.length ? sep : '') +
    afterInsets +
    '</div>' +
    beforeOverlays +
    '<div class="terminal-choices">' + choiceHtml + '</div>' +
    afterOverlays +
    debugPanel +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div>';
  updatePrompt();

  if (isTypewriterOn()) startTypewriter(document.getElementById('prose-text'), node.text);
}

function renderEnding(view) {
  if (isAccessibleMode()) { renderAccessibleEnding(view); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'ending';
  setPageTitle(storyTitle(currentRun.entry), 'Ending');
  recordEnding(currentRun.story, currentRun.nodeId);
  deleteSave(currentRun.story.meta.id);

  var cfg = loadTypewriterSettings();
  var type = view.node.ending_type || 'neutral';
  var overlays = [].concat(view.overlays.before, view.overlays.after)
    .map(function(o) {
      var ov = Object.assign({}, o, { text: _assembleText(o.text, cfg) });
      return '<span class="terminal-overlay">' + renderStyledLine(ov, '') + '</span>';
    })
    .join('');

  app.innerHTML =
    '<div class="terminal-screen">' +
    overlays +
    '<div class="terminal-panel ' + escapeHtml(type) + '">' +
    '<span class="terminal-ending-label ' + escapeHtml(type) + '">' + escapeHtml(makeRule(type.toUpperCase() + ' ENDING', PANEL_RULE_WIDTH)) + '</span>' +
    '<div class="terminal-prose ending-prose" id="prose-text">' + escapeHtml(_assembleText(view.node.text, cfg)) + '</div>' +
    '</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div>';
  updatePrompt();

  if (isTypewriterOn()) startTypewriter(document.getElementById('prose-text'), view.node.text);
}

function renderSettings() {
  var feedbackToShow = resetFeedback;
  resetFeedback = '';
  if (isAccessibleMode()) { renderAccessibleSettings(feedbackToShow); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings';
  setPageTitle('Settings');
  if (!settingsDraft) {
    var s = loadTypewriterSettings();
    settingsDraft = {
      enabled: s.enabled,
      delay_ms: s.delay_ms,
      pauses: Object.assign({}, s.pauses),
      page_size: s.page_size,
      accessible_mode: s.accessible_mode,
      player_name: s.player_name,
      corruption: Object.assign({}, s.corruption),
    };
  }
  settingsEditRow = null;

  var rows = '';
  var rowNum = 0;
  SETTINGS_ROWS.forEach(function(row, i) {
    if (row.section) {
      rows += renderRule(row.section, 'dim');
    }
    rowNum++;
    var val = getSettingValue(settingsDraft, row.key);
    var display;
    if (row.type === 'boolean') {
      display = val ? 'on' : 'off';
    } else if (row.type === 'a11y') {
      if (val === null || val === undefined) {
        display = 'Auto (currently: ' + (isAccessibleMode() ? 'reader' : 'terminal') + ')';
      } else {
        display = val ? 'On' : 'Off';
      }
    } else if (row.type === 'cycle') {
      display = val;
    } else if (row.type === 'nav') {
      display = '→';
    } else {
      display = val + (row.unit ? ' ' + row.unit : '');
    }
    rows += '<div class="terminal-settings-row" data-action="settings-row" data-row="' + i + '">' +
      '<span class="setting-num">' + rowNum + '.</span>' +
      '<span class="setting-name">' + escapeHtml(row.label) + '</span>' +
      '<span class="setting-value">' + escapeHtml(String(display)) + '</span>' +
      '</div>';
  });

  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Settings', 'green') +
    '<div class="terminal-list">' + rows + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Enter a number to edit &middot; <span class="key-fwd">S</span> save &middot; <span class="key-back">X</span> discard &middot; <span class="key-fwd">R</span> reset. Press Enter to confirm.' +
    (feedbackToShow ? '<div class="reset-feedback" style="color:#6af;margin-top:4px">✓ ' + escapeHtml(feedbackToShow) + '</div>' : '') + '</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderSpeedPresets() {
  if (isAccessibleMode()) { renderAccessibleSpeedPresets(); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings-speed';
  setPageTitle('Settings');
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
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderAccessiblePicker() {
  pendingInput = '';
  currentScreen = 'library';
  document.body.classList.add('reader-mode');
  setPageTitle();

  var folders = {};
  var rootStories = [];
  library.forEach(function(entry) {
    var cat = entry.category || null;
    if (cat) { if (!folders[cat]) folders[cat] = []; folders[cat].push(entry); }
    else rootStories.push(entry);
  });

  var menuEntries = [];
  Object.keys(folders).sort().forEach(function(name) {
    menuEntries.push({ type: 'folder', name: name });
  });
  rootStories.forEach(function(entry) {
    menuEntries.push({ type: 'story', entry: entry });
  });
  activeMenuEntries = menuEntries;

  var totalPages = getTotalPages(menuEntries);
  var pagedEntries = getPagedEntries(menuEntries);

  var itemsHtml = pagedEntries.map(function(me, i) {
    if (me.type === 'folder') {
      var count = folders[me.name].length;
      return '<li><button class="r-story-btn"' +
        ' aria-label="' + escapeHtml(me.name) + ' folder, ' + count + ' ' + (count === 1 ? 'story' : 'stories') + '">' +
        '<span class="r-story-name">' + escapeHtml(me.name) + '/</span>' +
        '<span class="r-story-meta">' + count + ' ' + (count === 1 ? 'story' : 'stories') + '</span>' +
        '</button></li>';
    }
    var entry = me.entry;
    var story = entry.story;
    var save = loadSave(story.meta.id);
    var gallery = loadGallery(story.meta.id);
    var endings = endingCount(story);
    var found = gallery.endings_found ? gallery.endings_found.length : 0;
    var time = estimateTime(story);
    var nodeCount = nodeList(story).length;
    var hasWarn = !!(story.meta.warnings && story.meta.warnings.length);
    var title = storyTitle(entry);
    var ariaLabel = title +
      (hasWarn ? ', contains content warnings' : '') +
      '. ' + nodeCount + ' nodes. ' + found + ' of ' + (endings || '?') +
      ' endings found. About ' + time + '.' +
      (save ? ' Save found.' : '');
    return '<li><button class="r-story-btn" aria-label="' + escapeHtml(ariaLabel) + '">' +
      '<span class="r-story-name">' + escapeHtml(title) +
      (hasWarn ? ' <span class="r-badge warning" aria-hidden="true">! Warnings</span>' : '') +
      (save ? ' <span class="r-badge resume" aria-hidden="true">&#x25CF; Resume</span>' : '') +
      '</span>' +
      '<span class="r-story-meta">' + nodeCount + ' nodes \xB7 ' + found + '/' + (endings || '?') + ' endings \xB7 ' + escapeHtml(time) + '</span>' +
      '</button></li>';
  }).join('');

  var pageHtml = totalPages > 1
    ? '<p class="r-page-hint">Page ' + (currentPage + 1) + ' of ' + totalPages + '</p>' +
      '<p class="r-page-nav">' +
      (currentPage > 0 ? '<button class="r-prev-btn">&#8592; Previous</button> ' : '') +
      (currentPage < totalPages - 1 ? '<button class="r-next-btn">Next &#8594;</button>' : '') +
      '</p>'
    : '';

  var twOn = isTypewriterOn();
  var a11yOn = isAccessibleMode();

  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Choices Matter</h1>' +
    '<p class="r-page-sub">Select a story to play.</p>' +
    '<div class="r-section-label" aria-hidden="true">Stories</div>' +
    '<nav aria-label="Story library"><ul class="r-story-list">' + itemsHtml + '</ul></nav>' +
    pageHtml +
    '<div class="r-nav">' +
    '<span class="r-nav-hint" aria-hidden="true">Tab to move \xB7 Space or Enter to choose</span>' +
    '<button class="r-btn ghost r-settings-btn">Settings</button>' +
    '<button class="r-btn ghost r-clear-btn">Clear all saves</button>' +
    '</div>' +
    '<div class="r-nav" style="border-top:none;padding-top:0;margin-top:4px">' +
    '<button class="r-btn ghost r-tw-btn" aria-pressed="' + twOn + '">' +
    '<span class="r-btn-dot" aria-hidden="true"></span>' + (twOn ? 'Typewriter ON' : 'Typewriter OFF') + '</button>' +
    '<button class="r-btn ghost r-a11y-btn" aria-pressed="' + a11yOn + '">' +
    '<span class="r-btn-dot" aria-hidden="true"></span>' + (a11yOn ? 'Accessible mode ON' : 'Accessible mode OFF') + '</button>' +
    '</div>' +
    '</main>';

  app.querySelectorAll('.r-story-btn').forEach(function(btn, i) {
    btn.addEventListener('click', function() {
      var me = activeMenuEntries[currentPage * getPageSize() + i];
      if (!me) return;
      if (me.type === 'folder') renderFolder(me.name);
      else startStory(me.entry, { resume: !!loadSave(me.entry.story.meta.id) });
    });
  });
  var settingsBtn = app.querySelector('.r-settings-btn');
  if (settingsBtn) settingsBtn.addEventListener('click', function() { settingsDraft = null; renderSettings(); });
  var clearBtn = app.querySelector('.r-clear-btn');
  if (clearBtn) clearBtn.addEventListener('click', function() {
    if (confirm('Clear all browser saves and ending progress?')) { clearAllProgress(); renderLibrary(); }
  });
  var twBtn = app.querySelector('.r-tw-btn');
  if (twBtn) twBtn.addEventListener('click', toggleTypewriter);
  var a11yBtn = app.querySelector('.r-a11y-btn');
  if (a11yBtn) a11yBtn.addEventListener('click', toggleAccessibleMode);
  var prevBtn = app.querySelector('.r-prev-btn');
  if (prevBtn) prevBtn.addEventListener('click', function() { changePage(-1); });
  var nextBtn = app.querySelector('.r-next-btn');
  if (nextBtn) nextBtn.addEventListener('click', function() { changePage(+1); });

  var first = app.querySelector('.r-story-btn');
  if (first) setTimeout(function() { first.focus(); }, 0);
}

function renderAccessibleFolder(folderName) {
  pendingInput = '';
  currentScreen = 'folder';
  if (folderName !== currentFolder) currentPage = 0;
  currentFolder = folderName;
  document.body.classList.add('reader-mode');
  setPageTitle(folderName);

  var folderEntries = library.filter(function(e) { return e.category === folderName; });
  activeMenuEntries = folderEntries.map(function(entry) { return { type: 'story', entry: entry }; });
  var totalPages = getTotalPages(activeMenuEntries);
  var pagedEntries = getPagedEntries(activeMenuEntries);

  var itemsHtml = pagedEntries.map(function(me, i) {
    var entry = me.entry;
    var story = entry.story;
    var save = loadSave(story.meta.id);
    var gallery = loadGallery(story.meta.id);
    var endings = endingCount(story);
    var found = gallery.endings_found ? gallery.endings_found.length : 0;
    var time = estimateTime(story);
    var nodeCount = nodeList(story).length;
    var title = storyTitle(entry);
    var ariaLabel = title + '. ' + nodeCount + ' nodes. ' + found + ' of ' + (endings || '?') +
      ' endings found. About ' + time + '.' + (save ? ' Save found.' : '');
    return '<li><button class="r-story-btn" aria-label="' + escapeHtml(ariaLabel) + '">' +
      '<span class="r-story-name">' + escapeHtml(title) + '</span>' +
      '<span class="r-story-meta">' + nodeCount + ' nodes \xB7 ' + found + '/' + (endings || '?') + ' endings \xB7 ' + escapeHtml(time) + '</span>' +
      (save ? '<span class="r-badge-resume" aria-hidden="true">&#x25CF; Resume</span>' : '') +
      '</button></li>';
  }).join('');

  var pageHtml = totalPages > 1
    ? '<p class="r-page-hint">Page ' + (currentPage + 1) + ' of ' + totalPages + '</p>' +
      '<p class="r-page-nav">' +
      (currentPage > 0 ? '<button class="r-prev-btn">&#8592; Previous</button> ' : '') +
      (currentPage < totalPages - 1 ? '<button class="r-next-btn">Next &#8594;</button>' : '') +
      '</p>'
    : '';

  app.innerHTML =
    '<main class="reader-screen">' +
    '<p class="r-scene" aria-label="Folder: ' + escapeHtml(folderName) + '">&#128193; ' + escapeHtml(folderName) + '</p>' +
    '<h1 class="r-page-title">' + folderEntries.length + ' stories in this folder</h1>' +
    '<nav aria-label="Folder contents"><ul class="r-story-list">' + itemsHtml + '</ul></nav>' +
    pageHtml +
    '<div class="r-nav"><button class="r-btn ghost r-back-btn">&#8592; Back to library</button></div>' +
    '</main>';

  app.querySelectorAll('.r-story-btn').forEach(function(btn, i) {
    btn.addEventListener('click', function() {
      var me = activeMenuEntries[currentPage * getPageSize() + i];
      if (me) startStory(me.entry, { resume: !!loadSave(me.entry.story.meta.id) });
    });
  });
  var prevBtn = app.querySelector('.r-prev-btn');
  if (prevBtn) prevBtn.addEventListener('click', function() { changePage(-1); });
  var nextBtn = app.querySelector('.r-next-btn');
  if (nextBtn) nextBtn.addEventListener('click', function() { changePage(+1); });
  app.querySelector('.r-back-btn').addEventListener('click', renderLibrary);

  var first = app.querySelector('.r-story-btn');
  if (first) first.focus();
}

function renderAccessibleResume(entry, skipWarnings) {
  pendingInput = '';
  currentScreen = 'resume';
  resumeEntry = entry;
  resumeSkipWarnings = skipWarnings;
  document.body.classList.add('reader-mode');
  setPageTitle(storyTitle(entry));

  var save = loadSave(entry.story.meta.id);
  var saveInfo = save
    ? 'A previous run is saved at <strong>' + escapeHtml(save.current_node) + '</strong>.'
    : 'Save data could not be read.';
  var saveAge = save && save.timestamp
    ? '<p class="r-prose" style="color:var(--r-ink-muted);font-size:14px;margin-top:8px">' +
      (save.history ? save.history.length : 0) + ' nodes visited</p>'
    : '';

  app.innerHTML =
    '<main class="reader-screen">' +
    '<p class="r-scene" aria-label="Story title">' + escapeHtml(storyTitle(entry)) + '</p>' +
    '<h1 class="r-page-title">A save was found</h1>' +
    '<div class="r-panel" aria-label="Saved progress">' +
    '<p class="r-prose">' + saveInfo + '</p>' +
    saveAge +
    '</div>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-continue-btn">Continue saved run</button>' +
    '<button class="r-btn r-new-btn">Start new game</button>' +
    '<button class="r-btn ghost r-back-btn">&#8592; Back to library</button>' +
    '</div>' +
    '</main>';

  app.querySelector('.r-continue-btn').addEventListener('click', function() {
    startStory(resumeEntry, { resume: true, skipWarnings: resumeSkipWarnings, skipResume: true });
  });
  app.querySelector('.r-new-btn').addEventListener('click', function() {
    startStory(resumeEntry, { resume: false, skipWarnings: resumeSkipWarnings, skipResume: true });
  });
  app.querySelector('.r-back-btn').addEventListener('click', renderLibrary);

  app.querySelector('.r-continue-btn').focus();
}

function renderAccessibleWarnings(entry, resume) {
  pendingInput = '';
  currentScreen = 'warning';
  warningEntry = entry;
  warningResume = resume;
  document.body.classList.add('reader-mode');
  setPageTitle(storyTitle(entry));

  var warnings = entry.story.meta.warnings || [];
  var itemsHtml = warnings.map(function(w) { return '<li>' + escapeHtml(w) + '</li>'; }).join('');

  app.innerHTML =
    '<main class="reader-screen">' +
    '<p class="r-scene" aria-label="Story title">' + escapeHtml(storyTitle(entry)) + '</p>' +
    '<h1 class="r-page-title">Content warning</h1>' +
    '<p class="r-page-sub">This story contains material some readers may want to know about before starting.</p>' +
    '<section class="r-panel r-warning-panel" aria-label="Content warnings">' +
    '<h2 class="r-warning-title">This story contains</h2>' +
    '<ul>' + itemsHtml + '</ul>' +
    '</section>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-proceed-btn">Proceed to story</button>' +
    '<button class="r-btn ghost r-back-btn">&#8592; Back to library</button>' +
    '</div>' +
    '</main>';

  app.querySelector('.r-proceed-btn').addEventListener('click', function() {
    startStory(warningEntry, { resume: warningResume, skipWarnings: true });
  });
  app.querySelector('.r-back-btn').addEventListener('click', renderLibrary);

  app.querySelector('.r-proceed-btn').focus();
}

function renderAccessibleGame() {
  if (!currentRun) { renderLibrary(); return; }
  var view = currentView(currentRun);
  if (view.isEnding) { renderAccessibleEnding(view); return; }

  pendingInput = '';
  currentScreen = 'game';
  document.body.classList.add('reader-mode');
  setPageTitle(storyTitle(currentRun.entry));

  var node = view.node;
  var titleStr = storyTitle(currentRun.entry);

  var sceneHtml = currentRun.currentScene
    ? '<p class="r-scene" aria-label="Scene: ' + escapeHtml(currentRun.currentScene) + '">' +
      escapeHtml(currentRun.currentScene) + '</p>'
    : '';

  var insetKindMap = { system: 'Artifact', memory: 'Memory', echo: 'Echo' };
  var overlayKindMap = { echo: 'Echo', whisper: 'Whisper', memory: 'Memory', warning: 'Warning' };

  function renderInset(it) {
    var kindLabel = insetKindMap[it.style] || 'Note';
    var cleanText = _assembleText(it.text, { corruption: { enabled: false } });
    return '<p class="r-inset" role="note" aria-label="' + escapeHtml(kindLabel + ': ' + cleanText) + '">' +
      '<span class="r-inset-kind" aria-hidden="true">' + escapeHtml(kindLabel) + '</span>' +
      '<span>' + escapeHtml(cleanText) + '</span>' +
      '</p>';
  }

  function renderOverlay(o) {
    var kindLabel = overlayKindMap[o.style] || 'Note';
    var cleanText = _assembleText(o.text, { corruption: { enabled: false } });
    return '<p class="r-overlay ' + escapeHtml(o.style || '') + '" aria-label="' + escapeHtml(kindLabel + ': ' + cleanText) + '">' +
      '<span class="r-overlay-kind" aria-hidden="true">' + escapeHtml(kindLabel) + '</span>' +
      '<span>' + escapeHtml(cleanText) + '</span>' +
      '</p>';
  }

  var beforeInsetsHtml = view.insets.before.length
    ? '<aside class="r-insets" aria-label="Notes">' +
      view.insets.before.map(renderInset).join('') + '</aside>'
    : '';

  var afterInsetsHtml = view.insets.after.length
    ? '<aside class="r-insets" aria-label="Notes">' +
      view.insets.after.map(renderInset).join('') + '</aside>'
    : '';

  var beforeOverlaysHtml = view.overlays.before.map(renderOverlay).join('');
  var afterOverlaysHtml  = view.overlays.after.map(renderOverlay).join('');

  var choicesHtml = view.choices.map(function(choice, i) {
    var label = choice.obfuscated ? '[REDACTED]' : choice.label;
    var danger = choice.color === 'bright_red';
    var safe   = choice.color === 'green';
    var btnClass = 'r-choice-btn' + (danger ? ' danger' : '') + (safe ? ' safe' : '');
    var ariaLabel = 'Choice ' + (i + 1) + ': ' + label + (danger ? '. Risky.' : safe ? '. Safe.' : '');
    return '<li><button class="' + btnClass + '"' +
      ' aria-label="' + escapeHtml(ariaLabel) + '">' +
      '<span class="r-choice-num" aria-hidden="true">' + (i + 1) + '.</span>' +
      '<span class="r-choice-text">' + escapeHtml(label) + '</span>' +
      (danger ? '<span class="r-choice-tag" aria-hidden="true">Risky</span>' : '') +
      (safe   ? '<span class="r-choice-tag" aria-hidden="true">Safe</span>'  : '') +
      '</button></li>';
  }).join('');

  var debugPressed = debugMode !== false ? 'true' : 'false';

  var debugPanelHtml = '';
  if (debugMode) {
    var state = currentRun.state || {};
    var flagPairs = Object.entries(state).filter(function(pair) {
      return debugMode === 'all' || !pair[0].startsWith('visited_');
    });
    var hintText = debugMode === 'all'
      ? '(showing all flags)'
      : '(visited_* hidden — press Debug to show all)';
    var ddsHtml = flagPairs.length === 0
      ? '<dt>(none)</dt><dd>—</dd>'
      : flagPairs.map(function(pair) {
          return '<dt>' + escapeHtml(pair[0]) + '</dt><dd>' + escapeHtml(String(pair[1])) + '</dd>';
        }).join('');
    var debugModeLabel = debugMode === 'all' ? 'all' : 'author';
    debugPanelHtml =
      '<section class="r-debug" aria-label="Debug: flag state">' +
      '<h2 class="r-debug-title">Flags \xB7 ' + debugModeLabel + '</h2>' +
      '<dl class="r-debug-flags">' + ddsHtml + '</dl>' +
      '<p class="r-debug-hint">' + escapeHtml(hintText) + '</p>' +
      '</section>';
  }

  var timeStr = estimateTime(currentRun.entry);

  app.innerHTML =
    '<main class="reader-screen">' +
    sceneHtml +
    beforeInsetsHtml +
    '<article class="r-panel" aria-label="Story: ' + escapeHtml(titleStr) + '">' +
    '<h1 class="r-story-title"><span>' + escapeHtml(titleStr) + '</span>' +
    '<span class="r-time">~' + escapeHtml(timeStr) + '</span></h1>' +
    '<p class="r-prose">' + escapeHtml(_assembleText(node.text, { corruption: { enabled: false } })) + '</p>' +
    '</article>' +
    afterInsetsHtml +
    beforeOverlaysHtml +
    '<nav aria-label="Story choices"><ul class="r-choices">' + choicesHtml + '</ul></nav>' +
    afterOverlaysHtml +
    '<div class="r-nav">' +
    '<span class="r-nav-hint" aria-hidden="true">Tab to move \xB7 Space or Enter to choose</span>' +
    '<button class="r-btn ghost r-back-btn">&#8592; Back to library</button>' +
    '<button class="r-btn ghost r-save-btn">Save</button>' +
    '<button class="r-btn ghost r-debug-btn" aria-pressed="' + debugPressed + '">' +
    '<span class="r-btn-dot" aria-hidden="true"></span>Debug' +
    '</button>' +
    '</div>' +
    debugPanelHtml +
    '</main>';

  app.querySelectorAll('.r-choice-btn').forEach(function(btn, i) {
    btn.addEventListener('click', function() { choose(i); });
  });
  app.querySelector('.r-back-btn').addEventListener('click', renderLibrary);
  app.querySelector('.r-save-btn').addEventListener('click', function() {
    if (currentRun) {
      lastSaved = writeSave(currentRun.story, currentRun);
      renderAccessibleGame();
    }
  });
  app.querySelector('.r-debug-btn').addEventListener('click', function() {
    debugMode = debugMode === false ? 'author' : debugMode === 'author' ? 'all' : false;
    renderAccessibleGame();
  });

  var firstChoice = app.querySelector('.r-choice-btn');
  if (firstChoice) firstChoice.focus();
}

function renderAccessibleEnding(view) {
  pendingInput = '';
  currentScreen = 'ending';
  document.body.classList.add('reader-mode');

  recordEnding(currentRun.story, currentRun.nodeId);
  deleteSave(currentRun.story.meta.id);
  setPageTitle(storyTitle(currentRun.entry), 'Ending');

  var type = view.node.ending_type || 'neutral';
  var typeLabel = type.charAt(0).toUpperCase() + type.slice(1) + ' Ending';

  var overlaysHtml = [].concat(view.overlays.before, view.overlays.after).map(function(o) {
    return '<p class="r-overlay">' + escapeHtml(_assembleText(o.text, { corruption: { enabled: false } })) + '</p>';
  }).join('');

  app.innerHTML =
    '<main class="reader-screen">' +
    overlaysHtml +
    '<article class="r-panel r-ending ' + escapeHtml(type) + '" aria-label="' + escapeHtml(typeLabel) + ' — story complete">' +
    '<span class="r-ending-label ' + escapeHtml(type) + '" aria-hidden="true">' + escapeHtml(typeLabel) + '</span>' +
    '<p class="r-prose">' + escapeHtml(_assembleText(view.node.text, { corruption: { enabled: false } })) + '</p>' +
    '</article>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-play-again-btn">Play again</button>' +
    '<button class="r-btn r-library-btn">Return to library</button>' +
    '</div>' +
    '</main>';

  app.querySelector('.r-play-again-btn').addEventListener('click', function() {
    startStory(currentRun.entry, { resume: false, skipWarnings: true });
  });
  app.querySelector('.r-library-btn').addEventListener('click', renderLibrary);

  app.querySelector('.r-play-again-btn').focus();
}

function renderAccessibleSettings(feedback) {
  pendingInput = '';
  currentScreen = 'settings';
  document.body.classList.add('reader-mode');
  setPageTitle('Settings');

  if (!settingsDraft) {
    var s = loadTypewriterSettings();
    settingsDraft = {
      enabled: s.enabled, delay_ms: s.delay_ms,
      pauses: Object.assign({}, s.pauses),
      page_size: s.page_size, accessible_mode: s.accessible_mode,
      player_name: s.player_name,
      corruption: Object.assign({}, s.corruption),
    };
  }
  settingsEditRow = null;

  var rowsHtml = '';
  var rowNum = 0;
  SETTINGS_ROWS.forEach(function(row, i) {
    rowNum++;
    var val = getSettingValue(settingsDraft, row.key);
    var display;
    if (row.type === 'boolean') {
      display = val ? 'On' : 'Off';
    } else if (row.type === 'a11y') {
      if (val === null || val === undefined) {
        display = 'Auto (currently: ' + (isAccessibleMode() ? 'reader' : 'terminal') + ')';
      } else {
        display = val ? 'On' : 'Off';
      }
    } else if (row.type === 'cycle') {
      display = val;
    } else {
      display = val + (row.unit ? ' ' + row.unit : '');
    }
    if (row.section) {
      rowsHtml += '<h2 class="r-settings-section">' + escapeHtml(row.section) + '</h2>';
    }
    rowsHtml +=
      '<div role="listitem" class="r-setting-row" tabindex="0" data-row-index="' + i + '"' +
      ' aria-label="' + escapeHtml(row.label) + ', currently ' + escapeHtml(String(display)) + '">' +
      '<span class="r-setting-num">' + rowNum + '.</span>' +
      '<span class="r-setting-label">' + escapeHtml(row.label) + '</span>' +
      '<span class="r-setting-value">' + escapeHtml(String(display)) + '</span>' +
      '</div>';
  });

  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Settings</h1>' +
    (feedback ? '<p class="r-reset-feedback" role="status" style="color:#6af">&#10003; ' + escapeHtml(feedback) + '</p>' : '') +
    '<p class="r-page-sub">Press Enter on a row to edit its value.</p>' +
    '<div class="r-settings" role="list" aria-label="Settings">' + rowsHtml + '</div>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-save-btn">Save</button>' +
    '<button class="r-btn ghost r-discard-btn">Discard</button>' +
    '<button class="r-btn ghost r-back-btn">&#8592; Back to library</button>' +
    '</div>' +
    '</main>';

  app.querySelectorAll('[data-row-index]').forEach(function(row) {
    row.addEventListener('click', function() { startSettingsEdit(Number(row.dataset.rowIndex)); });
    row.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); startSettingsEdit(Number(row.dataset.rowIndex)); }
    });
  });
  app.querySelector('.r-save-btn').addEventListener('click', function() {
    saveTypewriterSettings(settingsDraft);
    renderLibrary();
  });
  app.querySelector('.r-discard-btn').addEventListener('click', renderLibrary);
  app.querySelector('.r-back-btn').addEventListener('click', renderLibrary);

  var first = app.querySelector('[data-row-index]');
  if (first) first.focus();
}

function renderAccessibleSpeedPresets() {
  pendingInput = '';
  currentScreen = 'settings-speed';
  document.body.classList.add('reader-mode');
  speedCustomEdit = false;
  setPageTitle('Settings');

  var current = settingsDraft.delay_ms;

  var presetsHtml = SPEED_PRESETS.map(function(p, i) {
    var isActive = p.ms === current;
    var ariaLabel = p.label + ', ' + p.ms + ' ms' + (isActive ? '. Currently selected.' : '');
    return '<li><button class="r-preset-btn" aria-pressed="' + isActive + '" aria-label="' + escapeHtml(ariaLabel) + '">' +
      '<span class="r-preset-name">' + escapeHtml(p.label) + (isActive ? ' \xB7 current' : '') + '</span>' +
      '<span class="r-preset-ms">' + p.ms + ' ms</span>' +
      '</button></li>';
  }).join('');

  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Typewriter Speed</h1>' +
    '<p class="r-page-sub">Choose a preset. Current selection is highlighted.</p>' +
    '<nav aria-label="Speed presets"><ul class="r-presets">' + presetsHtml + '</ul></nav>' +
    '<div class="r-nav"><button class="r-btn ghost r-back-btn">&#8592; Back to settings</button></div>' +
    '</main>';

  app.querySelectorAll('.r-preset-btn').forEach(function(btn, i) {
    btn.addEventListener('click', function() {
      settingsDraft.delay_ms = SPEED_PRESETS[i].ms;
      if (speedPresetsReturn) { var fn = speedPresetsReturn; speedPresetsReturn = null; fn(); }
      else renderSettings();
    });
  });
  app.querySelector('.r-back-btn').addEventListener('click', renderSettings);

  var active = app.querySelector('.r-preset-btn[aria-pressed="true"]') || app.querySelector('.r-preset-btn');
  if (active) active.focus();
}

function renderAccessibleSectionSubscreen(section) {
  pendingInput = '';
  currentScreen = 'settings-section';
  document.body.classList.add('reader-mode');
  setPageTitle('Settings – ' + section.label);

  if (currentSectionScreen !== section) {
    sectionDraftSnapshot = {};
    section.defaultKeys.forEach(function(key) {
      var val = settingsDraft[key];
      sectionDraftSnapshot[key] = (val !== null && typeof val === 'object') ? Object.assign({}, val) : val;
    });
  }
  currentSectionScreen = section;

  var rowsHtml = section.rows.map(function(row, i) {
    var val = getSettingValue(settingsDraft, row.key);
    var display;
    if (row.type === 'boolean') display = val ? 'On' : 'Off';
    else if (row.type === 'a11y') display = val === null || val === undefined ? 'Auto' : val ? 'On' : 'Off';
    else if (row.type === 'cycle') display = val;
    else display = String(val != null ? val : '') + (row.unit ? ' ' + row.unit : '');
    return '<div role="listitem" class="r-setting-row" tabindex="0" data-section-row-index="' + i + '"' +
      ' aria-label="' + escapeHtml(row.label) + ', currently ' + escapeHtml(String(display)) + '">' +
      '<span class="r-setting-num">' + (i + 1) + '.</span>' +
      '<span class="r-setting-label">' + escapeHtml(row.label) + '</span>' +
      '<span class="r-setting-value">' + escapeHtml(String(display)) + '</span>' +
      '</div>';
  }).join('');

  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Settings – ' + escapeHtml(section.label) + '</h1>' +
    '<p class="r-page-sub">Press Enter on a row to edit its value.</p>' +
    '<div class="r-settings" role="list" aria-label="' + escapeHtml(section.label) + ' settings">' + rowsHtml + '</div>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-section-save-btn">Save</button>' +
    '<button class="r-btn ghost r-section-back-btn">&#8592; Back to settings</button>' +
    '<button class="r-btn ghost r-section-save-home-btn">Save &amp; Home</button>' +
    '<button class="r-btn ghost r-section-discard-home-btn">Discard &amp; Home</button>' +
    '<button class="r-btn ghost r-section-reset-btn">Reset section to defaults</button>' +
    '</div>' +
    '</main>';

  app.querySelectorAll('[data-section-row-index]').forEach(function(row) {
    row.addEventListener('click', function() { startSectionRowEdit(Number(row.dataset.sectionRowIndex)); });
    row.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); startSectionRowEdit(Number(row.dataset.sectionRowIndex)); }
    });
  });
  app.querySelector('.r-section-save-btn').addEventListener('click', function() {
    saveTypewriterSettings(settingsDraft); renderSettings();
  });
  app.querySelector('.r-section-back-btn').addEventListener('click', function() {
    Object.assign(settingsDraft, sectionDraftSnapshot); renderSettings();
  });
  app.querySelector('.r-section-save-home-btn').addEventListener('click', function() {
    saveTypewriterSettings(settingsDraft); settingsDraft = null; renderLibrary();
  });
  app.querySelector('.r-section-discard-home-btn').addEventListener('click', function() {
    settingsDraft = null; renderLibrary();
  });
  app.querySelector('.r-section-reset-btn').addEventListener('click', function() {
    if (confirm('Reset ' + section.label + ' to defaults?')) {
      applyDefaults(settingsDraft, section);
      renderAccessibleSectionSubscreen(section);
    }
  });

  var first = app.querySelector('[data-section-row-index]');
  if (first) first.focus();
}

function renderSectionSubscreen(section) {
  if (isAccessibleMode()) { renderAccessibleSectionSubscreen(section); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings-section';
  sectionEditRow = null;

  // Snapshot this section's keys so X can restore them — only on initial entry
  if (currentSectionScreen !== section) {
    sectionDraftSnapshot = {};
    section.defaultKeys.forEach(function(key) {
      var val = settingsDraft[key];
      sectionDraftSnapshot[key] = (val !== null && typeof val === 'object') ? Object.assign({}, val) : val;
    });
  }
  currentSectionScreen = section;

  setPageTitle('Settings – ' + section.label);

  var rows = '';
  section.rows.forEach(function(row, i) {
    var val = getSettingValue(settingsDraft, row.key);
    var display;
    if (row.type === 'boolean') {
      display = val ? 'on' : 'off';
    } else if (row.type === 'a11y') {
      display = val === null || val === undefined ? 'auto' : val ? 'on' : 'off';
    } else if (row.type === 'cycle') {
      display = val;
    } else {
      display = String(val != null ? val : '') + (row.unit ? ' ' + row.unit : '');
    }
    rows += '<div class="terminal-settings-row" data-action="section-row" data-row="' + i + '">' +
      '<span class="setting-num">' + (i + 1) + '.</span>' +
      '<span class="setting-name">' + escapeHtml(row.label) + '</span>' +
      '<span class="setting-value" id="section-val-' + i + '">' + escapeHtml(String(display)) + '</span>' +
      '</div>';
  });

  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Settings – ' + section.label, 'green') +
    '<div class="terminal-list">' + rows + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Enter a number to edit &middot; ' +
    '<span class="key-fwd">S</span> save &middot; ' +
    '<span class="key-back">X</span> back &middot; ' +
    '<span class="key-fwd">M</span> save+home &middot; ' +
    '<span class="key-back">Q</span> discard+home &middot; ' +
    '<span class="key-fwd">R</span> reset section</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">&#9000; Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderSectionResetConfirm() {
  if (!currentSectionScreen) return;
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings-section-reset';
  setPageTitle('Settings – ' + currentSectionScreen.label);
  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Reset ' + currentSectionScreen.label + ' to Defaults', 'green') +
    '<div class="terminal-list">' +
    '<div class="terminal-settings-row">' +
    '<span class="setting-name">Reset ' + escapeHtml(currentSectionScreen.label) + ' settings to defaults?</span>' +
    '</div></div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint"><span class="key-fwd">Y</span> confirm &middot; <span class="key-back">any other key</span> cancel</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">&#9000; Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderResetSelector() {
  if (isAccessibleMode()) { renderAccessibleResetSelector(); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings-reset';
  resetChecked = {};
  setPageTitle('Settings – Reset');
  renderResetSelectorView();
}

function renderResetSelectorView() {
  var resettable = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
  var rows = resettable.map(function(section, i) {
    var checked = !!resetChecked[section.id];
    var mark = checked ? '<span class="key-fwd">✓</span>' : ' ';
    return '<div class="terminal-settings-row" data-action="reset-toggle" data-index="' + i + '">' +
      '<span class="setting-num">' + (i + 1) + '.</span>' +
      '<span class="setting-name">[' + mark + '] ' + escapeHtml(section.label) + '</span>' +
      '</div>';
  }).join('');

  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Reset to Defaults', 'green') +
    '<div class="terminal-hint" style="padding:0 1em 0.5em;opacity:0.6">Note: Player name and accessible mode will always be preserved.</div>' +
    '<div class="terminal-list">' + rows + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Number + Enter to toggle &middot; <span class="key-fwd">Y</span> confirm &middot; <span class="key-back">X</span> cancel</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderAccessibleResetSelector() {
  pendingInput = '';
  currentScreen = 'settings-reset';
  resetChecked = {};
  document.body.classList.add('reader-mode');
  setPageTitle('Settings – Reset to Defaults');

  var resettable = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
  var itemsHtml = resettable.map(function(section, i) {
    return '<li><button class="r-btn ghost r-reset-section-btn" data-index="' + i + '"' +
      ' aria-pressed="false">' + escapeHtml(section.label) + '</button></li>';
  }).join('');

  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Reset to Defaults</h1>' +
    '<p class="r-page-sub">Note: Player name and accessible mode will always be preserved.</p>' +
    '<ul class="r-presets">' + itemsHtml + '</ul>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-reset-confirm-btn">Reset selected</button>' +
    '<button class="r-btn ghost r-reset-cancel-btn">Cancel</button>' +
    '</div>' +
    '</main>';

  app.querySelectorAll('.r-reset-section-btn').forEach(function(btn, i) {
    btn.addEventListener('click', function() {
      var sid = resettable[i].id;
      var checked = !!resetChecked[sid];
      resetChecked[sid] = !checked;
      btn.setAttribute('aria-pressed', String(!checked));
      btn.classList.toggle('r-btn-active', !checked);
    });
  });
  app.querySelector('.r-reset-confirm-btn').addEventListener('click', function() {
    var selected = resettable.filter(function(s) { return !!resetChecked[s.id]; });
    if (selected.length === 0) { alert('Nothing selected.'); return; }
    selected.forEach(function(s) { applyDefaults(settingsDraft, s); });
    resetFeedback = 'Reset: ' + selected.map(function(s) { return s.label; }).join(', ') + '.';
    renderSettings();
  });
  app.querySelector('.r-reset-cancel-btn').addEventListener('click', renderSettings);

  var first = app.querySelector('.r-reset-section-btn');
  if (first) first.focus();
}

function startSettingsEdit(rowIndex) {
  var row = SETTINGS_ROWS[rowIndex];
  if (!row) return;
  if (row.type === 'nav') {
    renderSectionSubscreen(row._section);
    return;
  }
  if (row.key === 'delay_ms') { renderSpeedPresets(); return; }
  var val = getSettingValue(settingsDraft, row.key);
  if (row.type === 'boolean') {
    setSettingValue(settingsDraft, row.key, !val);
    renderSettings();
    return;
  }
  if (row.type === 'a11y') {
    var cur = settingsDraft.accessible_mode;
    settingsDraft.accessible_mode = cur === null ? true : cur === true ? false : null;
    renderSettings();
    return;
  }
  if (row.type === 'cycle') {
    var cycleIdx = row.values ? row.values.indexOf(val) : -1;
    setSettingValue(settingsDraft, row.key, row.values[(cycleIdx < 0 ? 0 : cycleIdx + 1) % row.values.length]);
    renderSettings();
    return;
  }
  if (isAccessibleMode() && (row.type === 'number' || row.type === 'float' || row.type === 'text')) {
    var currentVal = getSettingValue(settingsDraft, row.key);
    var entered = window.prompt(row.label + ':', String(currentVal || ''));
    if (entered !== null) {
      if (row.type === 'text') {
        if (entered.trim() !== '') setSettingValue(settingsDraft, row.key, entered.trim());
      } else if (row.type === 'float') {
        var fnum = parseFloat(entered);
        if (!isNaN(fnum) && fnum >= 0 && fnum <= 1) setSettingValue(settingsDraft, row.key, fnum);
      } else {
        var num = parseInt(entered, 10);
        if (!isNaN(num)) {
          if (row.key === 'page_size') num = Math.max(1, Math.min(50, num));
          if (num >= 0) setSettingValue(settingsDraft, row.key, num);
        }
      }
    }
    renderSettings();
    return;
  }
  var rowEl = document.querySelector('.terminal-settings-row[data-row="' + rowIndex + '"]');
  if (!rowEl) return;
  settingsEditRow = rowIndex;
  var valEl = rowEl.querySelector('.setting-value');

  if (window.matchMedia('(pointer: coarse)').matches) {
    valEl.innerHTML = '<span class="setting-editing">(editing&hellip;)</span>';
    pendingInput = String(val);
    mobileCapture.value = String(val);
    var hintEl = document.querySelector('.footer-hint');
    if (hintEl) hintEl.innerHTML = 'Enter to confirm &middot; <span class="key-back">Esc</span> to cancel.';
    updatePrompt();
    mobileCapture.focus();
  } else {
    valEl.innerHTML = '<input class="setting-input" id="settings-edit-input" type="text" value="' + escapeHtml(String(val)) + '" autocomplete="off">';
    var input = document.getElementById('settings-edit-input');
    if (input) { input.focus(); input.select(); }
  }
}

function confirmSettingsEdit() {
  if (settingsEditRow === null) return;
  var row = SETTINGS_ROWS[settingsEditRow];
  if (!row) return;
  var inlineInput = document.getElementById('settings-edit-input');
  var valueStr = inlineInput ? inlineInput.value : pendingInput.trim();
  if (row.type === 'text') {
    if (valueStr.trim() !== '') {
      setSettingValue(settingsDraft, row.key, valueStr.trim());
    }
  } else if (row.type === 'float') {
    var fnum = parseFloat(valueStr);
    if (!isNaN(fnum) && fnum >= 0 && fnum <= 1) setSettingValue(settingsDraft, row.key, fnum);
  } else {
    var num = parseInt(valueStr, 10);
    if (!isNaN(num)) {
      if (row.key === 'page_size') num = Math.max(1, Math.min(50, num));
      if (num >= 0) setSettingValue(settingsDraft, row.key, num);
    }
  }
  settingsEditRow = null;
  pendingInput = '';
  renderSettings();
}

function cancelSettingsEdit() {
  settingsEditRow = null;
  pendingInput = '';
  renderSettings();
}

function startSectionRowEdit(rowIndex) {
  if (!currentSectionScreen) return;
  var row = currentSectionScreen.rows[rowIndex];
  if (!row) return;
  var val = getSettingValue(settingsDraft, row.key);

  if (row.key === 'delay_ms') {
    speedPresetsReturn = function() { renderSectionSubscreen(currentSectionScreen); };
    renderSpeedPresets();
    return;
  }
  if (row.type === 'boolean') {
    setSettingValue(settingsDraft, row.key, !val);
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  if (row.type === 'a11y') {
    var cur = settingsDraft.accessible_mode;
    settingsDraft.accessible_mode = cur === null ? true : cur === true ? false : null;
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  if (row.type === 'cycle') {
    var cycleIdx = row.values ? row.values.indexOf(val) : -1;
    setSettingValue(settingsDraft, row.key, row.values[(cycleIdx < 0 ? 0 : cycleIdx + 1) % row.values.length]);
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  if (isAccessibleMode() && (row.type === 'number' || row.type === 'float' || row.type === 'text')) {
    var entered = window.prompt(row.label + ':', String(val || ''));
    if (entered !== null) {
      if (row.type === 'text') {
        if (entered.trim() !== '') setSettingValue(settingsDraft, row.key, entered.trim());
      } else if (row.type === 'float') {
        var fnum = parseFloat(entered);
        if (!isNaN(fnum) && fnum >= 0 && fnum <= 1) setSettingValue(settingsDraft, row.key, fnum);
      } else {
        var num = parseInt(entered, 10);
        if (!isNaN(num) && num >= 0) setSettingValue(settingsDraft, row.key, num);
      }
    }
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  // Inline edit (desktop)
  sectionEditRow = rowIndex;
  var valEl = document.getElementById('section-val-' + rowIndex);
  if (!valEl) return;
  if (window.matchMedia('(pointer: coarse)').matches) {
    valEl.innerHTML = '<span class="setting-editing">(editing&hellip;)</span>';
    pendingInput = String(val);
    mobileCapture.value = String(val);
    var hintEl = document.querySelector('.footer-hint');
    if (hintEl) hintEl.innerHTML = 'Enter to confirm &middot; <span class="key-back">Esc</span> to cancel.';
    updatePrompt();
    mobileCapture.focus();
  } else {
    valEl.innerHTML = '<input class="setting-input" id="section-edit-input" type="text" value="' + escapeHtml(String(val)) + '" autocomplete="off">';
    var input = document.getElementById('section-edit-input');
    if (input) { input.focus(); input.select(); }
  }
}

function confirmSectionRowEdit() {
  if (sectionEditRow === null || !currentSectionScreen) return;
  var row = currentSectionScreen.rows[sectionEditRow];
  if (!row) return;
  var inlineInput = document.getElementById('section-edit-input');
  var valueStr = inlineInput ? inlineInput.value : pendingInput.trim();
  if (row.type === 'text') {
    if (valueStr.trim() !== '') setSettingValue(settingsDraft, row.key, valueStr.trim());
  } else if (row.type === 'float') {
    var fnum = parseFloat(valueStr);
    if (!isNaN(fnum) && fnum >= 0 && fnum <= 1) setSettingValue(settingsDraft, row.key, fnum);
  } else {
    var num = parseInt(valueStr, 10);
    if (!isNaN(num) && num >= 0) setSettingValue(settingsDraft, row.key, num);
  }
  sectionEditRow = null;
  pendingInput = '';
  renderSectionSubscreen(currentSectionScreen);
}

function cancelSectionRowEdit() {
  sectionEditRow = null;
  pendingInput = '';
  renderSectionSubscreen(currentSectionScreen);
}

// --- Library dispatch ---

function renderLibrary() {
  currentRun = null;
  lastSaved = '';
  currentFolder = null;
  currentPage = 0;
  debugMode = false;
  renderPicker();
}

function toggleTypewriter() {
  setSessionTw(!isTypewriterOn());
  if (currentScreen === 'library') renderPicker();
  else if (currentScreen === 'folder') renderFolder(currentFolder);
}

function isAccessibleMode() {
  if (sessionAccessible !== null) return sessionAccessible;
  var saved = loadTypewriterSettings().accessible_mode;
  if (saved !== null && saved !== undefined) return saved;
  return matchMedia('(prefers-reduced-motion: reduce)').matches ||
         matchMedia('(prefers-contrast: more)').matches;
}

function toggleAccessibleMode() {
  sessionAccessible = !isAccessibleMode();
  if (currentScreen === 'library') renderPicker();
  else if (currentScreen === 'folder') renderFolder(currentFolder);
}

// --- Story flow ---

function startStory(entry, { resume = false, skipWarnings = false, skipResume = false, skipNamePrompt = false, playerName = null } = {}) {
  if (!entry) return;
  if (!skipWarnings && entry.story.meta.warnings?.length) {
    renderWarnings(entry, resume);
    return;
  }
  if (resume && !skipResume && loadSave(entry.story.meta.id)) {
    renderResume(entry, skipWarnings);
    return;
  }
  if (entry.story.meta.name_prompt && !resume && !skipNamePrompt) {
    namePromptEntry = entry;
    renderNamePrompt();
    return;
  }
  const saved = resume ? loadSave(entry.story.meta.id) : null;
  if (!resume) deleteSave(entry.story.meta.id);
  const resolvedName = playerName !== null ? playerName : loadTypewriterSettings().player_name;
  currentRun = createRun(entry, saved, { player_name: resolvedName });
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
  } else if (action === 'section-row') {
    startSectionRowEdit(Number(button.dataset.row));
  } else if (action === 'show-keyboard') {
    mobileCapture.value = pendingInput;
    mobileCapture.focus();
  } else if (action === 'speed-preset') {
    settingsDraft.delay_ms = SPEED_PRESETS[Number(button.dataset.index)].ms;
    if (speedPresetsReturn) { var fn = speedPresetsReturn; speedPresetsReturn = null; fn(); }
    else renderSettings();
  } else if (action === 'reset-toggle') {
    var rtIdx = Number(button.dataset.index);
    var resettableList = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
    if (rtIdx >= 0 && rtIdx < resettableList.length) {
      var rtSid = resettableList[rtIdx].id;
      resetChecked[rtSid] = !resetChecked[rtSid];
      renderResetSelectorView();
    }
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
    if (input === 'a') { toggleAccessibleMode(); return; }
    if (input === 'c') {
      if (confirm('Clear all browser saves and ending progress?')) { clearAllProgress(); renderLibrary(); }
      return;
    }
    if (input === 's') { settingsDraft = null; renderSettings(); return; }
    var n = parseInt(input, 10);
    var ps = getPageSize();
    if (n >= 1 && n <= Math.min(ps, activeMenuEntries.length - currentPage * ps)) {
      var me = activeMenuEntries[currentPage * ps + (n - 1)];
      if (me.type === 'folder') renderFolder(me.name);
      else startStory(me.entry, { resume: !!loadSave(me.entry.story.meta.id) });
    }

  } else if (currentScreen === 'folder') {
    if (input === 'q' || input === 'b') { renderLibrary(); return; }
    var nf = parseInt(input, 10);
    var psf = getPageSize();
    if (nf >= 1 && nf <= Math.min(psf, activeMenuEntries.length - currentPage * psf)) {
      var fullIdxF = currentPage * psf + (nf - 1);
      startStory(activeMenuEntries[fullIdxF].entry, { resume: !!loadSave(activeMenuEntries[fullIdxF].entry.story.meta.id) });
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
    if (input === 'r') { renderResetSelector(); return; }
    var ns = parseInt(input, 10);
    if (ns >= 1 && ns <= SETTINGS_ROWS.length) startSettingsEdit(ns - 1);

  } else if (currentScreen === 'settings-section') {
    if (input === 's') { saveTypewriterSettings(settingsDraft); renderSettings(); return; }
    if (input === 'x') { if (sectionDraftSnapshot) Object.assign(settingsDraft, sectionDraftSnapshot); renderSettings(); return; }
    if (input === 'm') { saveTypewriterSettings(settingsDraft); settingsDraft = null; renderLibrary(); return; }
    if (input === 'q') { settingsDraft = null; renderLibrary(); return; }
    if (input === 'r') {
      renderSectionResetConfirm();
      return;
    }
    var nss = parseInt(input, 10);
    if (currentSectionScreen && nss >= 1 && nss <= currentSectionScreen.rows.length) startSectionRowEdit(nss - 1);

  } else if (currentScreen === 'settings-section-reset') {
    if (input === 'y') {
      applyDefaults(settingsDraft, currentSectionScreen);
    }
    renderSectionSubscreen(currentSectionScreen);

  } else if (currentScreen === 'settings-reset') {
    var resettable = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
    if (input === 'x') { renderSettings(); return; }
    if (input === 'y') {
      var selected = resettable.filter(function(s) { return !!resetChecked[s.id]; });
      if (selected.length === 0) {
        renderResetSelectorView();
        return;
      }
      selected.forEach(function(s) { applyDefaults(settingsDraft, s); });
      resetFeedback = 'Reset: ' + selected.map(function(s) { return s.label; }).join(', ') + '.';
      renderSettings();
      return;
    }
    var rn = parseInt(input, 10);
    if (rn >= 1 && rn <= resettable.length) {
      var sid = resettable[rn - 1].id;
      resetChecked[sid] = !resetChecked[sid];
      renderResetSelectorView();
    }

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
      if (speedPresetsReturn) { var fn = speedPresetsReturn; speedPresetsReturn = null; fn(); }
      else renderSettings();
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
  if (e.target === mobileCapture) return;
  if (isAccessibleMode()) return;

  var key = e.key;
  var keyUp = key.toUpperCase();

  if (isTwAnimating()) {
    e.preventDefault();
    skipTypewriter();
    return;
  }

  if (currentScreen === 'name-prompt' && keyUp === 'ESCAPE') {
    pendingInput = '';
    renderLibrary();
    return;
  }

  // Settings row edit — real <input> is focused; Enter confirms, Escape cancels
  if (currentScreen === 'settings' && settingsEditRow !== null) {
    if (keyUp === 'ENTER')  { confirmSettingsEdit(); return; }
    if (keyUp === 'ESCAPE') { cancelSettingsEdit();  return; }
    return;
  }
  // Section subscreen row edit — same pattern
  if (currentScreen === 'settings-section' && sectionEditRow !== null) {
    if (keyUp === 'ENTER')  { confirmSectionRowEdit(); return; }
    if (keyUp === 'ESCAPE') { cancelSectionRowEdit();  return; }
    return;
  }
  // Speed custom edit uses pendingInput (no real <input>), so falls through normally

  if (currentScreen === 'library' || currentScreen === 'folder') {
    if (key === 'ArrowUp')   { e.preventDefault(); changePage(-1);        return; }
    if (key === 'ArrowDown') { e.preventDefault(); changePage(+1);        return; }
    if (getTotalPages(activeMenuEntries) > 1) {
      if (keyUp === 'W') { e.preventDefault(); changePage(-1);        return; }
      if (keyUp === 'D') { e.preventDefault(); changePage(+1);        return; }
      if (key === '0')   { e.preventDefault(); changePage(-Infinity); return; }
    }
  }

  if (key === '-' && currentScreen === 'game') {
    e.preventDefault();
    debugMode = debugMode === false ? 'author' : debugMode === 'author' ? 'all' : false;
    renderGame();
    return;
  }

  if (keyUp === 'BACKSPACE') {
    pendingInput = pendingInput.slice(0, -1);
    updatePrompt();
    e.preventDefault();
    return;
  }

  if (keyUp === 'ENTER') {
    if (currentScreen === 'name-prompt') {
      var rawName = pendingInput.trim(); // preserve case — do NOT toLowerCase
      pendingInput = '';
      updatePrompt();
      var resolvedName = _resolvePlayerName(rawName, namePromptEntry.story.meta);
      if (resolvedName === null) { renderNamePrompt(); return; } // re-prompt
      startStory(namePromptEntry, { resume: false, skipWarnings: true, skipNamePrompt: true, playerName: resolvedName });
      return;
    }
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

// --- Mobile keyboard capture ---

document.addEventListener('click', function() {
  if (isTwAnimating()) { skipTypewriter(); }
});

mobileCapture.addEventListener('input', function() {
  if (currentScreen === 'settings' && settingsEditRow !== null) {
    var inline = document.getElementById('settings-edit-input');
    if (inline) {
      inline.value = mobileCapture.value;
    } else {
      pendingInput = mobileCapture.value;
      updatePrompt();
    }
    return;
  }
  if (currentScreen === 'settings-section' && sectionEditRow !== null) {
    var sectionInline = document.getElementById('section-edit-input');
    if (sectionInline) {
      sectionInline.value = mobileCapture.value;
    } else {
      pendingInput = mobileCapture.value;
      updatePrompt();
    }
    return;
  }
  pendingInput = mobileCapture.value;
  updatePrompt();
});

mobileCapture.addEventListener('keydown', function(e) {
  if (currentScreen === 'settings' && settingsEditRow !== null) {
    if (e.key === 'Enter') {
      e.preventDefault();
      mobileCapture.value = '';
      confirmSettingsEdit();
      setTimeout(function() { mobileCapture.focus(); }, 0);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      mobileCapture.value = '';
      cancelSettingsEdit();
      setTimeout(function() { mobileCapture.focus(); }, 0);
    }
    return;
  }
  if (currentScreen === 'settings-section' && sectionEditRow !== null) {
    if (e.key === 'Enter') {
      e.preventDefault();
      mobileCapture.value = '';
      confirmSectionRowEdit();
      setTimeout(function() { mobileCapture.focus(); }, 0);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      mobileCapture.value = '';
      cancelSectionRowEdit();
      setTimeout(function() { mobileCapture.focus(); }, 0);
    }
    return;
  }
  if (e.key === 'Enter') {
    e.preventDefault();
    if (currentScreen === 'name-prompt') {
      var rawName = pendingInput.trim();
      pendingInput = '';
      mobileCapture.value = '';
      var resolvedName = _resolvePlayerName(rawName, namePromptEntry.story.meta);
      if (resolvedName === null) { renderNamePrompt(); return; }
      startStory(namePromptEntry, { resume: false, skipWarnings: true, skipNamePrompt: true, playerName: resolvedName });
      return;
    }
    var input = pendingInput.trim().toLowerCase();
    pendingInput = '';
    mobileCapture.value = '';
    updatePrompt();
    handleSubmit(input);
    window.scrollTo(0, 0);
    setTimeout(function() { mobileCapture.focus(); }, 0);
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
