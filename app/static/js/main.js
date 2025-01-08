// Format date to a readable string
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Create HTML for a single message
function createMessageHTML(message) {
    return `
        <div class="message">
            <div class="message-header">
                <span class="fingerprint">${message.fingerprint}</span>
                <span class="date">${formatDate(message.date)}</span>
            </div>
            <div class="message-content">${escapeHtml(message.content)}</div>
        </div>
    `;
}

// Escape HTML to prevent XSS
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Scroll to bottom of messages container
function scrollToBottom() {
    const container = document.getElementById('messages-container');
    container.scrollTop = container.scrollHeight;
}

// Display messages in the container
function displayMessages(messages) {
    const container = document.getElementById('messages-container');
    const wasAtBottom = container.scrollHeight - container.scrollTop === container.clientHeight;
    
    container.innerHTML = messages.map(createMessageHTML).join('');
    
    // Only auto-scroll if we were already at the bottom
    if (wasAtBottom) {
        scrollToBottom();
    }
}

// Load messages from the server
async function loadMessages() {
    try {
        const response = await fetch('/messages');
        const messages = await response.json();
        displayMessages(messages);
    } catch (error) {
        console.error('Error loading messages:', error);
        alert('Failed to load messages. Please refresh the page.');
    }
}

// Send a new message
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

// Handle form submission
document.querySelector('.message-form').addEventListener('submit', async function(e) {
    // Only prevent default if JavaScript is enabled
    e.preventDefault();
    
    const textarea = this.querySelector('textarea');
    const content = textarea.value.trim();
    
    if (!content) {
        alert('Please enter a message');
        return;
    }
    
    const success = await sendMessage(content);
    if (success) {
        textarea.value = '';
        scrollToBottom();
    }
});

// Handle Enter key in textarea
document.querySelector('textarea[name="content"]').addEventListener('keydown', async function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        
        const content = this.value.trim();
        if (!content) {
            return;
        }
        
        const success = await sendMessage(content);
        if (success) {
            this.value = '';
            scrollToBottom();
        }
    }
});

// Load messages on page load
loadMessages();

// Poll for new messages every 5 seconds
setInterval(loadMessages, 5000);
