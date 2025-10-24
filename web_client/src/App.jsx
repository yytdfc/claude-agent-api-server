import { useState } from 'react'
import Header from './components/Header'
import ConfigPanel from './components/ConfigPanel'
import ChatContainer from './components/ChatContainer'
import PermissionModal from './components/PermissionModal'
import SessionList from './components/SessionList'
import SettingsModal from './components/SettingsModal'
import { useClaudeAgent } from './hooks/useClaudeAgent'

function App() {
  const [showSidebar, setShowSidebar] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [settings, setSettings] = useState({
    cwd: '/workspace',
    serverUrl: 'http://localhost:8000'
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

  const handleNewSession = () => {
    if (connected) {
      clearSession()
    }
  }

  const handleSaveSettings = (newSettings) => {
    setSettings(newSettings)
  }

  return (
    <div className="app-layout">
      <Header connected={connected} onSettingsClick={() => setShowSettings(true)} />

      <div className="main-content">
        {showSidebar && (
          <aside className="sidebar">
            <SessionList
              serverUrl={settings.serverUrl}
              currentSessionId={sessionId}
              onSessionSelect={loadSession}
              onNewSession={handleNewSession}
              cwd={settings.cwd}
            />
          </aside>
        )}

        <main className="content-area">
          <button
            className="sidebar-toggle"
            onClick={() => setShowSidebar(!showSidebar)}
            title={showSidebar ? 'Hide sidebar' : 'Show sidebar'}
          >
            {showSidebar ? '◀' : '▶'}
          </button>

          {!connected ? (
            <ConfigPanel
              onConnect={connect}
              connecting={connecting}
            />
          ) : (
            <ChatContainer
              sessionInfo={sessionInfo}
              messages={messages}
              onSendMessage={sendMessage}
              onDisconnect={disconnect}
              onClearSession={clearSession}
            />
          )}
        </main>
      </div>

      {pendingPermission && (
        <PermissionModal
          permission={pendingPermission}
          onRespond={respondToPermission}
        />
      )}

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
