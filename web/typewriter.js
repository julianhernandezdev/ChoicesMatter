const SETTINGS_KEY = "choices-matter:typewriter-settings";

export const TYPEWRITER_DEFAULTS = {
  enabled: true,
  delay_ms: 20,
  pause_ms: 500,
  pauses: { '.': 150, '!': 150, '?': 150, '…': 200, '—': 100 },
  page_size: 5,
  accessible_mode: null,
  player_name: "Felix",
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

var twAnimation = null;

export function isTwAnimating() {
  return twAnimation !== null;
}

export function startTypewriter(element, text) {
  var segments = text.split('{pause}');
  var cleanText = segments.join('');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    element.textContent = cleanText;
    return;
  }
  var settings = loadTypewriterSettings();
  var pauses = settings.pauses || {};
  var delay = settings.delay_ms || 20;
  var pauseMs = settings.pause_ms || 500;

  element.textContent = '';
  var toReveal = Array.from(
    document.querySelectorAll('.terminal-choice, .terminal-overlay, .terminal-prompt-line')
  );
  toReveal.forEach(function(el) { el.classList.add('tw-hidden'); });

  var segIdx = 0;
  var charIdx = 0;
  function step() {
    while (segIdx < segments.length && charIdx >= segments[segIdx].length) {
      segIdx++;
      charIdx = 0;
      if (segIdx < segments.length) {
        twAnimation = { id: setTimeout(step, pauseMs), text: cleanText, element: element, toReveal: toReveal };
        return;
      }
    }
    if (segIdx >= segments.length) {
      twAnimation = null;
      revealChoices(toReveal);
      return;
    }
    var ch = segments[segIdx][charIdx++];
    element.textContent += ch;
    var extra = pauses[ch] || 0;
    twAnimation = { id: setTimeout(step, delay + extra), text: cleanText, element: element, toReveal: toReveal };
  }
  twAnimation = { id: setTimeout(step, 0), text: cleanText, element: element, toReveal: toReveal };
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
