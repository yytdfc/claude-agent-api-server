import { useState, useEffect, useRef } from 'react'
import { File, X, FileText, Calendar, HardDrive, AlertCircle, Loader2 } from 'lucide-react'
import { createAPIClient } from '../api/client'

function FilePreview({ serverUrl, filePath, onClose }) {
  const [fileInfo, setFileInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const apiClientRef = useRef(null)

  // Create API client
  useEffect(() => {
    if (serverUrl && (!apiClientRef.current || apiClientRef.current.baseUrl !== serverUrl)) {
      apiClientRef.current = createAPIClient(serverUrl)
    }
  }, [serverUrl])

  // Load file info when filePath changes
  useEffect(() => {
    if (filePath && apiClientRef.current) {
      loadFileInfo(filePath)
    }
  }, [filePath])

  const loadFileInfo = async (path) => {
    if (!apiClientRef.current) return

    setLoading(true)
    setError(null)

    try {
      const data = await apiClientRef.current.getFileInfo(path)
      setFileInfo(data)
    } catch (err) {
      console.error('Failed to load file info:', err)
      setError(err.message)
      setFileInfo(null)
    } finally {
      setLoading(false)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Unknown'
    const date = new Date(timestamp * 1000)
    return date.toLocaleString()
  }

  if (!filePath) {
    return (
      <div className="file-preview">
        <div className="file-preview-empty">
          <File size={48} />
          <p>Select a file to preview</p>
        </div>
      </div>
    )
  }

  return (
    <div className="file-preview">
      <div className="file-preview-header">
        <div className="file-preview-title">
          <FileText size={16} />
          <span>File Preview</span>
        </div>
        <button className="btn-icon" onClick={onClose} title="Close preview">
          <X size={18} />
        </button>
      </div>

      {loading && (
        <div className="file-preview-loading">
          <Loader2 size={32} className="spinning" />
          <p>Loading file...</p>
        </div>
      )}

      {error && (
        <div className="file-preview-error">
          <AlertCircle size={32} />
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && fileInfo && (
        <div className="file-preview-content">
          <div className="file-info-section">
            <h3>File Information</h3>
            <div className="file-info-grid">
              <div className="file-info-item">
                <File size={16} />
                <div>
                  <div className="file-info-label">Name</div>
                  <div className="file-info-value">{fileInfo.name}</div>
                </div>
              </div>

              <div className="file-info-item">
                <HardDrive size={16} />
                <div>
                  <div className="file-info-label">Size</div>
                  <div className="file-info-value">{formatSize(fileInfo.size)}</div>
                </div>
              </div>

              <div className="file-info-item">
                <Calendar size={16} />
                <div>
                  <div className="file-info-label">Modified</div>
                  <div className="file-info-value">{formatDate(fileInfo.modified)}</div>
                </div>
              </div>

              {fileInfo.mime_type && (
                <div className="file-info-item">
                  <FileText size={16} />
                  <div>
                    <div className="file-info-label">Type</div>
                    <div className="file-info-value">{fileInfo.mime_type}</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {fileInfo.is_text && fileInfo.content && (
            <div className="file-content-section">
              <h3>Content</h3>
              <pre className="file-content-text">{fileInfo.content}</pre>
            </div>
          )}

          {fileInfo.is_text && fileInfo.error && (
            <div className="file-content-section">
              <div className="file-content-error">
                <AlertCircle size={20} />
                <span>{fileInfo.error}</span>
              </div>
            </div>
          )}

          {!fileInfo.is_text && (
            <div className="file-content-section">
              <div className="file-content-binary">
                <File size={48} />
                <p>Binary file - preview not available</p>
                <small>This file type cannot be displayed as text</small>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default FilePreview
