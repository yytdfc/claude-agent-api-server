/**
 * Authentication utility functions for token management
 */

import { fetchAuthSession } from 'aws-amplify/auth'

// Token refresh threshold: refresh if token expires in less than 5 minutes
const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000 // 5 minutes in milliseconds

/**
 * Get valid access token, refreshing if necessary
 * @returns {Promise<string|null>} Access token or null if not authenticated
 */
export async function getValidAccessToken() {
  try {
    const session = await fetchAuthSession({ forceRefresh: false })

    if (!session.tokens || !session.tokens.accessToken) {
      return null
    }

    const accessToken = session.tokens.accessToken
    const expiresAt = accessToken.payload.exp * 1000 // Convert to milliseconds
    const now = Date.now()
    const timeUntilExpiry = expiresAt - now

    // If token expires soon, force refresh
    if (timeUntilExpiry < TOKEN_REFRESH_THRESHOLD) {
      console.log('🔄 Access token expiring soon, refreshing...')
      const refreshedSession = await fetchAuthSession({ forceRefresh: true })
      return refreshedSession.tokens?.accessToken?.toString() || null
    }

    return accessToken.toString()
  } catch (error) {
    console.error('Failed to get access token:', error)
    return null
  }
}

/**
 * Get AgentCore session ID from access token
 * Extracts user_id from JWT 'sub' claim and formats as session ID
 * @returns {Promise<string|null>} Session ID or null if not available
 */
export async function getAgentCoreSessionId() {
  try {
    const token = await getValidAccessToken()
    if (!token) {
      return null
    }

    // Decode JWT token (without verification - just parse)
    const parts = token.split('.')
    if (parts.length !== 3) {
      return null
    }

    const payload = JSON.parse(atob(parts[1]))
    const userId = payload.sub

    if (!userId) {
      return null
    }

    // Format: user_id@workspace
    return `${userId}@workspace`
  } catch (error) {
    console.error('Failed to get AgentCore session ID:', error)
    return null
  }
}

/**
 * Create authorization headers for API requests
 * @param {boolean} includeSessionId - Whether to include X-Amzn-Bedrock-AgentCore-Runtime-Session-Id header
 * @returns {Promise<Object>} Headers object with Authorization header and optionally session ID
 */
export async function getAuthHeaders(includeSessionId = false) {
  const token = await getValidAccessToken()

  if (!token) {
    throw new Error('Not authenticated')
  }

  const headers = {
    'Authorization': `Bearer ${token}`
  }

  // Optionally include AgentCore session ID header
  if (includeSessionId) {
    const sessionId = await getAgentCoreSessionId()
    if (sessionId) {
      headers['X-Amzn-Bedrock-AgentCore-Runtime-Session-Id'] = sessionId
    }
  }

  return headers
}

/**
 * Check if error is authentication-related
 * @param {Error} error - Error object
 * @returns {boolean} True if authentication error
 */
export function isAuthError(error) {
  return (
    error.status === 401 ||
    error.statusCode === 401 ||
    error.message?.includes('401') ||
    error.message?.includes('Unauthorized') ||
    error.message?.includes('Not authenticated')
  )
}

/**
 * Global auth error handler - set by App component
 * This will be called when an authentication error is detected
 */
let globalAuthErrorHandler = null

/**
 * Set the global authentication error handler
 * @param {Function} handler - Function to call on auth errors
 */
export function setAuthErrorHandler(handler) {
  globalAuthErrorHandler = handler
}

/**
 * Trigger authentication error handling
 * This will cause the user to be logged out and redirected to login
 */
export function handleAuthError() {
  if (globalAuthErrorHandler) {
    globalAuthErrorHandler()
  } else {
    console.error('Auth error occurred but no handler is registered')
  }
}
