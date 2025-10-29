import { useState, useEffect, useCallback, useRef } from 'react'
import { createAPIClient } from '../api/client'
import { generateAgentCoreSessionId } from '../utils/sessionUtils'

// Helper function to format model names
const formatModel = (model) => {
  if (!model) return ''
  // Shorten common model names for better readability
  return model
    .replace('claude-3-5-sonnet-', 'sonnet-')
    .replace('claude-3-5-haiku-', 'haiku-')
    .replace('claude-3-opus-', 'opus-')
}

export function useClaudeAgent(initialServerUrl = 'http://127.0.0.1:8000', userId = null, projectName = null) {
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [sessionInfo, setSessionInfo] = useState('')
  const [messages, setMessages] = useState([])
  const [pendingPermission, setPendingPermission] = useState(null)
  const [serverConnected, setServerConnected] = useState(false) // Backend service connection status
  const [sessionError, setSessionError] = useState(null) // Critical session error state

  const serverUrlRef = useRef(initialServerUrl)
  const configRef = useRef(null)
  const permissionCheckIntervalRef = useRef(null)
  const healthCheckIntervalRef = useRef(null)
  const apiClientRef = useRef(null)
  const agentCoreSessionIdRef = useRef(null)
  const sessionErrorCountRef = useRef(0) // Track consecutive session errors
  const MAX_SESSION_ERRORS = 10 // Stop after 10 consecutive errors

  // Initialize API client when userId or projectName changes
  useEffect(() => {
    if (userId) {
      const newSessionId = generateAgentCoreSessionId(userId, projectName)

      // Only recreate client if session ID changed
      if (agentCoreSessionIdRef.current !== newSessionId) {
        agentCoreSessionIdRef.current = newSessionId
        console.log(`🆔 Generated Agent Core Session ID: ${agentCoreSessionIdRef.current}`)
        apiClientRef.current = createAPIClient(serverUrlRef.current, agentCoreSessionIdRef.current)

        // Reset connection state when project changes
        if (connected) {
          setConnected(false)
          setSessionId(null)
          setMessages([])
          setPendingPermission(null)
          setSessionError(null)
        }
      }
    }
  }, [userId, projectName, connected])

  // Add system message
  const addSystemMessage = useCallback((content) => {
    setMessages(prev => [...prev, { type: 'system', content }])
  }, [])

  // Add error message
  const addErrorMessage = useCallback((content) => {
    setMessages(prev => [...prev, { type: 'error', content }])
  }, [])

  // Check server health
  const checkServerHealth = useCallback(async () => {
    if (!apiClientRef.current) return

    try {
      await apiClientRef.current.healthCheck()
      setServerConnected(true)
    } catch (error) {
      console.warn('Server health check failed:', error)
      setServerConnected(false)
    }
  }, [])

  // Check for pending permissions
  const checkPermissions = useCallback(async () => {
    if (!sessionId || !apiClientRef.current) return

    // Don't check if we've hit the error limit
    if (sessionError) return

    try {
      const { response, data } = await apiClientRef.current.getSessionStatus(sessionId)

      // Handle 404 - Session not found
      if (response.status === 404) {
        sessionErrorCountRef.current += 1
        console.warn(`Session not found (attempt ${sessionErrorCountRef.current}/${MAX_SESSION_ERRORS})`)

        if (sessionErrorCountRef.current >= MAX_SESSION_ERRORS) {
          setSessionError({
            type: 'session_not_found',
            message: 'Session not found after multiple attempts. The session may have expired or been deleted.',
            attemptCount: sessionErrorCountRef.current
          })
          // Stop checking
          return
        }
        return
      }

      // Reset error count on successful response
      if (response.ok && data) {
        sessionErrorCountRef.current = 0

        if (data.pending_permission && !pendingPermission) {
          // Add permission request as a message in the chat
          setMessages(prev => [...prev, {
            type: 'permission',
            permission: data.pending_permission
          }])
          setPendingPermission(data.pending_permission)
        }
      }
    } catch (error) {
      console.error('Permission check error:', error)
      // Don't count non-404 errors toward the limit
    }
  }, [sessionId, pendingPermission, sessionError])

  // Start health check interval (only when page is visible and user is logged in)
  useEffect(() => {
    // Only start health check if user is logged in (apiClient exists)
    if (!apiClientRef.current || !userId) return

    // Start interval if page is currently visible
    const startInterval = () => {
      if (!document.hidden && !healthCheckIntervalRef.current) {
        // Initial check
        checkServerHealth()
        // Then check every 5 seconds
        healthCheckIntervalRef.current = setInterval(checkServerHealth, 5000)
      }
    }

    // Stop interval
    const stopInterval = () => {
      if (healthCheckIntervalRef.current) {
        clearInterval(healthCheckIntervalRef.current)
        healthCheckIntervalRef.current = null
      }
    }

    // Handle visibility change
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopInterval()
      } else {
        startInterval()
      }
    }

    // Start interval and listen for visibility changes
    startInterval()
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      stopInterval()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [userId, checkServerHealth])

  // Start permission checking interval (only when page is visible)
  useEffect(() => {
    if (!connected || !sessionId) return

    // Start interval if page is currently visible
    const startInterval = () => {
      if (!document.hidden && !permissionCheckIntervalRef.current) {
        permissionCheckIntervalRef.current = setInterval(checkPermissions, 1000)
      }
    }

    // Stop interval
    const stopInterval = () => {
      if (permissionCheckIntervalRef.current) {
        clearInterval(permissionCheckIntervalRef.current)
        permissionCheckIntervalRef.current = null
      }
    }

    // Handle visibility change
    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopInterval()
      } else {
        startInterval()
      }
    }

    // Start interval and listen for visibility changes
    startInterval()
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      stopInterval()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [connected, sessionId, checkPermissions])

  // Connect to server
  const connect = useCallback(async (config) => {
    if (!userId) {
      console.error('Cannot connect: userId is required')
      return
    }

    setConnecting(true)
    serverUrlRef.current = config.serverUrl.trim()
    configRef.current = config

    // Generate agent core session ID for this web client session
    agentCoreSessionIdRef.current = generateAgentCoreSessionId(userId)
    console.log(`🆔 Generated Agent Core Session ID: ${agentCoreSessionIdRef.current}`)

    // Create API client with agent core session ID
    apiClientRef.current = createAPIClient(serverUrlRef.current, agentCoreSessionIdRef.current)

    try {
      // Check server health
      await apiClientRef.current.healthCheck()

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
      if (config.cwd.trim()) {
        payload.cwd = config.cwd.trim()
      }

      const data = await apiClientRef.current.createSession(payload)
      setSessionId(data.session_id)
      setConnected(true)

      // Update session info with model and proxy details (without working directory)
      let info = ''
      if (config.model) info += `🤖 ${formatModel(config.model)}`
      if (config.backgroundModel) {
        if (info) info += ' | '
        info += `⚡ ${formatModel(config.backgroundModel)}`
      }
      if (config.enableProxy) {
        if (info) info += ' | '
        info += '🔌 Proxy'
      }
      setSessionInfo(info)

      addSystemMessage('✅ Connected to Claude Agent')
    } catch (error) {
      addErrorMessage(`Connection failed: ${error.message}`)
    } finally {
      setConnecting(false)
    }
  }, [userId, addSystemMessage, addErrorMessage])

  // Disconnect from server
  const disconnect = useCallback(async () => {
    try {
      if (sessionId && apiClientRef.current) {
        await apiClientRef.current.deleteSession(sessionId)
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
      if (sessionId && apiClientRef.current) {
        await apiClientRef.current.deleteSession(sessionId)
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

      const data = await apiClientRef.current.createSession(payload)
      setSessionId(data.session_id)
      setMessages([])
      addSystemMessage('✅ New session started')
    } catch (error) {
      addErrorMessage(`Failed to clear session: ${error.message}`)
    }
  }, [sessionId, addSystemMessage, addErrorMessage])

  // Send message
  const sendMessage = useCallback(async (message) => {
    if (!sessionId || !message.trim() || !apiClientRef.current) return

    try {
      // Add user message to UI
      setMessages(prev => [...prev, { type: 'text', role: 'user', content: message }])

      // Send to API
      const data = await apiClientRef.current.sendMessage(sessionId, message)

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
  const respondToPermission = useCallback(async (requestId, allowed, applySuggestions = false) => {
    if (!apiClientRef.current) return

    try {
      await apiClientRef.current.respondToPermission(sessionId, requestId, allowed, applySuggestions)

      // Remove the permission message from chat and add response
      setMessages(prev => {
        const filtered = prev.filter(msg =>
          msg.type !== 'permission' || msg.permission?.request_id !== requestId
        )
        let responseMessage = allowed ? '✓ Permission granted' : '✗ Permission denied'
        if (applySuggestions) {
          responseMessage = '⚡ Applied suggestions and granted permission'
        }
        return [...filtered, {
          type: 'system',
          content: responseMessage
        }]
      })

      setPendingPermission(null)
    } catch (error) {
      addErrorMessage(`Failed to respond to permission: ${error.message}`)
    }
  }, [sessionId, addErrorMessage])

  // Load existing session
  const loadSession = useCallback(async (existingSessionId, settings = null) => {
    try {
      setConnecting(true)

      // Use provided settings or fall back to configRef
      const config = settings || configRef.current
      if (!config) {
        throw new Error('No configuration available. Please check settings.')
      }

      // Update serverUrl if settings provided
      if (settings) {
        serverUrlRef.current = settings.serverUrl.trim()
        configRef.current = settings

        // Generate agent core session ID if not already set
        if (!agentCoreSessionIdRef.current && userId) {
          agentCoreSessionIdRef.current = generateAgentCoreSessionId(userId)
          console.log(`🆔 Generated Agent Core Session ID: ${agentCoreSessionIdRef.current}`)
        }

        apiClientRef.current = createAPIClient(serverUrlRef.current, agentCoreSessionIdRef.current)
      }

      // Ensure API client exists
      if (!apiClientRef.current) {
        // Generate agent core session ID if not already set
        if (!agentCoreSessionIdRef.current && userId) {
          agentCoreSessionIdRef.current = generateAgentCoreSessionId(userId)
          console.log(`🆔 Generated Agent Core Session ID: ${agentCoreSessionIdRef.current}`)
        }

        apiClientRef.current = createAPIClient(serverUrlRef.current, agentCoreSessionIdRef.current)
      }

      // First, try to get the session's original cwd from history
      let sessionCwd = config.cwd
      try {
        const { response: historyResponse, data: historyData } = await apiClientRef.current.getSessionHistory(existingSessionId)
        if (historyResponse.ok && historyData && historyData.metadata && historyData.metadata.cwd) {
          sessionCwd = historyData.metadata.cwd
        }
      } catch (error) {
        console.warn('Could not fetch session history for cwd:', error)
      }

      // Check session status
      const { response: statusResponse } = await apiClientRef.current.getSessionStatus(existingSessionId)

      // If session doesn't exist (404), create it with resume
      if (statusResponse.status === 404) {
        // Session not active, need to create/resume it
        const payload = {
          resume_session_id: existingSessionId,
          enable_proxy: config.enableProxy
        }
        if (config.model && config.model.trim()) {
          payload.model = config.model.trim()
        }
        if (config.backgroundModel && config.backgroundModel.trim()) {
          payload.background_model = config.backgroundModel.trim()
        }
        // Use the session's original cwd (from history) or fall back to config.cwd
        if (sessionCwd && sessionCwd.trim()) {
          payload.cwd = sessionCwd.trim()
        }

        const createData = await apiClientRef.current.createSession(payload)
        setSessionId(createData.session_id)
        setConnected(true)
      } else if (!statusResponse.ok) {
        throw new Error('Session error')
      } else {
        // Session is already active
        setSessionId(existingSessionId)
        setConnected(true)
      }

      // Try to load message history from disk
      try {
        const { response: historyResponse, data: historyData } = await apiClientRef.current.getSessionHistory(existingSessionId)
        if (historyResponse.ok && historyData) {

          // Convert history messages to UI format and filter out warmup messages
          const historyMessages = historyData.messages.map(msg => {
            // Check if it's a tool message
            if (msg.type === 'tool_use') {
              return {
                type: 'tool',
                toolName: msg.tool_name,
                toolInput: msg.tool_input
              }
            } else if (msg.type === 'tool_result') {
              return {
                type: 'tool_result',
                toolUseId: msg.tool_use_id,
                content: msg.content,
                isError: msg.is_error
              }
            } else {
              // Regular text message
              return {
                type: 'text',
                role: msg.role,
                content: msg.content
              }
            }
          })

          // Filter out the first 2 messages (warmup conversation)
          // These are typically the initial greeting exchange
          const filteredMessages = historyMessages.slice(2)

          setMessages(filteredMessages)

          // Update session info with metadata (without working directory)
          const metadata = historyData.metadata
          let info = ''
          if (config.model) {
            info += `🤖 ${formatModel(config.model)}`
          }
          if (config.backgroundModel) {
            if (info) info += ' | '
            info += `⚡ ${formatModel(config.backgroundModel)}`
          }
          if (metadata.git_branch) {
            if (info) info += ' | '
            info += `🌿 ${metadata.git_branch}`
          }
          setSessionInfo(info)

          addSystemMessage(`✅ Loaded session with ${historyData.message_count} messages`)
        } else {
          // No history available, start fresh
          setMessages([])
          addSystemMessage(`✅ Switched to session ${existingSessionId.slice(0, 8)}...`)

          // Build session info from config (without working directory)
          let info = ''
          if (config.model) info += `🤖 ${formatModel(config.model)}`
          if (config.backgroundModel) {
            if (info) info += ' | '
            info += `⚡ ${formatModel(config.backgroundModel)}`
          }
          setSessionInfo(info)
        }
      } catch (historyError) {
        // History loading failed, start fresh
        console.warn('Failed to load history:', historyError)
        setMessages([])
        addSystemMessage(`✅ Switched to session ${existingSessionId.slice(0, 8)}... (history unavailable)`)

        // Build session info from config (without working directory)
        let info = ''
        if (config.model) info += `🤖 ${formatModel(config.model)}`
        if (config.backgroundModel) {
          if (info) info += ' | '
          info += `⚡ ${formatModel(config.backgroundModel)}`
        }
        setSessionInfo(info)
      }
    } catch (error) {
      addErrorMessage(`Failed to load session: ${error.message}`)
    } finally {
      setConnecting(false)
    }
  }, [userId, addSystemMessage, addErrorMessage])

  // Retry session - reset error state and try to reconnect
  const retrySession = useCallback(async () => {
    console.log('🔄 Retrying session...')

    // Clear error state
    setSessionError(null)
    sessionErrorCountRef.current = 0

    // Try to reconnect with current config
    if (configRef.current) {
      await connect(configRef.current)
    } else {
      addErrorMessage('Cannot retry: No configuration available')
    }
  }, [connect, addErrorMessage])

  return {
    connected,
    connecting,
    sessionId,
    sessionInfo,
    messages,
    pendingPermission,
    serverConnected,
    sessionError,
    serverUrl: serverUrlRef.current,
    connect,
    disconnect,
    clearSession,
    sendMessage,
    respondToPermission,
    loadSession,
    retrySession
  }
}
