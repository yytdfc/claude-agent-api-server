/**
 * API Client abstraction layer
 *
 * Supports two modes:
 * 1. Direct mode: Calls REST endpoints directly
 * 2. Invocations mode: Routes all calls through /invocations endpoint
 *
 * Control via environment variable: VITE_USE_INVOCATIONS=true/false
 */

const USE_INVOCATIONS = import.meta.env.VITE_USE_INVOCATIONS === 'true'

/**
 * Direct API client - calls REST endpoints directly
 */
class DirectAPIClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl
  }

  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/health`)
    return response.json()
  }

  async createSession(payload) {
    const response = await fetch(`${this.baseUrl}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!response.ok) {
      throw new Error('Failed to create session')
    }
    return response.json()
  }

  async getSessionStatus(sessionId) {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/status`)
    return { response, data: response.ok ? await response.json() : null }
  }

  async getSessionHistory(sessionId) {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/history`)
    return { response, data: response.ok ? await response.json() : null }
  }

  async sendMessage(sessionId, message) {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    })
    if (!response.ok) {
      throw new Error('Failed to send message')
    }
    return response.json()
  }

  async respondToPermission(sessionId, requestId, allowed) {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/permissions/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        request_id: requestId,
        allowed: allowed,
        apply_suggestions: false
      })
    })
    if (!response.ok) {
      throw new Error('Failed to respond to permission')
    }
    return response.json()
  }

  async deleteSession(sessionId) {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}`, {
      method: 'DELETE'
    })
    return response.ok
  }

  async listSessions(cwd = null) {
    const url = cwd
      ? `${this.baseUrl}/sessions?cwd=${encodeURIComponent(cwd)}`
      : `${this.baseUrl}/sessions`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error('Failed to list sessions')
    }
    return response.json()
  }

  async listAvailableSessions(cwd = null) {
    const url = cwd
      ? `${this.baseUrl}/sessions/available?cwd=${encodeURIComponent(cwd)}`
      : `${this.baseUrl}/sessions/available`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error('Failed to list available sessions')
    }
    return response.json()
  }

  async listFiles(path = '.') {
    const url = `${this.baseUrl}/files?path=${encodeURIComponent(path)}`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error('Failed to list files')
    }
    return response.json()
  }

  async getFileInfo(path) {
    const url = `${this.baseUrl}/files/info?path=${encodeURIComponent(path)}`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error('Failed to get file info')
    }
    return response.json()
  }
}

/**
 * Invocations API client - routes all calls through /invocations
 */
class InvocationsAPIClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl
  }

  async _invoke(path, method = 'GET', payload = null, pathParams = null) {
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

    const response = await fetch(`${this.baseUrl}/invocations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

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

  async respondToPermission(sessionId, requestId, allowed) {
    return this._invoke(
      '/sessions/{session_id}/permissions/respond',
      'POST',
      {
        request_id: requestId,
        allowed: allowed,
        apply_suggestions: false
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
}

/**
 * Create API client based on configuration
 * @param {string} baseUrl - Base URL for API server
 * @returns {DirectAPIClient|InvocationsAPIClient}
 */
export function createAPIClient(baseUrl) {
  if (USE_INVOCATIONS) {
    console.log('🔀 Using Invocations API mode')
    return new InvocationsAPIClient(baseUrl)
  } else {
    console.log('📡 Using Direct API mode')
    return new DirectAPIClient(baseUrl)
  }
}

export { USE_INVOCATIONS }
