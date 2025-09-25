
let currentSessionId = null;
let userName = null;
let isChatOpen = false;
let isMinimized = false;
let isRecording = false;
let recognition = null;
let isFirstOpen = true;
let mediaRecorder = null;
let audioChunks = [];
let currentSession = null;

const chatbotContainer = document.getElementById('chatbotContainer');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const typingIndicator = document.getElementById('typingIndicator');
const clearModal = document.getElementById('clearModal');
const voiceBtn = document.getElementById('voiceBtn');
const fileUploadBtn = document.getElementById('fileUploadBtn');
const sendBtn = document.getElementById('sendBtn');
const filePreviewSection = document.getElementById('filePreviewSection');
const fileCounter = document.getElementById('fileCounter');

let selectedFiles = [];
const MAX_FILES = 6;
let messageCount = 0;
let isEmailFormActive = false;
let isWhatsAppFormActive = false;
let isLanguageFormActive = false;

function updateInputIndicators() {
    const hasText = chatInput.value.trim().length > 0;
    const hasFiles = selectedFiles.length > 0;
    const hasContent = hasText || hasFiles;
    
    if (hasText) {
        chatInput.classList.add('has-content');
    } else {
        chatInput.classList.remove('has-content');
    }
    
    if (hasContent) {
        sendBtn.classList.add('active');
    } else {
        sendBtn.classList.remove('active');
    }
    
    if (hasFiles) {
        fileUploadBtn.classList.add('active');
        fileCounter.style.display = 'flex';
        fileCounter.textContent = selectedFiles.length;
        fileUploadBtn.title = `${selectedFiles.length} fichier(s) sélectionné(s)`;
    } else {
        fileUploadBtn.classList.remove('active');
        fileCounter.style.display = 'none';
        fileUploadBtn.title = 'Upload files';
    }
}

chatInput.addEventListener('input', updateInputIndicators);
chatInput.addEventListener('keyup', updateInputIndicators);
chatInput.addEventListener('paste', () => {
    setTimeout(updateInputIndicators, 10);
});

if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        chatInput.value = transcript;
        updateInputIndicators();
        stopRecording();
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        stopRecording();
    };
    
    recognition.onend = function() {
        stopRecording();
    };
}

async function initializeMediaRecorder() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = function(event) {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = function() {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            audioChunks = [];
            
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = function() {
                const base64Audio = reader.result.split(',')[1];
                console.log('Audio recorded:', base64Audio.substring(0, 50) + '...');
                addMessage('Audio recorded (transcription not implemented)', 'user');
            };
        };
        
        return true;
    } catch (error) {
        console.error('Error accessing microphone:', error);
        return false;
    }
}
function toggleChat() {
    isChatOpen = !isChatOpen;
    isMinimized = false;
    chatbotContainer.style.display = isChatOpen ? 'block' : 'none';
    
    if (isChatOpen && isFirstOpen) {
        isFirstOpen = false;
        
        // Marquer le bouton UMI comme actif par défaut
        const umiButton = document.querySelector('.footer-btn[onclick="openChatbot()"]');
        if (umiButton) {
            umiButton.classList.add('active');
        }
        
        addMessage('Hello! How can I help you today?', 'bot');
        addQuickReplies(['What services do you offer?', 'Pricing information', 'Contact support']);
        setTimeout(testConnectionSilent, 2000);
    }
}

function minimizeChat() {
    isMinimized = true;
    chatbotContainer.style.display = 'none';
}

function closeChat() {
    isChatOpen = false;
    isMinimized = false;
    chatbotContainer.style.display = 'none';
}

function showClearConfirmation() {
    clearModal.style.display = 'flex';
}

function hideClearConfirmation() {
    clearModal.style.display = 'none';
}

function confirmClearChat() {
    clearChatHistory();
    hideClearConfirmation();
}

function clearChatHistory() {
    const messages = chatMessages.querySelectorAll('.clearfix');
    messages.forEach(message => message.remove());
    
    messageCount = 0;
    
    removeAllFiles();
    
    updateInputIndicators();
    
    addMessage('💬 Conversation supprimée. Comment puis-je vous aider ?', 'bot');
    addQuickReplies(['What services do you offer?', 'Pricing information', 'Contact support']);
    
    console.log('✅ Historique de chat supprimé');
}

clearModal.addEventListener('click', function(e) {
    if (e.target === clearModal) {
        hideClearConfirmation();
    }
});

