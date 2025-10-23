# Claude Agent Web Client

A modern, web-based client for interacting with the Claude Agent API Server. This client provides a user-friendly chat interface with session management, model configuration, and real-time permission handling.

## Features

- 💬 **Interactive Chat Interface**: Clean, modern chat UI with real-time message streaming
- 🔧 **Model Configuration**: Configure main and background models separately
- 🔌 **Proxy Mode Support**: Use alternative LLM providers (OpenAI, Azure, etc.) via LiteLLM
- 🔒 **Permission Management**: Interactive permission approval for tool usage
- 📊 **Session Management**: Create, clear, and manage multiple sessions
- 🎨 **Beautiful UI**: Modern, responsive design that works on desktop and mobile
- ⚡ **Real-time Updates**: Live connection status and permission checks

## Quick Start

### 1. Start the API Server

First, make sure the API server is running:

```bash
# From the api_server directory
python -m uvicorn src.server:app --host 127.0.0.1 --port 8000
```

### 2. Open the Web Client

Simply open `index.html` in your web browser:

```bash
# Option 1: Open directly in browser
open index.html

# Option 2: Use a simple HTTP server (recommended)
python -m http.server 8080
# Then visit http://localhost:8080 in your browser
```

### 3. Configure and Connect

1. **Server URL**: Enter your API server URL (default: `http://127.0.0.1:8000`)
2. **Main Model**: Choose your main model (e.g., `claude-3-5-sonnet-20241022` or `gpt-4`)
3. **Background Model**: Optional background model for agents (e.g., `claude-3-5-haiku-20241022`)
4. **Proxy Mode**: Enable if using non-Claude models via LiteLLM
5. Click **Connect** to start your session

## Usage

### Basic Conversation

1. Type your message in the text area at the bottom
2. Press **Enter** to send (or click the **Send** button)
3. Use **Shift+Enter** for new lines in your message
4. Wait for Claude's response to appear

### Session Management

- **New Session**: Click the "New Session" button to start fresh while keeping your settings
- **Disconnect**: Click "Disconnect" to close the current session and return to configuration

### Permission Requests

When Claude needs to use a tool (like reading or editing files), a permission dialog will appear:

1. Review the tool name and input parameters
2. Click **Allow** to grant permission
3. Click **Deny** to reject the request

## Configuration Options

### Server URL
- Default: `http://127.0.0.1:8000`
- Change this if your API server is running on a different host or port

### Main Model
Examples:
- Claude models: `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`
- OpenAI models: `gpt-4`, `gpt-3.5-turbo`
- Other providers: Any model supported by LiteLLM

### Background Model
Used by background agents for tasks like file exploration. Typically a faster/cheaper model:
- `claude-3-5-haiku-20241022` for Claude
- `gpt-3.5-turbo` for OpenAI

### Proxy Mode
Enable this checkbox when using non-Claude models. This routes requests through the server's LiteLLM integration.

## Example Configurations

### Using Claude Models
```
Server URL: http://127.0.0.1:8000
Main Model: claude-3-5-sonnet-20241022
Background Model: claude-3-5-haiku-20241022
Proxy Mode: ✓ (checked)
```

### Using OpenAI Models
```
Server URL: http://127.0.0.1:8000
Main Model: gpt-4
Background Model: gpt-3.5-turbo
Proxy Mode: ✓ (checked)
```

### Using Mixed Models
```
Server URL: http://127.0.0.1:8000
Main Model: claude-3-5-sonnet-20241022
Background Model: gpt-3.5-turbo
Proxy Mode: ✓ (checked)
```

## Features in Detail

### Message Types

The UI displays different types of messages with distinct styling:

- **User Messages**: Your input (blue background, right-aligned)
- **Assistant Messages**: Claude's responses (gray background, left-aligned)
- **Tool Usage**: When Claude uses tools (yellow background with tool icon)
- **System Messages**: Status updates (centered, gray)
- **Errors**: Error messages (red border, centered)

### Auto-formatting

The client automatically formats message content:
- Code blocks with syntax highlighting
- Inline code with `monospace` formatting
- Line breaks preserved
- Markdown-style **bold** text

### Connection Status

The header displays your connection status:
- **Disconnected**: Gray dot - not connected to server
- **Connected**: Green pulsing dot - active session

### Cost Tracking

When available, the client displays the cost of each interaction in USD.

## File Structure

```
web_client/
├── index.html      # Main HTML structure
├── style.css       # All styling and layout
├── app.js          # Client logic and API communication
└── README.md       # This file
```

## Browser Compatibility

The web client works on all modern browsers:
- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## CORS Configuration

The API server includes CORS middleware that allows requests from any origin (`allow_origins=["*"]`). This is suitable for development and local testing.

**For Production**: You should restrict `allow_origins` to specific domains:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Connection Failed
- Verify the API server is running on the specified URL
- Check that the server URL is correct (including `http://` prefix)
- Open browser console (F12) for detailed error messages

### Permission Dialog Not Appearing
- Check the browser console for errors
- Ensure JavaScript is enabled
- Try refreshing the page

### Messages Not Sending
- Verify you're connected (green dot in header)
- Check browser console for API errors
- Ensure the session hasn't timed out

### Styling Issues
- Clear browser cache and reload
- Verify all CSS files are loaded (check browser Network tab)
- Try a different browser

## Development

To modify the web client:

1. **HTML** (`index.html`): Update structure and layout
2. **CSS** (`style.css`): Modify styling and appearance
3. **JavaScript** (`app.js`): Add features or change behavior

The client is built with vanilla JavaScript - no build process or dependencies required!

## API Integration

The web client integrates with the Claude Agent API Server using these endpoints:

- `GET /health` - Check server health
- `POST /sessions` - Create new session
- `GET /sessions/{session_id}/status` - Get session status
- `POST /sessions/{session_id}/messages` - Send message
- `POST /sessions/{session_id}/permissions/respond` - Respond to permissions
- `DELETE /sessions/{session_id}` - Close session

See the main API documentation for complete endpoint details.

## License

This web client is part of the Claude Agent SDK Python API Server project.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Support

For questions or issues:
1. Check the troubleshooting section above
2. Review the main API server documentation
3. Open an issue on GitHub
