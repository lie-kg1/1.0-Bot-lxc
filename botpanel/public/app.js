const beacon = document.getElementById('beacon');
const statusWord = document.getElementById('status-word');
const cmdTag = document.getElementById('cmd-tag');
const metaPid = document.getElementById('meta-pid');
const metaUptime = document.getElementById('meta-uptime');
const metaRestarts = document.getElementById('meta-restarts');
const metaCwd = document.getElementById('meta-cwd');

const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const restartBtn = document.getElementById('restart-btn');

const logStream = document.getElementById('log-stream');
const logPauseBtn = document.getElementById('log-pause');
const logClearBtn = document.getElementById('log-clear');

const configTextarea = document.getElementById('config-textarea');
const configSaveBtn = document.getElementById('config-save');
const configStatus = document.getElementById('config-status');

const toast = document.getElementById('toast');
const logoutBtn = document.getElementById('logout-btn');

let logsPaused = false;

function showToast(message, type = '') {
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  setTimeout(() => { toast.className = 'toast'; }, 2500);
}

function formatUptime(seconds) {
  if (!seconds) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}

function renderStatus(data) {
  const state = data.status;
  beacon.dataset.state = state;
  statusWord.textContent = state.toUpperCase();
  cmdTag.textContent = data.command;
  metaPid.textContent = data.pid ?? '—';
  metaUptime.textContent = formatUptime(data.uptimeSeconds);
  metaRestarts.textContent = data.restartCount ?? 0;
  metaCwd.textContent = data.cwd;

  startBtn.disabled = state === 'running';
  stopBtn.disabled = state !== 'running';
  restartBtn.disabled = state !== 'running';
}

async function refreshStatus() {
  try {
    const res = await fetch('/api/status');
    if (res.status === 401) return (window.location.href = '/login.html');
    const data = await res.json();
    renderStatus(data);
  } catch (err) {
    // network hiccup, ignore silently
  }
}

async function callAction(url, successMsg) {
  try {
    const res = await fetch(url, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      showToast(successMsg, 'success');
    } else {
      showToast(data.error || 'Action failed.', 'error');
    }
    refreshStatus();
  } catch (err) {
    showToast('Could not reach server.', 'error');
  }
}

startBtn.addEventListener('click', () => callAction('/api/start', 'Bot started'));
stopBtn.addEventListener('click', () => callAction('/api/stop', 'Bot stopped'));
restartBtn.addEventListener('click', () => callAction('/api/restart', 'Bot restarting'));

logoutBtn.addEventListener('click', async () => {
  await fetch('/api/logout', { method: 'POST' });
  window.location.href = '/login.html';
});

// ---- Log stream (SSE) ----
function appendLogLine(entry) {
  if (logsPaused) return;
  const row = document.createElement('div');
  row.className = 'log-line';
  const time = new Date(entry.ts).toLocaleTimeString();
  row.innerHTML = `<span class="log-ts">${time}</span><span class="log-tag ${entry.stream}">${entry.stream}</span><span class="log-msg"></span>`;
  row.querySelector('.log-msg').textContent = entry.line;
  logStream.appendChild(row);
  logStream.scrollTop = logStream.scrollHeight;

  while (logStream.children.length > 500) {
    logStream.removeChild(logStream.firstChild);
  }
}

function connectLogStream() {
  const source = new EventSource('/api/logs/stream');
  source.onmessage = (e) => {
    try {
      appendLogLine(JSON.parse(e.data));
    } catch (err) {
      /* ignore malformed frame */
    }
  };
  source.onerror = () => {
    source.close();
    setTimeout(connectLogStream, 3000);
  };
}

logPauseBtn.addEventListener('click', () => {
  logsPaused = !logsPaused;
  logPauseBtn.textContent = logsPaused ? 'Resume' : 'Pause';
});

logClearBtn.addEventListener('click', async () => {
  logStream.innerHTML = '';
  await fetch('/api/logs/clear', { method: 'POST' });
});

// ---- Config editor ----
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    configTextarea.value = data.content || '';
    configStatus.textContent = data.exists ? 'Loaded config.json' : 'No config.json yet — saving will create one.';
  } catch (err) {
    configStatus.textContent = 'Could not load config.';
  }
}

configSaveBtn.addEventListener('click', async () => {
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: configTextarea.value }),
    });
    const data = await res.json();
    if (data.ok) {
      showToast('Config saved', 'success');
      configStatus.textContent = 'Saved.';
    } else {
      showToast(data.error, 'error');
    }
  } catch (err) {
    showToast('Could not save config.', 'error');
  }
});

// ---- Init ----
refreshStatus();
setInterval(refreshStatus, 3000);
connectLogStream();
loadConfig();