function handleFileUpload(event) {
    const files = Array.from(event.target.files);
    
    files.forEach(file => {
        if (selectedFiles.length >= MAX_FILES) {
            alert(`Maximum ${MAX_FILES} fichiers autorisés`);
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const fileData = {
                name: file.name,
                size: formatFileSize(file.size),
                type: file.type,
                base64: e.target.result,
                id: Date.now() + Math.random()
            };
            
            selectedFiles.push(fileData);
            showFilePreview();
            updateInputIndicators();
        };
        reader.readAsDataURL(file);
    });
    
    event.target.value = '';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileIcon(fileType, fileName) {
    if (fileType.startsWith('image/')) return '🖼️';
    if (fileType === 'application/pdf') return '📄';
    if (fileType.includes('word') || fileName.endsWith('.doc') || fileName.endsWith('.docx')) return '📝';
    if (fileType === 'text/plain' || fileName.endsWith('.txt')) return '📄';
    return '📎';
}

function showFilePreview() {
    if (selectedFiles.length === 0) {
        filePreviewSection.style.display = 'none';
        return;
    }
    
    filePreviewSection.style.display = 'block';
    filePreviewSection.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-preview-item';
        
        const icon = document.createElement('div');
        icon.className = 'file-preview-icon';
        icon.textContent = getFileIcon(file.type, file.name);
        
        if (file.type.startsWith('image/')) {
            const thumbnail = document.createElement('img');
            thumbnail.className = 'file-preview-thumbnail';
            thumbnail.src = file.base64;
            fileItem.appendChild(thumbnail);
        } else {
            fileItem.appendChild(icon);
        }
        
        const info = document.createElement('div');
        info.className = 'file-preview-info';
        
        const name = document.createElement('div');
        name.className = 'file-preview-name';
        name.textContent = file.name;
        
        const size = document.createElement('div');
        size.className = 'file-preview-size';
        size.textContent = file.size;
        
        info.appendChild(name);
        info.appendChild(size);
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'file-preview-remove';
        removeBtn.textContent = '×';
        removeBtn.onclick = () => removeFile(file.id);
        
        fileItem.appendChild(info);
        fileItem.appendChild(removeBtn);
        
        filePreviewSection.appendChild(fileItem);
    });
}

function removeFile(fileId) {
    selectedFiles = selectedFiles.filter(file => file.id !== fileId);
    showFilePreview();
    updateInputIndicators();
}

function removeAllFiles() {
    selectedFiles = [];
    filePreviewSection.style.display = 'none';
    document.getElementById('fileInput').value = '';
    updateInputIndicators();
}

function clearFilesAfterSend() {
    removeAllFiles();
    updateInputIndicators();
    console.log('✅ Fichiers supprimés, texte conservé');
}

function addMessage(text, sender, hasFiles = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + sender + '-message';
    
    if (text) {
        messageDiv.appendChild(document.createTextNode(text));
    }
    
    if (hasFiles && sender === 'user' && selectedFiles.length > 0) {
        const filesContainer = document.createElement('div');
        filesContainer.className = 'files-container';
        
        selectedFiles.forEach(file => {
            const fileAttachment = document.createElement('div');
            fileAttachment.className = 'file-attachment';
            
            const fileIcon = document.createElement('div');
            fileIcon.className = 'file-icon';
            fileIcon.innerHTML = getFileIcon(file.type, file.name);
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';
            
            const fileName = document.createElement('div');
            fileName.className = 'file-name';
            fileName.textContent = file.name;
            
            const fileSize = document.createElement('div');
            fileSize.className = 'file-size';
            fileSize.textContent = file.size;
            
            fileInfo.appendChild(fileName);
            fileInfo.appendChild(fileSize);
            
            fileAttachment.appendChild(fileIcon);
            fileAttachment.appendChild(fileInfo);
            
            filesContainer.appendChild(fileAttachment);
        });
        
        messageDiv.appendChild(filesContainer);
    }
    
    const container = document.createElement('div');
    container.className = 'clearfix';
    container.appendChild(messageDiv);
    
    chatMessages.insertBefore(container, typingIndicator);
    
    setTimeout(() => {
        scrollMessagesToBottom();
    }, 100);
    

}

function scrollMessagesToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addQuickReplies(replies) {
    const container = document.createElement('div');
    container.className = 'clearfix';
    
    const quickRepliesDiv = document.createElement('div');
    quickRepliesDiv.className = 'quick-replies';
    
    replies.forEach(reply => {
        const button = document.createElement('button');
        button.className = 'quick-reply';
        button.textContent = reply;
        button.onclick = () => {
            handleQuickReply(reply);
            container.remove();
        };
        quickRepliesDiv.appendChild(button);
    });
    
    container.appendChild(quickRepliesDiv);
    chatMessages.insertBefore(container, typingIndicator);
    scrollMessagesToBottom();
}

async function toggleVoiceRecording() {
    if (!isRecording) {
        if (recognition) {
            try {
                isRecording = true;
                voiceBtn.classList.add('voice-recording');
                voiceBtn.classList.add('active');
                voiceBtn.title = 'Recording... Click to stop';
                recognition.start();
                return;
            } catch (error) {
                console.log('Web Speech API failed, trying MediaRecorder:', error);
            }
        }
        
        if (!mediaRecorder) {
            const initialized = await initializeMediaRecorder();
            if (!initialized) {
                alert('Microphone access denied or not supported');
                return;
            }
        }
        
        try {
            isRecording = true;
            voiceBtn.classList.add('voice-recording');
            voiceBtn.classList.add('active');
            voiceBtn.title = 'Recording... Click to stop';
            mediaRecorder.start();
        } catch (error) {
            console.error('Recording failed:', error);
            stopRecording();
            alert('Recording failed. Please check microphone permissions.');
        }
    } else {
        stopRecording();
    }
}

