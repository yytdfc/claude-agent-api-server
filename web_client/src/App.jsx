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
import { setAuthErrorHandler } from './utils/authUtils'
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

  // Project state
  const [currentProject, setCurrentProject] = useState(null) // null means default workspace
  const [availableProjects, setAvailableProjects] = useState([])
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [showProjectSwitcher, setShowProjectSwitcher] = useState(false)

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
        const apiClient = createAPIClient(settings.serverUrl)
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
        const apiClient = createAPIClient(settings.serverUrl)
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
    const apiClient = createAPIClient(settings.serverUrl)
    const result = await apiClient.createProject(user.userId, projectName)
    console.log(`✅ Created project: ${projectName}`)

    // Reload projects list
    const projects = await apiClient.listProjects(user.userId)
    setAvailableProjects(projects.projects || [])

    // Switch to the new project (this will also update working directory)
    handleProjectChange(projectName)
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
        onSettingsClick={() => setShowSettings(true)}
        user={user}
        onLogout={logout}
        workingDirectory={workingDirectory}
        showTerminal={showTerminal}
        onTerminalToggle={() => setShowTerminal(!showTerminal)}
        currentProject={currentProject}
        onProjectSwitcherOpen={() => setShowProjectSwitcher(true)}
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

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
