const SETTINGS_KEY = "choices-matter:typewriter-settings";

export const TYPEWRITER_DEFAULTS = {
  enabled: true,
  delay_ms: 35,
  pause_ms: 500,
  pauses: { '.': 550, '!': 250, '?': 350, '…': 700, '—': 600 },
  page_size: 5,
  accessible_mode: null,
  player_name: "Felix",
  corruption: {
    enabled: true,
    charset: "blocks",
    intensity: 0.6,
    intensity_multiplier: 1.0,
    mode: "consistent",
    animate: true,
    scramble_frames: 85,
    scramble_delay_ms: 40,
    resolve_frames: null,
    resolve_delay_ms: null,
    cascade_stagger_ms: null,
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

function _twEffectiveMode(spanMode, corruption) {
  return spanMode || (corruption.mode != null ? corruption.mode : "consistent");
}

function _twEffectiveIntensity(spanIntensity, corruption) {
  var resolved = spanIntensity != null ? spanIntensity : (corruption.intensity != null ? corruption.intensity : 1.0);
  var multiplier = corruption.intensity_multiplier != null ? corruption.intensity_multiplier : 1.0;
  return Math.min(resolved * multiplier, 1.0);
}

function _twCorruptStringRaw(text, intensity, mode, seed, corruption) {
  var charset = corruption.charset === "custom"
    ? [...(corruption.custom_chars || "█▓▒░")]
    : (_TW_CHARSET_MAP[corruption.charset] || _TW_CHARSET_MAP.blocks);
  if (!charset.length) return text;
  var corruptible = [...text].map(function(c, i) { return _TW_PUNCT.has(c) ? null : i; }).filter(function(i) { return i !== null; });
  var count = Math.floor(corruptible.length * Math.min(intensity, 1.0));
  if (count === 0) return text;
  var positions = mode === "consistent"
    ? _twLcgSelect(corruptible.length, count, seed)
    : new Set([...Array(corruptible.length).keys()].sort(function() { return Math.random() - 0.5; }).slice(0, count));
  var a = 1664525, c = 1013904223, m = 4294967296;
  var state = seed % m;
  var chars = [...text];
  corruptible.forEach(function(charIdx, posIdx) {
    if (positions.has(posIdx)) {
      if (mode === "consistent") {
        state = (a * state + c) % m;
        chars[charIdx] = charset[state % charset.length];
      } else {
        chars[charIdx] = charset[Math.floor(Math.random() * charset.length)];
      }
    }
  });
  return chars.join("");
}

function _twCorruptString(span, corruption) {
  var mode = _twEffectiveMode(span.mode, corruption);
  var intensity = _twEffectiveIntensity(span.intensity, corruption);
  return _twCorruptStringRaw(span.text, intensity, mode, span.seed, corruption);
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
    if (!corruption.enabled || seg.resolve_style) return seg.text;
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
      if (corruption.enabled && seg.resolve_style === 'decay') {
        playQueue.push({ type: 'resolve-decay', span: seg });
      } else if (corruption.enabled && seg.resolve_style === 'cascade') {
        playQueue.push({ type: 'resolve-cascade', span: seg });
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
  var cascadeOrder = null;
  var cascadeChars = null;

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
    if (item.type === 'resolve-decay') {
      var resolveFrames = corruption.resolve_frames != null ? corruption.resolve_frames : corruption.scramble_frames;
      var resolveDelay = corruption.resolve_delay_ms != null ? corruption.resolve_delay_ms : corruption.scramble_delay_ms;
      if (scrambleFrame === 0) scrambleBase = element.textContent.slice(0, -item.span.text.length);
      var mode = _twEffectiveMode(item.span.mode, corruption);
      var baseIntensity = _twEffectiveIntensity(item.span.intensity, corruption);
      var intensity = baseIntensity * (1 - (scrambleFrame + 1) / resolveFrames);
      var frameText = _twCorruptStringRaw(item.span.text, intensity, mode, item.span.seed, corruption);
      element.textContent = scrambleBase + frameText;
      scrambleFrame++;
      if (scrambleFrame < resolveFrames) {
        twAnimation = { id: setTimeout(step, resolveDelay), text: fullText, element: element, toReveal: toReveal };
      } else {
        scrambleFrame = 0;
        element.textContent = scrambleBase + item.span.text;
        queueIdx++;
        twAnimation = { id: setTimeout(step, delay), text: fullText, element: element, toReveal: toReveal };
      }
      return;
    }
    if (item.type === 'resolve-cascade') {
      var cascadeStagger = corruption.cascade_stagger_ms != null ? corruption.cascade_stagger_ms : corruption.scramble_delay_ms;
      if (cascadeOrder === null) {
        scrambleBase = element.textContent.slice(0, -item.span.text.length);
        var settledForm = element.textContent.slice(-item.span.text.length);
        var mode = _twEffectiveMode(item.span.mode, corruption);
        var positions = [];
        for (var i = 0; i < item.span.text.length; i++) {
          if (settledForm[i] !== item.span.text[i]) positions.push(i);
        }
        cascadeOrder = positions;
        if (mode === 'consistent') {
          var a = 1664525, c = 1013904223, m = 4294967296;
          var state = item.span.seed % m;
          for (var j = cascadeOrder.length - 1; j > 0; j--) {
            state = (a * state + c) % m;
            var k = state % (j + 1);
            var tmp = cascadeOrder[j]; cascadeOrder[j] = cascadeOrder[k]; cascadeOrder[k] = tmp;
          }
        } else {
          cascadeOrder.sort(function() { return Math.random() - 0.5; });
        }
        cascadeChars = [...settledForm];
      }
      if (cascadeOrder.length > 0) {
        var nextIdx = cascadeOrder.shift();
        cascadeChars[nextIdx] = item.span.text[nextIdx];
        element.textContent = scrambleBase + cascadeChars.join('');
        twAnimation = { id: setTimeout(step, cascadeStagger), text: fullText, element: element, toReveal: toReveal };
      } else {
        cascadeOrder = null;
        cascadeChars = null;
        element.textContent = scrambleBase + item.span.text;
        queueIdx++;
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