function stopRecording() {
    isRecording = false;
    voiceBtn.classList.remove('voice-recording');
    voiceBtn.classList.remove('active');
    voiceBtn.title = 'Voice input';
    
    if (recognition) {
        try {
            recognition.stop();
        } catch (error) {
            console.log('Error stopping recognition:', error);
        }
    }
    
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        try {
            mediaRecorder.stop();
        } catch (error) {
            console.log('Error stopping recorder:', error);
        }
    }
}

function showTyping() {
    typingIndicator.style.display = 'block';
    scrollMessagesToBottom();
}

function hideTyping() {
    typingIndicator.style.display = 'none';
}

async function initializeSession() {
    try {
        const response = await fetch('http://localhost:5000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: '',
                session_id: currentSessionId
            })
        });

        if (response.ok) {
            const data = await response.json();
            currentSessionId = data.session_id;
            userName = data.user_name;

            if (currentSessionId) {
                const greetingResponse = await fetch(`http://localhost:5000/api/session/${currentSessionId}/greeting`);
                if (greetingResponse.ok) {
                    const greetingData = await greetingResponse.json();
                    addMessage(greetingData.greeting, 'bot');
                }
            }
        }
    } catch (error) {
        console.error('Erreur initialisation session:', error);
        addMessage('Bonjour ! Comment puis-je vous aider ?', 'bot');
    }
}


