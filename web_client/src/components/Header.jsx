import { Settings, Circle, Bot, LogOut, User, FolderOpen, Terminal, Folder, Github, XCircle } from 'lucide-react'

function Header({
  serverConnected,
  onSettingsClick,
  user,
  onLogout,
  workingDirectory,
  showTerminal,
  onTerminalToggle,
  currentProject,
  onProjectSwitcherOpen,
  onGithubAuthClick,
  githubAuthStatus,
  githubAuthMessage,
  onCloseProject,
  closingProject
}) {
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
        {onProjectSwitcherOpen && (
          <button
            className="btn-outline project-switcher-button"
            onClick={onProjectSwitcherOpen}
            title="Switch Project"
          >
            <Folder size={16} />
            <span className="project-name">{currentProject || 'Default Workspace'}</span>
          </button>
        )}
        <div className="connection-status" title="Backend service connection status">
          <Circle size={10} className={`status-dot ${serverConnected ? 'connected' : ''}`} fill="currentColor" />
          <span className="status-text">{serverConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
        {onGithubAuthClick && (
          <button
            className={`btn-icon github-auth-button ${githubAuthStatus === 'success' ? 'success' : ''} ${githubAuthStatus === 'error' ? 'error' : ''}`}
            onClick={onGithubAuthClick}
            title={githubAuthMessage || "Authenticate with GitHub"}
            disabled={githubAuthStatus === 'pending'}
          >
            <Github size={18} />
          </button>
        )}
        <button
          className={`btn-icon terminal-toggle-button ${showTerminal ? 'active' : ''}`}
          onClick={onTerminalToggle}
          title={showTerminal ? "Hide Terminal" : "Show Terminal"}
        >
          <Terminal size={18} />
        </button>
        {onCloseProject && currentProject && (
          <button
            className="btn-icon close-project-button"
            onClick={onCloseProject}
            title="Close Project (Stop AgentCore Session)"
            disabled={closingProject}
          >
            <XCircle size={18} />
          </button>
        )}
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
