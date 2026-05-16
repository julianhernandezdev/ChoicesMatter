const STORE_PREFIX = "choices-matter";

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

export function loadSave(storyId) {
  return loadJson(saveKey(storyId), null);
}

export function writeSave(story, run) {
  const saved = storeJson(saveKey(story.meta.id), {
    story_id: story.meta.id,
    current_node: run.nodeId,
    history: run.history,
    state: run.state,
    timestamp: new Date().toISOString(),
  });
  return saved
    ? "✓ Progress saved."
    : "Progress could not be saved in this browser.";
}

export function deleteSave(storyId) {
  removeStoredItem(saveKey(storyId));
}

export function loadGallery(storyId) {
  return loadJson(galleryKey(storyId), { story_id: storyId, endings_found: [] });
}

export function recordEnding(story, nodeId) {
  const gallery = loadGallery(story.meta.id);
  gallery.endings_found = Array.from(new Set([...(gallery.endings_found || []), nodeId])).sort();
  storeJson(galleryKey(story.meta.id), gallery);
}

export function clearAllProgress() {
  for (const key of storedKeys()) {
    if (key.startsWith(`${STORE_PREFIX}:`)) {
      removeStoredItem(key);
    }
  }
}
