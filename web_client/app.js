/**
 * Claude Agent Web Client
 *
 * A web-based client for interacting with the Claude Agent API Server.
 */

class ClaudeAgentClient {
    constructor() {
        this.serverUrl = 'http://127.0.0.1:8000';
        this.sessionId = null;
        this.permissionCheckInterval = null;
        this.pendingPermission = null;

        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        // Config panel
        this.configPanel = document.getElementById('configPanel');
        this.serverUrlInput = document.getElementById('serverUrl');
        this.modelInput = document.getElementById('model');
        this.backgroundModelInput = document.getElementById('backgroundModel');
        this.enableProxyCheckbox = document.getElementById('enableProxy');
        this.connectBtn = document.getElementById('connectBtn');
        this.disconnectBtn = document.getElementById('disconnectBtn');
        this.clearSessionBtn = document.getElementById('clearSessionBtn');

        // Chat container
        this.chatContainer = document.getElementById('chatContainer');
        this.messagesDiv = document.getElementById('messages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.sessionInfo = document.getElementById('sessionInfo');

        // Connection status
        this.connectionStatus = document.getElementById('connectionStatus');

        // Permission modal
        this.permissionModal = document.getElementById('permissionModal');
        this.permissionDetails = document.getElementById('permissionDetails');
        this.allowBtn = document.getElementById('allowBtn');
        this.denyBtn = document.getElementById('denyBtn');
    }

    attachEventListeners() {
        this.connectBtn.addEventListener('click', () => this.connect());
        this.disconnectBtn.addEventListener('click', () => this.disconnect());
        this.clearSessionBtn.addEventListener('click', () => this.clearSession());
        this.sendBtn.addEventListener('click', () => this.sendMessage());

        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.allowBtn.addEventListener('click', () => this.respondToPermission(true));
        this.denyBtn.addEventListener('click', () => this.respondToPermission(false));
    }

    async connect() {
        try {
            this.serverUrl = this.serverUrlInput.value.trim();

            // Check server health
            const healthResponse = await fetch(`${this.serverUrl}/health`);
            if (!healthResponse.ok) {
                throw new Error('Server is not healthy');
            }

            // Create session
            const payload = {
                enable_proxy: this.enableProxyCheckbox.checked
            };

            if (this.modelInput.value.trim()) {
                payload.model = this.modelInput.value.trim();
            }

            if (this.backgroundModelInput.value.trim()) {
                payload.background_model = this.backgroundModelInput.value.trim();
            }

            const response = await fetch(`${this.serverUrl}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error('Failed to create session');
            }

            const data = await response.json();
            this.sessionId = data.session_id;

            this.updateConnectionStatus(true);
            this.showChatInterface();
            this.updateSessionInfo(payload);
            this.startPermissionCheck();

            this.addSystemMessage('✅ Connected to Claude Agent');
        } catch (error) {
            this.showError(`Connection failed: ${error.message}`);
        }
    }

    async disconnect() {
        try {
            if (this.sessionId) {
                await fetch(`${this.serverUrl}/sessions/${this.sessionId}`, {
                    method: 'DELETE'
                });
            }

            this.stopPermissionCheck();
            this.sessionId = null;
            this.updateConnectionStatus(false);
            this.showConfigPanel();
            this.messagesDiv.innerHTML = '';
        } catch (error) {
            console.error('Disconnect error:', error);
        }
    }

    async clearSession() {
        try {
            // Close current session
            await fetch(`${this.serverUrl}/sessions/${this.sessionId}`, {
                method: 'DELETE'
            });

            // Create new session with same settings
            const payload = {
                enable_proxy: this.enableProxyCheckbox.checked
            };

            if (this.modelInput.value.trim()) {
                payload.model = this.modelInput.value.trim();
            }

            if (this.backgroundModelInput.value.trim()) {
                payload.background_model = this.backgroundModelInput.value.trim();
            }

            const response = await fetch(`${this.serverUrl}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            this.sessionId = data.session_id;

            this.messagesDiv.innerHTML = '';
            this.addSystemMessage('✅ New session started');
        } catch (error) {
            this.showError(`Failed to clear session: ${error.message}`);
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        try {
            // Clear input
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';

            // Add user message to UI
            this.addMessage('user', message);

            // Disable send button
            this.sendBtn.disabled = true;
            this.sendBtn.textContent = 'Sending...';

            // Send to API
            const response = await fetch(`${this.serverUrl}/sessions/${this.sessionId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            const data = await response.json();

            // Process response messages
            for (const msg of data.messages) {
                if (msg.type === 'text') {
                    this.addMessage('assistant', msg.content);
                } else if (msg.type === 'tool_use') {
                    this.addToolUse(msg.tool_name, msg.tool_input);
                }
            }

            // Show cost if available
            if (data.cost_usd !== null) {
                this.addSystemMessage(`💰 Cost: $${data.cost_usd.toFixed(4)}`);
            }
        } catch (error) {
            this.showError(`Failed to send message: ${error.message}`);
        } finally {
            // Re-enable send button
            this.sendBtn.disabled = false;
            this.sendBtn.textContent = 'Send';
        }
    }

    async checkPermissions() {
        try {
            const response = await fetch(`${this.serverUrl}/sessions/${this.sessionId}/status`);
            if (!response.ok) return;

            const data = await response.json();

            if (data.pending_permission && !this.pendingPermission) {
                this.pendingPermission = data.pending_permission;
                this.showPermissionDialog(data.pending_permission);
            }
        } catch (error) {
            console.error('Permission check error:', error);
        }
    }

    async respondToPermission(allowed) {
        try {
            await fetch(`${this.serverUrl}/sessions/${this.sessionId}/permissions/respond`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    request_id: this.pendingPermission.request_id,
                    allowed: allowed,
                    apply_suggestions: false
                })
            });

            this.hidePermissionDialog();
            this.pendingPermission = null;
        } catch (error) {
            this.showError(`Failed to respond to permission: ${error.message}`);
        }
    }

    showPermissionDialog(permission) {
        this.permissionDetails.innerHTML = `
            <div class="permission-info">
                <p><strong>Tool:</strong> ${permission.tool_name}</p>
                <p><strong>Input:</strong></p>
                <pre>${JSON.stringify(permission.tool_input, null, 2)}</pre>
            </div>
        `;
        this.permissionModal.style.display = 'flex';
    }

    hidePermissionDialog() {
        this.permissionModal.style.display = 'none';
    }

    startPermissionCheck() {
        this.permissionCheckInterval = setInterval(() => this.checkPermissions(), 1000);
    }

    stopPermissionCheck() {
        if (this.permissionCheckInterval) {
            clearInterval(this.permissionCheckInterval);
            this.permissionCheckInterval = null;
        }
    }

    updateConnectionStatus(connected) {
        const statusDot = this.connectionStatus.querySelector('.status-dot');
        const statusText = this.connectionStatus.querySelector('.status-text');

        if (connected) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusText.textContent = 'Disconnected';
        }
    }

    showConfigPanel() {
        this.configPanel.style.display = 'block';
        this.chatContainer.style.display = 'none';
        this.connectBtn.style.display = 'inline-block';
        this.disconnectBtn.style.display = 'none';
        this.clearSessionBtn.style.display = 'none';
    }

    showChatInterface() {
        this.configPanel.style.display = 'none';
        this.chatContainer.style.display = 'flex';
        this.connectBtn.style.display = 'none';
        this.disconnectBtn.style.display = 'inline-block';
        this.clearSessionBtn.style.display = 'inline-block';
    }

    updateSessionInfo(config) {
        let info = '📋 Session: ';
        if (config.model) {
            info += `Main: ${config.model}`;
        }
        if (config.background_model) {
            info += `, Background: ${config.background_model}`;
        }
        if (config.enable_proxy) {
            info += ' (Proxy Mode)';
        }
        this.sessionInfo.textContent = info;
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const icon = role === 'user' ? '👤' : '🤖';
        const label = role === 'user' ? 'You' : 'Claude';

        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-icon">${icon}</span>
                <span class="message-label">${label}</span>
            </div>
            <div class="message-content">${this.formatContent(content)}</div>
        `;

        this.messagesDiv.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addToolUse(toolName, toolInput) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message tool';

        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-icon">🔧</span>
                <span class="message-label">Tool: ${toolName}</span>
            </div>
            <div class="message-content">
                <pre>${JSON.stringify(toolInput, null, 2)}</pre>
            </div>
        `;

        this.messagesDiv.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addSystemMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system';
        messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
        this.messagesDiv.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message error';
        errorDiv.innerHTML = `
            <div class="message-content">
                ❌ Error: ${message}
            </div>
        `;
        this.messagesDiv.appendChild(errorDiv);
        this.scrollToBottom();
    }

    formatContent(content) {
        // Simple markdown-like formatting
        return content
            .replace(/\n/g, '<br>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    }

    scrollToBottom() {
        this.messagesDiv.scrollTop = this.messagesDiv.scrollHeight;
    }
}

// Initialize the client when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ClaudeAgentClient();
});
