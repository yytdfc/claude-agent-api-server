import { useState, useRef, useEffect } from 'react'
import Message from './Message'

function ChatContainer({ sessionInfo, messages, onSendMessage, onDisconnect, onClearSession }) {
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
      {/* Session Info */}
      <div className="session-info">{sessionInfo}</div>

      {/* Messages */}
      <div className="messages">
        {messages.map((msg, index) => (
          <Message key={index} message={msg} />
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
          className="btn btn-primary"
          disabled={sending || !input.trim()}
        >
          {sending ? 'Sending...' : 'Send'}
        </button>
      </div>

      {/* Action Buttons */}
      <div className="chat-actions">
        <button onClick={onClearSession} className="btn btn-secondary">
          New Session
        </button>
        <button onClick={onDisconnect} className="btn btn-secondary">
          Disconnect
        </button>
      </div>
    </div>
  )
}

export default ChatContainer
