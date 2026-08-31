import { useCallback, useEffect, useMemo, useState } from 'react'

import { ErrorBoundary } from './components/ErrorBoundary'
import { PostTimeline } from './components/PostTimeline'
import { RepoQueue } from './components/RepoQueue'
import { TagPerformance } from './components/TagPerformance'
import { useAuth } from './hooks/useAuth'
import { useFirestore } from './hooks/useFirestore'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const createStamp = () => new Date().toLocaleTimeString([], {
  hour: '2-digit',
  minute: '2-digit',
})

const defaultActivity = [
  { id: 'boot', label: 'Dashboard ready', detail: 'Monitoring backend pipeline', stamp: createStamp() },
]

const defaultPipeline = [
  { id: 'discover', label: 'Discover GitHub repos', status: 'pending', detail: 'Search for trending repositories' },
  { id: 'analyze', label: 'Analyze repo content', status: 'pending', detail: 'Read README and extract insight' },
  { id: 'linkedin', label: 'Publish LinkedIn', status: 'pending', detail: 'Write and post to LinkedIn' },
  { id: 'devto', label: 'Publish Dev.to', status: 'pending', detail: 'Generate and publish article' },
]

function App() {
  const { user } = useAuth()
  const { loadSnapshot } = useFirestore({ apiBase: API_BASE })
  const [repos, setRepos] = useState([])
  const [posts, setPosts] = useState([])
  const [stats, setStats] = useState({
    total_repos: 0,
    total_posts: 0,
    platforms: [],
  })
  const [health, setHealth] = useState({ status: 'checking', database: 'pending' })
  const [activity, setActivity] = useState(defaultActivity)
  const [pipeline, setPipeline] = useState(defaultPipeline)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('Backend pipeline is waiting for the next sync.')
  const [agentLogs, setAgentLogs] = useState([{ id: 'boot', time: createStamp(), level: 'info', text: 'Agent idle. Waiting for a new run.' }])
  const [logExpanded, setLogExpanded] = useState(true)
  const [runTimeline, setRunTimeline] = useState([])

  const appendActivity = useCallback((label, detail) => {
    setActivity((current) => [
      {
        id: `${Date.now()}-${Math.random()}`,
        label,
        detail,
        stamp: createStamp(),
      },
      ...current,
    ].slice(0, 6))
  }, [])

  const appendLog = useCallback((text, level = 'info') => {
    setAgentLogs((current) => [
      {
        id: `${Date.now()}-${Math.random()}`,
        time: createStamp(),
        level,
        text,
      },
      ...current,
    ].slice(0, 8))
  }, [])

  const appendTimelineEvent = useCallback((label, detail, durationMs = 0) => {
    setRunTimeline((current) => [
      {
        id: `${Date.now()}-${Math.random()}`,
        label,
        detail,
        stamp: createStamp(),
        durationMs,
      },
      ...current,
    ].slice(0, 8))
  }, [])

  const updatePipelineStep = useCallback((stepId, status, detail = '') => {
    setPipeline((current) => current.map((step) => {
      if (step.id !== stepId) return step
      return { ...step, status, detail: detail || step.detail }
    }))
  }, [])

  const resetPipeline = useCallback(() => {
    setPipeline(defaultPipeline)
  }, [])

  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, options)
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(errorText || 'Request failed')
    }
    return response.json()
  }

  const refreshDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const snapshot = await loadSnapshot()
      setRepos(snapshot.repos)
      setPosts(snapshot.posts)
      setStats(snapshot.stats)
      setHealth(snapshot.health)
      setMessage('Live backend data synced successfully.')
      appendLog('Backend snapshot refreshed successfully.', 'info')
      appendTimelineEvent('Backend sync', 'Fetched repo, post, and health data', 220)
    } catch (error) {
      setMessage(`Backend unreachable: ${error.message}`)
      appendActivity('Connection issue', error.message)
      appendLog(`Refresh failed: ${error.message}`, 'error')
      appendTimelineEvent('Backend sync failed', error.message, 0)
    } finally {
      setLoading(false)
    }
  }, [appendActivity, appendLog, appendTimelineEvent, loadSnapshot])

  const handleDiscover = async () => {
    setLoading(true)
    appendActivity('Discovery started', 'Searching GitHub for trending repos')
    try {
      const response = await fetchJson(`${API_BASE}/agent/discover?languages=typescript,python&limit=5`, {
        method: 'POST',
      })
      setMessage(`Discovery complete: ${response.count} saved, ${response.github_found} found, ${response.duplicates_skipped} duplicates skipped.`)
      appendActivity('Discovery complete', `${response.count} repos saved to Firestore`)
      appendLog(JSON.stringify({ action: 'discover', result: response }, null, 2), 'success')
      appendTimelineEvent('GitHub discover', `${response.count} repos saved`, 520)
      await refreshDashboard()
    } catch (error) {
      setMessage(`Discovery failed: ${error.message}`)
      appendActivity('Discovery failed', error.message)
      appendLog(`Discovery failed: ${error.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async (repoId) => {
    setLoading(true)
    appendActivity('Analysis running', `Analyzing repo ${repoId}`)
    try {
      const response = await fetchJson(`${API_BASE}/agent/analyze/${repoId}`, { method: 'POST' })
      setMessage(response.status === 'failed' ? `Analyze failed: ${response.reason}` : 'Repository analysis completed.')
      appendActivity('Analysis complete', response.status === 'failed' ? response.reason : 'AI summary generated')
      appendLog(JSON.stringify({ action: 'analyze', result: response }, null, 2), response.status === 'failed' ? 'warning' : 'success')
      appendTimelineEvent('Repo analyze', response.status === 'failed' ? response.reason : 'AI analysis generated', 1450)
      await refreshDashboard()
    } catch (error) {
      setMessage(`Analysis failed: ${error.message}`)
      appendActivity('Analysis failed', error.message)
      appendLog(`Analysis failed: ${error.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async (repoId, platform) => {
    setLoading(true)
    appendActivity('Publishing started', `${platform} post generation`)
    try {
      const endpoint = platform === 'linkedin' ? 'linkedin' : 'devto'
      await fetchJson(`${API_BASE}/agent/publish/${endpoint}/${repoId}`, { method: 'POST' })
      setMessage(`${platform} publish succeeded.`)
      appendActivity('Publish complete', `${platform.toUpperCase()} article shared`)
      appendLog(JSON.stringify({ action: 'publish', platform, result: 'success' }, null, 2), 'success')
      appendTimelineEvent(`${platform} publish`, 'Content posted to platform', 2100)
      await refreshDashboard()
    } catch (error) {
      setMessage(`Publish failed: ${error.message}`)
      appendActivity('Publish failed', error.message)
      appendLog(`Publish failed: ${error.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleStartAgent = useCallback(async () => {
    setLoading(true)
    resetPipeline()
    setMessage('Starting autonomous content pipeline…')
    setLogExpanded(true)
    appendLog('Agent workflow started.', 'info')
    appendTimelineEvent('Workflow start', 'Agent session initialized', 0)

    try {
      updatePipelineStep('discover', 'running', 'Searching GitHub for trending repositories')
      const discoverResult = await fetchJson(`${API_BASE}/agent/discover?languages=typescript,python&limit=5`, { method: 'POST' })
      updatePipelineStep('discover', 'done', `${discoverResult.count} repos saved to Firestore`)
      appendActivity('Discovery complete', `${discoverResult.count} repos saved to Firestore`)
      appendLog(JSON.stringify({ action: 'discover', result: discoverResult }, null, 2), 'success')
      appendTimelineEvent('GitHub discover', `${discoverResult.count} repos saved`, 520)

      const repoList = await fetchJson(`${API_BASE}/agent/repos?limit=10`)
      const nextRepo = repoList.find((repo) => repo.status === 'pending_analysis') || repoList[0]

      if (!nextRepo) {
        updatePipelineStep('analyze', 'failed', 'No repository ready for analysis')
        setMessage('No repo was eligible for the publishing chain.')
        appendLog('No repository was eligible for analysis.', 'warning')
        return
      }

      updatePipelineStep('analyze', 'running', `Reviewing ${nextRepo.raw_name || nextRepo.name}`)
      const analysisResult = await fetchJson(`${API_BASE}/agent/analyze/${nextRepo.id}`, { method: 'POST' })
      updatePipelineStep('analyze', 'done', analysisResult.status === 'failed' ? analysisResult.reason : 'README reviewed and summary generated')
      appendActivity('Analysis complete', nextRepo.raw_name || nextRepo.name)
      appendLog(JSON.stringify({ action: 'analyze', result: analysisResult }, null, 2), analysisResult.status === 'failed' ? 'warning' : 'success')
      appendTimelineEvent('Repo analyze', analysisResult.status === 'failed' ? analysisResult.reason : 'AI analysis generated', 1450)

      if (analysisResult.status === 'failed') {
        setMessage('Analysis failed before publishing. Review the repo and retry.')
        appendLog('Analysis failed before publishing. Review the repo and retry.', 'warning')
        return
      }

      updatePipelineStep('linkedin', 'running', 'Writing a LinkedIn post for the repo')
      const linkedInResult = await fetchJson(`${API_BASE}/agent/publish/linkedin/${nextRepo.id}`, { method: 'POST' })
      updatePipelineStep('linkedin', 'done', 'LinkedIn post shared successfully')
      appendActivity('LinkedIn published', nextRepo.raw_name || nextRepo.name)
      appendLog(JSON.stringify({ action: 'publish_linkedin', result: linkedInResult }, null, 2), 'success')
      appendTimelineEvent('LinkedIn publish', 'LinkedIn post sent', 1980)

      updatePipelineStep('devto', 'running', 'Drafting and publishing a Dev.to article')
      const devtoResult = await fetchJson(`${API_BASE}/agent/publish/devto/${nextRepo.id}`, { method: 'POST' })
      updatePipelineStep('devto', 'done', 'Dev.to article published successfully')
      appendActivity('Dev.to published', nextRepo.raw_name || nextRepo.name)
      appendLog(JSON.stringify({ action: 'publish_devto', result: devtoResult }, null, 2), 'success')
      appendTimelineEvent('Dev.to publish', 'Dev.to article sent', 2120)

      setMessage('Agent finished the GitHub → analysis → publishing workflow successfully.')
      appendLog('Workflow completed successfully.', 'success')
      appendTimelineEvent('Workflow complete', 'Agent pipeline finished successfully', 0)
      await refreshDashboard()
    } catch (error) {
      const failedStep = pipeline.find((step) => step.status === 'running')?.id || 'discover'
      updatePipelineStep(failedStep, 'failed', error.message)
      setMessage(`Agent workflow failed during ${failedStep}: ${error.message}`)
      appendActivity('Workflow failed', error.message)
      appendLog(`Workflow failed during ${failedStep}: ${error.message}`, 'error')
      appendTimelineEvent('Workflow failed', `${failedStep}: ${error.message}`, 0)
    } finally {
      setLoading(false)
    }
  }, [appendActivity, appendLog, appendTimelineEvent, pipeline, refreshDashboard, resetPipeline, updatePipelineStep])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshDashboard()
    }, 0)

    return () => window.clearTimeout(timer)
  }, [refreshDashboard])

  const cards = useMemo(() => [
    { label: 'Repos discovered', value: stats.total_repos, tone: 'cyan' },
    { label: 'Posts published', value: stats.total_posts, tone: 'green' },
    { label: 'Pending review', value: repos.filter((repo) => repo.status === 'pending_analysis').length, tone: 'amber' },
    { label: 'Live health', value: health.status === 'healthy' ? 'OK' : 'Checking', tone: 'violet' },
  ], [repos, stats, health])

  return (
    <ErrorBoundary>
      <div className="app-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">Autonomous DevRel engine</p>
            <h1>Content Discovery Dashboard</h1>
          </div>
          <div className="user-pill">{user.name}</div>
        </header>

        <div className="toolbar">
          <button className="primary" onClick={handleStartAgent} disabled={loading}>
            {loading ? 'Running workflow…' : 'Start agent'}
          </button>
          <button className="secondary" onClick={handleDiscover} disabled={loading}>
            Discover repos
          </button>
          <button className="secondary" onClick={refreshDashboard} disabled={loading}>
            Refresh
          </button>
        </div>

        <div className="alert-bar">{message}</div>

        <section className="metrics-grid">
          {cards.map((card) => (
            <article key={card.label} className={`metric-card ${card.tone}`}>
              <span>{card.label}</span>
              <strong>{card.value}</strong>
            </article>
          ))}
        </section>

        <section className="content-grid">
          <article className="panel pipeline-panel">
            <div className="panel-header">
              <h3>Agent thought chain</h3>
              <div className="thinking-badge">
                <span className="thinking-orbit" />
                {loading ? 'Thinking' : 'Idle'}
              </div>
            </div>
            <div className="pipeline-list">
              {pipeline.map((step) => (
                <div key={step.id} className={`pipeline-step ${step.status}`}>
                  <span className="step-indicator" aria-label={step.status} />
                  <div>
                    <strong>{step.label}</strong>
                    <small>{step.detail}</small>
                  </div>
                </div>
              ))}
            </div>
          </article>
          <article className="panel">
            <div className="panel-header">
              <h3>Backend response log</h3>
              <button className="mini-toggle" onClick={() => setLogExpanded((value) => !value)}>
                {logExpanded ? 'Collapse' : 'Expand'}
              </button>
            </div>
            {logExpanded && (
              <div className="log-list">
                {agentLogs.map((log) => (
                  <div key={log.id} className={`log-entry ${log.level}`}>
                    <div className="log-meta">
                      <span>{log.level}</span>
                      <time>{log.time}</time>
                    </div>
                    <pre>{log.text}</pre>
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>

        <section className="content-grid lower-grid">
          <RepoQueue
            repos={repos}
            onAnalyze={handleAnalyze}
            onPublishLinkedIn={(repoId) => handlePublish(repoId, 'linkedin')}
            onPublishDevTo={(repoId) => handlePublish(repoId, 'devto')}
            loading={loading}
          />
          <div className="side-stack">
            <TagPerformance repos={repos} />
            <article className="panel activity-panel">
              <div className="panel-header">
                <h3>Backend activity</h3>
              </div>
              <ul className="activity-list">
                {activity.map((item) => (
                  <li key={item.id}>
                    <span className="activity-time">{item.stamp}</span>
                    <div>
                      <strong>{item.label}</strong>
                      <small>{item.detail}</small>
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        <section className="timeline-wrap">
          <article className="panel">
            <div className="panel-header">
              <h3>Backend timeline</h3>
            </div>
            <div className="timeline-list">
              {runTimeline.length === 0 ? (
                <p className="empty-state">No backend calls yet.</p>
              ) : (
                runTimeline.map((event) => (
                  <div key={event.id} className="timeline-item">
                    <span className="timeline-time">{event.stamp}</span>
                    <div className="timeline-content">
                      <strong>{event.label}</strong>
                      <small>{event.detail}</small>
                      <span className="duration-badge">{event.durationMs ? `${event.durationMs}ms` : 'instant'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </article>
          <PostTimeline posts={posts} />
        </section>
      </div>
    </ErrorBoundary>
  )
}

export default App
