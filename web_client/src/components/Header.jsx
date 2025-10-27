import { Settings, Circle, Bot, LogOut, User } from 'lucide-react'

function Header({ connected, onSettingsClick, user, onLogout }) {
  return (
    <header className="header">
      <h1><Bot size={20} className="header-icon" /> Claude Agent Web Client</h1>
      <div className="header-right">
        {user && (
          <div className="user-info">
            <User size={16} />
            <span className="user-email">{user.username}</span>
          </div>
        )}
        <div className="connection-status">
          <Circle size={10} className={`status-dot ${connected ? 'connected' : ''}`} fill="currentColor" />
          <span className="status-text">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        <button className="btn-icon settings-button" onClick={onSettingsClick} title="Settings">
          <Settings size={18} />
        </button>
        {user && onLogout && (
          <button className="btn-icon logout-button" onClick={onLogout} title="Logout">
            <LogOut size={18} />
          </button>
        )}
      </div>
    </header>
  )
}

export default Header
