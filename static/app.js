document.addEventListener('DOMContentLoaded', () => {
    // ═══════════════════════════════════════
    //  DOM REFERENCES
    // ═══════════════════════════════════════
    const chatBox     = document.getElementById('chat-box');
    const textInput   = document.getElementById('text-input');
    const btnMic      = document.getElementById('btn-mic');
    const micIcon     = document.getElementById('mic-icon');
    const btnUpload   = document.getElementById('btn-upload');
    const fileUpload  = document.getElementById('file-upload');
    const mediaPreview= document.getElementById('media-preview');
    const modelSelect = document.getElementById('model-select');
    const modelDot    = document.getElementById('model-dot');
    const modelStatusText = document.getElementById('model-status-text');
    const btnLoad     = document.getElementById('btn-load');
    const btnUnload   = document.getElementById('btn-unload');
    const liveMetrics = document.getElementById('live-metrics');
    const metricTps   = document.getElementById('metric-tps');
    const metricTime  = document.getElementById('metric-time');
    const modelInfoBar= document.getElementById('model-info-bar');
    const modelInfoText = document.getElementById('model-info-text');
    const modelInfoClose= document.getElementById('model-info-close');
    const sendIcon    = document.getElementById('send-icon');

    // Sidebar
    const btnSidebar  = document.getElementById('btn-sidebar');
    const sidebar     = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const sbClose     = document.getElementById('sb-close');
    const sbNewChat   = document.getElementById('sb-new-chat');
    const sbConvList  = document.getElementById('sb-conv-list');
    const spPersona   = document.getElementById('sp-persona');
    const spStyle     = document.getElementById('sp-style');
    const spRules     = document.getElementById('sp-rules');

    let currentImages = [];
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let isSending = false;
    let currentConvId = null;

    let ttsAudioQueue = [];
    let isPlayingTTS = false;
    let currentTTSAudio = null;

    function playNextTTS() {
        if (ttsAudioQueue.length === 0) {
            isPlayingTTS = false;
            // Resume voice mode listening if active!
            if (isVoiceModeActive && continuousRecognition) {
                try { continuousRecognition.start(); } catch(e){}
            }
            return;
        }
        isPlayingTTS = true;
        const b64 = ttsAudioQueue.shift();
        currentTTSAudio = new Audio("data:audio/wav;base64," + b64);
        currentTTSAudio.onended = playNextTTS;
        currentTTSAudio.play().catch(e => { playNextTTS(); });
    }

    let currentVisionMode = 'vlm';
    let currentSTTMode = 'whisper';
    let currentTTSMode = 'none';

    // Pre-request mic permission at load so pywebview doesn't show ugly popup later
    try { navigator.mediaDevices.getUserMedia({ audio: true }).then(s => s.getTracks().forEach(t => t.stop())).catch(() => {}); } catch(e) {}

    function setupToggleGroup(selector, btnClass, callback) {
        const btns = document.querySelectorAll(selector + ' .' + btnClass);
        btns.forEach(btn => {
            btn.addEventListener('click', () => {
                btns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                callback(btn.getAttribute('data-val'));
            });
        });
    }

    setupToggleGroup('#vision-settings-group', 'vision-btn', val => currentVisionMode = val);
    setupToggleGroup('#stt-settings-group', 'stt-btn', val => currentSTTMode = val);
    setupToggleGroup('#tts-settings-group', 'tts-btn', val => currentTTSMode = val);

    // ═══════════════════════════════════════
    //  SIDEBAR
    // ═══════════════════════════════════════
    function openSidebar() {
        sidebar.classList.remove('hidden');
        sidebarOverlay.classList.remove('hidden');
        loadConversations();
        loadSettings();
    }
    function closeSidebar() {
        sidebar.classList.add('hidden');
        sidebarOverlay.classList.add('hidden');
    }
    btnSidebar.addEventListener('click', openSidebar);
    sbClose.addEventListener('click', closeSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);



    // ═══════════════════════════════════════
    //  CONVERSATIONS
    // ═══════════════════════════════════════
    async function loadConversations() {
        try {
            const r = await fetch('/api/conversations');
            const d = await r.json();
            sbConvList.innerHTML = '';
            if (d.conversations.length === 0) {
                sbConvList.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text3);font-size:0.82em">אין שיחות</div>';
                return;
            }
            for (const c of d.conversations) {
                const item = document.createElement('div');
                item.className = 'sb-conv-item' + (c.id === currentConvId ? ' active' : '');
                const dateStr = new Date(c.updated_at).toLocaleDateString('he-IL', {day:'2-digit', month:'2-digit'});
                item.innerHTML = `
                    <i class="fa-regular fa-message conv-icon"></i>
                    <span class="conv-title">${esc(c.title)}</span>
                    <span class="conv-date">${dateStr}</span>
                    <div class="conv-actions">
                        <button class="conv-act-btn rename" title="שנה שם"><i class="fa-solid fa-pen"></i></button>
                        <button class="conv-act-btn del" title="מחק"><i class="fa-solid fa-trash"></i></button>
                    </div>`;
                
                item.addEventListener('click', (e) => {
                    if (e.target.closest('.conv-act-btn')) return;
                    loadConversation(c.id);
                    closeSidebar();
                });
                item.querySelector('.rename').addEventListener('click', async () => {
                    const name = prompt('שם חדש לשיחה:', c.title);
                    if (name) {
                        await fetch(`/api/conversations/${c.id}`, {
                            method: 'PUT',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({title: name})
                        });
                        loadConversations();
                    }
                });
                item.querySelector('.del').addEventListener('click', async () => {
                    if (!confirm('למחוק את השיחה?')) return;
                    await fetch(`/api/conversations/${c.id}`, {method: 'DELETE'});
                    if (currentConvId === c.id) newChat();
                    loadConversations();
                });
                sbConvList.appendChild(item);
            }
        } catch {}
    }

    async function loadConversation(cid) {
        try {
            const r = await fetch(`/api/conversations/${cid}`);
            const d = await r.json();
            currentConvId = cid;
            chatBox.innerHTML = '';
            // Render messages
            for (const m of d.messages) {
                if (m.role === 'user') {
                    if (m.content.includes('[TOOL RESULT:') || m.content.includes('[TOOL OBSERVATION]')) {
                        // Parse tool result back into a widget
                        let toolName = 'system';
                        let toolRes = m.content;
                        
                        const match = m.content.match(/\[TOOL RESULT:\s*(.*?)\]\n([\s\S]*)/);
                        if (match) {
                            toolName = match[1];
                            toolRes = match[2].replace(/סכם את התוצאה בעברית בקצרה.*/s, '').trim();
                        } else {
                            toolRes = toolRes.replace('[TOOL OBSERVATION]', '').trim();
                        }
                        
                        const row = document.createElement('div');
                        row.className = 'msg-row bot tool-row';
                        finalizeToolWidget(row, toolName, toolRes);
                        chatBox.appendChild(row);
                    } else {
                        createUserMsg(m.content, '', true);
                    }
                } else if (m.role === 'assistant') {
                    // Strip thinking tags & raw thought logs for display
                    let text = m.content.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
                    text = text.replace(/Thinking Process:[\s\S]*?(?=\n\n|$)/i, '').trim();
                    
                    // Gemma4 alternative monologue headers
                    if (text.startsWith('The user said')) {
                        text = text.replace(/^The user said[\s\S]*?(?=[א-ת])/i, '');
                    }
                    if (text.startsWith('User asks')) {
                        text = text.replace(/^User asks[\s\S]*?(?=[א-ת])/i, '');
                    }
                    
                    text = text.trim();

                    if (text && !text.includes('```json')) {
                        const row = document.createElement('div');
                        row.className = 'msg-row bot';
                        const bub = document.createElement('div');
                        bub.className = 'msg-bubble';
                        bub.innerHTML = renderMarkdown(text);
                        row.appendChild(bub);
                        addCopyIcon(row, text);
                        chatBox.appendChild(row);
                    }
                }
            }
            scroll();
        } catch {}
    }

    function newChat() {
        currentConvId = null;
        chatBox.innerHTML = `
            <div class="welcome-block">
                <div class="welcome-icon"><i class="fa-solid fa-microchip"></i></div>
                <h2>JARVIS NEURAL CORE</h2>
                <p>שמע · ראייה · פעולות מחשב</p>
                <div class="welcome-caps">
                    <span><i class="fa-solid fa-microphone"></i> שמע</span>
                    <span><i class="fa-solid fa-image"></i> ראייה</span>
                    <span><i class="fa-solid fa-terminal"></i> פעולות</span>
                </div>
            </div>`;
    }
    sbNewChat.addEventListener('click', () => { newChat(); closeSidebar(); });

    // ═══════════════════════════════════════
    //  SETTINGS MODAL & CONFIG
    // ═══════════════════════════════════════
    const btnSettings = document.getElementById('btn-settings');
    const settingsModal = document.getElementById('settings-modal');
    const settingsClose = document.getElementById('settings-close');
    const btnSaveSettings = document.getElementById('btn-save-settings');
    const settingsStatus = document.getElementById('settings-status');
    
    const engineBtns = document.querySelectorAll('.engine-btn');
    const cloudSettingsSection = document.getElementById('cloud-settings-section');
    const envAnthropic = document.getElementById('env-anthropic');
    const envOpenai = document.getElementById('env-openai');
    
    let currentEngine = 'local';
    
    btnSettings.addEventListener('click', () => {
        settingsModal.classList.remove('hidden');
        loadSettings();
    });
    settingsClose.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });
    
    engineBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            engineBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentEngine = btn.getAttribute('data-val');
            
            if (currentEngine === 'cloud') {
                cloudSettingsSection.style.display = 'flex';
            } else {
                cloudSettingsSection.style.display = 'none';
            }
        });
    });

    async function loadSettings() {
        try {
            const r = await fetch('/api/config');
            const d = await r.json();
            
            const cfg = d.config || {};
            spPersona.value = cfg.persona || '';
            spStyle.value = cfg.style || '';
            spRules.value = cfg.rules || '';
            
            const env = d.env || {};
            if (env.ANTHROPIC_API_KEY) envAnthropic.value = env.ANTHROPIC_API_KEY;
            if (env.OPENAI_API_KEY) envOpenai.value = env.OPENAI_API_KEY;
            
        } catch (e) {
            console.error("Failed to load settings", e);
        }
    }
    
    btnSaveSettings.addEventListener('click', async () => {
        const payload = {
            config: {
                persona: spPersona.value,
                style: spStyle.value,
                rules: spRules.value
            },
            env: {
                ANTHROPIC_API_KEY: envAnthropic.value,
                OPENAI_API_KEY: envOpenai.value
            }
        };
        
        try {
            settingsStatus.textContent = 'שומר...';
            const r = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const d = await r.json();
            if (d.success) {
                settingsStatus.textContent = 'נשמר בהצלחה ✓';
                setTimeout(() => { settingsStatus.textContent = ''; settingsModal.classList.add('hidden'); }, 1500);
            } else {
                settingsStatus.textContent = 'שגיאה: ' + (d.error || '');
            }
        } catch (e) {
            settingsStatus.textContent = 'שגיאת רשת.';
        }
    });

    // ═══════════════════════════════════════
    //  MODEL MANAGEMENT
    // ═══════════════════════════════════════
    function showInfo(msg, type = 'ok') {
        modelInfoBar.classList.remove('hidden', 'error-bar', 'loading-bar');
        if (type === 'error') modelInfoBar.classList.add('error-bar');
        if (type === 'loading') modelInfoBar.classList.add('loading-bar');
        modelInfoText.textContent = msg;
    }
    modelInfoClose.addEventListener('click', () => modelInfoBar.classList.add('hidden'));

    // Track loaded models for cross-function use
    let _cachedLoadedModels = [];
    const modelTrigger = document.getElementById('model-trigger');
    const modelDropdown = document.getElementById('model-dropdown');
    const modelDropdownList = document.getElementById('model-dropdown-list');
    const modelNameDisplay = document.getElementById('model-name-display');

    async function loadModelList() {
        try {
            const r = await fetch('/api/models');
            const data = await r.json();
            if (!data.models || data.models.length === 0) {
                modelNameDisplay.textContent = 'אין מודלים זמינים';
                modelDropdownList.innerHTML = '<div style="padding:10px; color:var(--text3); font-size:0.8em; text-align:center;">לא נמצאו מודלים ב-Ollama</div>';
                return;
            }

            const prevValue = modelSelect.value;

            // Update hidden select
            modelSelect.innerHTML = '';
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.name;
                opt.textContent = m.name;
                modelSelect.appendChild(opt);
            });

            // Restore previous selection if still available
            if (prevValue && data.models.some(m => m.name === prevValue)) {
                modelSelect.value = prevValue;
            } else if (data.models.length > 0) {
                modelSelect.value = data.models[0].name;
            }

            // Update display name
            modelNameDisplay.textContent = modelSelect.value;

            // Build custom dropdown cards
            modelDropdownList.innerHTML = '';
            data.models.forEach(m => {
                const isSelected = m.name === modelSelect.value;
                const isLoaded = _cachedLoadedModels.some(l => l.name === m.name);
                const loadedInfo = isLoaded ? _cachedLoadedModels.find(l => l.name === m.name) : null;

                const card = document.createElement('div');
                card.className = 'model-card' + (isSelected ? ' selected' : '');
                
                // Construct tags
                let tagsHTML = `<span class="model-card-tag">${m.size_gb} GB</span>`;
                if (m.params && m.params !== "?") tagsHTML += `<span class="model-card-tag">${m.params}</span>`;
                if (m.quant && m.quant !== "?") tagsHTML += `<span class="model-card-tag">${m.quant}</span>`;
                if (isLoaded) {
                    const ramStr = loadedInfo && loadedInfo.vram_gb ? `(RAM ${loadedInfo.vram_gb}GB)` : '';
                    tagsHTML += `<span class="model-card-tag loaded-tag">טעון ${ramStr} ●</span>`;
                }

                card.innerHTML = `
                    <div class="model-card-main">
                        <span class="model-card-dot ${isLoaded ? 'loaded' : ''}"></span>
                        <div class="model-card-info">
                            <div class="model-card-name">${m.name}</div>
                            <div class="model-card-meta">
                                ${tagsHTML}
                            </div>
                        </div>
                    </div>
                    <i class="fa-solid fa-check model-card-check"></i>
                `;
                card.addEventListener('click', () => {
                    modelSelect.dataset.userSelected = 'true';
                    modelSelect.value = m.name;
                    modelNameDisplay.textContent = m.name;
                    modelDropdown.classList.add('hidden');
                    
                    if (!isLoaded) {
                        try { document.getElementById('btn-load').click(); } catch (e) {}
                    } else {
                        checkModelStatus();
                        showInfo(`מודל פעיל נבחר: ${m.name}`, 'ok');
                    }
                    
                    // Rebuild cards to update selection
                    loadModelList();
                });
                modelDropdownList.appendChild(card);
            });
        } catch {
            modelNameDisplay.textContent = 'שגיאה';
        }
    }

    // Toggle dropdown
    modelTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        modelDropdown.classList.toggle('hidden');
        if (!modelDropdown.classList.contains('hidden')) {
            loadModelList(); // Refresh when opening
        }
    });
    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!modelDropdown.contains(e.target) && e.target !== modelTrigger) {
            modelDropdown.classList.add('hidden');
        }
    });

    async function checkModelStatus() {
        // Skip auto-update while a load operation is in progress
        if (_isModelLoading) return;
        const wrap = document.getElementById('model-trigger');
        const sizeBadge = document.getElementById('model-size-badge');
        try {
            const sr = await fetch('/api/ollama-status');
            const sd = await sr.json();
            if (!sd.online) {
                modelDot.className = 'dot error';
                modelStatusText.textContent = 'Ollama לא פעיל!';
                wrap.className = 'model-selector-wrap model-error';
                return;
            }
            const lr = await fetch('/api/loaded-models');
            const ld = await lr.json();
            _cachedLoadedModels = ld.loaded || [];

            if (_cachedLoadedModels.length > 0) {
                const loadedName = _cachedLoadedModels[0].name;
                if (!modelSelect.dataset.userSelected && modelSelect.value !== loadedName) {
                    modelSelect.value = loadedName;
                    if (modelNameDisplay) modelNameDisplay.textContent = loadedName;
                    loadModelList();
                }

                const current = _cachedLoadedModels.find(m => m.name === modelSelect.value);
                if (current) {
                    modelDot.className = 'dot on';
                    modelStatusText.textContent = `✓ טעון ומוכן · ${current.vram_gb || '?'}GB RAM`;
                    wrap.className = 'model-selector-wrap model-active';
                    if (sizeBadge) sizeBadge.textContent = `${current.vram_gb || '?'}GB`;
                    // Auto-hide the info bar if it's showing a loading state
                    if (modelInfoBar && !modelInfoBar.classList.contains('hidden')) {
                        const infoText = modelInfoText.textContent || '';
                        if (infoText.includes('טוען') || infoText.includes('מכין')) {
                            showInfo(`✓ ${current.name} טעון ומוכן`, 'ok');
                            setTimeout(() => modelInfoBar.classList.add('hidden'), 3000);
                        }
                    }
                } else {
                    modelDot.className = 'dot off';
                    const loadedName = _cachedLoadedModels[0].name;
                    modelStatusText.textContent = `⚠ טעון: ${loadedName} (לא הנבחר)`;
                    wrap.className = 'model-selector-wrap model-error';
                    if (sizeBadge) sizeBadge.textContent = '';
                }
            } else {
                modelDot.className = 'dot off';
                modelStatusText.textContent = 'לא טעון — לחץ "טען"';
                wrap.className = 'model-selector-wrap';
                if (sizeBadge) sizeBadge.textContent = '';
            }
        } catch {
            modelDot.className = 'dot error';
            modelStatusText.textContent = 'שגיאת חיבור';
        }
    }

    let _isModelLoading = false;
    let _loadStatusTimer = null;

    // ── Background load status poller ──
    function startLoadStatusPolling() {
        if (_loadStatusTimer) return; // already polling
        _isModelLoading = true;
        _loadStatusTimer = setInterval(async () => {
            try {
                const r = await fetch('/api/load-status');
                const s = await r.json();
                if (!s.active) {
                    // No active operation
                    stopLoadStatusPolling();
                    return;
                }
                const actionLabel = s.action === 'load' ? 'טוען' : 'מפנה';
                
                if (!s.completed) {
                    // Still in progress
                    const secs = Math.round(s.elapsed);
                    modelDot.className = 'dot loading';
                    modelStatusText.textContent = `${actionLabel}: ${secs}s...`;
                    showInfo(`${actionLabel} ${s.model}... (${secs}s)`, 'loading');
                    btnLoad.disabled = true;
                } else {
                    // Completed
                    btnLoad.disabled = false;
                    if (s.success) {
                        if (s.action === 'load') {
                            showInfo(`✓ ${s.model} הוכן ב-${s.load_time} שניות`, 'ok');
                        } else {
                            showInfo(`${s.model} פונה ✓`, 'ok');
                            modelDot.className = 'dot off';
                            modelStatusText.textContent = 'לא טעון';
                            _cachedLoadedModels = [];
                        }
                        setTimeout(() => modelInfoBar.classList.add('hidden'), 4000);
                    } else {
                        showInfo(`שגיאה: ${s.error || 'Unknown'}`, 'error');
                        modelDot.className = 'dot error';
                    }
                    checkModelStatus();
                    loadModelList();
                    stopLoadStatusPolling();
                }
            } catch {
                // Network error, keep trying
            }
        }, 1000);
    }

    function stopLoadStatusPolling() {
        if (_loadStatusTimer) {
            clearInterval(_loadStatusTimer);
            _loadStatusTimer = null;
        }
        _isModelLoading = false;
    }

    // Check for in-progress operations on page load
    async function checkResumeLoad() {
        try {
            const r = await fetch('/api/load-status');
            const s = await r.json();
            if (s.active && !s.completed) {
                // There's an operation in progress — resume polling!
                startLoadStatusPolling();
            } else if (s.active && s.completed && s.success) {
                // Just finished, update UI
                checkModelStatus();
            }
        } catch {}
    }

    btnLoad.addEventListener('click', async () => {
        const model = modelSelect.value;
        if (!model) { showInfo('לא נבחר מודל', 'error'); return; }
        if (_isModelLoading) { showInfo('כבר בתהליך טעינה...', 'loading'); return; }

        modelDot.className = 'dot loading';
        modelStatusText.textContent = 'טוען: 0s';
        showInfo(`מכין ${model}...`, 'loading');
        btnLoad.disabled = true;

        try {
            await fetch('/api/load-model', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model})
            });
            // Don't wait for response — start polling status
            startLoadStatusPolling();
        } catch (e) {
            showInfo('שגיאת חיבור', 'error');
            btnLoad.disabled = false;
        }
    });

    btnUnload.addEventListener('click', async () => {
        const model = modelSelect.value;
        if (!model || _isModelLoading) return;

        _isModelLoading = true;
        btnUnload.disabled = true;
        modelDot.className = 'dot loading';
        modelStatusText.textContent = 'מפנה...';
        showInfo(`מפנה ${model}...`, 'loading');

        try {
            await fetch('/api/unload-model', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({model})
            });
            startLoadStatusPolling();
        } catch {}
        btnUnload.disabled = false;
    });

    // Initial load
    loadModelList();
    checkModelStatus();
    checkResumeLoad();  // Resume any in-progress background operation
    setInterval(() => {
        checkModelStatus();
        loadModelList();
    }, 30000);

    // ═══════════════════════════════════════
    //  MARKDOWN + CITATION RENDERER
    // ═══════════════════════════════════════
    
    // Configure marked.js
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,         // \n → <br>
            gfm: true,            // GitHub Flavored Markdown (tables, strikethrough, etc.)
            headerIds: false,
        });
        
        // Add syntax highlighting for code blocks
        const renderer = new marked.Renderer();
        renderer.code = (code, lang) => {
            const validLang = lang && hljs && hljs.getLanguage(lang) ? lang : 'plaintext';
            try {
                const highlighted = typeof hljs !== 'undefined'
                    ? hljs.highlight(code, { language: validLang }).value
                    : esc(code);
                return `<pre><code class="hljs language-${validLang}">${highlighted}</code></pre>`;
            } catch {
                return `<pre><code>${esc(code)}</code></pre>`;
            }
        };
        // Make links open in new tab
        renderer.link = (href, title, text) =>
            `<a href="${href}" target="_blank" rel="noopener" title="${title||href}">${text}</a>`;
        marked.use({ renderer });
    }
    
    function renderMarkdown(text) {
        if (!text) return '';
        if (typeof marked === 'undefined') return esc(text);  // Fallback if CDN fails
        
        // Strip ```json tool call blocks before rendering
        let cleaned = text
            .replace(/```\s*json\s*[\s\S]*?```/gi, '')
            .replace(/```\s*\[[\s\S]*?\]\s*```/gi, '')
            .trim();
        
        // Extract "Source: url" lines for citation rendering
        const sources = [];
        cleaned = cleaned.replace(/^Source:\s*(https?:\/\/\S+)/gim, (_, url) => {
            sources.push(url);
            const n = sources.length;
            return `<sup class="cite-ref" data-url="${url}" title="${url}">[${n}]</sup>`;
        });
        
        // Render markdown
        let html = marked.parse(cleaned);
        
        // Add sources section at the bottom if any
        if (sources.length > 0) {
            html += `<div class="sources-section"><div class="sources-label"><i class="fa-solid fa-link"></i> מקורות</div>`;
            sources.forEach((url, i) => {
                const domain = (() => { try { return new URL(url).hostname.replace('www.', ''); } catch { return url; } })();
                html += `<a class="source-link" href="${url}" target="_blank" rel="noopener"><sup>[${i+1}]</sup> ${domain}</a>`;
            });
            html += `</div>`;
        }
        
        return html;
    }
    
    function renderMarkdownStream(text) {
        // Used during streaming — same as renderMarkdown but without source injection
        // (sources only appear in final message)
        if (!text) return '';
        if (typeof marked === 'undefined') return esc(text);
        let cleaned = text
            .replace(/```\s*json\s*[\s\S]*?```/gi, '')
            .replace(/```\s*\[[\s\S]*?\]\s*```/gi, '')
            .trim();
        return marked.parse(cleaned);
    }
    
    function esc(t) {
        if (!t) return '';
        return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
    }
    function stripJson(t) {
        // Remove ```json ... ``` blocks from displayed text (with optional spaces)
        return t.replace(/```\s*json\s*[\s\S]*?```/gi, '').replace(/```\s*\[[\s\S]*?\]\s*```/gi, '').trim();
    }
    function timeNow() {
        return new Date().toLocaleTimeString('he-IL', {hour:'2-digit', minute:'2-digit'});
    }
    
    let activeTarget = null;

    function scroll(target = null) {
        if (target) activeTarget = target;
        requestAnimationFrame(() => { 
            if (activeTarget) {
                const chatRect = chatBox.getBoundingClientRect();
                const targetRect = activeTarget.getBoundingClientRect();
                // If active typing reaches the bottom zone (120px above screen bottom), scroll down
                if (targetRect.bottom > chatRect.bottom - 120) {
                    chatBox.scrollTop += (targetRect.bottom - (chatRect.bottom - 120)) + 20;
                }
            } else {
                const rows = chatBox.querySelectorAll('.msg-row');
                if (rows.length > 0) {
                    rows[rows.length - 1].scrollIntoView({ behavior: 'auto', block: 'end' });
                }
            }
        });
    }

    function createUserMsg(text, extras = '', isHistory = false) {
        const wb = chatBox.querySelector('.welcome-block');
        if (wb) wb.remove();
        const id = 'chk-' + Date.now();
        const row = document.createElement('div');
        row.className = 'msg-row user';
        row.innerHTML = `
            <div class="msg-bubble">${esc(text)}${extras}</div>
            <div class="msg-meta">
                <span class="msg-time">${timeNow()}</span>
                <span class="checks" id="${id}">✓</span>
            </div>`;
        chatBox.appendChild(row);
        
        const bub = row.querySelector('.msg-bubble');
        if (text) addCopyIcon(bub, text);
        
        if (!isHistory) {
            // Scroll specifically this new message to the top of the chatBox INSTANTLY. 
            // We use 'auto' instead of 'smooth' to prevent standard token streaming from 
            // interrupting the scroll animation mid-way.
            setTimeout(() => {
                chatBox.scrollTop = row.offsetTop - 20;
                activeTarget = null; // Reset target on new user msg so it doesn't force scroll past user msg immediately
            }, 10);
        }
        
        return document.getElementById(id);
    }

    function createBotGroup() {
        const row = document.createElement('div');
        row.className = 'msg-row bot';
        const tw = document.createElement('div');
        tw.className = 'think-window collapsed';
        tw.innerHTML = `
            <div class="think-bar">
                <i class="fa-solid fa-circle-notch fa-spin spinner"></i>
                <span class="think-label">ממתין...</span>
                <span class="think-time"></span>
                <i class="fa-solid fa-chevron-down expand-icon"></i>
            </div>
            <div class="think-body" style="position:relative;">
                <div class="think-text-col"></div>
                <div class="think-img-col" style="display:none;"></div>
                <button class="copy-icon-btn" title="העתק מחשבות" style="position:absolute; top:4px; left:4px;">
                    <i class="fa-regular fa-copy"></i>
                </button>
            </div>`;
        
        tw.querySelector('.copy-icon-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            const txt = tw.querySelector('.think-text-col').textContent;
            navigator.clipboard.writeText(txt).then(() => {
                const btn = tw.querySelector('.copy-icon-btn');
                btn.innerHTML = '<i class="fa-solid fa-check"></i>';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
                    btn.classList.remove('copied');
                }, 2000);
            });
        });
        tw.querySelector('.think-bar').addEventListener('click', () => {
            tw.classList.toggle('collapsed');
            tw.classList.toggle('expanded');
        });
        const bub = document.createElement('div');
        bub.className = 'msg-bubble hidden';
        row.appendChild(tw);
        row.appendChild(bub);
        chatBox.appendChild(row);
        scroll();
        return {
            row, tw,
            spinner: tw.querySelector('.spinner'),
            label:   tw.querySelector('.think-label'),
            ttime:   tw.querySelector('.think-time'),
            body:    tw.querySelector('.think-text-col'),
            imgCol:  tw.querySelector('.think-img-col'),
            textBodyBase: tw.querySelector('.think-body'),
            bubble:  bub
        };
    }

    function addCopyIcon(bubble, text) {
        if (!text) return;
        const btn = document.createElement('button');
        btn.className = 'copy-icon-btn';
        btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
        btn.title = 'העתק';
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(text).then(() => {
                btn.innerHTML = '<i class="fa-solid fa-check"></i>';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
                    btn.classList.remove('copied');
                }, 2000);
            });
        });
        bubble.style.position = 'relative';
        bubble.appendChild(btn);
    }

    // ═══════════════════════════════════════
    //  TOOL METADATA (icon, color, label per tool)
    // ═══════════════════════════════════════
    const TOOL_META = {
        set_brightness:    { icon: 'fa-sun',            color: '#facc15', label: 'בהירות מסך' },
        set_volume:        { icon: 'fa-volume-high',    color: '#38bdf8', label: 'עוצמת קול' },
        control_media:     { icon: 'fa-music',          color: '#a78bfa', label: 'מדיה' },
        launch_app:        { icon: 'fa-rocket',         color: '#4ade80', label: 'פתיחת אפליקציה' },
        open_url:          { icon: 'fa-globe',          color: '#22d3ee', label: 'פתיחת אתר' },
        search_web:        { icon: 'fa-magnifying-glass', color: '#34d399', label: 'חיפוש ברשת' },
        deep_research:     { icon: 'fa-microscope',      color: '#818cf8', label: 'מחקר מעמיק' },
        get_weather:       { icon: 'fa-cloud-sun',      color: '#60a5fa', label: 'מזג אוויר' },
        get_time:          { icon: 'fa-clock',          color: '#94a3b8', label: 'שעה' },
        get_date:          { icon: 'fa-calendar',       color: '#94a3b8', label: 'תאריך' },
        system_health:     { icon: 'fa-heart-pulse',    color: '#f87171', label: 'מצב מחשב' },
        battery_status:    { icon: 'fa-battery-three-quarters', color: '#4ade80', label: 'סוללה' },
        system_ops:        { icon: 'fa-power-off',      color: '#f87171', label: 'פקודת מערכת' },
        take_screenshot:   { icon: 'fa-camera',         color: '#c084fc', label: 'צילום מסך' },
        remember_fact:     { icon: 'fa-brain',          color: '#fb923c', label: 'שמירת זיכרון' },
        recall_memories:   { icon: 'fa-database',       color: '#fb923c', label: 'שליפת זיכרון' },
        read_telegram_news:{ icon: 'fa-newspaper',      color: '#2dd4bf', label: 'חדשות טלגרם' },
        play_song:         { icon: 'fa-play',           color: '#a78bfa', label: 'השמעת שיר' },
        list_files:        { icon: 'fa-folder-open',    color: '#fbbf24', label: 'קבצים' },
        search_file:       { icon: 'fa-file-magnifying-glass', color: '#fbbf24', label: 'חיפוש קובץ' },
        read_file:         { icon: 'fa-file-lines',     color: '#60a5fa', label: 'קריאת קובץ' },
        write_file:        { icon: 'fa-file-pen',       color: '#4ade80', label: 'כתיבת קובץ' },
        run_command:       { icon: 'fa-terminal',       color: '#a78bfa', label: 'פקודת טרמינל' },
        clipboard_ops:     { icon: 'fa-clipboard',      color: '#94a3b8', label: 'לוח גזירה' },
        wifi_info:         { icon: 'fa-wifi',           color: '#38bdf8', label: 'רשת WiFi' },
        kill_process:      { icon: 'fa-skull-crossbones', color: '#f87171', label: 'סגירת תהליך' },
        list_windows:      { icon: 'fa-window-restore', color: '#22d3ee', label: 'חלונות פתוחים' },
        set_wallpaper:     { icon: 'fa-image',          color: '#c084fc', label: 'רקע שולחן עבודה' },
        read_webpage:      { icon: 'fa-globe',          color: '#34d399', label: 'קריאת דף אינטרנט' },
        computer_action:   { icon: 'fa-robot',          color: '#00e5ff', label: 'שליטה במחשב' },
    };
    const DEFAULT_TOOL_META = { icon: 'fa-bolt', color: '#00e5ff', label: 'פעולה' };

    function getToolMeta(toolName) {
        return TOOL_META[toolName] || { ...DEFAULT_TOOL_META, label: toolName };
    }

    // Show "Tool in progress" widget — returns the element so we can update it later
    function showToolInProgress(toolName, toolArgs) {
        const m = getToolMeta(toolName);
        const row = document.createElement('div');
        row.className = 'msg-row bot tool-row';
        row.dataset.toolName = toolName;
        row.innerHTML = `
        <div class="tool-widget tool-loading" style="--tool-color:${m.color}">
            <div class="tool-header">
                <span class="tool-icon"><i class="fa-solid ${m.icon}"></i></span>
                <span class="tool-label">${m.label}</span>
                <span class="tool-status-dot"><i class="fa-solid fa-circle-notch fa-spin"></i></span>
            </div>
            <div class="tool-detail">ממשתמש בכלי <code>${toolName}</code>...</div>
        </div>`;
        chatBox.appendChild(row);
        scroll(row);
        return row;
    }

    // Replace progress widget with actual result
    // Long results (> 200 chars) are collapsed by default, click header to expand
    const LONG_RESULT_TOOLS = ['read_telegram_news', 'search_web', 'list_files', 'recall_memories'];

    function finalizeToolWidget(row, toolName, result) {
        const m = getToolMeta(toolName);
        const resultStr = String(result);
        const isLong = resultStr.length > 200 || LONG_RESULT_TOOLS.includes(toolName);
        const collapsed = isLong;
        const widget = document.createElement('div');
        widget.className = `tool-widget tool-done${collapsed ? ' result-collapsed' : ''}`;
        widget.style.cssText = `--tool-color:${m.color}`;
        widget.innerHTML = `
        <div class="tool-header tool-header-clickable">
            <span class="tool-icon"><i class="fa-solid ${m.icon}"></i></span>
            <span class="tool-label">${m.label}</span>
            ${isLong ? '<span class="tool-expand-hint"><i class="fa-solid fa-chevron-down"></i></span>' : ''}
            <span class="tool-status-dot done"><i class="fa-solid fa-check"></i></span>
        </div>
        <div class="tool-result msg-bubble" style="padding-top:10px; margin:0;">${renderMarkdown(resultStr)}</div>`;
        
        // Add copy button to tool result
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-icon-btn tool-copy-btn';
        copyBtn.title = 'העתק תוצאה';
        copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
        copyBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            try {
                await navigator.clipboard.writeText(resultStr);
                copyBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
                copyBtn.classList.add('copied');
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
                    copyBtn.classList.remove('copied');
                }, 2000);
            } catch {}
        });
        widget.querySelector('.tool-header').appendChild(copyBtn);
        
        if (isLong) {
            widget.querySelector('.tool-header-clickable').addEventListener('click', (e) => {
                if (e.target.closest('.tool-copy-btn')) return; // don't toggle on copy click
                widget.classList.toggle('result-collapsed');
                const chevron = widget.querySelector('.tool-expand-hint i');
                if (chevron) {
                    chevron.className = widget.classList.contains('result-collapsed')
                        ? 'fa-solid fa-chevron-down'
                        : 'fa-solid fa-chevron-up';
                }
            });
        }
        row.innerHTML = '';
        row.appendChild(widget);
        scroll(row);
    }

    // Pending tool rows map: toolName → row element (for updating when result arrives)
    let _pendingToolRows = {};

    function addAction(tool, result) {
        // Try to find and update existing progress widget
        if (_pendingToolRows[tool]) {
            finalizeToolWidget(_pendingToolRows[tool], tool, result);
            delete _pendingToolRows[tool];
        } else {
            // Fallback: create fresh completed widget
            const row = document.createElement('div');
            row.className = 'msg-row bot tool-row';
            finalizeToolWidget(row, tool, result);
            chatBox.appendChild(row);
            scroll(row);
        }
    }

    function addError(msg) {
        const row = document.createElement('div');
        row.className = 'msg-row bot';
        row.innerHTML = `<div class="msg-bubble" style="border-color:var(--red);">❌ ${esc(msg)}</div>`;
        chatBox.appendChild(row);
        scroll(row);
    }

    // ═══════════════════════════════════════
    //  STOP BUTTON
    // ═══════════════════════════════════════
    function setStopMode(botRef) {
        const btn = document.getElementById('btn-send');
        btn.className = 'icon-btn stop-btn';
        btn.querySelector('i').className = 'fa-solid fa-stop';
        btn.onclick = async () => {
            isSending = false;
            try { await fetch('/api/abort', { method: 'POST' }); } catch {}
            resetSendButton();
            if (botRef) {
                botRef.label.textContent = 'הופסק על ידי המשתמש';
                botRef.spinner.className = 'fa-solid fa-ban';
                botRef.spinner.style.color = 'var(--red)';
                if (botRef.tw) {
                    botRef.tw.classList.add('collapsed');
                    botRef.tw.classList.remove('expanded');
                }
                if (botRef.timerID) {
                    clearInterval(botRef.timerID);
                }
            }
        };
    }
    function resetSendButton() {
        const btn = document.getElementById('btn-send');
        btn.className = 'icon-btn send-btn';
        btn.querySelector('i').className = 'fa-solid fa-paper-plane';
        btn.onclick = triggerSend;
        btn.disabled = false;
        isSending = false;
        liveMetrics.classList.add('hidden');
    }

    // ═══════════════════════════════════════
    //  FILE UPLOAD
    // ═══════════════════════════════════════
    btnUpload.addEventListener('click', () => fileUpload.click());
    fileUpload.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            currentImages.push(ev.target.result);
            mediaPreview.classList.remove('hidden');
            const w = document.createElement('div');
            w.style.cssText = 'display:flex;align-items:center;gap:4px;';
            w.innerHTML = `<img src="${ev.target.result}" class="thumb"><button class="remove-media" title="הסר"><i class="fa-solid fa-xmark"></i></button>`;
            w.querySelector('.remove-media').onclick = () => {
                const idx = currentImages.indexOf(ev.target.result);
                if (idx > -1) currentImages.splice(idx, 1);
                w.remove();
                if (currentImages.length === 0) mediaPreview.classList.add('hidden');
            };
            mediaPreview.appendChild(w);
        };
        reader.readAsDataURL(file);
        fileUpload.value = '';
    });

    // ═══════════════════════════════════════
    // ═══════════════════════════════════════
    //  MICROPHONE — Native GemmaTranscription + WhatsApp Style
    // ═══════════════════════════════════════
    let audioStream = null;

    btnMic.addEventListener('click', () => {
        if (isRecording) {
            stopVoice();
        } else {
            startVoice();
        }
    });

    async function startVoice() {
        if (isSending) return;
        try {
            // Setup MediaRecorder for the voice note
            audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const opts = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? { mimeType: 'audio/webm;codecs=opus' }
                : MediaRecorder.isTypeSupported('audio/webm')
                ? { mimeType: 'audio/webm' }
                : {};
            mediaRecorder = new MediaRecorder(audioStream, opts);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
            
            mediaRecorder.onstop = async () => {
                // Stop mic stream
                if (audioStream) { audioStream.getTracks().forEach(t => t.stop()); audioStream = null; }
                
                const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
                if (blob.size < 1000) {
                    textInput.placeholder = 'כתוב לג\'ארביס...';
                    return; // Too short, ignore
                }

                // Show processing indicator
                btnMic.classList.add('transcribing');
                micIcon.className = 'fa-solid fa-cloud-arrow-up fa-bounce';
                textInput.placeholder = currentSTTMode === 'whisper' ? '⏳ מתמלל מקומית (Whisper-HE)...' : '⏳ מתמלל (Gemma4)...';

                try {
                    // Convert blob to base64
                    const arrayBuf = await blob.arrayBuffer();
                    const uint8 = new Uint8Array(arrayBuf);
                    let binary = '';
                    uint8.forEach(b => binary += String.fromCharCode(b));
                    const audio_b64 = btoa(binary);

                    // Send to backend to save the file and transcribe
                    const model = modelSelect.value || 'gemma4:e4b';
                    const stt_mode = currentSTTMode === 'whisper' ? 'whisper' : 'gemma';
                    const resp = await fetch('/api/transcribe_and_save', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ audio_b64, model, stt_mode })
                    });
                    const result = await resp.json();
                    
                    const transcript = (result.transcript || '').trim();
                    const finalAudioUrl = result.url || URL.createObjectURL(blob); // Fallback

                    if (transcript) {
                        // WhatsApp style: voice player + text below
                        const extras = `<div class="msg-audio" style="margin-top: 8px;">
                            <audio controls src="${finalAudioUrl}" style="height: 35px; border-radius: 20px;"></audio>
                        </div>`;
                        const chk = createUserMsg(transcript, extras);
                        sendToServer(transcript, [], chk);
                    } else {
                        textInput.placeholder = 'לא הצלחתי לזהות (Ollama Error), נסה שוב';
                        setTimeout(() => { textInput.placeholder = 'כתוב לג\'ארביס...'; }, 3000);
                    }
                } catch (err) {
                    textInput.placeholder = 'שגיאה: ' + err.message;
                    setTimeout(() => { textInput.placeholder = 'כתוב לג\'ארביס...'; }, 3500);
                } finally {
                    btnMic.classList.remove('transcribing');
                    micIcon.className = 'fa-solid fa-microphone';
                }
            };

            mediaRecorder.start();
            isRecording = true;
            btnMic.classList.add('recording');
            micIcon.className = 'fa-solid fa-stop';
            textInput.placeholder = '🔴 מקליט... לחץ שוב לעצירה';
        } catch (err) { alert('שגיאת מיקרופון: ' + err.message); }
    }

    function stopVoice() {
        if (!isRecording) return;
        isRecording = false;
        btnMic.classList.remove('recording');
        textInput.placeholder = '⏳ מתמלל...';
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop(); // Will trigger onstop → transcription
        }
    }

    // ═══════════════════════════════════════
    //  CONTINUOUS VOICE MODE (PHONE CALL)
    // ═══════════════════════════════════════
    let isVoiceModeActive = false;
    let continuousRecognition = null;

    const btnCall = document.getElementById('btn-call');
    const callIcon = document.getElementById('call-icon');
    let voiceCallStream = null;
    let voiceCallRecorder = null;

    function toggleVoiceMode() {
        isVoiceModeActive = !isVoiceModeActive;

        if (isVoiceModeActive) {
            btnCall.classList.add('recording');
            callIcon.className = 'fa-solid fa-phone-slash';
            textInput.placeholder = '📞 מצב שיחה פעיל — מאזין...';
            voiceCallListen(); // Start the loop
        } else {
            btnCall.classList.remove('recording');
            callIcon.className = 'fa-solid fa-phone';
            textInput.placeholder = 'כתוב לג\'ארביס...';
            if (voiceCallRecorder && voiceCallRecorder.state !== 'inactive') voiceCallRecorder.stop();
            if (voiceCallStream) { voiceCallStream.getTracks().forEach(t => t.stop()); voiceCallStream = null; }
        }
    }

    async function voiceCallListen() {
        if (!isVoiceModeActive || isSending || isPlayingTTS) {
            // Wait and retry
            if (isVoiceModeActive) setTimeout(voiceCallListen, 500);
            return;
        }
        try {
            voiceCallStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const chunks = [];
            const opts = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? { mimeType: 'audio/webm;codecs=opus' } : {};
            voiceCallRecorder = new MediaRecorder(voiceCallStream, opts);
            
            voiceCallRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
            voiceCallRecorder.onstop = async () => {
                if (voiceCallStream) { voiceCallStream.getTracks().forEach(t => t.stop()); voiceCallStream = null; }
                if (!isVoiceModeActive) return;
                
                const blob = new Blob(chunks, { type: voiceCallRecorder.mimeType || 'audio/webm' });
                if (blob.size < 2000) { voiceCallListen(); return; } // Too short
                
                textInput.placeholder = '📞 מעבד דיבור...';
                try {
                    const ab = await blob.arrayBuffer();
                    const uint8 = new Uint8Array(ab);
                    let bin = ''; uint8.forEach(b => bin += String.fromCharCode(b));
                    const b64 = btoa(bin);
                    
                    // Use local Whisper STT
                    const resp = await fetch('/api/stt', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ audio_b64: b64 })
                    });
                    const result = await resp.json();
                    const text = (result.text || '').trim();
                    
                    if (text) {
                        textInput.value = text;
                        triggerSend(); // Auto send
                    } else {
                        textInput.placeholder = '📞 לא זוהה דיבור — ממשיך להאזין...';
                        setTimeout(voiceCallListen, 300);
                    }
                } catch (e) {
                    console.warn('Voice call STT error:', e);
                    if (isVoiceModeActive) setTimeout(voiceCallListen, 500);
                }
            };
            
            voiceCallRecorder.start();
            textInput.placeholder = '📞 🔴 מאזין...';
            
            // Auto-stop after 8 seconds of recording
            setTimeout(() => {
                if (voiceCallRecorder && voiceCallRecorder.state !== 'inactive') {
                    voiceCallRecorder.stop();
                }
            }, 8000);
            
        } catch (e) {
            console.warn('Voice call mic error:', e);
            if (isVoiceModeActive) setTimeout(voiceCallListen, 1000);
        }
    }

    if(btnCall) btnCall.addEventListener('click', toggleVoiceMode);

    // ═══════════════════════════════════════
    //  SEND & INPUT
    // ═══════════════════════════════════════
    document.getElementById('btn-send').addEventListener('click', triggerSend);
    textInput.addEventListener('keypress', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); triggerSend(); }
    });

    // ═══════════════════════════════════════
    //  CTRL+V PASTE SUPPORT (IMAGES)
    // ═══════════════════════════════════════
    document.addEventListener('paste', e => {
        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
        for (let item of items) {
            if (item.type.indexOf('image/') === 0) {
                const blob = item.getAsFile();
                const reader = new FileReader();
                reader.onload = ev => {
                    currentImages.push(ev.target.result);
                    mediaPreview.classList.remove('hidden');
                    const w = document.createElement('div');
                    w.style.cssText = 'display:flex;align-items:center;gap:4px;';
                    w.innerHTML = `<img src="${ev.target.result}" class="thumb"><button class="remove-media" title="הסר"><i class="fa-solid fa-xmark"></i></button>`;
                    w.querySelector('.remove-media').onclick = () => {
                        const idx = currentImages.indexOf(ev.target.result);
                        if (idx > -1) currentImages.splice(idx, 1);
                        w.remove();
                        if (currentImages.length === 0) mediaPreview.classList.add('hidden');
                    };
                    mediaPreview.appendChild(w);
                };
                reader.readAsDataURL(blob);
            }
        }
    });

    function triggerSend() {
        if (isSending) return;
        const text = textInput.value.trim();
        if (!text && currentImages.length === 0) return;

        if (!modelSelect.value) {
            addError('יש לטעון מודל לפני שליחת הודעה.');
            return;
        }

        let extras = '';
        for (const img of currentImages) {
            if (img.startsWith('data:image'))
                extras += `<img src="${img}" class="msg-image">`;
        }

        const hasImages = currentImages.some(i => i.startsWith('data:image'));
        const chk = createUserMsg(text || '[תמונה]', extras);
        const imgs = [...currentImages];

        textInput.value = '';
        currentImages = [];
        mediaPreview.innerHTML = '';
        mediaPreview.classList.add('hidden');

        sendToServer(text, imgs, chk, hasImages);
    }

    async function sendToServer(text, images, checksEl, hasMedia = false) {
        if (isSending) return;
        isSending = true;
        const model = modelSelect.value;
        console.log(`[JARVIS] Sending to model: ${model}`);
        const t0 = Date.now();
        let firstToken = 0;

        liveMetrics.classList.remove('hidden');
        metricTps.textContent = '...';
        metricTime.textContent = '0s';
        const timer = setInterval(() => {
            metricTime.textContent = ((Date.now() - t0) / 1000).toFixed(0) + 's';
        }, 1000);

        const bot = createBotGroup();
        setStopMode(bot);

        // Store timer on bot for cleanup
        bot.timerID = timer;

        let thinkText = '';
        let respText = '';
        let gotContent = false;

        if (hasMedia) {
            bot.label.textContent = 'מנתח תמונה...';
            bot.spinner.className = 'fa-solid fa-image fa-beat spinner';
        }

        try {
            const visionMode = currentVisionMode;
            const resp = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    message: text, 
                    images, 
                    model, 
                    conv_id: currentConvId, 
                    vision_mode: currentVisionMode, 
                    stt_mode: currentSTTMode,
                    tts_mode: currentTTSMode,
                    engine: currentEngine 
                })
            });

            if (!resp.ok) {
                throw new Error(`Server returned ${resp.status}`);
            }

            if (checksEl) { checksEl.textContent = '✓✓'; checksEl.className = 'checks delivered'; }

            const reader = resp.body.getReader();
            const dec = new TextDecoder();
            let buf = '';
            let isDone = false;

            while (true) {
                if (!isSending) break;
                const { value, done } = await reader.read();
                if (done || !isSending) {
                    if (!isDone && isSending) {
                        // Stream ended unexpectedly (e.g. server restarted mid-generation)
                        throw new Error('Connection lost mid-generation');
                    }
                    break;
                }
                buf += dec.decode(value, { stream: true });
                const lines = buf.split('\n');
                buf = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    let d;
                    try { d = JSON.parse(line.substring(6)); } catch { continue; }

                    if (d.type === 'done' || d.type === 'error') {
                        isDone = true;
                    }

                    if (d.type === 'conv_id') {
                        currentConvId = d.id;
                        continue;
                    }
                    if (d.type === 'heartbeat') {
                        const elapsed = ((Date.now() - t0) / 1000).toFixed(0);
                        bot.label.textContent = hasMedia && !firstToken
                            ? `מנתח מדיה... (${elapsed}s)`
                            : `ממתין... (${elapsed}s)`;
                        continue;
                    }
                    if (d.type === 'status') continue;

                    if (checksEl && !checksEl.classList.contains('read')) {
                        checksEl.textContent = '✓✓';
                        checksEl.className = 'checks read';
                    }

                    if (firstToken === 0 && (d.type === 'thinking' || d.type === 'content')) {
                        firstToken = (Date.now() - t0) / 1000;
                        bot.label.textContent = `חושב...`;
                        bot.spinner.className = 'fa-solid fa-brain fa-beat spinner';
                    }

                    switch (d.type) {
                        case 'thinking':
                            thinkText += d.content;
                            // Trim leading/trailing blank lines
                            bot.body.textContent = thinkText.replace(/^\n+/, '').replace(/\n+$/, '');
                            if (bot.tw.classList.contains('collapsed')) {
                                bot.tw.classList.remove('collapsed');
                                bot.tw.classList.add('expanded');
                            }
                            // Auto-scroll inside think window to follow live output
                            bot.textBodyBase.scrollTop = bot.textBodyBase.scrollHeight;
                            break;

                        case 'think_end':
                            bot.label.textContent = 'מנסח תגובה...';
                            bot.spinner.className = 'fa-solid fa-check spinner';
                            bot.spinner.style.color = 'var(--green)';
                            bot.tw.classList.add('collapsed');
                            bot.tw.classList.remove('expanded');
                            break;

                        case 'content': {
                            if (!gotContent && bot.tw.classList.contains('expanded')) {
                                bot.tw.classList.add('collapsed');
                                bot.tw.classList.remove('expanded');
                            }
                            gotContent = true;
                            respText += d.content;

                            // Detect if we're streaming a JSON tool call
                            const stripped = stripJson(respText);
                            const looksLikeJson = respText.trimStart().startsWith('[{') || respText.trimStart().startsWith('{"tool"');
                            
                            if (looksLikeJson) {
                                // Hide the bubble — don't show raw JSON to user
                                bot.bubble.innerHTML = '';
                                bot.bubble.classList.add('hidden');
                                bot.label.textContent = 'מפעיל כלי...';
                                bot.spinner.className = 'fa-solid fa-bolt fa-beat spinner';
                                bot.spinner.style.color = '#facc15';
                                
                                // Try to detect tool name from partial JSON for early widget
                                const toolMatch = respText.match(/"tool"\s*:\s*"([^"]+)"/);
                                if (toolMatch) {
                                    const tName = toolMatch[1];
                                    if (!_pendingToolRows[tName]) {
                                        _pendingToolRows[tName] = showToolInProgress(tName, {});
                                    }
                                }
                            } else if (stripped) {
                                bot.bubble.classList.remove('hidden');
                                bot.bubble.innerHTML = renderMarkdownStream(stripped);
                                scroll(bot.row);
                            } else {
                                bot.bubble.innerHTML = '';
                            }
                            break;
                        }

                        case 'action_result':
                            addAction(d.tool, d.result);
                            break;

                        case 'tts_audio':
                            ttsAudioQueue.push(d.audio_b64);
                            if (!isPlayingTTS) playNextTTS();
                            break;

                        case 'narration': {
                            // Show narration as a styled status line
                            const narRow = document.createElement('div');
                            narRow.className = 'msg-row bot narration-row';
                            narRow.innerHTML = `<div class="narration-bubble"><i class="fa-solid fa-robot"></i> ${esc(d.content)}</div>`;
                            chatBox.appendChild(narRow);
                            scroll(narRow);
                            break;
                        }

                        case 'agent_vision': {
                            bot.tw.classList.add('wide-agent-dash', 'expanded');
                            bot.tw.classList.remove('collapsed');
                            bot.row.classList.add('dash-mode');
                            bot.imgCol.style.display = 'flex';
                            
                            const visionImg = document.createElement('img');
                            visionImg.src = `data:image/png;base64,${d.image}`;
                            visionImg.alt = "Agent Vision";
                            bot.imgCol.prepend(visionImg);
                            
                            // Scroll the text body to keep image and text in view
                            bot.textBodyBase.scrollTop = bot.textBodyBase.scrollHeight;
                            scroll(bot.row);
                            break;
                        }

                        case 're_think':
                            if (respText.trim() && !bot.bubble.classList.contains('hidden')) {
                                addCopyIcon(bot.bubble, stripJson(respText).trim());
                            }
                            thinkText += '\n── מעבד תוצאות... ──\n';
                            bot.body.textContent = thinkText;
                            bot.label.textContent = 'מעבד...';
                            bot.spinner.className = 'fa-solid fa-circle-notch fa-spin spinner';
                            bot.spinner.style.color = 'var(--primary)';
                            gotContent = false;
                            respText = '';
                            const newBub = document.createElement('div');
                            newBub.className = 'msg-bubble hidden';
                            bot.row.appendChild(newBub);
                            bot.bubble = newBub;
                            break;
                        case 'intermediate_done': {
                            const tps = d.metrics?.tps ? d.metrics.tps.toFixed(1) : '?';
                            const total = ((Date.now() - t0) / 1000).toFixed(1);
                            bot.label.textContent = 'מפעיל כלי...';
                            bot.ttime.textContent = `${total}s · ${tps} tok/s`;
                            bot.spinner.className = 'fa-solid fa-cogs fa-spin spinner';
                            bot.spinner.style.color = '#facc15';
                            break;
                        }

                        case 'done': {
                            const tps = d.metrics?.tps ? d.metrics.tps.toFixed(1) : '?';
                            const total = ((Date.now() - t0) / 1000).toFixed(1);
                            bot.label.textContent = 'הושלם';
                            bot.ttime.textContent = `${total}s · ${tps} tok/s`;
                            bot.spinner.className = 'fa-solid fa-check spinner';
                            bot.spinner.style.color = 'var(--green)';
                            bot.tw.classList.add('collapsed');
                            bot.tw.classList.remove('expanded');
                            metricTps.textContent = tps + ' tok/s';
                            metricTime.textContent = total + 's';
                            if (respText.trim() && !bot.bubble.classList.contains('hidden')) {
                                // Final render: full markdown with citations
                                const finalText = stripJson(respText).trim();
                                bot.bubble.innerHTML = renderMarkdown(finalText);
                                addCopyIcon(bot.bubble, finalText);
                            }
                            checkModelStatus();
                            break;
                        }

                        case 'error':
                            addError(d.content);
                            break;
                    }
                }
            }
        } catch (err) {
            if (isSending) {
                addError('שגיאת תקשורת: ' + err.message);
                if (bot) {
                    bot.label.textContent = 'שגיאת רשת';
                    bot.spinner.className = 'fa-solid fa-triangle-exclamation';
                    bot.spinner.style.color = 'var(--red)';
                    if (bot.tw) {
                        bot.tw.classList.add('collapsed');
                        bot.tw.classList.remove('expanded');
                    }
                }
            }

        } finally {
            clearInterval(timer);
            isSending = false;
            resetSendButton();
        }
    }

    // ═══════════════════════════════════════
    //  TERMINAL OVERLAY
    // ═══════════════════════════════════════
    const btnTerminal = document.getElementById('btn-terminal');
    const terminalOverlay = document.getElementById('terminal-overlay');
    const terminalClose = document.getElementById('terminal-close');
    const terminalOutput = document.getElementById('terminal-output');
    const terminalInput = document.getElementById('terminal-input');
    let terminalPollInterval = null;

    if (terminalInput) {
        terminalInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                const cmd = terminalInput.value.trim();
                if (!cmd) return;
                terminalInput.value = '';
                try {
                    await fetch('/api/terminal/input', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ command: cmd })
                    });
                } catch(err) {}
            }
        });
    }

    btnTerminal.addEventListener('click', () => {
        const isHidden = terminalOverlay.classList.contains('hidden');
        if (isHidden) {
            terminalOverlay.classList.remove('hidden');
            startTerminalPolling();
        } else {
            terminalOverlay.classList.add('hidden');
            stopTerminalPolling();
        }
    });

    terminalClose.addEventListener('click', () => {
        terminalOverlay.classList.add('hidden');
        stopTerminalPolling();
    });

    // Terminal copy button
    const terminalCopy = document.getElementById('terminal-copy');
    if (terminalCopy) {
        terminalCopy.addEventListener('click', () => {
            const text = terminalOutput.innerText || terminalOutput.textContent;
            navigator.clipboard.writeText(text).then(() => {
                terminalCopy.innerHTML = '<i class="fa-solid fa-check"></i>';
                terminalCopy.title = 'הועתק!';
                setTimeout(() => {
                    terminalCopy.innerHTML = '<i class="fa-regular fa-copy"></i>';
                    terminalCopy.title = 'העתק לוג';
                }, 2000);
            }).catch(() => {
                // Fallback for pywebview where clipboard API may not work
                const range = document.createRange();
                range.selectNodeContents(terminalOutput);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                document.execCommand('copy');
                sel.removeAllRanges();
                terminalCopy.innerHTML = '<i class="fa-solid fa-check"></i>';
                setTimeout(() => {
                    terminalCopy.innerHTML = '<i class="fa-regular fa-copy"></i>';
                }, 2000);
            });
        });
    }

    function startTerminalPolling() {
        if (terminalPollInterval) return;
        
        // Use fetch polling instead of SSE — more reliable in pywebview
        async function pollLogs() {
            try {
                const r = await fetch('/api/logs/poll');
                const d = await r.json();
                if (d.logs) {
                    const isScrolledToBottom = terminalOutput.scrollHeight - terminalOutput.clientHeight <= terminalOutput.scrollTop + 30;
                    const lines = d.logs.split('\n');
                    terminalOutput.innerHTML = lines.map(line => `<div class="log-line">${esc(line)}</div>`).join('');
                    if (isScrolledToBottom) {
                        terminalOutput.scrollTop = terminalOutput.scrollHeight;
                    }
                }
            } catch (err) { /* server not ready yet */ }
        }
        pollLogs(); // Initial load
        terminalPollInterval = setInterval(pollLogs, 1000);
    }

    function stopTerminalPolling() {
        if (terminalPollInterval) {
            clearInterval(terminalPollInterval);
            terminalPollInterval = null;
        }
    }

});
