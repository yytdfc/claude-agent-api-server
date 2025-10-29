/**
 * API Client abstraction layer
 *
 * Supports two modes:
 * 1. Direct mode: Calls REST endpoints directly
 * 2. Invocations mode: Routes all calls through /invocations endpoint
 *
 * Control via environment variable: VITE_USE_INVOCATIONS=true/false
 */

import { getAuthHeaders, isAuthError, handleAuthError } from '../utils/authUtils'

const USE_INVOCATIONS = import.meta.env.VITE_USE_INVOCATIONS === 'true'

/**
 * Helper to handle authentication errors in fetch responses
 */
function handleFetchResponse(response) {
  if (response.status === 401) {
    console.error('🔐 Authentication failed - triggering logout')
    handleAuthError()
    const error = new Error('Authentication required')
    error.status = 401
    throw error
  }
  return response
}

/**
 * Direct API client - calls REST endpoints directly
 */
class DirectAPIClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl
  }

  async healthCheck() {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/health`, {
      headers: authHeaders
    })
    return response.json()
  }

  async createSession(payload) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify(payload)
    })
    handleFetchResponse(response)
    if (!response.ok) {
      throw new Error('Failed to create session')
    }
    return response.json()
  }

  async getSessionStatus(sessionId) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/status`, {
      headers: authHeaders
    })
    return { response, data: response.ok ? await response.json() : null }
  }

  async getSessionHistory(sessionId) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/history`, {
      headers: authHeaders
    })
    return { response, data: response.ok ? await response.json() : null }
  }

  async sendMessage(sessionId, message) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ message })
    })
    handleFetchResponse(response)
    if (!response.ok) {
      throw new Error('Failed to send message')
    }
    return response.json()
  }

  async respondToPermission(sessionId, requestId, allowed, applySuggestions = false) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/permissions/respond`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({
        request_id: requestId,
        allowed: allowed,
        apply_suggestions: applySuggestions
      })
    })
    if (!response.ok) {
      throw new Error('Failed to respond to permission')
    }
    return response.json()
  }

  async deleteSession(sessionId) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: authHeaders
    })
    return response.ok
  }

  async listSessions(cwd = null) {
    const authHeaders = await getAuthHeaders()
    const url = cwd
      ? `${this.baseUrl}/sessions?cwd=${encodeURIComponent(cwd)}`
      : `${this.baseUrl}/sessions`
    const response = await fetch(url, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to list sessions')
    }
    return response.json()
  }

  async listAvailableSessions(cwd = null) {
    const authHeaders = await getAuthHeaders()
    const url = cwd
      ? `${this.baseUrl}/sessions/available?cwd=${encodeURIComponent(cwd)}`
      : `${this.baseUrl}/sessions/available`
    const response = await fetch(url, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to list available sessions')
    }
    return response.json()
  }

  async listFiles(path = '.') {
    const authHeaders = await getAuthHeaders()
    const url = `${this.baseUrl}/files?path=${encodeURIComponent(path)}`
    const response = await fetch(url, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to list files')
    }
    return response.json()
  }

  async getFileInfo(path) {
    const authHeaders = await getAuthHeaders()
    const url = `${this.baseUrl}/files/info?path=${encodeURIComponent(path)}`
    const response = await fetch(url, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to get file info')
    }
    return response.json()
  }

  async saveFile(path, content) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/files/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ path, content })
    })
    if (!response.ok) {
      throw new Error('Failed to save file')
    }
    return response.json()
  }

  async executeShellCommand(command, cwd) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/shell/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ command, cwd })
    })
    if (!response.ok) {
      throw new Error('Failed to execute command')
    }
    return response // Return response for streaming
  }

  async getShellCwd() {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/shell/cwd`, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to get current directory')
    }
    return response.json()
  }

  async setShellCwd(cwd) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/shell/cwd`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ cwd })
    })
    if (!response.ok) {
      throw new Error('Failed to set current directory')
    }
    return response.json()
  }

  async createTerminalSession(payload) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/terminal/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify(payload)
    })
    handleFetchResponse(response)
    if (!response.ok) {
      throw new Error('Failed to create terminal session')
    }
    return response.json()
  }

  async getTerminalOutput(sessionId, seq) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/terminal/sessions/${sessionId}/output?seq=${seq}`, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to get terminal output')
    }
    return response.json()
  }

  async sendTerminalInput(sessionId, data) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/terminal/sessions/${sessionId}/input`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ data })
    })
    if (!response.ok) {
      throw new Error('Failed to send terminal input')
    }
    return response.json()
  }

  async resizeTerminal(sessionId, rows, cols) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/terminal/sessions/${sessionId}/resize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify({ rows, cols })
    })
    if (!response.ok) {
      throw new Error('Failed to resize terminal')
    }
    return response.json()
  }

  async closeTerminalSession(sessionId) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/terminal/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to close terminal session')
    }
    return response.json()
  }

  async getTerminalStatus(sessionId) {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/terminal/sessions/${sessionId}/status`, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to get terminal status')
    }
    return response.json()
  }

  async listTerminalSessions() {
    const authHeaders = await getAuthHeaders()
    const response = await fetch(`${this.baseUrl}/terminal/sessions`, {
      headers: authHeaders
    })
    if (!response.ok) {
      throw new Error('Failed to list terminal sessions')
    }
    return response.json()
  }
}

/**
 * Invocations API client - routes all calls through /invocations
 */
class InvocationsAPIClient {
  constructor(baseUrl, agentCoreSessionId = null) {
    this.baseUrl = baseUrl
    this.agentCoreSessionId = agentCoreSessionId
  }

  /**
   * Set the agent core session ID for all subsequent requests
   * @param {string} sessionId - Agent core session ID
   */
  setAgentCoreSessionId(sessionId) {
    this.agentCoreSessionId = sessionId
  }

  async _invoke(path, method = 'GET', payload = null, pathParams = null) {
    const authHeaders = await getAuthHeaders()
    const body = {
      path,
      method,
    }

    if (payload) {
      body.payload = payload
    }

    if (pathParams) {
      body.path_params = pathParams
    }

    // Build headers with agent core session ID if available
    const headers = {
      'Content-Type': 'application/json',
      ...authHeaders
    }

    if (this.agentCoreSessionId) {
      headers['X-Amzn-Bedrock-AgentCore-Runtime-Session-Id'] = this.agentCoreSessionId
    }

    const response = await fetch(`${this.baseUrl}/invocations`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    })

    handleFetchResponse(response)

    if (!response.ok) {
      const error = new Error(`Invocation failed: ${path}`)
      error.status = response.status
      error.statusText = response.statusText

      // Try to get error details from response
      try {
        const errorData = await response.json()
        error.detail = errorData.detail || errorData.message
      } catch {
        // Ignore JSON parse errors
      }

      throw error
    }

    return response.json()
  }

  async healthCheck() {
    return this._invoke('/health', 'GET')
  }

  async createSession(payload) {
    return this._invoke('/sessions', 'POST', payload)
  }

  async getSessionStatus(sessionId) {
    try {
      const data = await this._invoke(
        '/sessions/{session_id}/status',
        'GET',
        null,
        { session_id: sessionId }
      )
      return { response: { ok: true, status: 200 }, data }
    } catch (error) {
      // Handle 404 case - check status code or error message
      if (error.status === 404 || error.message.includes('404') || error.detail?.includes('not found')) {
        return { response: { ok: false, status: 404 }, data: null }
      }
      throw error
    }
  }

  async getSessionHistory(sessionId) {
    try {
      const data = await this._invoke(
        '/sessions/{session_id}/history',
        'GET',
        null,
        { session_id: sessionId }
      )
      return { response: { ok: true, status: 200 }, data }
    } catch (error) {
      // Return appropriate status code
      const status = error.status || 500
      return { response: { ok: false, status }, data: null }
    }
  }

  async sendMessage(sessionId, message) {
    return this._invoke(
      '/sessions/{session_id}/messages',
      'POST',
      { message },
      { session_id: sessionId }
    )
  }

  async respondToPermission(sessionId, requestId, allowed, applySuggestions = false) {
    return this._invoke(
      '/sessions/{session_id}/permissions/respond',
      'POST',
      {
        request_id: requestId,
        allowed: allowed,
        apply_suggestions: applySuggestions
      },
      { session_id: sessionId }
    )
  }

  async deleteSession(sessionId) {
    try {
      await this._invoke(
        '/sessions/{session_id}',
        'DELETE',
        null,
        { session_id: sessionId }
      )
      return true
    } catch (error) {
      return false
    }
  }

  async listSessions(cwd = null) {
    const payload = cwd ? { cwd } : null
    return this._invoke('/sessions', 'GET', payload)
  }

  async listAvailableSessions(cwd = null) {
    const payload = cwd ? { cwd } : null
    return this._invoke('/sessions/available', 'GET', payload)
  }

  async listFiles(path = '.') {
    return this._invoke('/files', 'GET', { path })
  }

  async getFileInfo(path) {
    return this._invoke('/files/info', 'GET', { path })
  }

  async saveFile(path, content) {
    return this._invoke('/files/save', 'POST', { path, content })
  }

  async executeShellCommand(command, cwd) {
    // For streaming response, we need to handle it specially
    const authHeaders = await getAuthHeaders()
    const body = {
      path: '/shell/execute',
      method: 'POST',
      payload: { command, cwd }
    }

    // Build headers with agent core session ID if available
    const headers = {
      'Content-Type': 'application/json',
      ...authHeaders
    }

    if (this.agentCoreSessionId) {
      headers['X-Amzn-Bedrock-AgentCore-Runtime-Session-Id'] = this.agentCoreSessionId
    }

    const response = await fetch(`${this.baseUrl}/invocations`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      throw new Error('Failed to execute command')
    }

    return response // Return response for streaming
  }

  async getShellCwd() {
    return this._invoke('/shell/cwd', 'GET')
  }

  async setShellCwd(cwd) {
    return this._invoke('/shell/cwd', 'POST', { cwd })
  }

  async createTerminalSession(payload) {
    return this._invoke('/terminal/sessions', 'POST', payload)
  }

  async getTerminalOutput(sessionId, seq) {
    return this._invoke(`/terminal/sessions/${sessionId}/output?seq=${seq}`, 'GET', null, { session_id: sessionId })
  }

  async sendTerminalInput(sessionId, data) {
    return this._invoke('/terminal/sessions/{session_id}/input', 'POST', { data }, { session_id: sessionId })
  }

  async resizeTerminal(sessionId, rows, cols) {
    return this._invoke('/terminal/sessions/{session_id}/resize', 'POST', { rows, cols }, { session_id: sessionId })
  }

  async closeTerminalSession(sessionId) {
    return this._invoke('/terminal/sessions/{session_id}', 'DELETE', null, { session_id: sessionId })
  }

  async getTerminalStatus(sessionId) {
    return this._invoke('/terminal/sessions/{session_id}/status', 'GET', null, { session_id: sessionId })
  }

  async listTerminalSessions() {
    return this._invoke('/terminal/sessions', 'GET')
  }
}

/**
 * Create API client based on configuration
 * @param {string} baseUrl - Base URL for API server
 * @param {string|null} agentCoreSessionId - Optional agent core session ID for invocations mode
 * @returns {DirectAPIClient|InvocationsAPIClient}
 */
export function createAPIClient(baseUrl, agentCoreSessionId = null) {
  if (USE_INVOCATIONS) {
    console.log('🔀 Using Invocations API mode')
    if (agentCoreSessionId) {
      console.log(`🆔 Agent Core Session ID: ${agentCoreSessionId}`)
    }
    return new InvocationsAPIClient(baseUrl, agentCoreSessionId)
  } else {
    console.log('📡 Using Direct API mode')
    return new DirectAPIClient(baseUrl)
  }
}

export { USE_INVOCATIONS }
