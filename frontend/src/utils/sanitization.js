export function sanitizeText(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

export function truncateText(value = '', limit = 150) {
  const text = String(value)
  return text.length > limit ? `${text.slice(0, limit).trim()}...` : text
}
