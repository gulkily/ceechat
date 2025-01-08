## Implementation Notes
1. Sort messages by timestamp when displaying
2. Sanitize all user inputs
3. Handle both JSON and form-data POST requests
4. Pressing Enter in the message form sends message (Shift+Enter for new line)
5. The chat container should scroll to the bottom when new messages are added
6. All error responses include descriptive messages
7. Messages are identified by author's key fingerprint
8. Do not use venv
9. Messages should be pushed to GitHub automatically after being stored

# CeeChat Minimal Implementation Spec

Create a secure chat system with message signing. Messages are stored as text files and signed cryptographically. Each message is identified by the fingerprint of its author's public key.

## Core Requirements

### Message Storage
- Store each message as a text file: `YYYYMMDD_HHMMSS.txt`
- Message format:
  ```
  Date: ISO-8601 timestamp
  Type: message|system|error
  Fingerprint: 8-char-hex
  Signature: hex_encoded_signature

  message content
  ```

### Security
- System has RSA public/private keypair for message signing
- Sign messages with private key
- Verify message signatures with public key
- Identify messages by SHA-256 fingerprint of author's public key (first 8 characters)

### API Endpoints
```
GET /messages
  Returns: Array of message objects
  Response: [
    {
      date: ISO-8601 string,
      type: string,
      fingerprint: string,
      signature: string,
      content: string
    }
  ]

POST /messages
  Body: { content: string, type: string }
  Response: { status: "success", id: string }
  Error: { status: "error", message: string }
```

### Error Handling
- Client-side: Display error messages to user via alerts
- Server-side: Return proper HTTP status codes with JSON error messages
- Common errors:
  - 400: Invalid JSON format
  - 400: Content is required
  - 400: Content must be a string
  - 404: Endpoint not found
  - 500: Internal server error

## Frontend Implementation

### HTML Structure
```html
<!DOCTYPE html>
<html>
<head>
    <title>CeeChat</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CeeChat</h1>
        </div>
        
        <div id="messages">
            <div id="messages-container"></div>
        </div>
        
        <form method="POST" action="/messages" class="message-form">
            <textarea name="content" required></textarea>
            <button type="submit">Send</button>
        </form>
    </div>
    <script src="/static/js/main.js"></script>
</body>
</html>
```

### Message Display
```html
<div class="message">
    <div class="message-header">
        <span class="fingerprint">a1b2c3d4</span>
        <span class="date">2025-01-08 15:28:42</span>
    </div>
    <div class="message-content">Hello, world!</div>
</div>
```

### JavaScript Core Functions
```javascript
// Main functions
async function loadMessages() {
    try {
        const response = await fetch('/messages');
        const messages = await response.json();
        displayMessages(messages);
        
        // Always scroll to bottom when new messages are loaded
        const container = document.getElementById('messages-container');
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

async function sendMessage(content) {
    try {
        const response = await fetch('/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content,
                type: 'message'
            })
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Failed to send message');
        }
        
        await loadMessages();
        return true;
    } catch (error) {
        console.error('Error sending message:', error);
        alert(error.message || 'Failed to send message. Please try again.');
        return false;
    }
}
```

## Python Server Implementation

### Core Classes
```python
class KeyManager:
    def __init__(self, keys_dir):
        self.keys_dir = Path(keys_dir)
        self.private_key_path = self.keys_dir / 'local.pem'
        self.public_key_path = self.keys_dir / 'local.pub'
        self._ensure_keypair()
        self._fingerprint = self._calculate_fingerprint()
    
    def _calculate_fingerprint(self):
        # Calculate SHA-256 hash of the public key (first 8 characters)
        result = subprocess.run(
            ['openssl', 'dgst', '-sha256', '-r', str(self.public_key_path)],
            capture_output=True, text=True
        )
        return result.stdout.split()[0][:8]
    
    def sign_message(self, message):
        result = subprocess.run(
            ['openssl', 'dgst', '-sha256', '-sign', str(self.private_key_path)],
            input=message.encode(),
            capture_output=True
        )
        return result.stdout.hex()

class MessageManager:
    def save_message(self, content, type='message'):
        now = datetime.now()
        timestamp = now.isoformat()
        filename = now.strftime("%Y%m%d_%H%M%S.txt")
        signature = self.key_manager.sign_message(content)
        fingerprint = self.key_manager.get_fingerprint()
        
        message = f"""Date: {timestamp}
Type: {type}
Fingerprint: {fingerprint}
Signature: {signature}

{content}"""
        
        (self.messages_dir / filename).write_text(message)
        return filename
