const SETTINGS_KEY = "choices-matter:typewriter-settings";

export const TYPEWRITER_DEFAULTS = {
  enabled: true,
  delay_ms: 20,
  pause_ms: 500,
  pauses: { '.': 150, '!': 150, '?': 150, '…': 200, '—': 100 },
  page_size: 5,
  accessible_mode: null,
  player_name: "Felix",
  corruption: {
    enabled: true,
    charset: "blocks",
    intensity: 1.0,
    animate: true,
    scramble_frames: 5,
    scramble_delay_ms: 50,
  },
};

export function loadTypewriterSettings() {
  try {
    var stored = JSON.parse(localStorage.getItem(SETTINGS_KEY));
    if (!stored) throw new Error();
    return {
      enabled: typeof stored.enabled === 'boolean' ? stored.enabled : TYPEWRITER_DEFAULTS.enabled,
      delay_ms: typeof stored.delay_ms === 'number' ? stored.delay_ms : TYPEWRITER_DEFAULTS.delay_ms,
      pause_ms: typeof stored.pause_ms === 'number' ? stored.pause_ms : TYPEWRITER_DEFAULTS.pause_ms,
      pauses: Object.assign({}, TYPEWRITER_DEFAULTS.pauses, stored.pauses || {}),
      page_size: (typeof stored.page_size === 'number' && stored.page_size >= 1) ? stored.page_size : TYPEWRITER_DEFAULTS.page_size,
      accessible_mode: (stored.accessible_mode === true || stored.accessible_mode === false)
        ? stored.accessible_mode
        : TYPEWRITER_DEFAULTS.accessible_mode,
      player_name: typeof stored.player_name === 'string' ? stored.player_name : TYPEWRITER_DEFAULTS.player_name,
      corruption: stored.corruption && typeof stored.corruption === 'object'
        ? Object.assign({}, TYPEWRITER_DEFAULTS.corruption, stored.corruption)
        : Object.assign({}, TYPEWRITER_DEFAULTS.corruption),
    };
  } catch {
    return {
      enabled: TYPEWRITER_DEFAULTS.enabled,
      delay_ms: TYPEWRITER_DEFAULTS.delay_ms,
      pause_ms: TYPEWRITER_DEFAULTS.pause_ms,
      pauses: Object.assign({}, TYPEWRITER_DEFAULTS.pauses),
      page_size: TYPEWRITER_DEFAULTS.page_size,
      accessible_mode: TYPEWRITER_DEFAULTS.accessible_mode,
      player_name: TYPEWRITER_DEFAULTS.player_name,
      corruption: Object.assign({}, TYPEWRITER_DEFAULTS.corruption),
    };
  }
}

export function saveTypewriterSettings(settings) {
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch {}
}

var sessionTwEnabled = null;

export function isTypewriterOn() {
  return sessionTwEnabled !== null ? sessionTwEnabled : loadTypewriterSettings().enabled;
}

export function setSessionTw(value) {
  sessionTwEnabled = value;
}

export function stripPauseTokens(text) {
  return text.split('{pause}').join('');
}

// --- Corruption helpers for typewriter ---

var _TW_CHARSET_MAP = {
  blocks:    ["█", "▓", "▒", "░"],
  symbols:   ["#", "@", "!", "?", "&", "*", "~"],
  diacritics: ["̈", "̊", "̃", "̂", "̄"],
};
var _TW_PUNCT = new Set([...".,!?…—;:'\"()-\n "]);

