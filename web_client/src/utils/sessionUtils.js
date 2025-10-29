/**
 * Session utility functions for agent core session management
 */

/**
 * Generate a UUID v4
 * @returns {string} UUID v4 string
 */
function generateUUID() {
  // Use crypto.randomUUID if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }

  // Fallback implementation for older browsers
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/**
 * Generate agent core session ID based on user ID
 * Format: "web-session-{userId}" for consistent user sessions
 * @param {string} userId - User ID from authentication
 * @returns {string} Agent core session ID
 */
export function generateAgentCoreSessionId(userId) {
  if (!userId) {
    throw new Error('userId is required to generate agent core session ID')
  }
  return `web-session-${userId}`
}

/**
 * Validate agent core session ID format
 * @param {string} sessionId - Session ID to validate
 * @returns {boolean} True if valid format
 */
export function isValidAgentCoreSessionId(sessionId) {
  if (!sessionId || typeof sessionId !== 'string') {
    return false
  }

  // Check format: prefix-uuid (where uuid is 36 characters)
  // Total length should be around 48-50 characters
  return sessionId.length >= 40 && sessionId.includes('-')
}
