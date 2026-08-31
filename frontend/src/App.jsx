import { useCallback, useEffect, useMemo, useState } from 'react'
import { ErrorBoundary } from './components/ErrorBoundary'
import { PostTimeline } from './components/PostTimeline'
import { RepoQueue } from './components/RepoQueue'
import { TagPerformance } from './components/TagPerformance'
import { useAuth } from './hooks/useAuth'
import { useFirestore } from './hooks/useFirestore'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const stamp = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const defaultPipeline = [
  { id: 'discover', label: 'Discover GitHub repos', status: 'pending', detail: 'Waiting to start' },
]

function App() {
  const { user } = useAuth()
  const { loadSnapshot } = useFirestore({ apiBase: API_BASE })
  const [repos, setRepos] = useState([])
  const [posts, setPosts] = useState([])
  const [stats, setStats] = useState({ total_repos: 0, total_posts: 0, platforms: [] })
  const [health, setHealth] = useState({ status: 'checking', database: 'pending' })
  const [activity, setActivity] = useState([{ id: 'boot', label: 'Dashboard ready', detail: 'Monitoring backend pipeline', stamp: stamp() }])
  const [pipeline, setPipeline] = useState(defaultPipeline)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('Backend pipeline is waiting for the next run.')
  const [agentLogs, setAgentLogs] = useState([{ id: 'boot', time: stamp(), level: 'info', text: 'Agent idle. Waiting for a new run.' }])
  const [logExpanded, setLogExpanded] = useState(true)

  const appendLog = useCallback((text, level = 'info') => setAgentLogs(current => [{ id: `${Date.now()}-${Math.random()}`, time: stamp(), level, text }, ...current].slice(0, 20)), [])
  const appendActivity = useCallback((label, detail) => setActivity(current => [{ id: `${Date.now()}-${Math.random()}`, label, detail, stamp: stamp() }, ...current].slice(0, 8)), [])
  const updateStep = useCallback((id, status, detail) => setPipeline(current => {
    const exists = current.some(step => step.id === id)
    const next = { id, label: id === 'discover' ? 'Discover GitHub repos' : id, status, detail }
    return exists ? current.map(step => step.id === id ? { ...step, status, detail } : step) : [...current, next]
  }), [])

  const refreshDashboard = useCallback(async () => {
    const snapshot = await loadSnapshot()
    setRepos(snapshot.repos); setPosts(snapshot.posts); setStats(snapshot.stats); setHealth(snapshot.health)
  }, [loadSnapshot])

  const handleStartAgent = useCallback(async () => {
    setLoading(true); setPipeline(defaultPipeline); setLogExpanded(true)
    setMessage('Connecting to backend agent…'); appendLog('Agent workflow started.', 'info')
    try {
      const response = await fetch(`${API_BASE}/agent/run?languages=typescript,python&limit=5`, { method: 'POST', headers: { Accept: 'text/event-stream' } })
      if (!response.ok || !response.body) throw new Error(await response.text() || 'Unable to start agent')
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''
      while (true) {
        const { value, done } = await reader.read(); if (done) break
        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n'); buffer = blocks.pop() || ''
        for (const block of blocks) {
          let eventName = 'message'; let raw = ''
          for (const line of block.split('\n')) { if (line.startsWith('event:')) eventName = line.slice(6).trim(); if (line.startsWith('data:')) raw += line.slice(5).trim() }
          if (!raw) continue
          let event; try { event = JSON.parse(raw) } catch { appendLog(`Invalid backend event: ${raw}`, 'error'); continue }
          if (eventName === 'step') { updateStep(event.step, event.status, event.message); appendLog(event.message, event.status === 'failed' ? 'error' : 'info') }
          if (eventName === 'log') appendLog(event.message, event.level || 'info')
          if (eventName === 'result') { appendActivity('Agent result', `${event.repos?.length || 0} repositories returned`); appendLog(JSON.stringify(event, null, 2), 'success') }
          if (eventName === 'completed') { setMessage(event.message); appendLog(event.message, 'success') }
          if (eventName === 'error') { setMessage(event.message); appendLog(event.message, 'error'); updateStep('discover', 'failed', event.message) }
        }
      }
      await refreshDashboard()
    } catch (error) { const text = error.message || 'Unknown error'; setMessage(`Agent failed: ${text}`); appendLog(`Agent failed: ${text}`, 'error'); updateStep('discover', 'failed', text) }
    finally { setLoading(false) }
  }, [appendActivity, appendLog, refreshDashboard, updateStep])

  useEffect(() => { void refreshDashboard().catch(error => appendLog(`Initial sync failed: ${error.message}`, 'error')) }, [appendLog, refreshDashboard])

  const cards = useMemo(() => [
    { label: 'Repos discovered', value: stats.total_repos, tone: 'cyan' },
    { label: 'Posts published', value: stats.total_posts, tone: 'green' },
    { label: 'Pending review', value: repos.filter(repo => repo.status === 'pending_analysis').length, tone: 'amber' },
    { label: 'Live health', value: health.status === 'healthy' ? 'OK' : 'Checking', tone: 'violet' },
  ], [health, repos, stats])

  return <ErrorBoundary><div className="app-shell"><header className="topbar"><div><p className="eyebrow">Autonomous DevRel engine</p><h1>Content Discovery Dashboard</h1></div><div className="user-pill">{user.name}</div></header><div className="toolbar"><button className="primary" onClick={handleStartAgent} disabled={loading}>{loading ? 'Running agent…' : 'Run agent'}</button><button className="secondary" onClick={() => void refreshDashboard()} disabled={loading}>Refresh</button></div><div className="alert-bar">{message}</div><section className="metrics-grid">{cards.map(card => <article key={card.label} className={`metric-card ${card.tone}`}><span>{card.label}</span><strong>{card.value}</strong></article>)}</section><section className="content-grid"><article className="panel pipeline-panel"><div className="panel-header"><h3>Live Agent Execution</h3><div className="thinking-badge"><span className="thinking-orbit" />{loading ? 'Running' : 'Idle'}</div></div><div className="pipeline-list">{pipeline.map(step => <div key={step.id} className={`pipeline-step ${step.status}`}><span className="step-indicator" /><div><strong>{step.label}</strong><small>{step.detail}</small></div></div>)}</div></article><article className="panel"><div className="panel-header"><h3>Backend execution log</h3><button className="mini-toggle" onClick={() => setLogExpanded(v => !v)}>{logExpanded ? 'Collapse' : 'Expand'}</button></div>{logExpanded && <div className="log-list">{agentLogs.map(log => <div key={log.id} className={`log-entry ${log.level}`}><div className="log-meta"><span>{log.level}</span><time>{log.time}</time></div><pre>{log.text}</pre></div>)}</div>}</article></section><section className="content-grid lower-grid"><RepoQueue repos={repos} loading={loading} onAnalyze={() => {}} onPublishLinkedIn={() => {}} onPublishDevTo={() => {}} /><div className="side-stack"><TagPerformance repos={repos} /><article className="panel activity-panel"><div className="panel-header"><h3>Backend activity</h3></div><ul className="activity-list">{activity.map(item => <li key={item.id}><span>{item.stamp}</span><div><strong>{item.label}</strong><small>{item.detail}</small></div></li>)}</ul></article></div></section><PostTimeline posts={posts} /></div></ErrorBoundary>
}
export default App
