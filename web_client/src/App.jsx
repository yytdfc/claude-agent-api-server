import { useState, useEffect } from 'react'
import Header from './components/Header'
import ChatContainer from './components/ChatContainer'
import PermissionModal from './components/PermissionModal'
import SessionList from './components/SessionList'
import FileBrowser from './components/FileBrowser'
import SettingsModal from './components/SettingsModal'
import Login from './components/Login'
import Signup from './components/Signup'
import { useClaudeAgent } from './hooks/useClaudeAgent'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { Loader2 } from 'lucide-react'

const SETTINGS_STORAGE_KEY = 'claude-agent-settings'

const DEFAULT_SETTINGS = {
  serverUrl: 'http://127.0.0.1:8000',
  cwd: '/workspace',
  model: 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
  backgroundModel: 'global.anthropic.claude-haiku-4-5-20251001-v1:0',
  enableProxy: false
}

function AppContent() {
  const [showSettings, setShowSettings] = useState(false)
  const [authView, setAuthView] = useState('login') // 'login' or 'signup'
  const { user, loading: authLoading, logout } = useAuth()

  // Load settings from localStorage or use defaults
  const [settings, setSettings] = useState(() => {
    try {
      const saved = localStorage.getItem(SETTINGS_STORAGE_KEY)
      if (saved) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
      }
    } catch (error) {
      console.error('Failed to load settings from localStorage:', error)
    }
    return DEFAULT_SETTINGS
  })

  // Store the working directory from settings (configuration, not changed by browsing)
  const [workingDirectory, setWorkingDirectory] = useState(settings.cwd)

  // Separate browsing path from configured working directory
  const [currentBrowsePath, setCurrentBrowsePath] = useState(settings.cwd)

  const {
    connected,
    connecting,
    sessionId,
    sessionInfo,
    messages,
    pendingPermission,
    serverUrl,
    connect,
    disconnect,
    clearSession,
    sendMessage,
    respondToPermission,
    loadSession
  } = useClaudeAgent()

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
    } catch (error) {
      console.error('Failed to save settings to localStorage:', error)
    }
  }, [settings])

  const handleNewSession = () => {
    if (connected) {
      clearSession()
    } else {
      // Auto-connect with current settings
      connect(settings)
    }
  }

  const handleSaveSettings = (newSettings) => {
    setSettings(newSettings)
    // Update working directory when settings change
    setWorkingDirectory(newSettings.cwd)
    // Also update current browse path to match new working directory
    setCurrentBrowsePath(newSettings.cwd)
  }

  const handleSessionSelect = async (sessionId) => {
    // Load session with current settings
    await loadSession(sessionId, settings)
  }

  const handleBrowsePathChange = (newPath) => {
    // Only change the browsing path, don't modify settings
    setCurrentBrowsePath(newPath)
  }

  // Show loading spinner during auth check
  if (authLoading) {
    return (
      <div className="auth-loading">
        <Loader2 size={48} className="spinning" />
        <p>Loading...</p>
      </div>
    )
  }

  // Show auth screens if not logged in
  if (!user) {
    if (authView === 'signup') {
      return <Signup onSwitchToLogin={() => setAuthView('login')} />
    }
    return <Login onSwitchToSignup={() => setAuthView('signup')} />
  }

  // Main app content (user is authenticated)
  return (
    <div className="app-layout">
      <Header
        connected={connected}
        onSettingsClick={() => setShowSettings(true)}
        user={user}
        onLogout={logout}
        workingDirectory={workingDirectory}
      />

      <div className="main-content">
        <aside className="sidebar">
          <FileBrowser
            serverUrl={settings.serverUrl}
            currentPath={currentBrowsePath}
            workingDirectory={workingDirectory}
            onPathChange={handleBrowsePathChange}
          />
          <SessionList
            serverUrl={settings.serverUrl}
            currentSessionId={sessionId}
            onSessionSelect={handleSessionSelect}
            onNewSession={handleNewSession}
            cwd={settings.cwd}
          />
        </aside>

        <main className="content-area">
          {!connected ? (
            <div className="welcome-screen">
              <div className="welcome-content">
                <h2>Welcome to Claude Agent</h2>
                <p>Select a session from the sidebar or create a new one to get started.</p>
                <p className="welcome-hint">
                  Configure settings using the ⚙️ button in the top-right corner.
                </p>
              </div>
            </div>
          ) : (
            <ChatContainer
              sessionInfo={sessionInfo}
              messages={messages}
              onSendMessage={sendMessage}
              onDisconnect={disconnect}
              onClearSession={clearSession}
              onPermissionRespond={respondToPermission}
            />
          )}
        </main>
      </div>

      {showSettings && (
        <SettingsModal
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
          settings={settings}
          onSave={handleSaveSettings}
        />
      )}
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