async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message && selectedFiles.length === 0) return;

    addMessage(message || `${selectedFiles.length} fichier(s) uploadé(s)`, 'user', selectedFiles.length > 0);

    clearFilesAfterSend();

    showTyping();


    try {
        console.log('🚀 Envoi à l\'API:', { 
            message: message, 
            filesCount: selectedFiles.length,
            url: 'http://localhost:5000/api/chat'
        });
        
        const filesData = selectedFiles.map(file => ({
            data: file.base64.split(',')[1],
            type: file.type,
            name: file.name
        }));
        
        const response = await fetch('http://localhost:5000/api/chat', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                message: message || `Analysez ces ${filesData.length} fichier(s)`,
                files: filesData
            })
        });

        console.log('📡 Réponse HTTP:', response.status, response.statusText);

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch {
                errorData = { error: `HTTP ${response.status}: ${response.statusText}` };
            }
            throw new Error(errorData.error || `Erreur HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('📨 Données reçues:', data);
        
        if (data.error) {
            addMessage(`⚠ ${data.error}`, 'bot');
        } else if (data.response) {
            addMessage(data.response, 'bot');
            
            if (data.model_used || data.rag_used) {
                const debugInfo = [];
                if (data.model_used) debugInfo.push(`Modèle: ${data.model_used}`);
                if (data.rag_used) debugInfo.push('RAG utilisé');
                console.log(`🔧 Debug: ${debugInfo.join(', ')}`);
            }
            
            if (data.response.toLowerCase().includes('help')) {
                addQuickReplies(['Contact support', 'View documentation', 'FAQ']);
            } else if (data.response.toLowerCase().includes('service')) {
                addQuickReplies(['Pricing', 'Features', 'Demo request', 'Free trial']);
            }
        } else {
            addMessage('⚠ Réponse vide du serveur', 'bot');
        }

    } catch (error) {
        console.error('⚠ Erreur complète:', error);
        
        let errorMessage = '⚠ Erreur: ';
        
        if (error.message.includes('Failed to fetch')) {
            errorMessage += 'Impossible de contacter le serveur. Vérifications:';
            addMessage(errorMessage, 'bot');
            addMessage('1. Le serveur Flask est-il démarré?', 'bot');
            addMessage('2. Testez: http://localhost:5000/api/test', 'bot');
            addMessage('3. Vérifiez la console pour plus de détails', 'bot');
        } else if (error.message.includes('503') || error.message.includes('Service')) {
            errorMessage += 'Service indisponible. Vérifications:';
            addMessage(errorMessage, 'bot');
            addMessage('1. Ollama est-il démarré? (ollama serve)', 'bot');
            addMessage('2. Le modèle llava est-il installé? (ollama list)', 'bot');
            addMessage('3. Testez: ollama run llava "hello"', 'bot');
        } else if (error.message.includes('timeout')) {
            errorMessage += 'Timeout - La requête a pris trop de temps';
            addMessage(errorMessage, 'bot');
            addMessage('💡 Essayez avec un message plus court', 'bot');
        } else {
            errorMessage += error.message;
            addMessage(errorMessage, 'bot');
        }
        
        addQuickReplies(['Test connexion', 'Vérifier status', 'Aide technique']);
        
    } finally {
        hideTyping();
    }
}

async function testConnectionDetailed() {
    addMessage('🔧 Test de connexion en cours...', 'bot');
    
    try {
        const testResponse = await fetch('http://localhost:5000/api/test');
        if (testResponse.ok) {
            addMessage('✅ Serveur Flask accessible', 'bot');
        } else {
            addMessage('⚠ Serveur Flask inaccessible', 'bot');
            return;
        }
        
        const statusResponse = await fetch('http://localhost:5000/api/status');
        if (statusResponse.ok) {
            const statusData = await statusResponse.json();
            
            addMessage(`📊 Status système:`, 'bot');
            addMessage(`- Ollama: ${statusData.ollama_connected ? '✅' : '⚠'}`, 'bot');
            addMessage(`- Llava: ${statusData.llava_ready ? '✅' : '⚠'}`, 'bot');
            addMessage(`- RAG: ${statusData.rag_available ? '✅' : '⚠'}`, 'bot');
            
            if (statusData.models_available && statusData.models_available.length > 0) {
                addMessage(`- Modèles: ${statusData.models_available.join(', ')}`, 'bot');
            }
            
        } else {
            addMessage('⚠ Impossible de récupérer le status', 'bot');
        }
        
    } catch (error) {
        addMessage(`⚠ Erreur test: ${error.message}`, 'bot');
        addMessage('💡 Vérifiez que le serveur est démarré', 'bot');
    }
}

async function testConnectionSilent() {
    try {
        const response = await fetch('http://localhost:5000/api/status');
        const data = await response.json();
        console.log('📄 Status silencieux:', data);
        
        if (!data.ollama_connected) {
            console.warn('⚠️ Ollama non connecté');
        } else if (!data.llava_ready) {
            console.warn('⚠️ Modèle llava non disponible');
        } else {
            console.log('✅ Système opérationnel');
        }
    } catch (error) {
        console.warn('⚠️ Impossible de contacter le serveur:', error.message);
    }
}

function handleQuickReply(reply) {
    if (reply === 'Test connexion') {
        testConnectionDetailed();
    } else if (reply === 'Vérifier status') {
        chatInput.value = 'Quel est le status du système?';
        sendMessage();
    } else if (reply === 'Aide technique') {
        addMessage('🔧 Aide technique:', 'bot');
        addMessage('1. Vérifiez que Ollama tourne: ollama serve', 'bot');
        addMessage('2. Vérifiez les modèles: ollama list', 'bot');
        addMessage('3. Testez llava: ollama run llava "hello"', 'bot');
        addMessage('4. Redémarrez le serveur si nécessaire', 'bot');
    } else {
        chatInput.value = reply;
        sendMessage();
    }
}


async function checkMemoryStatus() {
    try {
        const response = await fetch('/api/memory/status');
        const data = await response.json();
        
        if (data.status === 'ok') {
            console.log('✅ Mémoire active:', data.memory_stats);
            if (data.session_stats.active_sessions > 0) {
                console.log(`📊 Sessions actives: ${data.session_stats.active_sessions}`);
            }
        }
    } catch (error) {
        console.log('⚠️ Mémoire non disponible');
    }
}

async function checkStatus() {
    const statusDiv = document.getElementById('status');
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        let statusHTML = '';
        
        if (data.status === 'ok') {
            statusHTML = '🟢 Système opérationnel';

            if (currentSession) {
                statusHTML += ` | Session: ${currentSession.substring(0, 8)}...`;
            }
            
            if (data.session_stats && data.session_stats.users_with_names > 0) {
                statusHTML += ` | ${data.session_stats.users_with_names} utilisateur(s) identifié(s)`;
            }
            
        } else {
            statusHTML = '🟠 Problèmes détectés';
        }
        
        statusDiv.innerHTML = statusHTML;
        statusDiv.className = 'status ' + (data.status === 'ok' ? 'ok' : 'warning');
        
        // Vérifier aussi la mémoire
        await checkMemoryStatus();
        
    } catch (error) {
        statusDiv.innerHTML = '🔴 Serveur inaccessible';
        statusDiv.className = 'status error';
    }
}


chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideClearConfirmation();
    }
});

window.addEventListener('beforeunload', () => {
    if (mediaRecorder && mediaRecorder.stream) {
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
});

document.addEventListener('DOMContentLoaded', () => {
    updateInputIndicators();
    loadChatHistory();
    initializeSession();
    checkServerStatus();
    checkStatus();
    setInterval(checkStatus, 30000);
});
function showLogoFallback() {
    const logoImage = document.getElementById('logoImage');
    const logoFallback = document.getElementById('logoFallback');
    
    logoImage.style.display = 'none';
    logoFallback.style.display = 'flex';
}

function openEmailForm() {
const emailModal = document.getElementById('emailModal');
emailModal.style.display = 'flex';

// Clear form when opening
document.getElementById('emailForm').reset();
updateEmailSubmitButton();
}

function hideEmailForm() {
const emailModal = document.getElementById('emailModal');
emailModal.style.display = 'none';
}

function updateEmailSubmitButton() {
const form = document.getElementById('emailForm');
const submitBtn = document.getElementById('emailSubmitBtn');
const nameField = document.getElementById('emailName');
const emailField = document.getElementById('emailAddress');
const messageField = document.getElementById('emailMessage');
const termsCheckbox = document.getElementById('emailTerms');

const isValid = nameField.value.trim() !== '' && 
            emailField.value.trim() !== '' && 
            messageField.value.trim() !== '' && 
            termsCheckbox.checked;

submitBtn.disabled = !isValid;
}

function handleEmailSubmit(event) {
event.preventDefault();

const formData = new FormData(event.target);
const emailData = {
    name: formData.get('name'),
    email: formData.get('email'),
    message: formData.get('message'),
    terms: formData.get('terms')
};

// Simulate sending email
const submitBtn = document.getElementById('emailSubmitBtn');
const originalText = submitBtn.textContent;

submitBtn.textContent = 'Sending...';
submitBtn.disabled = true;

// Simulate API call
setTimeout(() => {
    console.log('Email data:', emailData);
    
    // Show success message in chat
    addMessage(`Email sent successfully! We'll get back to you at ${emailData.email}`, 'bot');
    
    // Hide modal
    hideEmailForm();
    
    // Reset button
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
    

}, 1500);
}

