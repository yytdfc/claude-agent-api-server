import { useState, useEffect, useRef } from 'react'
import { Folder, File, ChevronRight, ChevronDown, RefreshCw, FolderOpen, Home } from 'lucide-react'
import { createAPIClient } from '../api/client'

function FileBrowser({ serverUrl, currentPath, onPathChange }) {
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedDirs, setExpandedDirs] = useState(new Set())
  const apiClientRef = useRef(null)

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

  const handleDirectoryClick = (item) => {
    if (item.is_directory) {
      onPathChange(item.path)
    }
  }

  const handleParentDirectory = () => {
    if (currentPath && currentPath !== '/' && currentPath !== '.') {
      const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/'
      onPathChange(parentPath)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="file-browser">
      <div className="file-browser-header">
        <div className="file-browser-title">
          <Folder size={16} />
          <span>Files</span>
        </div>
        <button
          className="btn-icon btn-refresh"
          onClick={handleRefresh}
          disabled={loading}
          title="Refresh"
        >
          <RefreshCw size={14} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      <div className="file-browser-path">
        <button
          className="btn-path-segment"
          onClick={() => onPathChange(currentPath)}
          title="Go to home"
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
                onClick={() => handleDirectoryClick(item)}
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
    </div>
  )
}

export default FileBrowser
