import { useEffect, useRef, useState } from 'react'
import { Terminal as XTerm } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { X } from 'lucide-react'
import { createAPIClient } from '../api/client'

function TerminalPTY({ serverUrl, initialCwd, onClose }) {
  const terminalRef = useRef(null)
  const xtermRef = useRef(null)
  const fitAddonRef = useRef(null)
  const apiClientRef = useRef(null)
  const sessionIdRef = useRef(null)
  const pollIntervalRef = useRef(null)
  const outputSeqRef = useRef(0)
  const [isConnected, setIsConnected] = useState(false)
  const isPollingRef = useRef(false) // Prevent concurrent polling requests
  const inputQueueRef = useRef([]) // Queue for input data
  const isSendingInputRef = useRef(false) // Flag to prevent concurrent input sending

  useEffect(() => {
    apiClientRef.current = createAPIClient(serverUrl)
  }, [serverUrl])

  // Process input queue to ensure sequential sending
  const processInputQueue = async () => {
    if (isSendingInputRef.current || inputQueueRef.current.length === 0) {
      return
    }

    isSendingInputRef.current = true

    while (inputQueueRef.current.length > 0) {
      const data = inputQueueRef.current.shift()
      try {
        await apiClientRef.current.sendTerminalInput(sessionIdRef.current, data)
      } catch (error) {
        console.error('Failed to send input:', error)
        break
      }
    }

    isSendingInputRef.current = false
  }

  const queueInput = (data) => {
    inputQueueRef.current.push(data)
    processInputQueue()
  }

  useEffect(() => {
    if (!terminalRef.current) return

    const xterm = new XTerm({
      cursorBlink: false,
      cursorStyle: 'block',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        cursorAccent: '#1e1e1e',
        selection: '#264f78',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#ffffff',
      },
      fontSize: 14,
      fontFamily: 'Monaco, Menlo, "Courier New", monospace',
      rows: 24,
      cols: 80,
      scrollback: 10000,
    })

    const fitAddon = new FitAddon()
    xterm.loadAddon(fitAddon)

    xterm.open(terminalRef.current)

    xtermRef.current = xterm
    fitAddonRef.current = fitAddon

    // Wait for DOM to be ready before fitting
    setTimeout(() => {
      fitAddon.fit()
    }, 0)


    xterm.onData((data) => {
      if (sessionIdRef.current) {
        queueInput(data)
      }
    })

    const handleResize = () => {
      fitAddon.fit()
      if (sessionIdRef.current) {
        const { rows, cols } = xterm
        apiClientRef.current.resizeTerminal(sessionIdRef.current, rows, cols).catch(console.error)
      }
    }
    window.addEventListener('resize', handleResize)

    const resizeObserver = new ResizeObserver(() => {
      handleResize()
    })
    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current)
    }

    // Initialize session after xterm is ready
    const initSession = async () => {
      try {
        // Ensure terminal is fitted before getting dimensions
        await new Promise(resolve => setTimeout(resolve, 100))
        fitAddon.fit()

        const { rows, cols } = xterm

        const response = await apiClientRef.current.createTerminalSession({
          rows,
          cols,
          cwd: initialCwd || '/workspace',
          shell: 'bash'
        })

        sessionIdRef.current = response.session_id
        setIsConnected(true)
        startPolling()
      } catch (error) {
        console.error('TerminalPTY: Failed to create session:', error)
        xterm.writeln(`\x1b[1;31mFailed to create terminal session: ${error.message}\x1b[0m`)
      }
    }

    initSession()

    return () => {
      window.removeEventListener('resize', handleResize)
      resizeObserver.disconnect()
      stopPolling()
      if (sessionIdRef.current) {
        apiClientRef.current.closeTerminalSession(sessionIdRef.current).catch(console.error)
      }
      xterm.dispose()
    }
  }, [])

  const startPolling = () => {
    if (pollIntervalRef.current) return

    pollIntervalRef.current = setInterval(async () => {
      if (!sessionIdRef.current || isPollingRef.current) return

      isPollingRef.current = true

      try {
        const response = await apiClientRef.current.getTerminalOutput(
          sessionIdRef.current,
          outputSeqRef.current
        )

        if (response.output) {
          xtermRef.current.write(response.output)
        }

        outputSeqRef.current = response.seq

        if (response.exit_code !== null) {
          stopPolling()
          setIsConnected(false)
          xtermRef.current.writeln(`\r\n\x1b[1;33m[Process exited with code ${response.exit_code}]\x1b[0m`)
        }
      } catch (error) {
        console.error('Failed to poll output:', error)
      } finally {
        isPollingRef.current = false
      }
    }, 100)
  }

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  return (
    <>
      <div className="terminal-header">
        <span className="terminal-title">
          PTY Terminal {sessionIdRef.current ? `- ${sessionIdRef.current.substring(0, 8)}` : ''}
        </span>
        <div className="terminal-actions">
          <button
            className="btn-icon btn-terminal-action"
            onClick={onClose}
            title="Close terminal"
          >
            <X size={16} />
          </button>
        </div>
      </div>
      <div ref={terminalRef} className="terminal-content" />
    </>
  )
}

export default TerminalPTY
