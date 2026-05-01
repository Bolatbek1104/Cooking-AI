let imageData = null;
let isLoading = false;

window.addEventListener('load', () => {
  updateThemeToggle();
  startSession();
});

function toggleTheme() {
  const currentTheme = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
  const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = nextTheme;
  try {
    localStorage.setItem('theme', nextTheme);
  } catch (e) {}
  updateThemeToggle();
}

function updateThemeToggle() {
  const isDark = document.documentElement.dataset.theme === 'dark';
  const button = document.getElementById('theme-toggle');
  const icon = document.getElementById('theme-toggle-icon');
  const text = document.getElementById('theme-toggle-text');

  if (!button || !icon || !text) return;

  button.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
  icon.textContent = isDark ? 'L' : 'D';
  text.textContent = isDark ? 'Light' : 'Dark';
}

async function startSession() {
  const res = await fetch('/start', { method: 'POST' });
  const data = await res.json();

  if (data.messages && data.messages.length) {
    data.messages.forEach((message) => appendMessage(
  message.role === 'assistant' ? 'chef' : 'user',
  message.content
));
  } else if (data.response) {
    appendMessage('chef', data.response);
  }

  if (data.dish_options && data.dish_options.length) {
    appendRecipeOptions(data.dish_options);
  }

  updateAgentPanel(data);
}

async function sendMessage() {
  if (isLoading) return;

  const input = document.getElementById('msg-input');
  const msg = input.value.trim();
  if (!msg && !imageData) return;

  input.value = '';
  autoResize(input);
  appendMessage('user', msg || '[Sent fridge photo]');

  const payload = { message: msg };
  if (imageData) {
    payload.image = imageData;
    clearImage();
  }

  setLoading(true);

  try {
    await streamChefResponse(payload);
  } catch (e) {
    console.error('JS Error:', e);
    appendMessage('chef', 'Chef crashed while loading the response. Refresh and try again.');
  }

  setLoading(false);
}

function appendMessage(role, text) {
  const container = document.getElementById('messages');

  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'chef' ? 'C' : 'me';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatText(text);

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;

  return bubble;
}

function appendStreamingMessage() {
  return appendMessage('chef', '');
}

function formatText(text) {
  return escapeHtml(text || '')
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function appendRecipeOptions(options) {
  const container = document.getElementById('messages');
  const wrap = document.createElement('div');
  wrap.className = 'message chef recipe-options-message';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = 'C';

  const grid = document.createElement('div');
  grid.className = 'recipe-options';

  options.forEach((option) => {
    const card = document.createElement('button');
    card.className = 'recipe-card';
    card.type = 'button';
    card.onclick = () => chooseRecipeOption(option);

    const media = document.createElement('div');
    media.className = 'recipe-card-media image-loading';

    const img = document.createElement('img');
    const fallbackQuery = option.image_query || option.title;
    img.alt = option.title || 'Recipe option';
    img.loading = 'eager';
    img.referrerPolicy = 'no-referrer';

    const status = document.createElement('div');
    status.className = 'recipe-card-image-status';
    status.textContent = 'Generating photo...';

    media.appendChild(img);
    media.appendChild(status);

    const imageUrls = recipeImageUrls(fallbackQuery, option.image_url);
    let imageIndex = 0;
    let retryCount = 0;
    const maxRetries = 8;

    img.onload = () => {
      media.classList.remove('image-loading', 'image-failed');
      media.classList.add('image-ready');
    };

    img.src = imageUrls[imageIndex];
    img.onerror = () => {
      retryCount += 1;
      if (retryCount <= maxRetries) {
        imageIndex = (imageIndex + 1) % imageUrls.length;
        setTimeout(() => {
          img.src = withCacheBust(imageUrls[imageIndex], retryCount);
        }, 1400 * retryCount);
      } else {
        media.classList.remove('image-loading');
        media.classList.add('image-failed');
        status.textContent = 'Photo still cooking';
      }
    };

    const body = document.createElement('div');
    body.className = 'recipe-card-body';

    const title = document.createElement('div');
    title.className = 'recipe-card-title';
    title.textContent = option.title || 'Untitled dish';

    const desc = document.createElement('div');
    desc.className = 'recipe-card-desc';
    desc.textContent = option.description || '';

    const meta = document.createElement('div');
    meta.className = 'recipe-card-meta';
    meta.textContent = [option.time, option.difficulty].filter(Boolean).join(' - ');

    body.appendChild(title);
    body.appendChild(desc);
    body.appendChild(meta);
    card.appendChild(media);
    card.appendChild(body);
    grid.appendChild(card);
  });

  wrap.appendChild(avatar);
  wrap.appendChild(grid);
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

function recipeImageUrls(query, primaryUrl) {
  return [
    primaryUrl,
    pollinationImageUrl(query, 1),
    pollinationImageUrl(query, 2),
    pollinationImageUrl(query, 3),
  ].filter(Boolean);
}

function pollinationImageUrl(query, variant) {
  const dish = query || 'home cooked meal';
  const prompt = encodeURIComponent(
    `realistic food photography, finished plated dish, no people, no animals, restaurant lighting, appetizing, ${dish}`
  );
  const seed = encodeURIComponent(`${dish}-${variant}`);
  return `https://image.pollinations.ai/prompt/${prompt}?width=640&height=480&seed=${seed}&nologo=true`;
}

function withCacheBust(url, attempt) {
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}retry=${Date.now()}-${attempt}`;
}

async function chooseRecipeOption(option) {
  if (isLoading) return;

  appendMessage('user', `I choose: ${option.title}`);
  setLoading(true);

  try {
    await streamChefResponse({
      message: `I choose "${option.title}". Show the full recipe for this selected dish.`,
      selected_option: option
    });
  } catch (e) {
    console.error('JS Error:', e);
    appendMessage('chef', 'Could not load the selected recipe. Try clicking it again.');
  }

  setLoading(false);
}

async function streamChefResponse(payload) {
  const bubble = appendStreamingMessage();
  const typer = createTypewriter(bubble);
  let finalData = null;

  const res = await fetch('/chat-stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!res.ok || !res.body) {
    throw new Error(`Streaming request failed with status ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop();

    for (const rawEvent of events) {
      const eventResult = handleStreamEvent(rawEvent, bubble, (text) => typer.enqueue(text));
      if (eventResult?.type === 'done') {
        finalData = eventResult.data;
      }
    }
  }

  if (buffer.trim()) {
    const eventResult = handleStreamEvent(buffer, bubble, (text) => typer.enqueue(text));
    if (eventResult?.type === 'done') {
      finalData = eventResult.data;
    }
  }

  await typer.finish();

  if (finalData) {
    bubble.innerHTML = formatText(finalData.response || '');
    if (finalData.dish_options && finalData.dish_options.length) {
      appendRecipeOptions(finalData.dish_options);
    }
    updateAgentPanel(finalData);
  }
}