document.addEventListener('DOMContentLoaded', function() {
// Remplacer les anciens event listeners
document.querySelectorAll('.footer-btn').forEach(btn => {
// Supprimer l'ancien event listener
btn.removeEventListener('click', function() {
    resetAllButtonStates();
    this.classList.add('active');
});
});

// Ajouter les nouveaux event listeners spécifiques
const buttons = document.querySelectorAll('.footer-btn');
buttons.forEach((btn, index) => {
btn.addEventListener('click', function(e) {
    e.preventDefault();
    
    // Identifier le bouton cliqué
    const isUmiButton = this.textContent.trim() === 'UMI' || this.onclick?.toString().includes('openChatbot');
    const isEmailButton = this.textContent.includes('✉') || this.onclick?.toString().includes('openEmailForm');
    const isWhatsAppButton = this.textContent.includes('✆') || this.onclick?.toString().includes('openWhatsApp');
    const isLanguageButton = this.textContent.includes('🗣') || this.onclick?.toString().includes('openlanguage');
    
    // Réinitialiser tous les états
    resetAllButtonStates();
    
    // Marquer ce bouton comme actif
    this.classList.add('active');
    
    // Exécuter l'action appropriée
    if (isUmiButton) {
        // Pour UMI, afficher les messages d'accueil
        addMessage('Hello! How can I help you today?', 'bot');
        addQuickReplies(['What services do you offer?', 'Pricing information', 'Contact support']);
    } else if (isEmailButton) {
        addEmailFormMessage();
    } else if (isWhatsAppButton) {
        addWhatsAppFormMessage();
    } else if (isLanguageButton) {
        addLanguageFormMessage();
    }
});
});
});

// Close modal when clicking outside
document.getElementById('emailModal').addEventListener('click', function(e) {
if (e.target === this) {
    hideEmailForm();
}
});

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
if (e.key === 'Escape') {
    hideEmailForm();
}
});
function openEmailForm() {
// Remove the modal approach and add form directly to chat
addEmailFormMessage();
}

function addEmailFormMessage() {
    hideAllMessages();
    isEmailFormActive = true;
    hideInputControls();

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message email-form-message';

    messageDiv.innerHTML = `
        <h3>📧 Send us an email</h3>
        <form id="chatEmailForm" onsubmit="handleChatEmailSubmit(event)">
            <div class="email-form-group">
                <input 
                    type="text" 
                    id="chatEmailName" 
                    name="name" 
                    placeholder="Your name" 
                    required
                >
            </div>
            
            <div class="email-form-group">
                <input 
                    type="email" 
                    id="chatEmailAddress" 
                    name="email" 
                    placeholder="Your email" 
                    required
                >
            </div>

            <div class="email-form-group">
                <input 
                    type="text" 
                    id="chatEmailSubject" 
                    name="subject" 
                    placeholder="Subject" 
                    required
                >
            </div>
            
            <div class="email-form-group">
                <textarea 
                    id="chatEmailMessage" 
                    name="message" 
                    placeholder="Your message" 
                    required
                ></textarea>
            </div>
            
            <div class="email-checkbox-group">
                <input 
                    type="checkbox" 
                    id="chatEmailTerms" 
                    name="terms" 
                    class="email-checkbox"
                    required
                >
                <label for="chatEmailTerms" class="email-checkbox-label">
                    I accept the website terms
                </label>
            </div>
            
            <div class="email-form-buttons">
                <button type="button" class="email-btn cancel" onclick="removeChatEmailForm(this)">
                    Cancel
                </button>
                <button type="submit" class="email-btn submit" id="chatEmailSubmitBtn" disabled>
                    Send Email
                </button>
            </div>
        </form>
    `;

    const container = document.createElement('div');
    container.className = 'clearfix email-form-container';
    container.appendChild(messageDiv);

    chatMessages.insertBefore(container, typingIndicator);
    scrollMessagesToBottom();

    // Add event listeners for validation
    const form = messageDiv.querySelector('#chatEmailForm');
    const inputs = form.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        input.addEventListener('input', updateChatEmailSubmitButton);
        input.addEventListener('change', updateChatEmailSubmitButton);
    });
}

