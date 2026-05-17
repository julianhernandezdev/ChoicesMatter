const SETTINGS_KEY = "choices-matter:typewriter-settings";

export const TYPEWRITER_DEFAULTS = {
  enabled: true,
  delay_ms: 20,
  pauses: { '.': 150, '!': 150, '?': 150, '…': 200, '—': 100 },
  page_size: 5,
};

export function loadTypewriterSettings() {
  try {
    var stored = JSON.parse(localStorage.getItem(SETTINGS_KEY));
    if (!stored) throw new Error();
    return {
      enabled: typeof stored.enabled === 'boolean' ? stored.enabled : TYPEWRITER_DEFAULTS.enabled,
      delay_ms: typeof stored.delay_ms === 'number' ? stored.delay_ms : TYPEWRITER_DEFAULTS.delay_ms,
      pauses: Object.assign({}, TYPEWRITER_DEFAULTS.pauses, stored.pauses || {}),
      page_size: (typeof stored.page_size === 'number' && stored.page_size >= 1) ? stored.page_size : TYPEWRITER_DEFAULTS.page_size,
    };
  } catch {
    return {
      enabled: TYPEWRITER_DEFAULTS.enabled,
      delay_ms: TYPEWRITER_DEFAULTS.delay_ms,
      pauses: Object.assign({}, TYPEWRITER_DEFAULTS.pauses),
      page_size: TYPEWRITER_DEFAULTS.page_size,
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

var twAnimation = null;

export function isTwAnimating() {
  return twAnimation !== null;
}

export function startTypewriter(element, text) {
  var settings = loadTypewriterSettings();
  var pauses = settings.pauses || {};
  var delay = settings.delay_ms || 20;

  element.textContent = '';
  var toReveal = Array.from(
    document.querySelectorAll('.terminal-choice, .terminal-overlay, .terminal-prompt-line')
  );
  toReveal.forEach(function(el) { el.classList.add('tw-hidden'); });

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
