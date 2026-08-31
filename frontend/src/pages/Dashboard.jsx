import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSessionId } from '../utils/session'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const REPOS_PER_PAGE = 5

const now = () => {
  const d = new Date()
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0')).join(':')
}

/* ─── Repo Detail Modal ─── */
function RepoModal({ repo, onClose, onAnalyze, onPublish, loading }) {
  const a = repo.analysis || {}
  const isAnalyzed = repo.status === 'analyzed'
  const isPending  = repo.status === 'pending_analysis'
  const isPublished = repo.status === 'published'

  // Close on backdrop click
  const handleBackdrop = (e) => { if (e.target === e.currentTarget) onClose() }

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const novelty = parseFloat(a.novelty_score) || 0

  return (
    <div className="modal-backdrop" onClick={handleBackdrop}>
      <div className="modal" role="dialog" aria-modal="true">

        {/* ── head ── */}
        <div className="modal-head">
          <span className="modal-title">{repo.raw_name || repo.name}</span>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {/* ── body ── */}
        <div className="modal-body">
          {/* meta row */}
          <div className="modal-meta-row">
            <span className="repo-meta-item">⭐ {repo.stars ?? 0}</span>
            <span className="repo-meta-item">{repo.source || 'github'}</span>
            <span className={`badge badge-${repo.status?.replace('_', '-') || 'pending'}`}>
              {repo.status?.replace('_', ' ') || 'pending'}
            </span>
          </div>

          {/* URL */}
          <a
            href={repo.github_url}
            target="_blank"
            rel="noopener noreferrer"
            className="modal-url"
          >
            {repo.github_url}
          </a>

          {/* hook */}
          {a.one_liner_hook && (
            <div className="modal-hook">{a.one_liner_hook}</div>
          )}

          {/* analysis sections */}
          {a.problem_solved ? (
            <>
              <div className="modal-section">
                <div className="modal-section-label">Problem solved</div>
                <div className="modal-section-body">{a.problem_solved}</div>
              </div>

              {/* novelty bar */}
              <div className="modal-section">
                <div className="modal-section-label">Novelty score</div>
                <div className="modal-score-row">
                  <div className="modal-score-bar">
                    <div
                      className="modal-score-fill"
                      style={{ width: `${novelty * 10}%`, background: novelty >= 7.5 ? 'var(--acc)' : 'var(--ink-45)' }}
                    />
                  </div>
                  <span className="modal-score-num">{novelty.toFixed(1)} / 10</span>
                </div>
              </div>

              {/* complexity + audience */}
              <div className="modal-two-col">
                <div className="modal-section">
                  <div className="modal-section-label">Complexity</div>
                  <span className="modal-chip modal-chip-ink">{a.complexity || '—'}</span>
                </div>
                <div className="modal-section">
                  <div className="modal-section-label">Target audience</div>
                  <div className="modal-section-body">{a.target_audience || '—'}</div>
                </div>
              </div>

              {/* tech stack */}
              {a.tech_stack?.length > 0 && (
                <div className="modal-section">
                  <div className="modal-section-label">Tech stack</div>
                  <div className="modal-chip-row">
                    {a.tech_stack.map(t => (
                      <span key={t} className="modal-chip modal-chip-acc">{t}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* domain tags */}
              {a.domain_tags?.length > 0 && (
                <div className="modal-section">
                  <div className="modal-section-label">Domain tags</div>
                  <div className="modal-chip-row">
                    {a.domain_tags.map(t => (
                      <span key={t} className="modal-chip">{t}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* key files */}
              {a.key_files?.length > 0 && (
                <div className="modal-section">
                  <div className="modal-section-label">Key files</div>
                  <div className="modal-files">
                    {a.key_files.map(f => (
                      <span key={f} className="modal-file">{f}</span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="modal-empty-analysis">
              <p>Not analyzed yet. Click <strong>Analyze</strong> below to run Gemini analysis on this repo.</p>
            </div>
          )}
        </div>

        {/* ── footer actions ── */}
        <div className="modal-footer">
          {isPending && (
            <button
              className="btn btn-accent"
              disabled={loading[`analyze-${repo.id}`]}
              onClick={() => { onAnalyze(repo.id, repo.raw_name || repo.name); onClose() }}
            >
              {loading[`analyze-${repo.id}`] ? 'Analyzing…' : 'Analyze'}
            </button>
          )}
          {isAnalyzed && (
            <>
              <button
                className="btn btn-sm btn-linkedin"
                disabled={loading[`pub-linkedin-${repo.id}`]}
                onClick={() => { onPublish('linkedin', repo.id, repo.raw_name || repo.name); onClose() }}
              >
                {loading[`pub-linkedin-${repo.id}`] ? 'Publishing…' : 'Publish to LinkedIn'}
              </button>
              <button
                className="btn btn-sm btn-devto"
                disabled={loading[`pub-devto-${repo.id}`]}
                onClick={() => { onPublish('devto', repo.id, repo.raw_name || repo.name); onClose() }}
              >
                {loading[`pub-devto-${repo.id}`] ? 'Publishing…' : 'Publish to Dev.to'}
              </button>
            </>
          )}
          {isPublished && (
            <span className="badge badge-published" style={{ padding: '.5rem 1rem' }}>Already published</span>
          )}
          <button className="btn-ghost" onClick={onClose} style={{ marginLeft: 'auto' }}>Close</button>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function Dashboard({ toast }) {
  const navigate = useNavigate()

  // Stable session ID — one UUID per browser, stored in localStorage
  const sessionId = useMemo(() => getSessionId(), [])

  /* ── state ── */
  const [repos, setRepos]           = useState([])
  const [posts, setPosts]           = useState([])
  const [stats, setStats]           = useState(null)
  const [loading, setLoading]       = useState({})
  const [activityLog, setActivityLog] = useState([
    { time: now(), tag: 'sys', text: 'Dashboard initialized · waiting for commands' },
  ])
  const [languages, setLanguages]   = useState('typescript,python')
  const [repoPage, setRepoPage]     = useState(1)
  const [selectedRepo, setSelectedRepo] = useState(null)
  const logEndRef = useRef(null)

  /* ── derived pagination ── */
  const totalRepoPages = Math.max(1, Math.ceil(repos.length / REPOS_PER_PAGE))
  const pagedRepos = repos.slice((repoPage - 1) * REPOS_PER_PAGE, repoPage * REPOS_PER_PAGE)

  /* ── activity logger ── */
  const log = useCallback((tag, text) => {
    setActivityLog(p => [...p.slice(-50), { time: now(), tag, text }])
  }, [])

  /* ── auto-scroll log ── */
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [activityLog])

  /* ── API helpers — every call carries the session ID header ── */
  const apiCall = useCallback(async (url, options = {}) => {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
        ...options.headers,
      },
    })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    return res.json()
  }, [sessionId])

  const refreshRepos = useCallback(async () => {
    try {
      const data = await apiCall(`${API_BASE}/agent/repos?limit=50`)
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
      const data = await apiCall(
        `${API_BASE}/agent/discover?languages=${encodeURIComponent(languages)}&limit=5`,
        { method: 'POST' }
      )
      log('scout', `Discovery complete · ${data.count} new repos found`)
      if (data.repos?.length) {
        data.repos.forEach(r => log('info', `  → ${r.name} (${r.url})`))
      }
      toast(`Discovered ${data.count} repos!`)
      setRepoPage(1) // jump to first page so user sees new results
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
      const data = await apiCall(
        `${API_BASE}/agent/publish/${platform}/${repoId}`,
        { method: 'POST' }
      )
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

  /* ── helpers ── */
  const statusBadge = (status) => {
    const map = {
      pending_analysis: { label: 'Pending',   cls: 'badge-pending'  },
      analyzed:         { label: 'Analyzed',   cls: 'badge-analyzed' },
      published:        { label: 'Published',  cls: 'badge-published'},
      failed:           { label: 'Failed',     cls: 'badge-failed'   },
      approved:         { label: 'Approved',   cls: 'badge-approved' },
      rejected:         { label: 'Rejected',   cls: 'badge-rejected' },
    }
    const s = map[status] || { label: status, cls: '' }
    return <span className={`badge ${s.cls}`}>{s.label}</span>
  }

  const platformIcon = (p) => ({ linkedin: 'in', devto: 'dev' }[p] || p)

  /* ═══════════════════════════════════════════════════════════════════════════ */
  return (
    <>
      {/* ── modal ── */}
      {selectedRepo && (
        <RepoModal
          repo={selectedRepo}
          onClose={() => setSelectedRepo(null)}
          onAnalyze={analyzeRepo}
          onPublish={publishRepo}
          loading={loading}
        />
      )}

      {/* ═══ DASHBOARD HEADER ═══ */}
      <header className="dash-header">
        <div className="wrap dash-nav">
          <a className="wordmark" href="#" onClick={e => { e.preventDefault(); navigate('/') }}>
            AutoPost<b>.</b>
          </a>
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
                <div className="dash-panel-head"><span>Agent controls</span></div>
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
                    <>
                      <div className="repo-table">
                        {pagedRepos.map(repo => (
                          <div className="repo-row" key={repo.id}>
                            <div className="repo-info">
                              <div className="repo-name-row">
                                <strong>{repo.raw_name || repo.name}</strong>
                                {statusBadge(repo.status)}
                              </div>
                              <div className="repo-meta">
                                <span>⭐ {repo.stars ?? 0}</span>
                                <span>{repo.source || 'github'}</span>
                                {repo.analysis && (
                                  <span className="repo-score">
                                    Score {repo.analysis.novelty_score}/10
                                  </span>
                                )}
                              </div>
                              {repo.analysis?.one_liner_hook && (
                                <div className="repo-hook">{repo.analysis.one_liner_hook}</div>
                              )}
                            </div>
                            <div className="repo-actions">
                              {/* Open always visible */}
                              <button
                                className="btn btn-sm btn-open"
                                onClick={() => setSelectedRepo(repo)}
                              >
                                Open
                              </button>
                              {/* Quick-action shortcuts alongside Open */}
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

                      {/* ── pagination ── */}
                      {totalRepoPages > 1 && (
                        <div className="pagination">
                          <span className="pagination-info">
                            {(repoPage - 1) * REPOS_PER_PAGE + 1}–
                            {Math.min(repoPage * REPOS_PER_PAGE, repos.length)} of {repos.length}
                          </span>
                          <div className="pagination-btns">
                            <button
                              className="btn btn-sm"
                              disabled={repoPage === 1}
                              onClick={() => setRepoPage(p => p - 1)}
                            >
                              ← Prev
                            </button>
                            <span className="pagination-page">
                              {repoPage} / {totalRepoPages}
                            </span>
                            <button
                              className="btn btn-sm"
                              disabled={repoPage === totalRepoPages}
                              onClick={() => setRepoPage(p => p + 1)}
                            >
                              Next →
                            </button>
                          </div>
                        </div>
                      )}
                    </>
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
                              <span className={`platform-tag platform-${post.platform}`}>
                                {platformIcon(post.platform)}
                              </span>
                              <strong>{post.platform.toUpperCase()}</strong>
                              {statusBadge(post.status)}
                            </div>
                            {post.content?.headline && (
                              <div className="post-headline">{post.content.headline}</div>
                            )}
                          </div>
                          <div className="post-actions">
                            {post.published_url ? (
                              <a
                                className="btn btn-sm"
                                href={post.published_url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                View
                              </a>
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
                  <div
                    className="feed"
                    style={{ justifyContent: 'flex-start', overflowY: 'auto', maxHeight: 'calc(100vh - 220px)' }}
                  >
                    {activityLog.map((l, i) => (
                      <div
                        key={i}
                        className={`fl${l.tag === 'pub' ? ' hot' : l.tag === 'err' || l.tag === 'warn' ? ' err-line' : ''}`}
                      >
                        <span className="ft">[{l.time}]</span>
                        <span className="fg">{l.tag}</span>
                        <span>{l.text}</span>
                      </div>
                    ))}
                    <div ref={logEndRef} />
                  </div>
                  <div style={{ padding: '0 1rem .9rem' }}>
                    <span className="caret-block" />
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
