export function useFirestore({ apiBase = 'http://localhost:8000' } = {}) {
  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, options)
    if (!response.ok) {
      const text = await response.text()
      throw new Error(text || 'Request failed')
    }
    return response.json()
  }

  const loadSnapshot = async () => {
    const [repos, posts, stats, health] = await Promise.all([
      fetchJson(`${apiBase}/agent/repos?limit=10`),
      fetchJson(`${apiBase}/agent/posts?limit=10`),
      fetchJson(`${apiBase}/agent/stats`),
      fetchJson(`${apiBase}/health`),
    ])

    return {
      repos,
      posts,
      stats,
      health,
    }
  }

  return { loadSnapshot }
}
