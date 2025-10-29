import { useState, useRef, useEffect } from 'react'
import { Send, X, Loader2, AlertTriangle, RefreshCw } from 'lucide-react'
import Message from './Message'

function ChatContainer({ sessionInfo, messages, onSendMessage, onDisconnect, onClearSession, onPermissionRespond, sessionError, onRetrySession }) {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || sending) return

    setSending(true)
    try {
      await onSendMessage(input)
      setInput('')
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="chat-container">
      {/* Header with Session Info and Close Button */}
      <div className="chat-header">
        <div className="session-info">{sessionInfo}</div>
        <button
          onClick={onDisconnect}
          className="btn-icon btn-close-session"
          title="Close Session"
        >
          <X size={18} />
        </button>
      </div>

      {/* Error Banner */}
      {sessionError && (
        <div className="session-error-banner">
          <div className="error-banner-icon">
            <AlertTriangle size={20} />
          </div>
          <div className="error-banner-content">
            <div className="error-banner-title">Session Error</div>
            <div className="error-banner-message">{sessionError.message}</div>
            <div className="error-banner-details">
              Attempted {sessionError.attemptCount} times without success.
            </div>
          </div>
          <button
            onClick={onRetrySession}
            className="btn btn-primary error-banner-retry"
            title="Retry connecting to session"
          >
            <RefreshCw size={16} />
            Retry
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="messages">
        {messages.map((msg, index) => (
          <Message key={index} message={msg} onPermissionRespond={onPermissionRespond} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message here... (Press Enter to send, Shift+Enter for new line)"
          rows="3"
          disabled={sending}
        />
        <button
          onClick={handleSubmit}
          className="btn-icon btn-send"
          disabled={sending || !input.trim()}
          title={sending ? 'Sending...' : 'Send message'}
        >
          {sending ? <Loader2 size={20} className="spinning" /> : <Send size={20} />}
        </button>
      </div>
    </div>
  )
}

export default ChatContainer
