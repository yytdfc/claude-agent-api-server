import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './style.css'

// Temporarily disable StrictMode to avoid double-mounting effects
// which causes issues with terminal PTY session management
ReactDOM.createRoot(document.getElementById('root')).render(
  <App />
)
