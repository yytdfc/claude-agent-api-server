import { useEffect, useState } from 'react'
import { Plus, Circle } from 'lucide-react'

function SessionList({ serverUrl, currentSessionId, onSessionSelect, onNewSession, cwd }) {
  const [sessions, setSessions] = useState([])
  const [activeSessions, setActiveSessions] = useState(new Set())
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!serverUrl) return

    const fetchSessions = async () => {
      setLoading(true)
      try {
        // Fetch available sessions from disk
        const availableUrl = cwd
          ? `${serverUrl}/sessions/available?cwd=${encodeURIComponent(cwd)}`
          : `${serverUrl}/sessions/available`

        const availableResponse = await fetch(availableUrl)
        if (availableResponse.ok) {
          const availableData = await availableResponse.json()
          setSessions(availableData.sessions || [])
        }

        // Fetch active sessions to mark them with indicator
        const activeUrl = cwd
          ? `${serverUrl}/sessions?cwd=${encodeURIComponent(cwd)}`
          : `${serverUrl}/sessions`

        const activeResponse = await fetch(activeUrl)
        if (activeResponse.ok) {
          const activeData = await activeResponse.json()
          const activeIds = new Set(activeData.sessions.map(s => s.session_id))
          setActiveSessions(activeIds)

          // Sort sessions: active first, then by time (newest first)
          setSessions(prev => {
            return [...prev].sort((a, b) => {
              const aIsActive = activeIds.has(a.session_id)
              const bIsActive = activeIds.has(b.session_id)

              // Active sessions always come first
              if (aIsActive && !bIsActive) return -1
              if (!aIsActive && bIsActive) return 1

              // If both active or both inactive, sort by modified time (newest first)
              return new Date(b.modified) - new Date(a.modified)
            })
          })
        }
      } catch (error) {
        console.error('Failed to fetch sessions:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchSessions()
    // Refresh session list every 5 seconds
    const interval = setInterval(fetchSessions, 5000)
    return () => clearInterval(interval)
  }, [serverUrl, cwd])

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)

      if (diffMins < 1) return 'just now'
      if (diffMins < 60) return `${diffMins}m ago`

      const diffHours = Math.floor(diffMins / 60)
      if (diffHours < 24) return `${diffHours}h ago`

      const diffDays = Math.floor(diffHours / 24)
      return `${diffDays}d ago`
    } catch {
      return dateStr
    }
  }

  return (
    <div className="session-list">
      <div className="session-list-header">
        <h2>Sessions</h2>
        <button
          className="btn btn-primary btn-sm"
          onClick={onNewSession}
          title="Create new session"
        >
          <Plus size={16} /> New
        </button>
      </div>

      {loading && sessions.length === 0 ? (
        <div className="session-list-loading">Loading...</div>
      ) : sessions.length === 0 ? (
        <div className="session-list-empty">No sessions found</div>
      ) : (
        <div className="session-list-items">
          {sessions.map((session) => {
            const isActive = activeSessions.has(session.session_id)
            const isCurrentSession = session.session_id === currentSessionId

            return (
              <div
                key={session.session_id}
                className={`session-item ${isCurrentSession ? 'current' : ''}`}
                onClick={() => onSessionSelect(session.session_id)}
              >
                <div className="session-item-header">
                  <div className="session-id-wrapper">
                    {isActive && <Circle size={8} className="active-indicator" fill="currentColor" title="Active session" />}
                    <span className="session-id" title={session.session_id}>
                      {session.session_id.slice(0, 8)}...
                    </span>
                  </div>
                  <span className="session-project" title={session.project}>
                    {session.project}
                  </span>
                </div>
                <div className="session-item-info">
                  <span className="session-preview" title={session.preview}>
                    {session.preview}
                  </span>
                  <span className="session-time" title={session.modified}>
                    {formatDate(session.modified)}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default SessionList
