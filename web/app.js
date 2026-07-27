const PROVIDER_DEFAULTS = {
  pollinations: 'mistral',
  puter: 'anthropic/claude-sonnet-4-5',
  openrouter: 'meta-llama/llama-3.3-70b-instruct:free',
  groq: 'llama-3.3-70b-versatile',
  'custom-openai': 'model-name-here',
  ollama: 'llama3.2:1b'
};

const PROVIDER_HINTS = {
  pollinations: 'Не скачивает модель. Работает через интернет. Без ключа используется простой бесплатный text endpoint; стабильность и лимиты не гарантируются.',
  puter: 'Не скачивает модель. Работает прямо в браузере через Puter.js и может попросить вход в Puter. Сервер и API key не нужны.',
  openrouter: 'Не скачивает модель. Нужен OPENROUTER_API_KEY в переменной окружения сервера. Не вставляй ключ в чат.',
  groq: 'Не скачивает модель. Нужен GROQ_API_KEY в переменной окружения сервера. Не вставляй ключ в чат.',
  'custom-openai': 'Не скачивает модель. Нужен OPENAI_COMPATIBLE_BASE_URL, например свой gateway или совместимый API.',
  ollama: 'Локальный режим. Нужен Ollama и скачанная модель. Выбирай только если готов запускать модель на ПК.'
};

const DEFAULT_SETTINGS = {
  provider: 'puter',
  model: PROVIDER_DEFAULTS.puter,
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
    prompt: `Ты — помощник по Android-доступу к AI. Если пользователь не хочет скачивать модель, предлагай no-download провайдеры: Pollinations, Puter.js, OpenRouter/Groq с ключом. Если пользователь хочет локально — объясняй Ollama/Open WebUI. Давай команды для локальной сети, Tailscale/ZeroTier и предупреждай не открывать порты в интернет без защиты.`
  },
  {
    title: 'AI без скачивания модели',
    description: 'Использует удалённые бесплатные или free-tier провайдеры вместо локальной модели.',
    prompt: `Ты — помощник по AI без скачивания моделей. Главная стратегия: сайт на Android/ПК + remote provider. Сначала пробуй Pollinations или Puter.js без серверного ключа, затем OpenRouter/Groq/Gemini через ключи, если пользователь сам их настроит. Не обещай абсолютный безлимит. Объясняй лимиты в запросах, токенах, скорости и правилах сервиса.`
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
  providerInput: document.getElementById('providerInput'),
  providerHint: document.getElementById('providerHint'),
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
let puterScriptPromise = null;

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
  const provider = els.providerInput.value || DEFAULT_SETTINGS.provider;
  return {
    provider,
    model: els.modelInput.value.trim() || PROVIDER_DEFAULTS[provider] || DEFAULT_SETTINGS.model,
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

function updateProviderHint() {
  const provider = els.providerInput.value || DEFAULT_SETTINGS.provider;
  els.providerHint.textContent = PROVIDER_HINTS[provider] || '';
}

function applySettings(settings) {
  els.providerInput.value = settings.provider || DEFAULT_SETTINGS.provider;
  els.modelInput.value = settings.model || PROVIDER_DEFAULTS[els.providerInput.value] || DEFAULT_SETTINGS.model;
  els.temperatureInput.value = settings.temperature;
  els.contextInput.value = settings.num_ctx;
  els.predictInput.value = settings.num_predict;
  els.systemPromptInput.value = settings.systemPrompt;
  updateProviderHint();
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
    addMessage('system', 'Готов. По умолчанию включён no-download режим Puter.js: модель скачивать не надо. Он работает в браузере и может попросить вход в Puter. Если не подходит, выбери Pollinations или OpenRouter/Groq через env key. Для старта спроси: «Сделай нулевую настройку бесплатного AI на Android без скачивания модели».');
    return;
  }
  for (const item of messages) addMessage(item.role, item.content);
}

async function checkStatus() {
  const provider = els.providerInput.value || DEFAULT_SETTINGS.provider;
  els.statusDot.className = 'dot';

  if (provider === 'pollinations') {
    els.statusDot.className = 'dot ok';
    els.statusText.textContent = 'No-download режим: Pollinations. Ollama не нужен. Нужен интернет.';
    return;
  }
  if (provider === 'puter') {
    els.statusDot.className = 'dot ok';
    els.statusText.textContent = 'No-download режим: Puter.js. Ollama не нужен. Может потребоваться вход в Puter.';
    return;
  }
  if (['openrouter', 'groq', 'custom-openai'].includes(provider)) {
    try {
      const response = await fetch('/api/providers');
      const data = await response.json();
      const info = data.providers?.[provider];
      els.statusDot.className = info?.configured ? 'dot ok' : 'dot bad';
      els.statusText.textContent = info?.configured
        ? `${info.label}: сервер настроен.`
        : `${info?.label || provider}: нужен env key/base url на сервере.`;
    } catch (error) {
      els.statusDot.className = 'dot bad';
      els.statusText.textContent = `Не могу проверить провайдера: ${error.message}`;
    }
    return;
  }

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
    els.statusText.textContent = 'Ollama не отвечает. Для no-download выбери Pollinations или Puter.js.';
  } catch (error) {
    els.statusDot.className = 'dot bad';
    els.statusText.textContent = `Сайт работает, но health недоступен: ${error.message}`;
  }
}

