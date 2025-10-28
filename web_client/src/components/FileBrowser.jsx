import { useState, useEffect, useRef } from 'react'
import { Folder, File, ChevronRight, ChevronDown, RefreshCw, FolderOpen, Home } from 'lucide-react'
import { createAPIClient } from '../api/client'

function FileBrowser({ serverUrl, currentPath, workingDirectory, onPathChange, onFileClick }) {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedDirs, setExpandedDirs] = useState(new Set())
  const [height, setHeight] = useState(300) // Default height in pixels
  const [isResizing, setIsResizing] = useState(false)
  const apiClientRef = useRef(null)
  const resizeRef = useRef(null)

  // Create API client
  useEffect(() => {
    if (serverUrl && (!apiClientRef.current || apiClientRef.current.baseUrl !== serverUrl)) {
      apiClientRef.current = createAPIClient(serverUrl)
    }
  }, [serverUrl])

  // Load files when path changes
  useEffect(() => {
    if (currentPath && apiClientRef.current) {
      loadFiles(currentPath)
    }
  }, [currentPath])

  const loadFiles = async (path) => {
    if (!apiClientRef.current) return

    setLoading(true)
    setError(null)

    try {
      const data = await apiClientRef.current.listFiles(path)
      setFiles(data.items || [])
    } catch (err) {
      console.error('Failed to load files:', err)
      setError(err.message)
      setFiles([])
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    if (currentPath) {
      loadFiles(currentPath)
    }
  }

  const handleItemClick = (item) => {
    if (item.is_directory) {
      onPathChange(item.path)
    } else {
      // It's a file, trigger file preview
      if (onFileClick) {
        onFileClick(item.path)
      }
    }
  }

  const handleParentDirectory = () => {
    if (currentPath && currentPath !== '/' && currentPath !== '.') {
      const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/'
      onPathChange(parentPath)
    }
  }

  const handleResetToWorkingDirectory = () => {
    if (workingDirectory) {
      onPathChange(workingDirectory)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Handle resize
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return

      const newHeight = e.clientY - resizeRef.current.getBoundingClientRect().top
      // Constrain height between 150px and 600px
      if (newHeight >= 150 && newHeight <= 600) {
        setHeight(newHeight)
      }
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ns-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing])

  const handleResizeStart = (e) => {
    e.preventDefault()
    setIsResizing(true)
  }

  return (
    <div className="file-browser" ref={resizeRef} style={{ height: `${height}px` }}>
      <div className="file-browser-header">
        <div className="file-browser-title">
          <Folder size={16} />
          <span>Files</span>
        </div>
        <div className="file-browser-actions">
          <button
            className="btn-icon btn-refresh"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw size={14} className={loading ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      <div className="file-browser-path">
        <button
          className="btn-path-segment"
          onClick={handleResetToWorkingDirectory}
          disabled={!workingDirectory || currentPath === workingDirectory}
          title={`Go to working directory: ${workingDirectory || ''}`}
        >
          <Home size={14} />
        </button>
        {currentPath && currentPath !== '/' && currentPath !== '.' && (
          <button
            className="btn-path-segment"
            onClick={handleParentDirectory}
            title="Parent directory"
          >
            ..
          </button>
        )}
      </div>

      <div className="file-browser-content">
        {error && (
          <div className="file-browser-error">
            <span>{error}</span>
          </div>
        )}

        {loading && files.length === 0 && (
          <div className="file-browser-loading">
            <RefreshCw size={16} className="spinning" />
            <span>Loading...</span>
          </div>
        )}

        {!loading && !error && files.length === 0 && (
          <div className="file-browser-empty">
            <Folder size={32} />
            <span>Empty directory</span>
          </div>
        )}

        {files.length > 0 && (
          <div className="file-list">
            {files.map((item, index) => (
              <div
                key={`${item.path}-${index}`}
                className={`file-item ${item.is_directory ? 'directory' : 'file'}`}
                onClick={() => handleItemClick(item)}
                title={item.path}
              >
                <div className="file-item-icon">
                  {item.is_directory ? (
                    <Folder size={16} />
                  ) : (
                    <File size={16} />
                  )}
                </div>
                <div className="file-item-content">
                  <div className="file-item-name">{item.name}</div>
                  {!item.is_directory && item.size !== null && (
                    <div className="file-item-size">{formatSize(item.size)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div
        className="file-browser-resize-handle"
        onMouseDown={handleResizeStart}
        title="Drag to resize"
      >
        <div className="resize-handle-bar" />
      </div>
    </div>
  )
}

export default FileBrowser
