export function SecurityHeaders() {
  const headers = [
    { label: 'CORS', value: 'enabled' },
    { label: 'GitHub auth', value: 'token checked' },
    { label: 'Firestore', value: 'active' },
    { label: 'HTTPS', value: 'required' },
  ]

  return (
    <article className="panel">
      <div className="panel-header">
        <h3>Security & pipeline</h3>
      </div>
      <div className="security-list">
        {headers.map((item) => (
          <div key={item.label} className="security-row">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
    </article>
  )
}