function _twLcgSelect(nTotal, nSelect, seed) {
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

function _twCorruptString(span, corruption) {
  var charset = corruption.charset === "custom"
    ? [...(corruption.custom_chars || "█▓▒░")]
    : (_TW_CHARSET_MAP[corruption.charset] || _TW_CHARSET_MAP.blocks);
  if (!charset.length) return span.text;
  var corruptible = [...span.text].map(function(c, i) { return _TW_PUNCT.has(c) ? null : i; }).filter(function(i) { return i !== null; });
  var count = Math.floor(corruptible.length * Math.min(span.intensity * (corruption.intensity != null ? corruption.intensity : 1.0), 1.0));
  if (count === 0) return span.text;
  var positions = span.mode === "consistent"
    ? _twLcgSelect(corruptible.length, count, span.seed)
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

// ---

var twAnimation = null;

export function isTwAnimating() {
  return twAnimation !== null;
}

export function startTypewriter(element, textOrSegments) {
  var settings = loadTypewriterSettings();
  var corruption = settings.corruption || {};
  var pauses = settings.pauses || {};
  var delay = settings.delay_ms || 20;
  var pauseMs = settings.pause_ms || 500;

  // Normalize input: plain string → single-element array
  var inputSegments = typeof textOrSegments === 'string' ? [textOrSegments]
    : Array.isArray(textOrSegments) ? textOrSegments
    : [String(textOrSegments || '')];

  // Build full assembled text for skip-to-end
  var fullText = inputSegments.map(function(seg) {
    if (typeof seg === 'string') return seg.replace(/\{pause\}/g, '');
    if (!corruption.enabled) return seg.text;
    return _twCorruptString(seg, corruption);
  }).join('');

  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    element.textContent = fullText;
    return;
  }

  // Build play queue: flat list of { type: 'text'|'pause', text? }
  var playQueue = [];
  inputSegments.forEach(function(seg) {
    if (typeof seg === 'string') {
      var parts = seg.split('{pause}');
      parts.forEach(function(part, i) {
        if (part.length > 0) playQueue.push({ type: 'text', text: part });
        if (i < parts.length - 1) playQueue.push({ type: 'pause' });
      });
    } else {
      // CorruptedSpan
      var rendered = corruption.enabled ? _twCorruptString(seg, corruption) : seg.text;
      if (corruption.enabled && corruption.animate && corruption.scramble_frames > 0) {
        playQueue.push({ type: 'scramble', span: seg, frames: corruption.scramble_frames, delay: corruption.scramble_delay_ms, settled: rendered });
      } else if (rendered.length > 0) {
        playQueue.push({ type: 'text', text: rendered });
      }
    }
  });

  element.textContent = '';
  var toReveal = Array.from(
    document.querySelectorAll('.terminal-choice, .terminal-overlay, .terminal-prompt-line')
  );
  toReveal.forEach(function(el) { el.classList.add('tw-hidden'); });

  var queueIdx = 0;
  var charIdx = 0;
  var scrambleFrame = 0;
  var scrambleBase = '';

  function step() {
    // Advance past exhausted text items
    while (queueIdx < playQueue.length
        && playQueue[queueIdx].type === 'text'
        && charIdx >= playQueue[queueIdx].text.length) {
      queueIdx++;
      charIdx = 0;
    }
    if (queueIdx >= playQueue.length) {
      twAnimation = null;
      revealChoices(toReveal);
      return;
    }
    var item = playQueue[queueIdx];
    if (item.type === 'pause') {
      queueIdx++;
      twAnimation = { id: setTimeout(step, pauseMs), text: fullText, element: element, toReveal: toReveal };
      return;
    }
    if (item.type === 'scramble') {
      if (scrambleFrame === 0) {
        scrambleBase = element.textContent;
      }
      var scrambled = _twCorruptString({ text: item.span.text, intensity: 1.0, mode: 'random', seed: 0 }, corruption);
      element.textContent = scrambleBase + scrambled;
      scrambleFrame++;
      if (scrambleFrame < item.frames) {
        twAnimation = { id: setTimeout(step, item.delay != null ? item.delay : delay), text: fullText, element: element, toReveal: toReveal };
      } else {
        scrambleFrame = 0;
        element.textContent = scrambleBase;
        playQueue[queueIdx] = { type: 'text', text: item.settled };
        twAnimation = { id: setTimeout(step, delay), text: fullText, element: element, toReveal: toReveal };
      }
      return;
    }
    // type === 'text'
    var ch = item.text[charIdx++];
    element.textContent += ch;
    var extra = pauses[ch] || 0;
    twAnimation = { id: setTimeout(step, delay + extra), text: fullText, element: element, toReveal: toReveal };
  }

  twAnimation = { id: setTimeout(step, 0), text: fullText, element: element, toReveal: toReveal };
}

export function skipTypewriter() {
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
      setTimeout(function() { el.classList.remove('tw-hidden'); }, i * 60);
    });
  }, 250);
}
