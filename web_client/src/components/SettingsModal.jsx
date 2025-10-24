import { useState, useEffect } from 'react'

function SettingsModal({ isOpen, onClose, settings, onSave }) {
  const [localSettings, setLocalSettings] = useState(settings)

  useEffect(() => {
    setLocalSettings(settings)
  }, [settings, isOpen])

  if (!isOpen) return null

  const handleChange = (key, value) => {
    setLocalSettings(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleSave = () => {
    onSave(localSettings)
    onClose()
  }

  const handleCancel = () => {
    setLocalSettings(settings) // Reset to original settings
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={handleCancel}>
      <div className="modal-content settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="modal-close" onClick={handleCancel}>×</button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label htmlFor="settings-cwd">Working Directory (CWD):</label>
            <input
              type="text"
              id="settings-cwd"
              value={localSettings.cwd}
              onChange={(e) => handleChange('cwd', e.target.value)}
              placeholder="/workspace"
            />
            <small>Default working directory for sessions</small>
          </div>

          <div className="form-group">
            <label htmlFor="settings-server-url">Server URL:</label>
            <input
              type="text"
              id="settings-server-url"
              value={localSettings.serverUrl}
              onChange={(e) => handleChange('serverUrl', e.target.value)}
              placeholder="http://localhost:8000"
            />
            <small>API server endpoint</small>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={handleCancel}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            Save Settings
          </button>
        </div>
      </div>
    </div>
  )
}

export default SettingsModal
