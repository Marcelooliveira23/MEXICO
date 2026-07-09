/**
 * V10 FLOATING COPILOT WIDGET
 * ===========================
 * Global AI assistant that:
 * 1. Appears on all pages (bottom-right corner)
 * 2. Captures page context (URL, form data, visible text)
 * 3. Provides quick AI insights without leaving the page
 * 4. Shows similar historical cases
 * 5. Suggests next actions
 */

class CopilotWidget {
    constructor() {
        this.widgetId = 'ai-copilot-float';
        this.isOpen = false;
        this.conversationHistory = [];
        this.pageContext = {};
        this.init();
    }

    init() {
        // Create widget HTML
        this.createWidget();

        // Capture page context
        setTimeout(() => this.capturePageContext(), 500);

        // Attach event listeners
        this.attachListeners();

        // Load conversation history
        this.loadConversationHistory();
    }

    createWidget() {
        const html = `
            <div id="${this.widgetId}" class="copilot-container">
                <!-- Floating Button -->
                <div class="copilot-button" id="copilot-btn" title="Ask AI Copilot">
                    <img src="/static/mexicana-symbol.svg" alt="Mexicana" class="copilot-logo">
                </div>

                <!-- Panel -->
                <div class="copilot-panel" id="copilot-panel">
                    <div class="copilot-header">
                        <h3>MEXICANA AI V10</h3>
                        <button class="copilot-close" id="copilot-close">&times;</button>
                    </div>

                    <div class="copilot-content">
                        <!-- Page Analysis Section -->
                        <div class="copilot-section">
                            <h4>📍 Page Context</h4>
                            <div id="page-analysis" class="copilot-analysis"></div>
                        </div>

                        <!-- Chat Area -->
                        <div class="copilot-chat" id="copilot-chat">
                            <div class="chat-message bot">
                                <p>Hello! I'm your AI maintenance copilot. Ask me about failures, trends, or get recommendations.</p>
                            </div>
                        </div>

                        <!-- Similar Cases Section -->
                        <div class="copilot-section" id="similar-cases-section" style="display:none;">
                            <h4>🔍 Similar Cases</h4>
                            <div id="similar-cases" class="copilot-similar"></div>
                        </div>

                        <!-- Input Area -->
                        <div class="copilot-input-area">
                            <textarea 
                                id="copilot-input" 
                                class="copilot-input" 
                                placeholder="Ask me anything about maintenance, trends, or failures..."
                                rows="2"
                            ></textarea>
                            <button class="copilot-send" id="copilot-send">Send</button>
                        </div>

                        <!-- Quick Actions -->
                        <div class="copilot-quick-actions">
                            <button class="quick-btn" onclick="window.copilot.quickAsk('Show daily brief')">📋 Daily Brief</button>
                            <button class="quick-btn" onclick="window.copilot.quickAsk('What are the top hotspots?')">🔥 Hotspots</button>
                            <button class="quick-btn" onclick="window.copilot.quickAsk('Forecast next 30 days')">📈 Forecast</button>
                        </div>
                    </div>
                </div>
            </div>

            <style>
                ${this.getStyles()}
            </style>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
    }

    getStyles() {
        return `
            /* Copilot Widget Styles */
            .copilot-container {
                position: fixed;
                bottom: 20px;
                right: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                z-index: 9999;
            }

            .copilot-button {
                width: 56px;
                height: 56px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                color: white;
                transition: all 0.3s ease;
            }

            .copilot-button:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 16px rgba(102, 126, 234, 0.6);
            }

