document.addEventListener('DOMContentLoaded', () => {
  const API_BASE = '/api';
  
  // State
  let currentChatId = null;
  let currentModel = 'ChatGPT v4.0';
  let isRecording = false;
  let recognition = null;
  
  // DOM Elements
  const heroView = document.getElementById('hero-view');
  const chatMessagesView = document.getElementById('chat-messages-view');
  const promptInput = document.getElementById('prompt-input');
  const sendBtn = document.getElementById('send-btn');
  const micBtn = document.getElementById('mic-btn');
  const newChatBtn = document.getElementById('new-chat-btn');
  const modelDropdownBtn = document.getElementById('model-dropdown-btn');
  const modelDropdownMenu = document.getElementById('model-dropdown-menu');
  const currentModelLabel = document.getElementById('current-model-label');
  const historyList = document.getElementById('history-list');
  
  // Modals
  const configModal = document.getElementById('config-modal');
  const exportModal = document.getElementById('export-modal');
  const openConfigBtn = document.getElementById('open-config-btn');
  const closeConfigBtn = document.getElementById('close-config-btn');
  const saveConfigBtn = document.getElementById('save-config-btn');
  const openExportBtn = document.getElementById('open-export-btn');
  const closeExportBtn = document.getElementById('close-export-btn');

  // Load Initial Data
  fetchOllamaStatus();
  fetchOllamaModels();
  fetchConfig();
  fetchChatHistory();

  // Temperature Slider Sync
  const cfgTemp = document.getElementById('cfg-temp');
  const tempVal = document.getElementById('temp-val');
  if (cfgTemp && tempVal) {
    cfgTemp.addEventListener('input', () => {
      tempVal.textContent = cfgTemp.value;
    });
  }

  // Model Pull Handler
  const pullBtn = document.getElementById('ollama-pull-btn');
  const pullInput = document.getElementById('ollama-pull-name');
  const pullStatusMsg = document.getElementById('pull-status-msg');

  if (pullBtn && pullInput) {
    pullBtn.addEventListener('click', async () => {
      const modelName = pullInput.value.trim();
      if (!modelName) return;

      pullBtn.disabled = true;
      pullBtn.textContent = 'Pulling...';
      pullStatusMsg.classList.remove('hidden');
      pullStatusMsg.textContent = `Starting pull for ${modelName}...`;

      try {
        const response = await fetch(`${API_BASE}/ollama/pull`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: modelName })
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          if (chunk.includes('percent')) {
            try {
              const line = chunk.split('\n\n')[0].replace('data: ', '');
              const parsed = JSON.parse(line);
              pullStatusMsg.textContent = `${parsed.status} (${parsed.percent}%)`;
            } catch (e) {}
          }
        }
        pullStatusMsg.textContent = `Successfully pulled ${modelName}!`;
        fetchOllamaModels();
      } catch (err) {
        pullStatusMsg.textContent = `Failed to pull ${modelName}.`;
      } finally {
        pullBtn.disabled = false;
        pullBtn.textContent = 'Pull';
        pullInput.value = '';
      }
    });
  }

  async function fetchOllamaStatus() {
    const badge = document.getElementById('ollama-status-badge');
    if (!badge) return;
    try {
      const res = await fetch(`${API_BASE}/ollama/status`);
      const data = await res.json();
      if (data.running) {
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-900/40 text-green-300 border border-green-500/30';
        badge.textContent = `Connected (${data.version || 'Ollama'})`;
      } else {
        badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-yellow-900/40 text-yellow-300 border border-yellow-500/30';
        badge.textContent = 'Offline (Fallback Mode)';
      }
    } catch (e) {
      badge.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-900/40 text-red-300 border border-red-500/30';
      badge.textContent = 'Offline';
    }
  }

  async function fetchOllamaModels() {
    try {
      const res = await fetch(`${API_BASE}/ollama/models`);
      const models = await res.json();
      if (models && models.length > 0) {
        modelDropdownMenu.innerHTML = '';
        models.forEach((m, idx) => {
          const btn = document.createElement('button');
          btn.className = `model-opt w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-purple-600/20 text-gray-300 transition flex items-center justify-between`;
          btn.dataset.model = m.name;
          btn.innerHTML = `<span>${m.name} <span class="text-[10px] text-purple-400 font-mono">(${m.size})</span></span>`;
          if (idx === 0) {
            btn.classList.add('text-white');
            btn.innerHTML += ` <i class="fa-solid fa-check text-purple-400"></i>`;
            currentModel = m.name;
            currentModelLabel.textContent = m.name;
          }
          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            currentModel = m.name;
            currentModelLabel.textContent = currentModel;
            modelDropdownMenu.classList.add('hidden');
            document.querySelectorAll('.model-opt i').forEach(icon => icon.remove());
            btn.innerHTML += ` <i class="fa-solid fa-check text-purple-400"></i>`;
          });
          modelDropdownMenu.appendChild(btn);
        });
      }
    } catch (e) {
      console.warn('Failed to fetch Ollama models dynamically');
    }
  }


  // Model Selector Toggle
  modelDropdownBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    modelDropdownMenu.classList.toggle('hidden');
  });
  
  document.addEventListener('click', () => {
    modelDropdownMenu.classList.add('hidden');
  });

  document.querySelectorAll('.model-opt').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      currentModel = btn.dataset.model;
      currentModelLabel.textContent = currentModel;
      modelDropdownMenu.classList.add('hidden');
      
      // Update check icons
      document.querySelectorAll('.model-opt i').forEach(icon => icon.remove());
      btn.innerHTML += ` <i class="fa-solid fa-check text-purple-400"></i>`;
    });
  });

  // Action Chips & Feature Cards
  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      promptInput.value = btn.dataset.prompt;
      promptInput.focus();
    });
  });

  document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('click', () => {
      const title = card.querySelector('h4').textContent;
      promptInput.value = `Help me with ${title}: `;
      promptInput.focus();
    });
  });

  // New Chat Button
  newChatBtn.addEventListener('click', () => {
    currentChatId = null;
    chatMessagesView.innerHTML = '';
    chatMessagesView.classList.add('hidden');
    heroView.classList.remove('hidden');
    promptInput.value = '';
  });

  // Configuration Modal Handlers
  openConfigBtn.addEventListener('click', () => configModal.classList.remove('hidden'));
  closeConfigBtn.addEventListener('click', () => configModal.classList.add('hidden'));
  saveConfigBtn.addEventListener('click', async () => {
    const configData = {
      model: document.getElementById('cfg-model').value,
      search_provider: document.getElementById('cfg-search').value,
      automation_mode: document.getElementById('cfg-automation').value
    };
    await fetch(`${API_BASE}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configData)
    });
    configModal.classList.add('hidden');
  });

  // Export Modal Handlers
  openExportBtn.addEventListener('click', () => exportModal.classList.remove('hidden'));
  closeExportBtn.addEventListener('click', () => exportModal.classList.add('hidden'));
  
  document.querySelectorAll('.export-opt').forEach(btn => {
    btn.addEventListener('click', () => {
      const format = btn.dataset.format;
      exportChat(format);
      exportModal.classList.add('hidden');
    });
  });

  // Microphone Voice Input
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      promptInput.value += (promptInput.value ? ' ' : '') + transcript;
      stopRecording();
    };

    recognition.onerror = stopRecording;
    recognition.onend = stopRecording;
  }

  micBtn.addEventListener('click', () => {
    if (!recognition) {
      alert('Speech Recognition is not supported in this browser.');
      return;
    }
    if (isRecording) {
      recognition.stop();
      stopRecording();
    } else {
      recognition.start();
      isRecording = true;
      micBtn.classList.add('bg-red-600', 'text-white', 'recording-pulse');
      micBtn.classList.remove('bg-[#20143D]');
    }
  });

  function stopRecording() {
    isRecording = false;
    micBtn.classList.remove('bg-red-600', 'text-white', 'recording-pulse');
    micBtn.classList.add('bg-[#20143D]');
  }

  // Send Message & Streaming Logic
  sendBtn.addEventListener('click', handleSendMessage);
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  async function handleSendMessage() {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    promptInput.value = '';
    
    // Show chat view, hide hero
    heroView.classList.add('hidden');
    chatMessagesView.classList.remove('hidden');

    // Create Chat session on server if new
    if (!currentChatId) {
      const res = await fetch(`${API_BASE}/chats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: prompt.slice(0, 25), model: currentModel })
      });
      const data = await res.json();
      currentChatId = data.id;
      fetchChatHistory();
    }

    // Append User Message UI
    appendMessageUI('user', prompt);

    // Create placeholder for Assistant Response
    const assistantMsgEl = appendMessageUI('assistant', '');
    const textContainer = assistantMsgEl.querySelector('.msg-text');
    const toolContainer = assistantMsgEl.querySelector('.tool-status');

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: currentChatId, prompt: prompt, model: currentModel })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep last incomplete chunk

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.replace('data: ', '').trim();
            if (!jsonStr) continue;
            try {
              const event = JSON.parse(jsonStr);
              if (event.type === 'token') {
                textContainer.innerHTML += event.content;
              } else if (event.type === 'tool_start') {
                toolContainer.classList.remove('hidden');
                toolContainer.innerHTML = `<span class="inline-flex items-center text-xs text-purple-400 bg-purple-900/30 px-2.5 py-1 rounded-full border border-purple-500/20"><i class="fa-solid fa-spinner fa-spin mr-1.5"></i> ${event.status}</span>`;
              } else if (event.type === 'tool_end') {
                toolContainer.innerHTML = `<span class="inline-flex items-center text-xs text-green-400 bg-green-900/30 px-2.5 py-1 rounded-full border border-green-500/20"><i class="fa-solid fa-circle-check mr-1.5"></i> ${event.name} executed</span>`;
              } else if (event.type === 'image') {
                const imgEl = document.createElement('img');
                imgEl.src = event.url;
                imgEl.className = 'mt-3 rounded-xl max-w-sm border border-purple-500/30 shadow-lg';
                textContainer.appendChild(imgEl);
              }
            } catch (e) {
              console.error('SSE JSON error', e);
            }
          }
        }
      }

      // Voice TTS output if enabled
      speakText(textContainer.textContent);

    } catch (err) {
      textContainer.innerHTML = `<span class="text-red-400">Error connecting to assistant server.</span>`;
    }
  }

  function appendMessageUI(role, content) {
    const msgWrapper = document.createElement('div');
    msgWrapper.className = `flex space-x-3 mb-4 ${role === 'user' ? 'justify-end' : 'justify-start'}`;

    if (role === 'user') {
      msgWrapper.innerHTML = `
        <div class="bg-[#2E1A54] text-white px-4 py-2.5 rounded-2xl rounded-tr-none text-sm max-w-lg border border-purple-500/30 shadow-md">
          ${content}
        </div>
      `;
    } else {
      msgWrapper.innerHTML = `
        <div class="w-7 h-7 rounded-full bg-purple-600 flex items-center justify-center text-xs text-white shadow-md flex-shrink-0 mt-1">
          <i class="fa-solid fa-sparkles"></i>
        </div>
        <div class="bg-[#180F30] text-gray-200 px-4 py-3 rounded-2xl rounded-tl-none text-sm max-w-xl border border-[#2B1B4F] shadow-md space-y-2">
          <div class="tool-status hidden"></div>
          <div class="msg-text leading-relaxed">${content}</div>
        </div>
      `;
    }

    chatMessagesView.appendChild(msgWrapper);
    chatMessagesView.scrollTop = chatMessagesView.scrollHeight;
    return msgWrapper;
  }

  function speakText(text) {
    if ('speechSynthesis' in window && text) {
      const utterance = new SpeechSynthesisUtterance(text.slice(0, 200));
      utterance.rate = 1.0;
      speechSynthesis.speak(utterance);
    }
  }

  async function fetchConfig() {
    try {
      const res = await fetch(`${API_BASE}/config`);
      const data = await res.json();
      if (data.model) {
        currentModel = data.model;
        currentModelLabel.textContent = currentModel;
      }
    } catch (e) {
      console.warn('Config fetch failed');
    }
  }

  async function fetchChatHistory() {
    try {
      const res = await fetch(`${API_BASE}/chats`);
      const chats = await res.json();
      historyList.innerHTML = `
        <button id="new-proj-btn" class="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition">
          <i class="fa-regular fa-folder-plus text-purple-400"></i>
          <span>New Project</span>
        </button>
      `;
      chats.forEach(chat => {
        const item = document.createElement('button');
        item.className = 'w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:text-white hover:bg-white/5 transition text-left text-xs truncate';
        item.innerHTML = `<i class="fa-regular fa-comment text-gray-400"></i> <span class="truncate">${chat.title}</span>`;
        item.addEventListener('click', () => loadChatSession(chat.id));
        historyList.appendChild(item);
      });
    } catch (e) {
      console.warn('History fetch failed');
    }
  }

  async function loadChatSession(chatId) {
    currentChatId = chatId;
    heroView.classList.add('hidden');
    chatMessagesView.classList.remove('hidden');
    chatMessagesView.innerHTML = '';

    const res = await fetch(`${API_BASE}/chats/${chatId}`);
    const data = await res.json();

    data.messages.forEach(msg => {
      appendMessageUI(msg.role, msg.content);
    });
  }

  function exportChat(format) {
    const text = Array.from(chatMessagesView.children).map(el => el.textContent.trim()).join('\n\n');
    let blob, filename;

    if (format === 'json') {
      blob = new Blob([JSON.stringify({ chatId: currentChatId, content: text }, null, 2)], { type: 'application/json' });
      filename = 'zyricon-chat.json';
    } else {
      blob = new Blob([text], { type: 'text/plain' });
      filename = `zyricon-chat.${format === 'markdown' ? 'md' : 'txt'}`;
    }

    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  }
});
