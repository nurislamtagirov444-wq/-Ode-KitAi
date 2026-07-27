const DEFAULT_SETTINGS = {
  model: 'llama3.2:1b',
  temperature: 0.4,
  num_ctx: 4096,
  num_predict: 512,
  systemPrompt: ''
};

const PRESETS = [
  {
    title: 'Стратег-архитектор',
    description: 'Разбор цели, вариантов, рисков и пошаговый план для новичка.',
    prompt: `Ты — агент-архитектор и стратег-практик. Отвечай на русском, по полочкам и без эмодзи. Не обещай невозможное. Для сложных задач используй структуру: [ЦЕЛЬ], [ДАННЫЕ], [ВАРИАНТЫ], [ПРОВЕРКА ДЫР], [ВЫБОР], [ШАГИ С НУЛЯ], [ЕСЛИ НЕ РАБОТАЕТ], [СЛЕДУЮЩИЙ ЗАПРОС]. Не раскрывай скрытую цепочку мыслей, показывай только проверяемый открытый разбор.`
  },
  {
    title: 'GitHub-аудитор',
    description: 'Проверяет README, установку, зависимости, лицензию и риски репозитория.',
    prompt: `Ты — GitHub-аудитор для новичка. Когда пользователь даёт ссылку на репозиторий, объясни что это, как ставить, какие зависимости, какая лицензия, какие риски, подходит ли проект для локального AI-kit и Android. Не запускай подозрительный код без подтверждения. Не проси токены и пароли.`
  },
  {
    title: 'Android без лагов',
    description: 'Делает план, где Android — экран, а модель работает на ПК или облаке.',
    prompt: `Ты — помощник по Android-доступу к локальному AI. Объясняй, что тяжёлую модель лучше запускать на ПК, VPS или облачном ПК, а телефон использовать как веб-интерфейс. Давай команды для локальной сети, Tailscale/ZeroTier и предупреждай не открывать порты в интернет без защиты.`
  },
  {
    title: 'Локальный AI без платного API',
    description: 'Подбирает Ollama/Open WebUI/llama.cpp без упора на платные сервисы.',
    prompt: `Ты — помощник по локальному AI без платного API. Предлагай Llama, Mistral, Gemma, Phi и GGUF-варианты через Ollama или llama.cpp. Не рекомендуй Qwen и DeepSeek по умолчанию. Честно говори про ограничения RAM, VRAM, скорости и качества.`
  }
];

const els = {
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
  checkStatusBtn: document.getElementById('checkStatusBtn'),
  chatLog: document.getElementById('chatLog'),
  chatForm: document.getElementById('chatForm'),
  userInput: document.getElementById('userInput'),
  sendBtn: document.getElementById('sendBtn'),
  clearChatBtn: document.getElementById('clearChatBtn'),
  modelInput: document.getElementById('modelInput'),
  temperatureInput: document.getElementById('temperatureInput'),
  contextInput: document.getElementById('contextInput'),
  predictInput: document.getElementById('predictInput'),
  systemPromptInput: document.getElementById('systemPromptInput'),
  saveSettingsBtn: document.getElementById('saveSettingsBtn'),
  resetSettingsBtn: document.getElementById('resetSettingsBtn'),
  presetGrid: document.getElementById('presetGrid'),
  modsGrid: document.getElementById('modsGrid'),
  modSearch: document.getElementById('modSearch'),
  messageTemplate: document.getElementById('messageTemplate')
};

let messages = [];
let mods = [];

function toast(text) {
  const node = document.createElement('div');
  node.className = 'toast';
  node.textContent = text;
  document.body.appendChild(node);
  window.setTimeout(() => node.remove(), 2600);
}

function loadSettings() {
  const raw = localStorage.getItem('ode-kitai-settings');
  if (!raw) return { ...DEFAULT_SETTINGS };
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

function readSettingsFromForm() {
  return {
    model: els.modelInput.value.trim() || DEFAULT_SETTINGS.model,
    temperature: Number(els.temperatureInput.value || DEFAULT_SETTINGS.temperature),
    num_ctx: Number(els.contextInput.value || DEFAULT_SETTINGS.num_ctx),
    num_predict: Number(els.predictInput.value || DEFAULT_SETTINGS.num_predict),
    systemPrompt: els.systemPromptInput.value.trim()
  };
}

function saveSettings() {
  const settings = readSettingsFromForm();
  localStorage.setItem('ode-kitai-settings', JSON.stringify(settings));
  toast('Настройки сохранены');
}

function applySettings(settings) {
  els.modelInput.value = settings.model;
  els.temperatureInput.value = settings.temperature;
  els.contextInput.value = settings.num_ctx;
  els.predictInput.value = settings.num_predict;
  els.systemPromptInput.value = settings.systemPrompt;
}

function addMessage(role, content) {
  const node = els.messageTemplate.content.firstElementChild.cloneNode(true);
  node.classList.add(role);
  node.querySelector('.message-role').textContent = role;
  node.querySelector('.message-content').textContent = content;
  els.chatLog.appendChild(node);
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
}

function renderConversation() {
  els.chatLog.innerHTML = '';
  if (messages.length === 0) {
    addMessage('system', 'Готов. Если Ollama запущен, можно писать. Для старта спроси: «Составь нулевую настройку локального AI для Android и облачного ПК 16 GB RAM».');
    return;
  }
  for (const item of messages) addMessage(item.role, item.content);
}

async function checkStatus() {
  els.statusDot.className = 'dot';
  els.statusText.textContent = 'Проверяю Ollama...';
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    if (data.ollama_reachable) {
      els.statusDot.className = 'dot ok';
      els.statusText.textContent = `Ollama доступен. Моделей: ${data.models_count}`;
      return;
    }
    els.statusDot.className = 'dot bad';
    els.statusText.textContent = 'Ollama не отвечает. Запусти docker compose up -d или Ollama.';
  } catch (error) {
    els.statusDot.className = 'dot bad';
    els.statusText.textContent = `Сайт работает, но health недоступен: ${error.message}`;
  }
}

