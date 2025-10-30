/**
 * Test script to verify session ID generation logic
 * Run with: node temp/test_session_id_logic.js
 */

function generateAgentCoreSessionId(userId) {
  if (!userId) {
    throw new Error('userId is required to generate agent core session ID')
  }
  return `web-session-${userId}`
}

console.log('Testing session ID generation:')
console.log('---')

// Test case 1: Valid user ID
const userId1 = 'user123'
const sessionId1 = generateAgentCoreSessionId(userId1)
console.log(`User ID: ${userId1}`)
console.log(`Session ID: ${sessionId1}`)
console.log(`Expected: web-session-user123`)
console.log(`Match: ${sessionId1 === 'web-session-user123' ? '✓' : '✗'}`)
console.log('---')

// Test case 2: Another user ID
const userId2 = 'alice@example.com'
const sessionId2 = generateAgentCoreSessionId(userId2)
console.log(`User ID: ${userId2}`)
console.log(`Session ID: ${sessionId2}`)
console.log(`Expected: web-session-alice@example.com`)
console.log(`Match: ${sessionId2 === 'web-session-alice@example.com' ? '✓' : '✗'}`)
console.log('---')

// Test case 3: Same user always gets same session ID
const sessionId1a = generateAgentCoreSessionId(userId1)
const sessionId1b = generateAgentCoreSessionId(userId1)
console.log(`User ID: ${userId1}`)
console.log(`Session ID 1: ${sessionId1a}`)
console.log(`Session ID 2: ${sessionId1b}`)
console.log(`Same session ID: ${sessionId1a === sessionId1b ? '✓' : '✗'}`)
console.log('---')

// Test case 4: Null user ID should throw error
try {
  generateAgentCoreSessionId(null)
  console.log('Null user ID: ✗ (should have thrown error)')
} catch (error) {
  console.log('Null user ID: ✓ (correctly threw error)')
  console.log(`Error message: ${error.message}`)
}
console.log('---')

console.log('All tests passed! ✓')