function createTypewriter(bubble) {
  let visibleText = '';
  let queuedText = '';
  let timer = null;
  let finishResolver = null;
  const container = bubble.parentElement.parentElement;

  const render = () => {
    bubble.innerHTML = formatText(visibleText);
    container.scrollTop = container.scrollHeight;
  };

  const tick = () => {
    if (!queuedText) {
      timer = null;
      if (finishResolver) {
        finishResolver();
        finishResolver = null;
      }
      return;
    }

    const chunkSize = queuedText.length > 220 ? 4 : queuedText.length > 80 ? 3 : 2;
    visibleText += queuedText.slice(0, chunkSize);
    queuedText = queuedText.slice(chunkSize);
    render();
    timer = setTimeout(tick, 18);
  };

  return {
    enqueue(text) {
      queuedText += text || '';
      if (!timer) {
        timer = setTimeout(tick, 18);
      }
    },
    finish() {
      if (!queuedText && !timer) {
        return Promise.resolve();
      }
      return new Promise((resolve) => {
        finishResolver = resolve;
      });
    },
  };
}

function handleStreamEvent(rawEvent, bubble, onDelta) {
  const lines = rawEvent.split('\n');
  const eventName = (lines.find((line) => line.startsWith('event:')) || 'event: message')
    .replace('event:', '')
    .trim();
  const dataText = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.replace(/^data:\s?/, ''))
    .join('\n');

  if (!dataText) return;

  const data = JSON.parse(dataText);

  if (eventName === 'delta') {
    onDelta(data.text || '');
    return { type: 'delta', data };
  }

  if (eventName === 'done') {
    return { type: 'done', data };
  }

  if (eventName === 'error') {
    bubble.innerHTML = formatText(`Warning: ${data.error || data.response || 'Streaming error.'}`);
    updateAgentPanel(data);
    return { type: 'error', data };
  }
}

function showTyping() {
  const container = document.getElementById('messages');
  const t = document.createElement('div');
  t.className = 'typing-indicator';
  t.id = 'typing';
  t.innerHTML = `
    <div class="avatar">C</div>
    <div class="typing-dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
  `;
  container.appendChild(t);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  const t = document.getElementById('typing');
  if (t) t.remove();
}

function updateAgentPanel(data) {
  const { stage, profile, recipe_count } = data;
  const stages = ['profiling', 'recipe', 'cooking', 'followup'];
  const stageMap = { profiling: 0, profiled: 0, options: 1, recipe: 2, followup: 3 };
  const current = stageMap[stage] ?? 0;

  stages.forEach((s, i) => {
    const el = document.getElementById(`stage-${s}`);
    if (!el) return;
    el.className = 'stage-item ' + (i < current ? 'done' : i === current ? 'active' : 'pending');
  });

  if (profile) {
    setProfile('p-skill', profile.skill_level);
    setProfile('p-diet', profile.dietary);
    setProfile('p-tools', profile.tools);
    setProfile('p-time', profile.time_available);
  }

  document.getElementById('recipe-count').textContent = recipe_count || 0;
}

function setProfile(id, val) {
  const el = document.getElementById(id);
  if (val) {
    el.textContent = val;
    el.className = 'profile-value';
  } else {
    el.textContent = 'Gathering data...';
    el.className = 'profile-value empty';
  }
}

function handleImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (ev) => {
    imageData = ev.target.result.split(',')[1];
    document.getElementById('preview-img').src = ev.target.result;
    document.getElementById('img-preview').classList.add('show');
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  imageData = null;
  document.getElementById('img-preview').classList.remove('show');
  document.getElementById('file-input').value = '';
}

async function resetSession() {
  await fetch('/reset', { method: 'POST' });
  document.getElementById('messages').innerHTML = '';
  clearImage();
  updateAgentPanel({ stage: 'profiling', profile: {}, recipe_count: 0 });
  startSession();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function setLoading(v) {
  isLoading = v;
  document.getElementById('send-btn').disabled = v;
  document.getElementById('msg-input').disabled = v;
}