// 2. MODIFIER la fonction updateChatEmailSubmitButton()
function updateChatEmailSubmitButton() {
    const submitBtn = document.getElementById('chatEmailSubmitBtn');
    const nameField = document.getElementById('chatEmailName');
    const emailField = document.getElementById('chatEmailAddress');
    const subjectField = document.getElementById('chatEmailSubject');
    const messageField = document.getElementById('chatEmailMessage');
    const termsCheckbox = document.getElementById('chatEmailTerms');

    if (submitBtn && nameField && emailField && subjectField && messageField && termsCheckbox) {
        const isValid = nameField.value.trim() !== '' && 
                    emailField.value.trim() !== '' && 
                    subjectField.value.trim() !== '' &&
                    messageField.value.trim() !== '' && 
                    termsCheckbox.checked;

        submitBtn.disabled = !isValid;
    }
}

// 3. MODIFIER la fonction handleChatEmailSubmit()
function handleChatEmailSubmit(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const emailData = {
        name: formData.get('name'),
        email: formData.get('email'),
        subject: formData.get('subject'),
        message: formData.get('message'),
        terms: formData.get('terms')
    };

    const submitBtn = document.getElementById('chatEmailSubmitBtn');
    const originalText = submitBtn.textContent;

    submitBtn.textContent = 'Opening Email...';
    submitBtn.disabled = true;

    // Utiliser le sujet personnalisé de l'utilisateur
    const subject = encodeURIComponent(emailData.subject);
    const body = encodeURIComponent(
        `Name: ${emailData.name}\n` +
        `Email: ${emailData.email}\n` +
        `Message:\n${emailData.message}\n\n` +
        `---\n` +
        `Sent via UMI Chatbot`
    );

    const destinationEmail = 'hafsaelmahdi.in@gmail.com'; // Changez cette adresse

    // Essayer d'abord Gmail
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${destinationEmail}&su=${subject}&body=${body}`;
    
    try {
        const newWindow = window.open(gmailUrl, '_blank');
        
        if (!newWindow || newWindow.closed) {
            // Si Gmail ne s'ouvre pas, utiliser mailto
            const mailtoUrl = `mailto:${destinationEmail}?subject=${subject}&body=${body}`;
            window.location.href = mailtoUrl;
        }
    } catch (error) {
        // Fallback vers mailto
        const mailtoUrl = `mailto:${destinationEmail}?subject=${subject}&body=${body}`;
        window.location.href = mailtoUrl;
    }
    
    // Supprimer le formulaire
    setTimeout(() => {
        const formContainer = event.target.closest('.email-form-container');
        if (formContainer) {
            formContainer.remove();
        }

        isEmailFormActive = false;
        showInputControls();

        addMessage(`✅ Email ready to send to ${destinationEmail}`, 'bot');
        
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }, 1500);
}

// Fonction modifiée pour masquer chatbot-input et étendre l'espace des messages
function hideInputControls() {
    const chatbotInput = document.querySelector('.chatbot-input');
    const chatMessages = document.getElementById('chatMessages');
    
    if (chatbotInput) {
        chatbotInput.style.display = 'none';
    }
    
    // Ajouter une classe pour étendre l'espace des messages
    if (chatMessages) {
        chatMessages.classList.add('form-expanded');
    }
    
    // Le footer reste visible avec sa largeur fixe
}

// Fonction modifiée pour réafficher chatbot-input et restaurer l'espace normal
function showInputControls() {
    const chatbotInput = document.querySelector('.chatbot-input');
    const chatMessages = document.getElementById('chatMessages');
    const footer = document.querySelector('.footer');
    
    if (chatbotInput) {
        chatbotInput.style.display = 'flex';
    }
    
    // Retirer la classe d'expansion des messages
    if (chatMessages) {
        chatMessages.classList.remove('form-expanded');
    }
    
    if (footer) {
        footer.style.display = 'flex';
    }
}

function removeChatEmailForm(button) {
const formContainer = button.closest('.email-form-container');
formContainer.remove();

isEmailFormActive = false;
showInputControls();

addMessage('Email form cancelled', 'bot');
}

// Update your existing hideEmailForm function (keep it for backward compatibility):
function hideEmailForm() {
const emailModal = document.getElementById('emailModal');
if (emailModal) {
emailModal.style.display = 'none';
}
}

//************************************
function addWhatsAppFormMessage() {
    hideAllMessages();
    isWhatsAppFormActive = true;
    hideInputControls();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message whatsapp-form-message';
    
    messageDiv.innerHTML = `
        <h3>📱 Send us a WhatsApp</h3>
        <form id="chatWhatsAppForm" onsubmit="handleChatWhatsAppSubmit(event)">
            <div class="whatsapp-form-group">
                <input type="text" id="chatWhatsAppName" name="name" placeholder="Your name" required>
            </div>
            
            <div class="whatsapp-form-group">
                <textarea id="chatWhatsAppMessage" name="message" placeholder="Your message" required></textarea>
            </div>

            <div class="whatsapp-form-buttons">
                <button type="button" class="whatsapp-btn cancel" onclick="removeChatWhatsAppForm(this)">Cancel</button>
                <button type="submit" class="whatsapp-btn submit" id="chatWhatsAppSubmitBtn" disabled>Send WhatsApp</button>
            </div>
        </form>
    `;
    
    const container = document.createElement('div');
    container.className = 'clearfix whatsapp-form-container';
    container.appendChild(messageDiv);
    
    chatMessages.insertBefore(container, typingIndicator);
    scrollMessagesToBottom();
    
    const inputs = messageDiv.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        input.addEventListener('input', updateChatWhatsAppSubmitButton);
        input.addEventListener('change', updateChatWhatsAppSubmitButton);
    });
}

function updateChatWhatsAppSubmitButton() {
    const submitBtn = document.getElementById('chatWhatsAppSubmitBtn');
    const nameField = document.getElementById('chatWhatsAppName');
    const messageField = document.getElementById('chatWhatsAppMessage');
    
    if (submitBtn && nameField && messageField) {
        const isValid = nameField.value.trim() !== '' && 
                    messageField.value.trim() !== '' ;
        
        submitBtn.disabled = !isValid;
    }
}

function handleChatWhatsAppSubmit(event) {
    event.preventDefault();

    const name = document.getElementById('chatWhatsAppName').value;
    const userPhone ='212720096311'
    const message = document.getElementById('chatWhatsAppMessage').value;
    
    
    // Construire le message à envoyer
    const customMessage = `Name: ${name}%0AMessage: ${message}`;
    
    // Créer l'URL WhatsApp
    const whatsappUrl = `https://wa.me/${userPhone}?text=${customMessage}`;
    
    // Ouvrir WhatsApp dans une nouvelle fenêtre
    window.open(whatsappUrl, '_blank');
    
    // Supprimer le formulaire
    const formContainer = event.target.closest('.whatsapp-form-container');
    formContainer.remove();
    
    // Réinitialiser l'état et afficher les contrôles
    isWhatsAppFormActive = false;
    showInputControls();
    
    // Afficher un message de confirmation
    addMessage('✅ WhatsApp message prepared. Please check the new window to send it.', 'bot');
}

