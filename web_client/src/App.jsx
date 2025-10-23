import { useState } from 'react'
import Header from './components/Header'
import ConfigPanel from './components/ConfigPanel'
import ChatContainer from './components/ChatContainer'
import PermissionModal from './components/PermissionModal'
import { useClaudeAgent } from './hooks/useClaudeAgent'

function App() {
  const {
    connected,
    connecting,
    sessionInfo,
    messages,
    pendingPermission,
    connect,
    disconnect,
    clearSession,
    sendMessage,
    respondToPermission
  } = useClaudeAgent()

  return (
    <div className="container">
      <Header connected={connected} />

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
