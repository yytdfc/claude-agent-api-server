function Header({ connected }) {
  return (
    <header className="header">
      <h1>🤖 Claude Agent Web Client</h1>
      <div className="connection-status">
        <span className={`status-dot ${connected ? 'connected' : ''}`}></span>
        <span className="status-text">{connected ? 'Connected' : 'Disconnected'}</span>
      </div>
    </header>
  )
}

export default Header
