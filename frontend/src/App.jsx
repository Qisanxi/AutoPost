import { useCallback, useEffect, useMemo, useState } from 'react'

import { ErrorBoundary } from './components/ErrorBoundary'
import { PostTimeline } from './components/PostTimeline'
import { RepoQueue } from './components/RepoQueue'
import { TagPerformance } from './components/TagPerformance'
import { useAuth } from './hooks/useAuth'
import { useFirestore } from './hooks/useFirestore'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const createStamp = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const defaultActivity = [{ id: 'boot', label: 'Dashboard ready', detail: 'Monitoring backend pipeline', stamp: createStamp() }]
const defaultPipeline = [
  { id: 'discover', label: 'Discover GitHub repos', status: 'pending', detail: 'Search for trending repositories' },
  { id: 'analyze', label: 'Analyze repo content', status: 'pending', detail: 'Read README and extract insight' },
  { id: 'generate', label: 'Generate content drafts', status: 'pending', detail: 'Create drafts for human review' },
]

function App() {
  const { user } = useAuth()
  const { loadSnapshot } = useFirestore({ apiBase: API_BASE })
  const [repos, setRepos] = useState([])
  const [posts, setPosts] = useState([])
  const [stats, setStats] = useState({ total_repos: 0, total_posts: 0, platforms: [] })
  const [health, setHealth] = useState({ status: 'checking', database: 'pending' })
  const [activity, setActivity] = useState(defaultActivity)
  const [pipeline, setPipeline] = useState(defaultPipeline)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('Backend pipeline is waiting for the next sync.')
  const [agentLogs, setAgentLogs] = useState([{ id: 'boot', time: createStamp(), level: 'info', text: 'Agent idle. Waiting for a new run.' }])
  const [logExpanded, setLogExpanded] = useState(true)
  const [runTimeline, setRunTimeline] = useState([])
  const [agentResult, setAgentResult] = useState(null)

  const appendActivity = useCallback((label, detail) => setActivity((current) => [{ id: `${Date.now()}-${Math.random()}`, label, detail, stamp: createStamp() }, ...current].slice(0, 6)), [])
  const appendLog = useCallback((text, level = 'info') => setAgentLogs((current) => [{ id: `${Date.now()}-${Math.random()}`, time: createStamp(), level, text }, ...current].slice(0, 20)), [])
  const appendTimelineEvent = useCallback((label, detail, durationMs = 0) => setRunTimeline((current) => [{ id: `${Date.now()}-${Math.random()}`, label, detail, stamp: createStamp(), durationMs }, ...current].slice(0, 8)), [])
  const updatePipelineStep = useCallback((stepId, status, detail = '') => setPipeline((current) => current.map((step) => step.id === stepId ? { ...step, status, detail: detail || step.detail } : step)), [])
  const resetPipeline = useCallback(() => setPipeline(defaultPipeline), [])

  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, options)
    if (!response.ok) throw new Error(await response.text() || 'Request failed')
    return response.json()
  }

  const refreshDashboard = useCallback(async () => {
    const snapshot = await loadSnapshot()
    setRepos(snapshot.repos); setPosts(snapshot.posts); setStats(snapshot.stats); setHealth(snapshot.health)
  }, [loadSnapshot])

  const handleDiscover = async () => {
    setLoading(true)
    try {
      const response = await fetchJson(`${API_BASE}/agent/discover?languages=typescript,python&limit=5`, { method: 'POST' })
      setMessage(`Discovery complete: ${response.count} saved.`); appendActivity('Discovery complete', `${response.count} repos saved`)
      await refreshDashboard()
    } catch (error) { setMessage(`Discovery failed: ${error.message}`); appendLog(`Discovery failed: ${error.message}`, 'error') }
    finally { setLoading(false) }
  }

  const handleAnalyze = async (repoId) => {
    setLoading(true)
    try {
      const response = await fetchJson(`${API_BASE}/agent/analyze/${repoId}`, { method: 'POST' })
      setMessage(response.status === 'failed' ? `Analyze failed: ${response.reason}` : 'Repository analysis completed.')
      await refreshDashboard()
    } catch (error) { setMessage(`Analysis failed: ${error.message}`); appendLog(`Analysis failed: ${error.message}`, 'error') }
    finally { setLoading(false) }
  }

  const handlePublish = async (repoId, platform) => {
    setLoading(true)
    try {
      const endpoint = platform === 'linkedin' ? 'linkedin' : 'devto'
      await fetchJson(`${API_BASE}/agent/publish/${endpoint}/${repoId}`, { method: 'POST' })
      setMessage(`${platform} publish succeeded.`); appendActivity('Publish complete', `${platform.toUpperCase()} content published`)
      await refreshDashboard()
    } catch (error) { setMessage(`Publish failed: ${error.message}`); appendLog(`Publish failed: ${error.message}`, 'error') }
    finally { setLoading(false) }
  }

  const handleStartAgent = useCallback(async () => {
    setLoading(true); resetPipeline(); setAgentResult(null); setLogExpanded(true)
    setMessage('Connecting to backend agent…'); appendLog('Agent workflow started.', 'info'); appendTimelineEvent('Workflow start', 'Agent session initialized')
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
          if (eventName === 'step') { updatePipelineStep(event.step, event.status, event.message); appendLog(event.message, event.status === 'failed' ? 'error' : 'info'); appendTimelineEvent(event.step, event.message) }
          if (eventName === 'log') appendLog(event.message, event.level || 'info')
          if (eventName === 'result') { setAgentResult(event); appendActivity('Agent result ready', event.repo?.name || 'Repository analysis completed'); appendLog('Analysis and reviewable drafts generated.', 'success') }
          if (eventName === 'completed') { setMessage(event.message); appendLog(event.message, 'success') }
          if (eventName === 'error') { setMessage(event.message); appendLog(event.message, 'error') }
        }
      }
      await refreshDashboard()
    } catch (error) { setMessage(`Agent failed: ${error.message}`); appendLog(`Agent failed: ${error.message}`, 'error') }
    finally { setLoading(false) }
  }, [appendActivity, appendLog, appendTimelineEvent, refreshDashboard, resetPipeline, updatePipelineStep])

  useEffect(() => { void refreshDashboard().catch((error) => appendLog(`Initial sync failed: ${error.message}`, 'error')) }, [appendLog, refreshDashboard])

  const cards = useMemo(() => [
    { label: 'Repos discovered', value: stats.total_repos, tone: 'cyan' },
    { label: 'Posts published', value: stats.total_posts, tone: 'green' },
    { label: 'Pending review', value: repos.filter((repo) => repo.status === 'pending_analysis').length, tone: 'amber' },
    { label: 'Live health', value: health.status === 'healthy' ? 'OK' : 'Checking', tone: 'violet' },
  ], [repos, stats, health])

  return <ErrorBoundary><div className="app-shell"><header className="topbar"><div><p className="eyebrow">Autonomous DevRel engine</p><h1>Content Discovery Dashboard</h1></div><div className="user-pill">{user.name}</div></header><div className="toolbar"><button className="primary" onClick={handleStartAgent} disabled={loading}>{loading ? 'Running workflow…' : 'Start agent'}</button><button className="secondary" onClick={handleDiscover} disabled={loading}>Discover repos</button><button className="secondary" onClick={() => void refreshDashboard()} disabled={loading}>Refresh</button></div><div className="alert-bar">{message}</div><section className="metrics-grid">{cards.map((card) => <article key={card.label} className={`metric-card ${card.tone}`}><span>{card.label}</span><strong>{card.value}</strong></article>)}</section><section className="content-grid"><article className="panel pipeline-panel"><div className="panel-header"><h3>Live Agent Execution</h3><div className="thinking-badge"><span className="thinking-orbit" />{loading ? 'Running' : 'Idle'}</div></div><div className="pipeline-list">{pipeline.map((step) => <div key={step.id} className={`pipeline-step ${step.status}`}><span className="step-indicator" /><div><strong>{step.label}</strong><small>{step.detail}</small></div></div>)}</div></article><article className="panel"><div className="panel-header"><h3>Backend execution log</h3><button className="mini-toggle" onClick={() => setLogExpanded((value) => !value)}>{logExpanded ? 'Collapse' : 'Expand'}</button></div>{logExpanded && <div className="log-list">{agentLogs.map((log) => <div key={log.id} className={`log-entry ${log.level}`}><div className="log-meta"><span>{log.level}</span><time>{log.time}</time></div><pre>{log.text}</pre></div>)}</div>}</article></section>{agentResult && <section className="panel agent-result"><div className="panel-header"><h3>Agent result</h3><span>Review before publishing</span></div><strong>{agentResult.repo?.name}</strong><p>{agentResult.analysis?.one_liner_hook || agentResult.analysis?.problem_solved}</p><details><summary>LinkedIn draft</summary><pre>{agentResult.drafts?.linkedin}</pre></details><details><summary>Dev.to draft</summary><pre>{agentResult.drafts?.devto}</pre></details></section>}<section className="content-grid lower-grid"><RepoQueue repos={repos} onAnalyze={handleAnalyze} onPublishLinkedIn={(repoId) => handlePublish(repoId, 'linkedin')} onPublishDevTo={(repoId) => handlePublish(repoId, 'devto')} loading={loading} /><div className="side-stack"><TagPerformance repos={repos} /><article className="panel activity-panel"><div className="panel-header"><h3>Backend activity</h3></div><ul className="activity-list">{activity.map((item) => <li key={item.id}><span>{item.stamp}</span><div><strong>{item.label}</strong><small>{item.detail}</small></div></li>)}</ul></article></div></section><PostTimeline posts={posts} /><div className="sr-only">{runTimeline.length} agent events recorded</div></div></ErrorBoundary>
}

export default App
