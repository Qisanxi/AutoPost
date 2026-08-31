export function PostTimeline({ posts = [] }) {
  return (
    <article className="panel">
      <div className="panel-header">
        <h3>Post timeline</h3>
      </div>

      <div className="post-list">
        {posts.length === 0 ? (
          <p className="empty-state">No posts published yet.</p>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="post-card">
              <div className="post-meta">
                <span className="platform-tag">{post.platform || 'unknown'}</span>
                <span className="status-pill">{post.status || 'queued'}</span>
              </div>
              <h4>{post.content?.headline || post.platform || 'Published content'}</h4>
              <p>{post.content?.body ? String(post.content.body).slice(0, 140) : 'Backend generated content is ready for review.'}</p>
              {post.published_url ? (
                <a href={post.published_url} target="_blank" rel="noreferrer">View live post</a>
              ) : null}
            </div>
          ))
        )}
      </div>
    </article>
  )
}
