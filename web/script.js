const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');

let chatHistory = [];
let isProcessing = false;

// Auto-resize textarea
userInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';

    // Enable/disable send button
    if (this.value.trim().length > 0) {
        sendBtn.removeAttribute('disabled');
    } else {
        sendBtn.setAttribute('disabled', 'true');
    }
});

// Handle Enter key
userInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (this.value.trim().length > 0 && !isProcessing) {
            sendMessage();
        }
    }
});

sendBtn.addEventListener('click', () => {
    if (!isProcessing) sendMessage();
});

newChatBtn.addEventListener('click', () => {
    chatHistory = [];
    // Clear all messages except the first one (Welcome)
    const messages = chatContainer.querySelectorAll('.message');
    for (let i = 1; i < messages.length; i++) {
        messages[i].remove();
    }
});

async function sendMessage() {
    const text = userInput.value.trim();

    if (!text) return;

    console.log('Sending message:', text);

    // 1. Add User Message
    addMessage(text, 'user');
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.setAttribute('disabled', 'true');
    isProcessing = true;

    // 2. Show Loading State
    const loadingId = addLoadingIndicator();

    try {
        // 3. Call API
        console.log('Calling API at http://localhost:8000/chat');
        const response = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: text,
                history: chatHistory
                // API Key is now handled by the backend env
            })
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error Response:', errorText);
            throw new Error(`API Error: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Received data:', data);

        // 4. Remove Loading & Add Bot Response
        removeLoadingIndicator(loadingId);
        addMessage(data.response, 'assistant', data.context);

        // 5. Update History
        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: data.response });

    } catch (error) {
        console.error('Error in sendMessage:', error);
        removeLoadingIndicator(loadingId);
        addMessage(`Error: ${error.message}. Please check your connection.`, 'assistant');
        console.error(error);
    } finally {
        isProcessing = false;
    }
}

function addMessage(content, role, context = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatarSrc = role === 'user' ? '../assets/user_icon.svg' : '../assets/guru_icon.svg';

    // Parse Markdown
    const parsedContent = marked.parse(content);

    let contextHtml = '';
    if (context) {
        contextHtml = `
            <div class="context-box">
                <div class="context-toggle" onclick="toggleContext(this)">View Sources & References</div>
                <div class="context-content">
                    ${context}
                </div>
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div>
            <img src="${avatarSrc}" alt="${role}" width="36" height="36">
        </div>
        <div class="message-content">
            ${parsedContent}
            ${contextHtml}
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addLoadingIndicator() {
    const id = 'loading-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message assistant`;
    messageDiv.id = id;

    messageDiv.innerHTML = `
        <div class="avatar">
            <img src="../assets/guru_icon.svg" alt="Guru" width="36" height="36">
        </div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    scrollToBottom();
    return id;
}

function removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Global function for context toggle
window.toggleContext = function (element) {
    const content = element.nextElementSibling;
    content.classList.toggle('show');
    element.innerText = content.classList.contains('show') ? 'Hide Sources' : 'View Sources & References';
}