function removeChatWhatsAppForm(button) {
    const formContainer = button.closest('.whatsapp-form-container');
    formContainer.remove();
    
    isWhatsAppFormActive = false;
    showInputControls();
    
    addMessage('WhatsApp form cancelled', 'bot');
}

function openWhatsApp() {
    addWhatsAppFormMessage();
}
//************************************

// 1. Modifiez la fonction resetAllButtonStates() dans chatbot.js
function resetAllButtonStates() {
    // Supprimer la classe active de tous les boutons
    document.querySelectorAll('.footer-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Réinitialiser les états des formulaires
    isEmailFormActive = false;
    isWhatsAppFormActive = false;
    isLanguageFormActive = false;

    // Supprimer tous les formulaires actifs
    document.querySelectorAll('.email-form-container, .whatsapp-form-container, .language-form-container').forEach(container => {
        container.remove();
    });

    // *** SUPPRIMÉ: Ne plus supprimer l'historique des messages ***
    // const messages = chatMessages.querySelectorAll('.clearfix');
    // messages.forEach(message => message.remove());
    // messageCount = 0;

    showInputControls(); // Toujours afficher les contrôles
}

// 2. Ajoutez ces nouvelles fonctions pour cacher/afficher les messages
function hideAllMessages() {
    const messages = chatMessages.querySelectorAll('.clearfix:not(.email-form-container):not(.whatsapp-form-container):not(.language-form-container)');
    messages.forEach(message => {
        message.style.display = 'none';
    });
}

function showAllMessages() {
    const messages = chatMessages.querySelectorAll('.clearfix');
    messages.forEach(message => {
        if (!message.classList.contains('email-form-container') && 
            !message.classList.contains('whatsapp-form-container') && 
            !message.classList.contains('language-form-container')) {
            message.style.display = 'block';
        }
    });
}

document.querySelectorAll('.footer-btn').forEach(btn => {
btn.addEventListener('click', function() {
resetAllButtonStates();     // enlève active des autres
this.classList.add('active'); // ajoute active au bouton cliqué
});
});

function setActiveButton(buttonElement) {
resetAllButtonStates();
buttonElement.classList.add('active');
}

function addLanguageFormMessage() {
    hideAllMessages();
    isLanguageFormActive = true;
    hideInputControls();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message language-form-message';
    
    messageDiv.innerHTML = `
        <h3>🗣️ Select Your Preferred Language</h3>
        
        <div class="language-buttons-container" id="languageButtonsContainer" style="flex-direction: column; align-items: center; gap: 10px;">
            <button type="button" class="language-button" data-lang="english" style="width: 150px; justify-content: center;">
                <span class="language-flag">🇬🇧</span> English
            </button>
            <button type="button" class="language-button" data-lang="french" style="width: 150px; justify-content: center;">
                <span class="language-flag">🇫🇷</span> Français
            </button>
            <button type="button" class="language-button" data-lang="arabic" style="width: 150px; justify-content: center;">
                <span class="language-flag">🇸🇦</span> العربية
            </button>
            <button type="button" class="language-button" data-lang="spanish" style="width: 150px; justify-content: center;">
                <span class="language-flag">🇪🇸</span> Español
            </button>
        </div>
        
        <div class="language-form-buttons">
            <button type="button" class="language-btn cancel" onclick="removeChatLanguageForm(this)">
                Cancel
            </button>
            <button type="button" class="language-btn submit" id="chatLanguageSubmitBtn" disabled>
                Confirm Selection
            </button>
        </div>
    `;
    
    const container = document.createElement('div');
    container.className = 'clearfix language-form-container';
    container.appendChild(messageDiv);
    
    chatMessages.insertBefore(container, typingIndicator);
    scrollMessagesToBottom();
    
    const languageButtons = messageDiv.querySelectorAll('.language-button');
    let selectedLanguage = null;
    
    languageButtons.forEach(button => {
        button.addEventListener('click', function() {
            languageButtons.forEach(btn => btn.classList.remove('selected'));

            this.classList.add('selected');
            selectedLanguage = this.getAttribute('data-lang');
            
            updateChatLanguageSubmitButton(selectedLanguage);
        });
    });
    
    const messageField = messageDiv.querySelector('#chatLanguageMessage');
    const termsCheckbox = messageDiv.querySelector('#chatLanguageTerms');
    
    if (messageField) {
        messageField.addEventListener('input', () => updateChatLanguageSubmitButton(selectedLanguage));
    }
    
    if (termsCheckbox) {
        termsCheckbox.addEventListener('change', () => updateChatLanguageSubmitButton(selectedLanguage));
    }
    
    // Écouteur pour le bouton de soumission
    const submitBtn = messageDiv.querySelector('#chatLanguageSubmitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            handleChatLanguageSubmit(selectedLanguage);
        });
    }
}

