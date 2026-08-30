import React, { useCallback, useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TRIAL_KEY = 'autopost-agent-trial-used'

const agentCapabilities = [
  { icon: '🔎', title: 'Repo discovery agent', description: 'Finds fast-growing TypeScript and Python repositories before they become crowded topics.', metric: '5 repos / run' },
  { icon: '🧠', title: 'Analysis agent', description: 'Scores novelty, extracts the strongest hook, and turns repository metadata into creator-ready insight.', metric: '10-point score' },
  { icon: '✍️', title: 'Content agent', description: 'Drafts platform-aware snippets for LinkedIn and Dev.to so teams can publish with less manual rewriting.', metric: '2 channels' },
  { icon: '📈', title: 'Performance agent', description: 'Keeps a dashboard of discovered repositories, post history, and publishing outcomes in one view.', metric: 'Live stats' },
]

const workflowSteps = [
  { label: 'Discover', detail: 'Scan GitHub trends', icon: '🌐' },
  { label: 'Analyze', detail: 'Score novelty + hook', icon: '🧪' },
  { label: 'Generate', detail: 'Create snippets', icon: '📝' },
  { label: 'Publish', detail: 'LinkedIn + Dev.to', icon: '🚀' },
  { label: 'Learn', detail: 'Track results', icon: '📊' },
]

const snippetExamples = [
  { platform: 'LinkedIn', code: `Just found a promising open-source repo gaining traction.\n\nWhy it matters:\n• Clear developer pain point\n• Strong adoption signal\n• Practical automation workflow\n\nWorth watching this week.` },
  { platform: 'Dev.to', code: `## Project spotlight\n\nThis repo stands out because it combines strong DX, useful docs, and a focused use case.\n\n**Agent score:** 8/10\n**Best angle:** ship faster with reusable automation.` },
]

function App() {
  const [repos, setRepos] = useState([])
  const [posts, setPosts] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [trialUsed, setTrialUsed] = useState(() => localStorage.getItem(TRIAL_KEY) === 'true')
  const [showLogin, setShowLogin] = useState(false)
  const [loginForm, setLoginForm] = useState({ name: '', email: '', role: '' })

  const isLocked = trialUsed && !showLogin

  const safeFetchJson = useCallback(async (url, options) => {
    const res = await fetch(url, options)
    if (!res.ok) throw new Error(`Request failed with ${res.status}`)
    return res.json()
  }, [])
  const fetchRepos = useCallback(async () => setRepos(await safeFetchJson(`${API_BASE}/agent/repos?limit=10`)), [safeFetchJson])
  const fetchPosts = useCallback(async () => setPosts(await safeFetchJson(`${API_BASE}/agent/posts?limit=10`)), [safeFetchJson])
  const fetchStats = useCallback(async () => setStats(await safeFetchJson(`${API_BASE}/agent/stats`)), [safeFetchJson])

  const refreshDashboard = useCallback(async () => {
    try { await Promise.all([fetchRepos(), fetchPosts(), fetchStats()]) }
    catch (err) { setMessage(`Connect the API to load live data: ${err.message}`) }
  }, [fetchPosts, fetchRepos, fetchStats])

  const discoverRepos = async (fromTrial = false) => {
    setLoading(true); setMessage('')
    try {
      const data = await safeFetchJson(`${API_BASE}/agent/discover?languages=typescript,python&limit=5`, { method: 'POST' })
      setMessage(`Discovered ${data.count} repos! Your sample agent run is complete.`)
      if (fromTrial) { localStorage.setItem(TRIAL_KEY, 'true'); setTrialUsed(true); setShowLogin(true) }
      await Promise.all([fetchRepos(), fetchStats()])
    } catch (err) { setMessage(`Error: ${err.message}`) }
    finally { setLoading(false) }
  }

  const startTrial = async () => trialUsed ? setShowLogin(true) : discoverRepos(true)
  const guardAction = (action) => (...args) => isLocked ? setShowLogin(true) : action(...args)

  const analyzeRepo = async (repoId) => {
    setLoading(true)
    try {
      const data = await safeFetchJson(`${API_BASE}/agent/analyze/${repoId}`, { method: 'POST' })
      setMessage(`Analyzed: ${data.analysis?.one_liner_hook || 'Done'}`); fetchRepos()
    } catch (err) { setMessage(`Error: ${err.message}`) }
    finally { setLoading(false) }
  }

  const publishPost = async (platform, repoId) => {
    setLoading(true)
    try {
      const data = await safeFetchJson(`${API_BASE}/agent/publish/${platform}/${repoId}`, { method: 'POST' })
      setMessage(`${platform === 'linkedin' ? 'LinkedIn' : 'Dev.to'}: ${data.result?.post_url || 'Published!'}`)
      await Promise.all([fetchPosts(), fetchStats()])
    } catch (err) { setMessage(`Error: ${err.message}`) }
    finally { setLoading(false) }
  }

  const handleLoginSubmit = (event) => {
    event.preventDefault()
    setMessage(`Thanks ${loginForm.name || 'there'} — your workspace request is ready for backend authentication.`)
    setShowLogin(false)
  }

  const dashboardStats = useMemo(() => [
    { label: 'Repos discovered', value: stats?.total_repos ?? repos.length, tone: 'blue' },
    { label: 'Posts published', value: stats?.total_posts ?? posts.length, tone: 'green' },
    { label: 'Active agents', value: agentCapabilities.length, tone: 'purple' },
  ], [posts.length, repos.length, stats])

  useEffect(() => {
    const timer = window.setTimeout(refreshDashboard, 0)
    return () => window.clearTimeout(timer)
  }, [refreshDashboard])

  return (
    <main className="app-shell">
      <nav className="topbar"><div className="brand"><span>🚀</span> AutoPost Agents</div><button className="ghost-button" onClick={() => setShowLogin(true)}>Login</button></nav>
      <section className="hero dashboard-panel"><div className="hero-copy"><p className="eyebrow">Autonomous content curation dashboard</p><h1>Show users what your agents can discover, analyze, write, and publish.</h1><p className="hero-text">A responsive homepage dashboard that explains the agent workflow with visual cards, a flow diagram, content snippets, and a one-time trial gate for new users.</p><div className="hero-actions"><button className="primary-button" onClick={startTrial} disabled={loading}>{loading ? 'Running agent...' : trialUsed ? 'Login to keep trying' : 'Try one agent run'}</button><button className="secondary-button" onClick={refreshDashboard}>Refresh dashboard</button></div></div><div className="agent-orbit" aria-label="Agent capability illustration">{agentCapabilities.map((agent) => <div className="orbit-card" key={agent.title}>{agent.icon}<span>{agent.metric}</span></div>)}</div></section>
      {message && <div className="notice">{message}</div>}
      <section className="stats-grid">{dashboardStats.map((item) => <article className={`stat-card ${item.tone}`} key={item.label}><strong>{item.value}</strong><span>{item.label}</span></article>)}</section>
      <section className="capability-grid">{agentCapabilities.map((agent) => <article className="capability-card" key={agent.title}><div className="capability-icon">{agent.icon}</div><h3>{agent.title}</h3><p>{agent.description}</p><span>{agent.metric}</span></article>)}</section>
      <section className="dashboard-panel"><h2>Agent workflow</h2><div className="flow-diagram">{workflowSteps.map((step, index) => <React.Fragment key={step.label}><div className="flow-step"><b>{step.icon}</b><strong>{step.label}</strong><span>{step.detail}</span></div>{index < workflowSteps.length - 1 && <div className="flow-arrow">→</div>}</React.Fragment>)}</div></section>
      <section className="content-grid"><div className="dashboard-panel"><h2>Snippet previews</h2>{snippetExamples.map((snippet) => <div className="snippet-card" key={snippet.platform}><span>{snippet.platform}</span><pre>{snippet.code}</pre></div>)}</div><div className="dashboard-panel"><h2>{showLogin ? 'Create your workspace' : 'Live repository queue'}</h2>{showLogin ? <form className="login-card" onSubmit={handleLoginSubmit}><input placeholder="Full name" value={loginForm.name} onChange={(e) => setLoginForm({ ...loginForm, name: e.target.value })} /><input placeholder="Work email" type="email" required value={loginForm.email} onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })} /><input placeholder="Role or team" value={loginForm.role} onChange={(e) => setLoginForm({ ...loginForm, role: e.target.value })} /><button className="primary-button">Continue</button></form> : <RepoList repos={repos} loading={loading} onAnalyze={guardAction(analyzeRepo)} onPublish={guardAction(publishPost)} />}</div></section>
      <section className="dashboard-panel"><h2>Published posts</h2><div className="post-list">{posts.length === 0 ? <p className="empty-state">No posts yet. Run discovery, analyze a repository, then publish a channel-specific post.</p> : posts.map((post) => <article className="post-card" key={post.id}><strong>{post.platform.toUpperCase()}</strong><span>{post.status}</span>{post.published_url && <a href={post.published_url} target="_blank" rel="noopener noreferrer">View post</a>}</article>)}</div></section>
    </main>
  )
}

function RepoList({ repos, loading, onAnalyze, onPublish }) {
  if (repos.length === 0) return <p className="empty-state">No repositories loaded yet. Try the discovery agent to fill this queue.</p>
  return <div className="repo-list">{repos.map((repo) => <article className="repo-card" key={repo.id}><div><strong>{repo.raw_name}</strong><span>⭐ {repo.stars} · {repo.status}</span><a href={repo.github_url} target="_blank" rel="noopener noreferrer">{repo.github_url}</a></div><div className="repo-actions">{repo.status === 'pending_analysis' && <button disabled={loading} onClick={() => onAnalyze(repo.id)}>Analyze</button>}{repo.status === 'analyzed' && <><button disabled={loading} onClick={() => onPublish('linkedin', repo.id)}>LinkedIn</button><button disabled={loading} onClick={() => onPublish('devto', repo.id)}>Dev.to</button></>}</div>{repo.analysis && <p className="analysis-note">{repo.analysis.one_liner_hook} · Score {repo.analysis.novelty_score}/10</p>}</article>)}</div>
}

export default App
