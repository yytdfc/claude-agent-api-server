import { useState } from 'react'
import Header from './components/Header'
import ConfigPanel from './components/ConfigPanel'
import ChatContainer from './components/ChatContainer'
import PermissionModal from './components/PermissionModal'
import SessionList from './components/SessionList'
import { useClaudeAgent } from './hooks/useClaudeAgent'

function App() {
  const [showSidebar, setShowSidebar] = useState(true)

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

  return (
    <div className="app-layout">
      <Header connected={connected} />

      <div className="main-content">
        {showSidebar && (
          <aside className="sidebar">
            <SessionList
              serverUrl={serverUrl}
              currentSessionId={sessionId}
              onSessionSelect={loadSession}
              onNewSession={handleNewSession}
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
    </div>
  )
}

export default App