async function sendMessage(text) {
  const settings = readSettingsFromForm();
  const outgoing = [];
  if (settings.systemPrompt) outgoing.push({ role: 'system', content: settings.systemPrompt });
  outgoing.push(...messages, { role: 'user', content: text });

  messages.push({ role: 'user', content: text });
  renderConversation();
  els.sendBtn.disabled = true;
  els.sendBtn.textContent = 'Думаю...';

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: settings.model,
        messages: outgoing,
        options: {
          temperature: settings.temperature,
          num_ctx: settings.num_ctx,
          num_predict: settings.num_predict
        }
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || data.details || 'Ошибка ответа от сервера');
    const content = data.message?.content || JSON.stringify(data, null, 2);
    messages.push({ role: 'assistant', content });
  } catch (error) {
    messages.push({
      role: 'assistant',
      content: `Не получилось получить ответ. Проверь, что Ollama запущен и модель скачана.\n\nОшибка: ${error.message}\n\nКоманды:\ndocker compose up -d\n./scripts/pull-model.sh ${settings.model}`
    });
  } finally {
    renderConversation();
    els.sendBtn.disabled = false;
    els.sendBtn.textContent = 'Отправить';
  }
}

function renderPresets() {
  els.presetGrid.innerHTML = '';
  for (const preset of PRESETS) {
    const card = document.createElement('article');
    card.className = 'preset-card';
    card.innerHTML = `
      <h3></h3>
      <p></p>
      <button class="secondary" type="button">Включить режим</button>
    `;
    card.querySelector('h3').textContent = preset.title;
    card.querySelector('p').textContent = preset.description;
    card.querySelector('button').addEventListener('click', () => {
      els.systemPromptInput.value = preset.prompt;
      saveSettings();
    });
    els.presetGrid.appendChild(card);
  }
}

function commandForMod(mod) {
  return `./scripts/clone-mod.sh ${mod.repo}`;
}

function renderMods(filter = '') {
  const q = filter.trim().toLowerCase();
  els.modsGrid.innerHTML = '';
  const visible = mods.filter((mod) => {
    const haystack = [mod.name, mod.category, mod.description, ...(mod.tags || [])].join(' ').toLowerCase();
    return !q || haystack.includes(q);
  });

  if (visible.length === 0) {
    els.modsGrid.innerHTML = '<p class="muted">Ничего не найдено.</p>';
    return;
  }

  for (const mod of visible) {
    const card = document.createElement('article');
    card.className = 'mod-card';
    const tags = (mod.tags || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('');
    card.innerHTML = `
      <h3>${escapeHtml(mod.name)}</h3>
      <p>${escapeHtml(mod.description)}</p>
      <div class="tags">${tags}</div>
      <p class="muted"><strong>Риск:</strong> ${escapeHtml(mod.risk)}</p>
      <div class="mod-actions">
        <a href="${mod.repo}" target="_blank" rel="noopener noreferrer">GitHub</a>
        <button class="secondary copy-command" type="button">Копировать clone</button>
        <button class="secondary ask-command" type="button">Запрос агенту</button>
      </div>
    `;
    card.querySelector('.copy-command').addEventListener('click', async () => {
      await navigator.clipboard.writeText(commandForMod(mod));
      toast('Команда клонирования скопирована');
    });
    card.querySelector('.ask-command').addEventListener('click', async () => {
      const prompt = `Прочитай GitHub-репозиторий: ${mod.repo}\n\nСделай:\n1. объясни, что это;\n2. проверь README, установку, зависимости, лицензии;\n3. найди риски и логические дыры;\n4. скажи, подходит ли это для Android/локального AI-kit;\n5. если подходит — дай пошаговую установку с нуля;\n6. не запускай подозрительный код без моего подтверждения.`;
      await navigator.clipboard.writeText(prompt);
      toast('Запрос агенту скопирован');
    });
    els.modsGrid.appendChild(card);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function loadSystemPromptIfEmpty(settings) {
  if (settings.systemPrompt) return settings;
  try {
    const response = await fetch('/prompts/system-ru.txt');
    if (response.ok) {
      settings.systemPrompt = (await response.text()).trim();
    }
  } catch {
    // Не критично: пользователь может выбрать preset вручную.
  }
  return settings;
}

async function loadMods() {
  try {
    const response = await fetch('/config/mods.json');
    mods = await response.json();
  } catch {
    mods = [];
  }
  renderMods();
}

function bindEvents() {
  els.chatForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = els.userInput.value.trim();
    if (!text) return;
    els.userInput.value = '';
    sendMessage(text);
  });

  els.userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      els.chatForm.requestSubmit();
    }
  });

  els.clearChatBtn.addEventListener('click', () => {
    messages = [];
    renderConversation();
  });

  els.saveSettingsBtn.addEventListener('click', saveSettings);
  els.resetSettingsBtn.addEventListener('click', async () => {
    localStorage.removeItem('ode-kitai-settings');
    const settings = await loadSystemPromptIfEmpty({ ...DEFAULT_SETTINGS });
    applySettings(settings);
    toast('Настройки сброшены');
  });
  els.checkStatusBtn.addEventListener('click', checkStatus);
  els.modSearch.addEventListener('input', () => renderMods(els.modSearch.value));
}

async function init() {
  const settings = await loadSystemPromptIfEmpty(loadSettings());
  applySettings(settings);
  renderConversation();
  renderPresets();
  await loadMods();
  bindEvents();
  checkStatus();
}

init();
