export function isValidUrl(value = '') {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

export function hasContent(value) {
  return String(value || '').trim().length > 0
}
