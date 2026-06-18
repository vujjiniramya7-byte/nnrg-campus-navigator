// Session state
let sessionId = localStorage.getItem('campus_navigator_session');
if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('campus_navigator_session', sessionId);
}

// Check and apply theme
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
updateThemeIcon(savedTheme);

// DOM Elements
const chatFeed = document.getElementById('chat-feed');
const chatInput = document.getElementById('chat-input');
const chatForm = document.getElementById('chat-form');
const systemStatus = document.getElementById('system-status');
const statusDot = document.querySelector('.status-dot');

// Configure marked to render safe markdown
marked.setOptions({
    sanitize: true, // Deprecated in some versions but good practice
    headerIds: false,
    mangle: false
});

// Preset Query execution
function askPreset(question) {
    chatInput.value = question;
    handleSendMessage(new Event('submit'));
}

// Theme toggler
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('.theme-toggle i');
    if (icon) {
        if (theme === 'dark') {
            icon.className = 'fa-solid fa-sun';
        } else {
            icon.className = 'fa-solid fa-moon';
        }
    }
}

// Append message block to feed
function appendMessage(role, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = role === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    // Parse markdown for assistant messages, keep plain text/escaping for user
    if (role === 'assistant') {
        bubbleDiv.innerHTML = marked.parse(text);
    } else {
        const textNode = document.createElement('p');
        textNode.textContent = text;
        bubbleDiv.appendChild(textNode);
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(bubbleDiv);
    chatFeed.appendChild(messageDiv);
    
    // Scroll to bottom
    chatFeed.scrollTop = chatFeed.scrollHeight;
}

// Show typing indicator
function showTypingIndicator() {
    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'message assistant-message typing-indicator-container';
    indicatorDiv.id = 'typing-indicator';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = '<i class="fa-solid fa-robot"></i>';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    
    const loader = document.createElement('div');
    loader.className = 'typing-indicator';
    loader.innerHTML = `
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
    `;
    bubbleDiv.appendChild(loader);

    indicatorDiv.appendChild(avatarDiv);
    indicatorDiv.appendChild(bubbleDiv);
    chatFeed.appendChild(indicatorDiv);
    chatFeed.scrollTop = chatFeed.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// Send Message Handler
async function handleSendMessage(event) {
    if (event) event.preventDefault();

    const query = chatInput.value.trim();
    if (!query) return;

    // Clear input field
    chatInput.value = '';

    // Append user query to UI
    appendMessage('user', query);

    // Show assistant typing indicator
    showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: query,
                sessionId: sessionId
            })
        });

        if (!response.ok) {
            throw new Error('Network error');
        }

        const data = await response.json();
        
        removeTypingIndicator();

        // Update status dot depending on connection type (Gemini vs Demo/Mock)
        if (data.isDemo) {
            systemStatus.textContent = "Demo Mode (Offline Fallback)";
            statusDot.className = "status-dot demo";
        } else {
            systemStatus.textContent = "System Connected (Gemini)";
            statusDot.className = "status-dot online";
        }

        appendMessage('assistant', data.response);

    } catch (error) {
        console.error('Error fetching chat response:', error);
        removeTypingIndicator();
        appendMessage('assistant', "I'm currently unable to retrieve that specific detail. Please check the official NNRG notice board or contact the administration office directly.");
    }
}

// Clear Chat History
async function clearChat() {
    if (confirm("Are you sure you want to clear your chat history?")) {
        try {
            await fetch('/api/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ sessionId: sessionId })
            });
            
            // Re-initialize session id
            sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('campus_navigator_session', sessionId);
            
            // Reset chat feed in UI
            chatFeed.innerHTML = `
                <div class="message assistant-message welcome-msg">
                    <div class="message-avatar">
                        <i class="fa-solid fa-robot"></i>
                    </div>
                    <div class="message-bubble">
                        <p>Chat history cleared! Welcome back. 🎓 I am <strong>CampusNavigator</strong>, your dedicated campus companion.</p>
                        <p>How can I help you today?</p>
                    </div>
                </div>
            `;
        } catch (e) {
            console.error("Failed to clear history on backend:", e);
        }
    }
}
