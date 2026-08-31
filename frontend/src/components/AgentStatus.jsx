export function AgentStatus({ health, stats, loading }) {
  const statusTone = health.status === 'healthy' ? 'healthy' : 'warning'

  return (
    <article className="panel">
      <div className="panel-header">
        <h3>Agent status</h3>
        <span className={`status-badge ${statusTone}`}>{loading ? 'Running' : health.status}</span>
      </div>

      <div className="status-list">
        <div>
          <span>Backend</span>
          <strong>{health.status || 'checking'}</strong>
        </div>
        <div>
          <span>Database</span>
          <strong>{health.database || 'pending'}</strong>
        </div>
        <div>
          <span>Platform mix</span>
          <strong>{stats.platforms?.length ? stats.platforms.join(', ') : 'linkedin, devto'}</strong>
        </div>
      </div>
    </article>
  )
}
