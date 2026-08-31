import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const now = () => {
  const d = new Date()
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0')).join(':')
}

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function Dashboard({ toast }) {
  const navigate = useNavigate()

  /* ── state ── */
  const [repos, setRepos] = useState([])
  const [posts, setPosts] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState({})
  const [activityLog, setActivityLog] = useState([
    { time: now(), tag: 'sys', text: 'Dashboard initialized · waiting for commands' },
  ])
  const [languages, setLanguages] = useState('typescript,python')
  const logEndRef = useRef(null)

  /* ── activity logger ── */
  const log = useCallback((tag, text) => {
    setActivityLog(p => [...p.slice(-50), { time: now(), tag, text }])
  }, [])

  /* ── auto-scroll log ── */
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [activityLog])

  /* ── API helpers ── */
  const apiCall = useCallback(async (url, options = {}) => {
    const res = await fetch(url, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    return res.json()
  }, [])

  const refreshRepos = useCallback(async () => {
 try {
      const data = await apiCall(`${API_BASE}/agent/repos?limit=20`)
      setRepos(data)
    } catch (e) { log('err', `Failed to load repos: ${e.message}`) }
  }, [apiCall, log])

  const refreshPosts = useCallback(async () => {
    try {
      const data = await apiCall(`${API_BASE}/agent/posts?limit=20`)
      setPosts(data)
    } catch (e) { log('err', `Failed to load posts: ${e.message}`) }
  }, [apiCall, log])

  const refreshStats = useCallback(async () => {
    try {
      const data = await apiCall(`${API_BASE}/agent/stats`)
      setStats(data)
    } catch (e) { log('err', `Failed to load stats: ${e.message}`) }
  }, [apiCall, log])

  /* ── initial load ── */
  useEffect(() => {
    log('sys', 'Connecting to agent backend…')
    Promise.all([refreshRepos(), refreshPosts(), refreshStats()])
      .then(() => log('sys', 'Backend connected · data loaded'))
      .catch(() => log('warn', 'Could not reach backend · check API_URL'))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /* ── actions ── */
  const runDiscovery = async () => {
    const key = 'discover'
    setLoading(p => ({ ...p, [key]: true }))
    log('scout', `Starting discovery run · languages: ${languages}`)
    try {
      const data = await apiCall(`${API_BASE}/agent/discover?languages=${encodeURIComponent(languages)}&limit=5`, { method: 'POST' })
      log('scout', `Discovery complete · ${data.count} new repos found`)
      if (data.repos?.length) {
        data.repos.forEach(r => log('info', `  → ${r.name} (${r.url})`))
      }
      toast(`Discovered ${data.count} repos!`)
      await Promise.all([refreshRepos(), refreshStats()])
    } catch (e) {
      log('err', `Discovery failed: ${e.message}`)
      toast(`Discovery failed: ${e.message}`, false)
    } finally {
      setLoading(p => ({ ...p, [key]: false }))
    }
  }

  const analyzeRepo = async (repoId, repoName) => {
    const key = `analyze-${repoId}`
    setLoading(p => ({ ...p, [key]: true }))
    log('draft', `Analyzing ${repoName} · fetching README · running Gemini…`)
    try {
      const data = await apiCall(`${API_BASE}/agent/analyze/${repoId}`, { method: 'POST' })
      if (data.status === 'failed') {
        log('warn', `Analysis failed for ${repoName}: ${data.reason}`)
        toast(`${repoName}: ${data.reason}`, false)
      } else {
        const hook = data.analysis?.one_liner_hook || 'Analysis complete'
        log('draft', `${repoName} analyzed · ${hook}`)
        toast(`${repoName}: ${hook}`)
      }
      await refreshRepos()
    } catch (e) {
      log('err', `Analysis error for ${repoName}: ${e.message}`)
      toast(`Analysis failed: ${e.message}`, false)
    } finally {
      setLoading(p => ({ ...p, [key]: false }))
    }
  }

  const publishRepo = async (platform, repoId, repoName) => {
    const key = `pub-${platform}-${repoId}`
    setLoading(p => ({ ...p, [key]: true }))
    log('pub', `Publishing ${repoName} to ${platform}…`)
    try {
      const data = await apiCall(`${API_BASE}/agent/publish/${platform}/${repoId}`, { method: 'POST' })
      const url = data.result?.post_url || 'published'
      log('pub', `${repoName} shipped to ${platform} · ${url}`)
      log('info', `Discord notification sent`)
      toast(`${platform}: ${repoName} published!`)
      await Promise.all([refreshPosts(), refreshStats(), refreshRepos()])
    } catch (e) {
      log('err', `Publish to ${platform} failed: ${e.message}`)
      toast(`Publish failed: ${e.message}`, false)
    } finally {
      setLoading(p => ({ ...p, [key]: false }))
    }
  }

  /* ── status helpers ── */
  const statusBadge = (status) => {
    const map = {
      pending_analysis: { label: 'Pending', cls: 'badge-pending' },
      analyzed: { label: 'Analyzed', cls: 'badge-analyzed' },
      published: { label: 'Published', cls: 'badge-published' },
      failed: { label: 'Failed', cls: 'badge-failed' },
      approved: { label: 'Approved', cls: 'badge-approved' },
      rejected: { label: 'Rejected', cls: 'badge-rejected' },
    }
    const s = map[status] || { label: status, cls: '' }
    return <span className={`badge ${s.cls}`}>{s.label}</span>
  }

  const platformIcon = (p) => {
    const map = { linkedin: 'in', devto: 'dev' }
    return map[p] || p
  }

  /* ═══════════════════════════════════════════════════════════════════════════ */
  return (
    <>
      {/* ═══ DASHBOARD HEADER ═══ */}
      <header className="dash-header">
        <div className="wrap dash-nav">
          <a className="wordmark" href="#" onClick={e => { e.preventDefault(); navigate('/') }}>AutoPost<b>.</b></a>
          <span className="status"><span className="dot" />AGENT ONLINE</span>
          <div className="dash-nav-right">
            <span className="dash-page-label">Dashboard</span>
            <button className="btn btn-sm" onClick={() => navigate('/')}>Home</button>
          </div>
        </div>
      </header>

      <div className="dash-body">
        <div className="wrap">

          {/* ═══ STATS STRIP ═══ */}
          <div className="dash-stats">
            <div className="dash-stat">
              <div className="dash-stat-n">{stats?.total_repos ?? repos.length}</div>
              <div className="dash-stat-l">Repos discovered</div>
            </div>
            <div className="dash-stat">
              <div className="dash-stat-n">{stats?.total_posts ?? posts.length}</div>
              <div className="dash-stat-l">Posts published</div>
            </div>
            <div className="dash-stat">
              <div className="dash-stat-n">{stats?.platforms?.length ?? 3}</div>
              <div className="dash-stat-l">Platforms active</div>
            </div>
            <div className="dash-stat">
              <div className="dash-stat-n">0</div>
              <div className="dash-stat-l">Humans required</div>
            </div>
          </div>

          <div className="dash-grid">
            {/* ═══ LEFT COLUMN ═══ */}
            <div className="dash-left">

              {/* ── Agent Controls ── */}
              <div className="dash-panel">
                <div className="dash-panel-head">
                  <span>Agent controls</span>
                </div>
                <div className="dash-panel-body">
                  <div className="ctrl-row">
                    <div className="field">
                      <label htmlFor="langInput">Languages</label>
                      <input
                        type="text"
                        id="langInput"
                        value={languages}
                        onChange={e => setLanguages(e.target.value)}
                        placeholder="typescript,python,rust"
                      />
                    </div>
                    <button
                      className="btn btn-accent"
                      disabled={loading.discover}
                      onClick={runDiscovery}
                    >
                      {loading.discover ? 'Discovering…' : 'Run discovery'}
                    </button>
                  </div>
                  <p className="dash-hint">Finds trending GitHub repos from the last 7 days.</p>
                </div>
              </div>

              {/* ── Discovered Repos ── */}
              <div className="dash-panel">
                <div className="dash-panel-head">
                  <span>Discovered repos</span>
                  <button className="btn-ghost" onClick={refreshRepos}>Refresh</button>
                </div>
                <div className="dash-panel-body">
                  {repos.length === 0 ? (
                    <div className="dash-empty">
                      <p>No repos yet. Run discovery to find trending repositories.</p>
                    </div>
                  ) : (
                    <div className="repo-table">
                      {repos.map(repo => (
                        <div className="repo-row" key={repo.id}>
                          <div className="repo-info">
                            <div className="repo-name-row">
                              <strong>{repo.raw_name || repo.name}</strong>
                              {statusBadge(repo.status)}
                            </div>
                            <div className="repo-meta">
                              <span>⭐ {repo.stars ?? 0}</span>
                              <span>{repo.source || 'github'}</span>
                              {repo.analysis && <span className="repo-score">Score {repo.analysis.novelty_score}/10</span>}
                            </div>
                            {repo.analysis?.one_liner_hook && (
                              <div className="repo-hook">{repo.analysis.one_liner_hook}</div>
                            )}
                          </div>
                          <div className="repo-actions">
                            {repo.status === 'pending_analysis' && (
                              <button
                                className="btn btn-sm"
                                disabled={loading[`analyze-${repo.id}`]}
                                onClick={() => analyzeRepo(repo.id, repo.raw_name || repo.name)}
                              >
                                {loading[`analyze-${repo.id}`] ? 'Analyzing…' : 'Analyze'}
                              </button>
                            )}
                            {repo.status === 'analyzed' && (
                              <>
                                <button
                                  className="btn btn-sm btn-linkedin"
                                  disabled={loading[`pub-linkedin-${repo.id}`]}
                                  onClick={() => publishRepo('linkedin', repo.id, repo.raw_name || repo.name)}
                                >
                                  {loading[`pub-linkedin-${repo.id}`] ? '…' : 'LinkedIn'}
                                </button>
                                <button
                                  className="btn btn-sm btn-devto"
                                  disabled={loading[`pub-devto-${repo.id}`]}
                                  onClick={() => publishRepo('devto', repo.id, repo.raw_name || repo.name)}
                                >
                                  {loading[`pub-devto-${repo.id}`] ? '…' : 'Dev.to'}
                                </button>
                              </>
                            )}
                            {repo.status === 'published' && (
                              <span className="badge badge-published">Shipped</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* ── Published Posts ── */}
              <div className="dash-panel">
                <div className="dash-panel-head">
                  <span>Published posts</span>
                  <button className="btn-ghost" onClick={refreshPosts}>Refresh</button>
                </div>
                <div className="dash-panel-body">
                  {posts.length === 0 ? (
                    <div className="dash-empty">
                      <p>No posts published yet. Analyze a repo, then publish to LinkedIn or Dev.to.</p>
                    </div>
                  ) : (
                    <div className="post-table">
                      {posts.map(post => (
                        <div className="post-row" key={post.id}>
                          <div className="post-info">
                            <div className="post-platform-row">
                              <span className={`platform-tag platform-${post.platform}`}>{platformIcon(post.platform)}</span>
                              <strong>{post.platform.toUpperCase()}</strong>
                              {statusBadge(post.status)}
                            </div>
                            {post.content?.headline && (
                              <div className="post-headline">{post.content.headline}</div>
                            )}
                          </div>
                          <div className="post-actions">
                            {post.published_url ? (
                              <a className="btn btn-sm" href={post.published_url} target="_blank" rel="noopener noreferrer">View</a>
                            ) : (
                              <span className="dash-muted">No URL</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ═══ RIGHT COLUMN — ACTIVITY CONSOLE ═══ */}
            <div className="dash-right">
              <div className="dash-panel dash-console-panel">
                <div className="dash-panel-head">
                  <span><span className="dot" style={{ marginRight: '.5rem' }} />Activity log</span>
                  <span className="dash-muted">live</span>
                </div>
                <div className="console">
                  <div className="feed" style={{ justifyContent: 'flex-start', overflowY: 'auto', maxHeight: 'calc(100vh - 220px)' }}>
                    {activityLog.map((l, i) => (
                      <div key={i} className={`fl${l.tag === 'pub' ? ' hot' : l.tag === 'err' || l.tag === 'warn' ? ' err-line' : ''}`}
                        >
                        <span className="ft">[{l.time}]</span>
                        <span className="fg">{l.tag}</span>
                        <span>{l.text}</span>
                      </div>
                    ))}
                    <div ref={logEndRef} />
                  </div>
                  <div style={{ padding: '0 1rem .9rem' }}><span className="caret-block" /></div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
