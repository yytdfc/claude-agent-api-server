import { useState, useEffect, useRef } from 'react'
import Header from './components/Header'
import ChatContainer from './components/ChatContainer'
import PermissionModal from './components/PermissionModal'
import SessionList from './components/SessionList'
import FileBrowser from './components/FileBrowser'
import FilePreview from './components/FilePreview'
import SettingsModal from './components/SettingsModal'
import TerminalPTY from './components/TerminalPTY'
import Login from './components/Login'
import Signup from './components/Signup'
import ProjectSwitcher from './components/ProjectSwitcher'
import { useClaudeAgent } from './hooks/useClaudeAgent'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { setAuthErrorHandler, getAgentCoreSessionId } from './utils/authUtils'
import { createAPIClient } from './api/client'
import { Loader2 } from 'lucide-react'

const SETTINGS_STORAGE_KEY = 'claude-agent-settings'

const DEFAULT_SETTINGS = {
  serverUrl: 'http://127.0.0.1:8000',
  cwd: '/workspace',
  model: 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',
  backgroundModel: 'global.anthropic.claude-haiku-4-5-20251001-v1:0',
  enableProxy: false
}

function AppContent() {
  const [showSettings, setShowSettings] = useState(false)
  const [authView, setAuthView] = useState('login') // 'login' or 'signup'
  const { user, loading: authLoading, logout } = useAuth()

  // Set up global authentication error handler
  useEffect(() => {
    setAuthErrorHandler(async () => {
      console.warn('🔐 Authentication error detected - logging out user')
      await logout()
    })
  }, [logout])

  // Load settings from localStorage or use defaults
  const [settings, setSettings] = useState(() => {
    try {
      const saved = localStorage.getItem(SETTINGS_STORAGE_KEY)
      if (saved) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
      }
    } catch (error) {
      console.error('Failed to load settings from localStorage:', error)
    }
    return DEFAULT_SETTINGS
  })

  // Store the working directory from settings (configuration, not changed by browsing)
  const [workingDirectory, setWorkingDirectory] = useState(settings.cwd)

  // Separate browsing path from configured working directory
  const [currentBrowsePath, setCurrentBrowsePath] = useState(settings.cwd)

  // File preview state
  const [previewFilePath, setPreviewFilePath] = useState(null)

  // Sidebar width state
  const [sidebarWidth, setSidebarWidth] = useState(300) // Default 300px
  const [isResizingSidebar, setIsResizingSidebar] = useState(false)

  // Terminal state
  const [showTerminal, setShowTerminal] = useState(false)
  const [terminalWidth, setTerminalWidth] = useState(600) // Default 600px
  const [isResizingTerminal, setIsResizingTerminal] = useState(false)

  // Project state - infer from settings.cwd
  const [currentProject, setCurrentProject] = useState(() => {
    // If cwd is /workspace/project_name, extract project_name
    if (settings.cwd.startsWith('/workspace/') && settings.cwd !== '/workspace') {
      const projectName = settings.cwd.replace('/workspace/', '')
      // Only set if it's a simple project name (no further slashes)
      if (projectName && !projectName.includes('/')) {
        return projectName
      }
    }
    return null // Default workspace
  })
  const [availableProjects, setAvailableProjects] = useState([])
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [showProjectSwitcher, setShowProjectSwitcher] = useState(false)

  // GitHub auth state
  const [githubAuthStatus, setGithubAuthStatus] = useState(null) // null | 'success' | 'pending' | 'error'
  const [githubAuthMessage, setGithubAuthMessage] = useState('')

  // Close project state
  const [closingProject, setClosingProject] = useState(false)

  const {
    connected,
    connecting,
    sessionId,
    sessionInfo,
    messages,
    pendingPermission,
    serverConnected,
    sessionError,
    serverUrl,
    connect,
    disconnect,
    clearSession,
    sendMessage,
    respondToPermission,
    loadSession,
    retrySession
  } = useClaudeAgent(settings.serverUrl, user?.userId, currentProject)

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
    } catch (error) {
      console.error('Failed to save settings to localStorage:', error)
    }
  }, [settings])

  // Load available projects when user logs in
  useEffect(() => {
    if (!user?.userId) return

    const loadProjects = async () => {
      setProjectsLoading(true)
      try {
        const agentCoreSessionId = await getAgentCoreSessionId()
        const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
        const result = await apiClient.listProjects(user.userId)
        setAvailableProjects(result.projects || [])
        console.log(`📁 Loaded ${result.projects?.length || 0} projects`)
      } catch (error) {
        console.error('Failed to load projects:', error)
        setAvailableProjects([])
      } finally {
        setProjectsLoading(false)
      }
    }

    loadProjects()
  }, [user?.userId, settings.serverUrl])

  const handleProjectChange = async (projectName) => {
    if (projectName === currentProject) return

    console.log(`📁 Switching to project: ${projectName || 'Default Workspace'}`)

    // Backup current project to S3 before switching (if not default workspace)
    if (currentProject) {
      try {
        console.log(`💾 Backing up current project "${currentProject}" to S3...`)
        const agentCoreSessionId = await getAgentCoreSessionId()
        const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
        const backupResult = await apiClient.backupProject(user.userId, currentProject)

        if (backupResult.status === 'success') {
          console.log(`✅ Backed up ${backupResult.files_synced} files to S3`)
        } else if (backupResult.status === 'skipped') {
          console.log(`⏭️  No files to backup for project "${currentProject}"`)
        }
      } catch (error) {
        console.error(`Failed to backup project "${currentProject}":`, error)
        // Continue with switch even if backup fails
      }
    }

    setCurrentProject(projectName)

    // Update working directory based on project
    const newWorkingDir = projectName ? `/workspace/${projectName}` : '/workspace'
    setWorkingDirectory(newWorkingDir)
    setCurrentBrowsePath(newWorkingDir)

    // IMPORTANT: Update settings.cwd so new sessions use the correct working directory
    setSettings(prev => ({
      ...prev,
      cwd: newWorkingDir
    }))

    console.log(`📂 Working directory changed to: ${newWorkingDir}`)

    // Disconnect current session when switching projects
    if (connected) {
      clearSession()
    }
  }

  const handleCreateProject = async (projectName) => {
    const agentCoreSessionId = await getAgentCoreSessionId()
    const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
    const result = await apiClient.createProject(user.userId, projectName)
    console.log(`✅ Created project: ${projectName}`)

    // Reload projects list
    const projects = await apiClient.listProjects(user.userId)
    setAvailableProjects(projects.projects || [])

    // Switch to the new project (this will also update working directory)
    handleProjectChange(projectName)
  }

  const handleGithubAuth = async () => {
    setGithubAuthStatus('pending')
    setGithubAuthMessage('Requesting GitHub authentication...')

    try {
      const agentCoreSessionId = await getAgentCoreSessionId()
      const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
      const result = await apiClient.getGithubToken()

      console.log('GitHub auth result:', result)

      // Check if we got an access token and gh auth was successful
      if (result.access_token) {
        if (result.gh_auth?.status === 'success') {
          setGithubAuthStatus('success')
          setGithubAuthMessage('GitHub authentication successful!')
          console.log('✅ GitHub authenticated successfully')
        } else if (result.gh_auth?.status === 'skipped') {
          setGithubAuthStatus('success')
          setGithubAuthMessage('GitHub token obtained (gh CLI not installed)')
          console.log('⚠️  GitHub token obtained but gh CLI not installed')
        } else {
          setGithubAuthStatus('error')
          setGithubAuthMessage(`GitHub CLI auth failed: ${result.gh_auth?.message || 'Unknown error'}`)
          console.error('GitHub CLI authentication failed:', result.gh_auth)
        }
      } else if (result.authorization_url) {
        // Need user to complete authorization
        setGithubAuthStatus('pending')
        setGithubAuthMessage('Opening authorization page...')
        console.log('🔗 Opening GitHub authorization URL:', result.authorization_url)
        window.open(result.authorization_url, '_blank')
      } else if (result.session_status === 'FAILED') {
        setGithubAuthStatus('error')
        setGithubAuthMessage('GitHub authorization failed')
        console.error('GitHub authorization failed')
      } else {
        setGithubAuthStatus('error')
        setGithubAuthMessage('Unexpected response from server')
        console.error('Unexpected GitHub auth response:', result)
      }
    } catch (error) {
      setGithubAuthStatus('error')
      setGithubAuthMessage(`Failed to authenticate: ${error.message}`)
      console.error('GitHub auth error:', error)
    }

    // Clear status after 5 seconds
    setTimeout(() => {
      setGithubAuthStatus(null)
      setGithubAuthMessage('')
    }, 5000)
  }

  const handleCloseProject = async () => {
    if (!connected) {
      console.warn('No active session to close')
      return
    }

    const projectName = currentProject || 'Default Workspace'
    if (!window.confirm(`Close "${projectName}"?\n\nThis will stop the AgentCore session.`)) {
      return
    }

    setClosingProject(true)
    console.log(`🛑 Closing session: ${projectName}`)

    try {
      const agentCoreSessionId = await getAgentCoreSessionId()
      const apiClient = createAPIClient(settings.serverUrl, agentCoreSessionId)
      await apiClient.stopAgentCoreSession('DEFAULT')

      console.log(`✅ Session "${projectName}" closed successfully`)

      // Disconnect current session
      disconnect()

      // If closing a specific project, switch back to default workspace
      if (currentProject) {
        setCurrentProject(null)
        const newSettings = { ...settings, cwd: '/workspace' }
        setSettings(newSettings)
        setWorkingDirectory('/workspace')
        setCurrentBrowsePath('/workspace')
      }
    } catch (error) {
      console.error('Failed to close session:', error)
      alert(`Failed to close session: ${error.message}`)
    } finally {
      setClosingProject(false)
    }
  }

  const handleNewSession = () => {
    if (connected) {
      clearSession()
    } else {
      // Auto-connect with current settings
      connect(settings)
    }
  }

  const handleSaveSettings = (newSettings) => {
    setSettings(newSettings)
    // Update working directory when settings change
    setWorkingDirectory(newSettings.cwd)
    // Also update current browse path to match new working directory
    setCurrentBrowsePath(newSettings.cwd)
  }

  const handleSessionSelect = async (sessionId) => {
    // Load session with current settings
    await loadSession(sessionId, settings)
  }

  const handleBrowsePathChange = (newPath) => {
    // Only change the browsing path, don't modify settings
    setCurrentBrowsePath(newPath)
  }

  const handleFileClick = (filePath) => {
    setPreviewFilePath(filePath)
  }

  const handleClosePreview = () => {
    setPreviewFilePath(null)
  }

  // Handle sidebar resize
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizingSidebar) return

      const newWidth = e.clientX
      // Constrain width between 200px and 600px
      if (newWidth >= 200 && newWidth <= 600) {
        setSidebarWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsResizingSidebar(false)
    }

    if (isResizingSidebar) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingSidebar])

  const handleResizeStart = (e) => {
    e.preventDefault()
    setIsResizingSidebar(true)
  }

  // Handle terminal resize
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizingTerminal) return

      const newWidth = window.innerWidth - e.clientX
      // Constrain width between 400px and 1000px
      if (newWidth >= 400 && newWidth <= 1000) {
        setTerminalWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsResizingTerminal(false)
    }

    if (isResizingTerminal) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingTerminal])

  const handleTerminalResizeStart = (e) => {
    e.preventDefault()
    setIsResizingTerminal(true)
  }

  // Show loading spinner during auth check
  if (authLoading) {
    return (
      <div className="auth-loading">
        <Loader2 size={48} className="spinning" />
        <p>Loading...</p>
      </div>
    )
  }

  // Show auth screens if not logged in
  if (!user) {
    if (authView === 'signup') {
      return <Signup onSwitchToLogin={() => setAuthView('login')} />
    }
    return <Login onSwitchToSignup={() => setAuthView('signup')} />
  }

  // Main app content (user is authenticated)
  return (
    <div className="app-layout">
      <Header
        serverConnected={serverConnected}
        connected={connected}
        onSettingsClick={() => setShowSettings(true)}
        user={user}
        onLogout={logout}
        workingDirectory={workingDirectory}
        showTerminal={showTerminal}
        onTerminalToggle={() => setShowTerminal(!showTerminal)}
        currentProject={currentProject}
        onProjectSwitcherOpen={() => setShowProjectSwitcher(true)}
        onGithubAuthClick={handleGithubAuth}
        githubAuthStatus={githubAuthStatus}
        githubAuthMessage={githubAuthMessage}
        onCloseProject={handleCloseProject}
        closingProject={closingProject}
      />

      <div className="main-content">
        <aside className="sidebar" style={{ width: `${sidebarWidth}px` }}>
          <FileBrowser
            serverUrl={settings.serverUrl}
            currentPath={currentBrowsePath}
            workingDirectory={workingDirectory}
            onPathChange={handleBrowsePathChange}
            onFileClick={handleFileClick}
            refreshTrigger={messages.length}
          />
          <SessionList
            serverUrl={settings.serverUrl}
            currentSessionId={sessionId}
            onSessionSelect={handleSessionSelect}
            onNewSession={handleNewSession}
            cwd={settings.cwd}
          />
          <div
            className="sidebar-resize-handle"
            onMouseDown={handleResizeStart}
            title="Drag to resize sidebar"
          >
            <div className="resize-handle-bar-vertical" />
          </div>
        </aside>

        <main className="content-area">
          {!connected ? (
            <div className="welcome-screen">
              <div className="welcome-content">
                <h2>Welcome to Claude Agent</h2>
                <p>Select a session from the sidebar or create a new one to get started.</p>
                <p className="welcome-hint">
                  Configure settings using the ⚙️ button in the top-right corner.
                </p>
              </div>
            </div>
          ) : (
            <ChatContainer
              sessionInfo={sessionInfo}
              messages={messages}
              onSendMessage={sendMessage}
              onDisconnect={disconnect}
              onClearSession={clearSession}
              onPermissionRespond={respondToPermission}
              sessionError={sessionError}
              onRetrySession={retrySession}
            />
          )}
        </main>

        {previewFilePath && (
          <aside className="preview-panel">
            <FilePreview
              serverUrl={settings.serverUrl}
              filePath={previewFilePath}
              onClose={handleClosePreview}
            />
          </aside>
        )}

        {showTerminal && (
          <aside className="terminal-panel" style={{ width: `${terminalWidth}px` }}>
            <div
              className="terminal-resize-handle"
              onMouseDown={handleTerminalResizeStart}
              title="Drag to resize terminal"
            >
              <div className="resize-handle-bar-vertical" />
            </div>
            <TerminalPTY
              serverUrl={settings.serverUrl}
              initialCwd={workingDirectory}
              onClose={() => setShowTerminal(false)}
            />
          </aside>
        )}
      </div>

      {showSettings && (
        <SettingsModal
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
          settings={settings}
          onSave={handleSaveSettings}
        />
      )}

      {showProjectSwitcher && (
        <ProjectSwitcher
          isOpen={showProjectSwitcher}
          onClose={() => setShowProjectSwitcher(false)}
          projects={availableProjects}
          currentProject={currentProject}
          onProjectChange={handleProjectChange}
          onCreateProject={handleCreateProject}
          hasActiveSession={connected}
        />
      )}
    </div>
  )
}

export default function App() {
  return <AppContent />
}
