/**
 * Session management — generates a persistent UUID per browser that
 * namespaces all Firestore data so every device gets its own isolated view.
 */

const SESSION_KEY = 'autopost_session_id'

function generateUUID() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // Fallback for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Returns the session ID for this browser, creating and persisting one if
 * it doesn't exist yet. Stable across page refreshes; resets only if the
 * user clears localStorage.
 */
export function getSessionId() {
  try {
    let id = localStorage.getItem(SESSION_KEY)
    if (!id || !/^[0-9a-f-]{36}$/.test(id)) {
      id = generateUUID()
      localStorage.setItem(SESSION_KEY, id)
    }
    return id
  } catch {
    // Private-browsing mode may block localStorage — fall back to a
    // per-page-load ID so the app still works, just won't persist.
    return generateUUID()
  }
}
