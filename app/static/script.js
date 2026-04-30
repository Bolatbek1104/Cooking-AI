let imageData = null;
let isLoading = false;

// ─── INIT ───────────────────────────────────────────────────────────────────
window.addEventListener('load', () => startSession());

async function startSession() {
  const res = await fetch('/start', { method: 'POST' });
  const data = await res.json();
  appendMessage('chef', data.response);
}

// ─── SEND MESSAGE ────────────────────────────────────────────────────────────
async function sendMessage() {
  if (isLoading) return;
  const input = document.getElementById('msg-input');
  const msg = input.value.trim();
  if (!msg && !imageData) return;

  input.value = '';
  autoResize(input);
  appendMessage('user', msg || '📷 [Sent fridge photo]');

  const payload = { message: msg };
  if (imageData) { payload.image = imageData; clearImage(); }

  setLoading(true);
  showTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    hideTyping();

    if (data.error) {
      appendMessage('chef', `⚠️ ${data.error}`);
    } else {
      appendMessage('chef', data.response);
      updateAgentPanel(data);
    }
  } catch (e) {
    hideTyping();
    appendMessage('chef', '💀 Chef crashed harder than a soufflé in an earthquake. Refresh and try again fam.');
  }

  setLoading(false);
}

// ─── APPEND MESSAGE ──────────────────────────────────────────────────────────
function appendMessage(role, text) {
  const container = document.getElementById('messages');

  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'chef' ? '👨‍🍳' : '🧑';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatText(text);

  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

function formatText(text) {
  return text
    .replace(/## (.*)/g, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

// ─── TYPING INDICATOR ────────────────────────────────────────────────────────
function showTyping() {
  const container = document.getElementById('messages');
  const t = document.createElement('div');
  t.className = 'typing-indicator';
  t.id = 'typing';
  t.innerHTML = `
    <div class="avatar" style="background:var(--orange)">👨‍🍳</div>
    <div class="typing-dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
  `;
  container.appendChild(t);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  const t = document.getElementById('typing');
  if (t) t.remove();
}

// ─── AGENT PANEL ─────────────────────────────────────────────────────────────
function updateAgentPanel(data) {
  const { stage, profile, recipe_count } = data;

  // Update stages
  const stages = ['profiling', 'recipe', 'followup'];
  const stageMap = { profiling: 0, profiled: 0, recipe: 1, followup: 2 };
  const current = stageMap[stage] ?? 0;

  stages.forEach((s, i) => {
    const el = document.getElementById(`stage-${s}`);
    if (!el) return;
    el.className = 'stage-item ' + (i < current ? 'done' : i === current ? 'active' : 'pending');
  });

  // Update profile
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

// ─── IMAGE UPLOAD ─────────────────────────────────────────────────────────────
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

// ─── RESET ────────────────────────────────────────────────────────────────────
async function resetSession() {
  await fetch('/reset', { method: 'POST' });
  document.getElementById('messages').innerHTML = '';
  clearImage();
  updateAgentPanel({ stage: 'profiling', profile: {}, recipe_count: 0 });
  startSession();
}

// ─── UTILS ────────────────────────────────────────────────────────────────────
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