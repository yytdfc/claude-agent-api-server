import { Wrench, CheckCircle, XCircle } from 'lucide-react'

function Message({ message }) {
  const { type, role, content, toolName, toolInput, isError } = message

  const formatContent = (text) => {
    if (!text) return ''
    return text
      .replace(/\n/g, '<br>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  }

  const formatToolContent = (text) => {
    if (!text) return ''
    // Limit tool result display length for readability
    const maxLength = 1000
    if (text.length > maxLength) {
      return text.substring(0, maxLength) + '\n... (truncated)'
    }
    return text
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
        <div className="message-content">
          <XCircle size={16} style={{ display: 'inline', marginRight: '6px' }} />
          Error: {content}
        </div>
      </div>
    )
  }

  if (type === 'tool') {
    return (
      <div className="message tool-use">
        <div className="message-header">
          <Wrench size={16} className="message-icon" />
          <span className="message-label">Tool: {toolName}</span>
        </div>
        <div className="message-content tool-input">
          <pre>{JSON.stringify(toolInput, null, 2)}</pre>
        </div>
      </div>
    )
  }

  if (type === 'tool_result') {
    return (
      <div className={`message tool-result ${isError ? 'error' : 'success'}`}>
        <div className="message-header">
          {isError ? (
            <XCircle size={16} className="message-icon" />
          ) : (
            <CheckCircle size={16} className="message-icon" />
          )}
          <span className="message-label">{isError ? 'Tool Error' : 'Tool Result'}</span>
        </div>
        <div className="message-content tool-output">
          <pre>{formatToolContent(content)}</pre>
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
