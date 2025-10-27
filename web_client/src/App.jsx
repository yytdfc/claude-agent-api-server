import { useState, useEffect } from 'react'
import Header from './components/Header'
import ChatContainer from './components/ChatContainer'
import PermissionModal from './components/PermissionModal'
import SessionList from './components/SessionList'
import SettingsModal from './components/SettingsModal'
import { useClaudeAgent } from './hooks/useClaudeAgent'

const SETTINGS_STORAGE_KEY = 'claude-agent-settings'

const DEFAULT_SETTINGS = {
  serverUrl: 'http://127.0.0.1:8000',
  cwd: '/workspace',
  model: 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
  backgroundModel: 'global.anthropic.claude-haiku-4-5-20251001-v1:0',
  enableProxy: false
}

function App() {
  const [showSettings, setShowSettings] = useState(false)

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
  }

  const handleSessionSelect = async (sessionId) => {
    // Load session with current settings
    await loadSession(sessionId, settings)
  }

  return (
    <div className="app-layout">
      <Header connected={connected} onSettingsClick={() => setShowSettings(true)} />

      <div className="main-content">
        <aside className="sidebar">
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

export default App