            .copilot-logo {
                width: 26px;
                height: 26px;
                object-fit: contain;
                filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.2));
            }

            .copilot-panel {
                position: absolute;
                bottom: 80px;
                right: 0;
                width: 400px;
                height: 600px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
                display: none;
                flex-direction: column;
                opacity: 0;
                transform: translateY(10px) scale(0.95);
                transition: all 0.3s ease;
                border: 1px solid rgba(0, 0, 0, 0.1);
                z-index: 10000;
            }

            .copilot-panel.open {
                display: flex;
                opacity: 1;
                transform: translateY(0) scale(1);
            }

            .copilot-header {
                padding: 16px;
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 12px 12px 0 0;
            }

            .copilot-header h3 {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
            }

            .copilot-close {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .copilot-content {
                flex: 1;
                overflow-y: auto;
                padding: 12px;
                display: flex;
                flex-direction: column;
            }

            .copilot-section {
                margin-bottom: 12px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 8px;
            }

            .copilot-section h4 {
                margin: 0 0 8px 0;
                font-size: 13px;
                font-weight: 600;
                color: #333;
            }

            .copilot-analysis, .copilot-similar {
                font-size: 12px;
                color: #666;
                line-height: 1.4;
            }

            .chat-message {
                margin-bottom: 12px;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 13px;
                line-height: 1.4;
            }

            .chat-message.user {
                background: #667eea;
                color: white;
                margin-left: auto;
                width: fit-content;
                max-width: 85%;
            }

            .chat-message.bot {
                background: #f0f0f0;
                color: #333;
                margin-right: auto;
                width: fit-content;
                max-width: 85%;
            }

            .copilot-input-area {
                padding: 12px;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                display: flex;
                gap: 8px;
                flex-shrink: 0;
            }

            .copilot-input {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 6px;
                font-size: 13px;
                font-family: inherit;
                resize: none;
            }

            .copilot-input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            .copilot-send {
                padding: 8px 16px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 600;
                transition: background 0.2s;
            }

            .copilot-send:hover {
                background: #5568d3;
            }

            .copilot-send:active {
                transform: scale(0.98);
            }

            .copilot-quick-actions {
                padding: 8px 12px 0;
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
            }

            .quick-btn {
                padding: 6px 10px;
                background: #f0f0f0;
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 4px;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.2s;
            }

            .quick-btn:hover {
                background: #e0e0e0;
            }

            @media (max-width: 768px) {
                .copilot-panel {
                    width: 320px;
                    height: 500px;
                }
            }
        `;
    }

    attachListeners() {
        const btn = document.getElementById('copilot-btn');
        const closeBtn = document.getElementById('copilot-close');
        const sendBtn = document.getElementById('copilot-send');
        const input = document.getElementById('copilot-input');

        btn.addEventListener('click', () => this.togglePanel());
        closeBtn.addEventListener('click', () => this.togglePanel());
        sendBtn.addEventListener('click', () => this.sendMessage());
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    capturePageContext() {
        const page_url = window.location.href;
        const form_data = {};

        // Capture form fields if present
        document.querySelectorAll('input, textarea, select').forEach(el => {
            if (el.id && !el.id.includes('password')) {
                form_data[el.id] = el.value;
            }
        });

        const visible_text = document.body.innerText.substring(0, 1000);

        this.pageContext = { page_url, form_data, visible_text };

        // Send context to backend
        fetch('/api/ai/page_context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.pageContext)
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    this.displayPageAnalysis(data.data);
                }
            })
            .catch(e => console.log('Context analysis skipped:', e));
    }

    displayPageAnalysis(context) {
        const pageType = context.page_type || 'unknown';
        const pageInfo = {
            'failure_registration': '📝 Failure Registration Page',
            'fleet_status': '✈️ Fleet Status Dashboard',
            'analytics_dashboard': '📊 Analytics Dashboard',
            'logbook_view': '📓 Logbook View'
        };

        const html = `
            <p><strong>${pageInfo[pageType] || pageType}</strong></p>
            <p>Form fields: ${context.form_fields?.length || 0}</p>
            <p>Extractable: ${context.extractable_data?.tails?.length || 0} tails, ${context.extractable_data?.atas?.length || 0} ATAs</p>
        `;

        document.getElementById('page-analysis').innerHTML = html;
    }

    togglePanel() {
        const panel = document.getElementById('copilot-panel');
        this.isOpen = !this.isOpen;

        if (this.isOpen) {
            panel.classList.add('open');
            document.getElementById('copilot-input').focus();
        } else {
            panel.classList.remove('open');
        }
    }

    quickAsk(question) {
        const input = document.getElementById('copilot-input');
        input.value = question;
        this.sendMessage();
    }

    sendMessage() {
        const input = document.getElementById('copilot-input');
        const message = input.value.trim();

        if (!message) return;

        // Add user message to chat
        this.addChatMessage('user', message);
        input.value = '';

        // Show loading
        this.addChatMessage('bot', '⏳ Analyzing...');

        // Send to AI copilot endpoint
        fetch('/api/ai/copilot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: message,
                page_context: this.pageContext,
                scope: 'global'
            })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    // Remove loading message
                    document.querySelectorAll('.chat-message.bot').forEach(el => {
                        if (el.textContent.includes('Analyzing')) el.remove();
                    });

                    // Add response
                    const response = data.data.response || 'No response generated.';
                    this.addChatMessage('bot', response.substring(0, 300) + (response.length > 300 ? '...' : ''));

                    // Show similar cases if available
                    if (data.data.similar_cases && data.data.similar_cases.length > 0) {
                        this.showSimilarCases(data.data.similar_cases);
                    }
                }
            })
            .catch(e => {
                document.querySelectorAll('.chat-message.bot').forEach(el => {
                    if (el.textContent.includes('Analyzing')) el.remove();
                });
                this.addChatMessage('bot', '❌ Error: Could not reach AI service.');
                console.error(e);
            });
    }

    addChatMessage(role, text) {
        const chat = document.getElementById('copilot-chat');
        const msgEl = document.createElement('div');
        msgEl.className = `chat-message ${role}`;
        msgEl.innerHTML = `<p>${text}</p>`;
        chat.appendChild(msgEl);
        chat.scrollTop = chat.scrollHeight;
    }

    showSimilarCases(cases) {
        const section = document.getElementById('similar-cases-section');
        const container = document.getElementById('similar-cases');

        let html = '';
        cases.slice(0, 3).forEach(c => {
            html += `
                <div style="margin-bottom: 8px; padding: 8px; background: white; border-left: 3px solid #667eea; border-radius: 4px;">
                    <p style="margin: 0 0 4px 0; font-weight: 600;">${c.tail} / ATA ${c.ata}</p>
                    <p style="margin: 0; font-size: 11px; color: #666;">${c.similarity}% match</p>
                </div>
            `;
        });

        if (html) {
            container.innerHTML = html;
            section.style.display = 'block';
        }
    }

    loadConversationHistory() {
        // Load from sessionStorage if available
        const stored = sessionStorage.getItem('copilot_history');
        if (stored) {
            this.conversationHistory = JSON.parse(stored);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.copilot = new CopilotWidget();
});
