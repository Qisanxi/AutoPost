import React, { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [repos, setRepos] = useState([])
  const [posts, setPosts] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const fetchRepos = async () => {
    const res = await fetch(`${API_BASE}/agent/repos?limit=10`)
    const data = await res.json()
    setRepos(data)
  }

  const fetchPosts = async () => {
    const res = await fetch(`${API_BASE}/agent/posts?limit=10`)
    const data = await res.json()
    setPosts(data)
  }

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/agent/stats`)
    const data = await res.json()
    setStats(data)
  }

  const discoverRepos = async () => {
    setLoading(true)
    setMessage('')
    try {
      const res = await fetch(`${API_BASE}/agent/discover?languages=typescript,python&limit=5`, { method: 'POST' })
      const data = await res.json()
      setMessage(`Discovered ${data.count} repos!`)
      fetchRepos()
      fetchStats()
    } catch (err) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const analyzeRepo = async (repoId) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/agent/analyze/${repoId}`, { method: 'POST' })
      const data = await res.json()
      setMessage(`Analyzed: ${data.analysis?.one_liner_hook || 'Done'}`)
      fetchRepos()
    } catch (err) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const publishLinkedIn = async (repoId) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/agent/publish/linkedin/${repoId}`, { method: 'POST' })
      const data = await res.json()
      setMessage(`LinkedIn: ${data.result?.post_url || 'Posted!'}`)
      fetchPosts()
      fetchStats()
    } catch (err) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const publishDevTo = async (repoId) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/agent/publish/devto/${repoId}`, { method: 'POST' })
      const data = await res.json()
      setMessage(`Dev.to: ${data.result?.post_url || 'Published!'}`)
      fetchPosts()
      fetchStats()
    } catch (err) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRepos()
    fetchPosts()
    fetchStats()
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>🚀 AutoPost Agent Dashboard</h1>
      <p>Autonomous content curation agent </p>

      {stats && (
        <div style={{ display: 'flex', gap: '1rem', margin: '1rem 0' }}>
          <div style={{ background: '#e3f2fd', padding: '1rem', borderRadius: '8px' }}>
            <strong>{stats.total_repos}</strong> Repos Discovered
          </div>
          <div style={{ background: '#e8f5e9', padding: '1rem', borderRadius: '8px' }}>
            <strong>{stats.total_posts}</strong> Posts Published
          </div>
        </div>
      )}

      <div style={{ margin: '1rem 0' }}>
        <button onClick={discoverRepos} disabled={loading} style={{ marginRight: '0.5rem' }}>
          {loading ? 'Working...' : '🔍 Discover Repos'}
        </button>
        <button onClick={() => { fetchRepos(); fetchPosts(); fetchStats(); }}>
          🔄 Refresh
        </button>
      </div>

      {message && (
        <div style={{ background: '#fff3e0', padding: '0.75rem', borderRadius: '4px', marginBottom: '1rem' }}>
          {message}
        </div>
      )}

      <h2>📦 Discovered Repos</h2>
      <div style={{ display: 'grid', gap: '0.5rem' }}>
        {repos.map(repo => (
          <div key={repo.id} style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{repo.raw_name}</strong> ⭐ {repo.stars}
                <div style={{ fontSize: '0.85rem', color: '#666' }}>{repo.github_url}</div>
                <div style={{ fontSize: '0.8rem', color: '#888' }}>Status: {repo.status}</div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {repo.status === 'pending_analysis' && (
                  <button onClick={() => analyzeRepo(repo.id)}>Analyze</button>
                )}
                {repo.status === 'analyzed' && (
                  <>
                    <button onClick={() => publishLinkedIn(repo.id)}>LinkedIn</button>
                    <button onClick={() => publishDevTo(repo.id)}>Dev.to</button>
                  </>
                )}
              </div>
            </div>
            {repo.analysis && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', background: '#f5f5f5', padding: '0.5rem', borderRadius: '4px' }}>
                <em>{repo.analysis.one_liner_hook}</em> | Score: {repo.analysis.novelty_score}/10
              </div>
            )}
          </div>
        ))}
      </div>

      <h2 style={{ marginTop: '2rem' }}>📝 Published Posts</h2>
      <div style={{ display: 'grid', gap: '0.5rem' }}>
        {posts.map(post => (
          <div key={post.id} style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px' }}>
            <strong>{post.platform.toUpperCase()}</strong> — {post.status}
            {post.published_url && (
              <div><a href={post.published_url} target="_blank" rel="noopener noreferrer">{post.published_url}</a></div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default App