function buildOutgoingMessages(text, settings) {
  const outgoing = [];
  if (settings.systemPrompt) outgoing.push({ role: 'system', content: settings.systemPrompt });
  outgoing.push(...messages, { role: 'user', content: text });
  return outgoing;
}

function extractPuterContent(result) {
  if (typeof result === 'string') return result;
  if (!result || typeof result !== 'object') return String(result);
  if (typeof result.text === 'string') return result.text;
  if (typeof result.content === 'string') return result.content;
  if (typeof result.message?.content === 'string') return result.message.content;
  if (Array.isArray(result.message?.content)) {
    return result.message.content
      .map((part) => (typeof part === 'string' ? part : part?.text || ''))
      .filter(Boolean)
      .join('\n');
  }
  return JSON.stringify(result, null, 2);
}

function loadPuterScript() {
  if (window.puter?.ai?.chat) return Promise.resolve();
  if (puterScriptPromise) return puterScriptPromise;
  puterScriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://js.puter.com/v2/';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Не удалось загрузить Puter.js'));
    document.head.appendChild(script);
  });
  return puterScriptPromise;
}

function messagesToPlainPrompt(outgoing) {
  const labels = { system: 'СИСТЕМНЫЕ ПРАВИЛА', user: 'ПОЛЬЗОВАТЕЛЬ', assistant: 'АССИСТЕНТ' };
  return `${outgoing.map((message) => `${labels[message.role] || message.role}:\n${message.content}`).join('\n\n')}\n\nАССИСТЕНТ:`;
}

async function sendPuterMessage(outgoing, settings) {
  await loadPuterScript();
  if (!window.puter?.ai?.chat) throw new Error('Puter.js загружен, но puter.ai.chat недоступен');

  try {
    const result = await window.puter.ai.chat(outgoing, { model: settings.model });
    return extractPuterContent(result);
  } catch (firstError) {
    const prompt = messagesToPlainPrompt(outgoing);
    const result = await window.puter.ai.chat(prompt, { model: settings.model });
    return extractPuterContent(result) || `Puter вернул пустой ответ. Первая ошибка: ${firstError.message}`;
  }
}

async function sendServerMessage(outgoing, settings) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider: settings.provider,
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
  if (!response.ok) throw new Error(data.error || data.details || JSON.stringify(data));
  return data.message?.content || JSON.stringify(data, null, 2);
}

async function sendMessage(text) {
  const settings = readSettingsFromForm();
  const outgoing = buildOutgoingMessages(text, settings);

  messages.push({ role: 'user', content: text });
  renderConversation();
  els.sendBtn.disabled = true;
  els.sendBtn.textContent = 'Думаю...';

  try {
    const content = settings.provider === 'puter'
      ? await sendPuterMessage(outgoing, settings)
      : await sendServerMessage(outgoing, settings);
    messages.push({ role: 'assistant', content });
  } catch (error) {
    const help = settings.provider === 'ollama'
      ? `\n\nДля Ollama нужны команды:\ndocker compose --profile local up -d ollama\n./scripts/pull-model.sh ${settings.model}`
      : '\n\nДля режима без скачивания попробуй provider Pollinations или Puter.js. Для OpenRouter/Groq ключ задаётся только в env сервера, не в чате.';
    messages.push({
      role: 'assistant',
      content: `Не получилось получить ответ.\n\nПровайдер: ${settings.provider}\nМодель: ${settings.model}\nОшибка: ${error.message}${help}`
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
      const prompt = `Прочитай GitHub-репозиторий: ${mod.repo}\n\nСделай:\n1. объясни, что это;\n2. проверь README, установку, зависимости, лицензии;\n3. найди риски и логические дыры;\n4. скажи, подходит ли это для Android/AI-kit без скачивания модели;\n5. если подходит — дай пошаговую установку с нуля;\n6. не запускай подозрительный код без моего подтверждения.`;
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

  els.providerInput.addEventListener('change', () => {
    const provider = els.providerInput.value;
    els.modelInput.value = PROVIDER_DEFAULTS[provider] || els.modelInput.value;
    updateProviderHint();
    saveSettings();
    checkStatus();
  });

  els.saveSettingsBtn.addEventListener('click', saveSettings);
  els.resetSettingsBtn.addEventListener('click', async () => {
    localStorage.removeItem('ode-kitai-settings');
    const settings = await loadSystemPromptIfEmpty({ ...DEFAULT_SETTINGS });
    applySettings(settings);
    toast('Настройки сброшены');
    checkStatus();
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
