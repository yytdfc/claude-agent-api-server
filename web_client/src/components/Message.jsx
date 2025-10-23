function Message({ message }) {
  const { type, role, content, toolName, toolInput } = message

  const formatContent = (text) => {
    return text
      .replace(/\n/g, '<br>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  }

  if (type === 'system') {
    return (
      <div className="message system">
        <div className="message-content">{content}</div>
      </div>
    )
  }

  if (type === 'error') {
    return (
      <div className="message error">
        <div className="message-content">❌ Error: {content}</div>
      </div>
    )
  }

  if (type === 'tool') {
    return (
      <div className="message tool">
        <div className="message-header">
          <span className="message-icon">🔧</span>
          <span className="message-label">Tool: {toolName}</span>
        </div>
        <div className="message-content">
          <pre>{JSON.stringify(toolInput, null, 2)}</pre>
        </div>
      </div>
    )
  }

  const icon = role === 'user' ? '👤' : '🤖'
  const label = role === 'user' ? 'You' : 'Claude'

  return (
    <div className={`message ${role}`}>
      <div className="message-header">
        <span className="message-icon">{icon}</span>
        <span className="message-label">{label}</span>
      </div>
      <div
        className="message-content"
        dangerouslySetInnerHTML={{ __html: formatContent(content) }}
      />
    </div>
  )
}

export default Message
