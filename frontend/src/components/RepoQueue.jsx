export function RepoQueue({ repos = [], onAnalyze, onPublishLinkedIn, onPublishDevTo, loading }) {
  return (
    <article className="panel">
      <div className="panel-header">
        <h3>Repository queue</h3>
      </div>

      <div className="repo-list">
        {repos.length === 0 ? (
          <p className="empty-state">No repositories discovered yet.</p>
        ) : (
          repos.map((repo) => (
            <div key={repo.id} className="repo-card">
              <div className="repo-topline">
                <div>
                  <h4>{repo.raw_name || repo.name || 'Repository'}</h4>
                  <span className="repo-url">{repo.github_url}</span>
                </div>
                <span className="stars">⭐ {repo.stars || 0}</span>
              </div>

              <p>{repo.raw_description || 'Repository description pending.'}</p>

              <div className="repo-meta-row">
                <span className="status-pill">{repo.status || 'pending'}</span>
                {repo.topics?.slice(0, 3).map((topic) => (
                  <span key={`${repo.id}-${topic}`} className="tag-pill">#{topic}</span>
                ))}
              </div>

              <div className="repo-actions">
                {repo.status === 'pending_analysis' && (
                  <button className="primary small" onClick={() => onAnalyze?.(repo.id)} disabled={loading}>
                    Analyze
                  </button>
                )}
                {repo.status === 'analyzed' && (
                  <>
                    <button className="secondary small" onClick={() => onPublishLinkedIn?.(repo.id)} disabled={loading}>
                      LinkedIn
                    </button>
                    <button className="secondary small" onClick={() => onPublishDevTo?.(repo.id)} disabled={loading}>
                      Dev.to
                    </button>
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </article>
  )
}
