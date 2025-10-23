/**
 * Claude Agent Web Client - Main Entry Point
 *
 * A web-based client for interacting with the Claude Agent API Server.
 */

import './style.css'
import { ClaudeAgentClient } from './client.js'

// Initialize the client when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ClaudeAgentClient()
})
