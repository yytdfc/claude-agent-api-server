import { useState, useEffect, useCallback, useRef } from 'react'

export function useClaudeAgent() {
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [sessionInfo, setSessionInfo] = useState('')
  const [messages, setMessages] = useState([])
  const [pendingPermission, setPendingPermission] = useState(null)

  const serverUrlRef = useRef('http://127.0.0.1:8000')
  const configRef = useRef(null)
  const permissionCheckIntervalRef = useRef(null)

  // Add system message
  const addSystemMessage = useCallback((content) => {
    setMessages(prev => [...prev, { type: 'system', content }])
  }, [])

  // Add error message
  const addErrorMessage = useCallback((content) => {
    setMessages(prev => [...prev, { type: 'error', content }])
  }, [])

  // Check for pending permissions
  const checkPermissions = useCallback(async () => {
    if (!sessionId) return

    try {
      const response = await fetch(`${serverUrlRef.current}/sessions/${sessionId}/status`)
      if (!response.ok) return

      const data = await response.json()
      if (data.pending_permission && !pendingPermission) {
        setPendingPermission(data.pending_permission)
      }
    } catch (error) {
      console.error('Permission check error:', error)
    }
  }, [sessionId, pendingPermission])

  // Start permission checking interval
  useEffect(() => {
    if (connected && sessionId) {
      permissionCheckIntervalRef.current = setInterval(checkPermissions, 1000)
    }
    return () => {
      if (permissionCheckIntervalRef.current) {
        clearInterval(permissionCheckIntervalRef.current)
      }
    }
  }, [connected, sessionId, checkPermissions])

  // Connect to server
  const connect = useCallback(async (config) => {
    setConnecting(true)
    serverUrlRef.current = config.serverUrl.trim()
    configRef.current = config

    try {
      // Check server health
      const healthResponse = await fetch(`${serverUrlRef.current}/health`)
      if (!healthResponse.ok) {
        throw new Error('Server is not healthy')
      }

      // Create session
      const payload = {
        enable_proxy: config.enableProxy
      }
      if (config.model.trim()) {
        payload.model = config.model.trim()
      }
      if (config.backgroundModel.trim()) {
        payload.background_model = config.backgroundModel.trim()
      }

      const response = await fetch(`${serverUrlRef.current}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        throw new Error('Failed to create session')
      }

      const data = await response.json()
      setSessionId(data.session_id)
      setConnected(true)

      // Update session info
      let info = '📋 Session: '
      if (config.model) info += `Main: ${config.model}`
      if (config.backgroundModel) info += `, Background: ${config.backgroundModel}`
      if (config.enableProxy) info += ' (Proxy Mode)'
      setSessionInfo(info)

      addSystemMessage('✅ Connected to Claude Agent')
    } catch (error) {
      addErrorMessage(`Connection failed: ${error.message}`)
    } finally {
      setConnecting(false)
    }
  }, [addSystemMessage, addErrorMessage])

  // Disconnect from server
  const disconnect = useCallback(async () => {
    try {
      if (sessionId) {
        await fetch(`${serverUrlRef.current}/sessions/${sessionId}`, {
          method: 'DELETE'
        })
      }
    } catch (error) {
      console.error('Disconnect error:', error)
    } finally {
      setSessionId(null)
      setConnected(false)
      setMessages([])
      setPendingPermission(null)
    }
  }, [sessionId])

  // Clear session and create new one
  const clearSession = useCallback(async () => {
    try {
      // Close current session
      if (sessionId) {
        await fetch(`${serverUrlRef.current}/sessions/${sessionId}`, {
          method: 'DELETE'
        })
      }

      // Create new session with same config
      const config = configRef.current
      const payload = {
        enable_proxy: config.enableProxy
      }
      if (config.model.trim()) {
        payload.model = config.model.trim()
      }
      if (config.backgroundModel.trim()) {
        payload.background_model = config.backgroundModel.trim()
      }

      const response = await fetch(`${serverUrlRef.current}/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const data = await response.json()
      setSessionId(data.session_id)
      setMessages([])
      addSystemMessage('✅ New session started')
    } catch (error) {
      addErrorMessage(`Failed to clear session: ${error.message}`)
    }
  }, [sessionId, addSystemMessage, addErrorMessage])

  // Send message
  const sendMessage = useCallback(async (message) => {
    if (!sessionId || !message.trim()) return

    try {
      // Add user message to UI
      setMessages(prev => [...prev, { type: 'text', role: 'user', content: message }])

      // Send to API
      const response = await fetch(`${serverUrlRef.current}/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()

      // Process response messages
      const newMessages = []
      for (const msg of data.messages) {
        if (msg.type === 'text') {
          newMessages.push({ type: 'text', role: 'assistant', content: msg.content })
        } else if (msg.type === 'tool_use') {
          newMessages.push({
            type: 'tool',
            toolName: msg.tool_name,
            toolInput: msg.tool_input
          })
        }
      }
      setMessages(prev => [...prev, ...newMessages])

      // Show cost if available
      if (data.cost_usd !== null) {
        addSystemMessage(`💰 Cost: $${data.cost_usd.toFixed(4)}`)
      }
    } catch (error) {
      addErrorMessage(`Failed to send message: ${error.message}`)
    }
  }, [sessionId, addSystemMessage, addErrorMessage])

  // Respond to permission request
  const respondToPermission = useCallback(async (requestId, allowed) => {
    try {
      await fetch(`${serverUrlRef.current}/sessions/${sessionId}/permissions/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: requestId,
          allowed: allowed,
          apply_suggestions: false
        })
      })
      setPendingPermission(null)
    } catch (error) {
      addErrorMessage(`Failed to respond to permission: ${error.message}`)
    }
  }, [sessionId, addErrorMessage])

  // Load existing session
  const loadSession = useCallback(async (existingSessionId) => {
    try {
      setConnecting(true)

      // Check session status
      const statusResponse = await fetch(`${serverUrlRef.current}/sessions/${existingSessionId}/status`)
      if (!statusResponse.ok) {
        throw new Error('Session not found or inactive')
      }

      const statusData = await statusResponse.json()

      // Set session as current
      setSessionId(existingSessionId)
      setConnected(true)

      // Load messages (if available)
      // Note: API doesn't provide message history endpoint, so start fresh
      setMessages([])
      addSystemMessage(`✅ Switched to session ${existingSessionId.slice(0, 8)}...`)

      // Update session info
      setSessionInfo(`📋 Session: ${existingSessionId.slice(0, 8)}... (${statusData.message_count} messages)`)
    } catch (error) {
      addErrorMessage(`Failed to load session: ${error.message}`)
    } finally {
      setConnecting(false)
    }
  }, [addSystemMessage, addErrorMessage])

  return {
    connected,
    connecting,
    sessionId,
    sessionInfo,
    messages,
    pendingPermission,
    serverUrl: serverUrlRef.current,
    connect,
    disconnect,
    clearSession,
    sendMessage,
    respondToPermission,
    loadSession
  }
}
