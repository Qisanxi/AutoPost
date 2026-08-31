export function TagPerformance({ repos = [] }) {
  const counts = new Map()

  repos.forEach((repo) => {
    ;(repo.topics || []).forEach((topic) => {
      const value = counts.get(topic) || 0
      counts.set(topic, value + 1)
    })
  })

  const tagData = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5)

  return (
    <article className="panel">
      <div className="panel-header">
        <h3>Top tags</h3>
      </div>
      <div className="tag-chart">
        {tagData.length === 0 ? (
          <p className="empty-state">No tags yet.</p>
        ) : (
          tagData.map(([tag, count]) => (
            <div key={tag} className="tag-row">
              <span>#{tag}</span>
              <div className="bar-track">
                <span style={{ width: `${Math.min(100, count * 25)}%` }} />
              </div>
              <strong>{count}</strong>
            </div>
          ))
        )}
      </div>
    </article>
  )
}
