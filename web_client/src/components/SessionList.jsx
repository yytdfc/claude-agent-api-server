import { useEffect, useState } from 'react'

function SessionList({ serverUrl, currentSessionId, onSessionSelect, onNewSession }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!serverUrl) return

    const fetchSessions = async () => {
      setLoading(true)
      try {
        const response = await fetch(`${serverUrl}/sessions`)
        if (response.ok) {
          const data = await response.json()
          setSessions(data.sessions || [])
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
  }, [serverUrl])

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
          + New
        </button>
      </div>

      {loading && sessions.length === 0 ? (
        <div className="session-list-loading">Loading...</div>
      ) : sessions.length === 0 ? (
        <div className="session-list-empty">No active sessions</div>
      ) : (
        <div className="session-list-items">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              className={`session-item ${session.session_id === currentSessionId ? 'active' : ''}`}
              onClick={() => onSessionSelect(session.session_id)}
            >
              <div className="session-item-header">
                <span className="session-id" title={session.session_id}>
                  {session.session_id.slice(0, 8)}...
                </span>
                <span className={`session-status status-${session.status}`}>
                  {session.status}
                </span>
              </div>
              <div className="session-item-info">
                <span className="session-messages">
                  {session.message_count} message{session.message_count !== 1 ? 's' : ''}
                </span>
                <span className="session-time" title={session.last_activity}>
                  {formatDate(session.last_activity)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SessionList
