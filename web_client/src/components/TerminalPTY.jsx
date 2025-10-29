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

  useEffect(() => {
    apiClientRef.current = createAPIClient(serverUrl)
  }, [serverUrl])

  useEffect(() => {
    if (!terminalRef.current) return

    console.log('TerminalPTY: Initializing xterm...')

    const xterm = new XTerm({
      cursorBlink: true,
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
    fitAddon.fit()

    xtermRef.current = xterm
    fitAddonRef.current = fitAddon

    console.log('TerminalPTY: xterm opened, dimensions:', xterm.rows, 'x', xterm.cols)

    xterm.onData(async (data) => {
      if (sessionIdRef.current && isConnected) {
        try {
          await apiClientRef.current.sendTerminalInput(sessionIdRef.current, data)
        } catch (error) {
          console.error('Failed to send input:', error)
        }
      }
    })

    const handleResize = () => {
      fitAddon.fit()
      if (sessionIdRef.current && isConnected) {
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
      console.log('TerminalPTY: Creating terminal session...')
      try {
        fitAddon.fit()
        const { rows, cols } = xterm

        console.log('TerminalPTY: Sending create session request:', { rows, cols, cwd: initialCwd || '/workspace' })

        const response = await apiClientRef.current.createTerminalSession({
          rows,
          cols,
          cwd: initialCwd || '/workspace',
          shell: 'bash'
        })

        console.log('TerminalPTY: Session created:', response)

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
      console.log('TerminalPTY: Cleaning up...')
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
    if (pollIntervalRef.current) {
      console.log('TerminalPTY: Polling already started')
      return
    }

    console.log('TerminalPTY: Starting output polling...')

    pollIntervalRef.current = setInterval(async () => {
      if (!sessionIdRef.current || !isConnected) return

      try {
        const response = await apiClientRef.current.getTerminalOutput(
          sessionIdRef.current,
          outputSeqRef.current
        )

        if (response.output) {
          console.log('TerminalPTY: Received output, length:', response.output.length, 'seq:', response.seq)
          xtermRef.current.write(response.output)
        }

        outputSeqRef.current = response.seq

        if (response.exit_code !== null) {
          console.log('TerminalPTY: Process exited with code:', response.exit_code)
          stopPolling()
          setIsConnected(false)
          xtermRef.current.writeln(`\r\n\x1b[1;33m[Process exited with code ${response.exit_code}]\x1b[0m`)
        }
      } catch (error) {
        console.error('TerminalPTY: Failed to poll output:', error)
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