function updateChatLanguageSubmitButton(selectedLanguage) {
    const submitBtn = document.getElementById('chatLanguageSubmitBtn');
    
    if (submitBtn) {
        // Correction: Vérifier uniquement si une langue est sélectionnée
        const isValid = selectedLanguage !== null;
        
        submitBtn.disabled = !isValid;
    }
}

function handleChatLanguageSubmit(selectedLanguage) {
    const messageField = document.getElementById('chatLanguageMessage');
    const message = messageField ? messageField.value.trim() : '';
    
    const languageData = {
        language: selectedLanguage,
        message: message,
        terms: true
    };
    
    const submitBtn = document.getElementById('chatLanguageSubmitBtn');
    const originalText = submitBtn.textContent;
    
    submitBtn.textContent = 'Processing...';
    submitBtn.disabled = true;
    
    // Simuler le traitement
    setTimeout(() => {
        console.log('Language support data:', languageData);
        
        // Supprimer le formulaire
        const formContainer = document.querySelector('.language-form-container');
        if (formContainer) {
            formContainer.remove();
        }
        
        // Réinitialiser l'état et afficher les contrôles
        isLanguageFormActive = false;
        showInputControls();
        const languageNames = {
            'english': 'English',
            'french': 'French',
            'arabic': 'Arabic', 
            'spanish': 'Spanish'
        };
        
        const selectedLanguageName = languageNames[selectedLanguage] || selectedLanguage;
        addMessage(`✅ Language preference set to ${selectedLanguageName}! We'll communicate with you in ${selectedLanguageName}.`, 'bot');
        
    }, 1500);
}

function removeChatLanguageForm(button) {
    const formContainer = button.closest('.language-form-container');
    if (formContainer) {
        formContainer.remove();
    }
    
    isLanguageFormActive = false;
    showInputControls();
    
    addMessage('Language selection cancelled', 'bot');
}

function openLanguageForm() {
    addLanguageFormMessage();
}

function openlanguage() {
    openLanguageForm();
}
function openChatbot() {
    // Réinitialiser les états des autres formulaires
    isEmailFormActive = false;
    isWhatsAppFormActive = false;
    isLanguageFormActive = false;

    // Supprimer uniquement les formulaires actifs
    document.querySelectorAll('.email-form-container, .whatsapp-form-container, .language-form-container').forEach(container => {
        container.remove();
    });

    // Marquer le bouton UMI comme actif
    document.querySelectorAll('.footer-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    const umiButton = document.querySelector('.footer-btn[onclick="openChatbot()"]');
    if (umiButton) {
        umiButton.classList.add('active');
    }

    // Réafficher tous les messages cachés
    showAllMessages();
    
    // Toujours afficher les contrôles
    showInputControls();

    const visibleMessages = Array.from(chatMessages.querySelectorAll('.clearfix')).filter(msg => 
        msg.style.display !== 'none' && 
        !msg.classList.contains('email-form-container') && 
        !msg.classList.contains('whatsapp-form-container') && 
        !msg.classList.contains('language-form-container')
    );
    
    if (visibleMessages.length === 0) {
        addMessage('Hello! How can I help you today?', 'bot');
        addQuickReplies(['What services do you offer?', 'Pricing information', 'Contact support']);
    }
}
