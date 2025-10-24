function Header({ connected, onSettingsClick }) {
  return (
    <header className="header">
      <h1>🤖 Claude Agent Web Client</h1>
      <div className="header-right">
        <div className="connection-status">
          <span className={`status-dot ${connected ? 'connected' : ''}`}></span>
          <span className="status-text">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        <button className="btn-icon settings-button" onClick={onSettingsClick} title="Settings">
          ⚙️
        </button>
      </div>
    </header>
  )
}

export default Header
