require('dotenv').config();
const express = require('express');
const session = require('express-session');
const path = require('path');
const fs = require('fs');
const BotController = require('./botController');

const PORT = process.env.PORT || 3000;
const PANEL_PASSWORD = process.env.PANEL_PASSWORD || 'change-me';
const SESSION_SECRET = process.env.SESSION_SECRET || 'insecure-dev-secret';

const BOT_COMMAND = process.env.BOT_COMMAND || 'python3';
const BOT_ARGS = (process.env.BOT_ARGS || 'bot.py').split(' ').filter(Boolean);
const BOT_CWD = path.resolve(process.env.BOT_CWD || './bot');

const bot = new BotController({ command: BOT_COMMAND, args: BOT_ARGS, cwd: BOT_CWD });

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(
  session({
    secret: SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: { httpOnly: true, maxAge: 1000 * 60 * 60 * 8 }, // 8 hours
  })
);

function requireAuth(req, res, next) {
  if (req.session && req.session.authed) return next();
  if (req.path.startsWith('/api/')) return res.status(401).json({ ok: false, error: 'Not authenticated' });
  return res.redirect('/login.html');
}

// ---- Auth routes ----
app.post('/api/login', (req, res) => {
  const { password } = req.body;
  if (password && password === PANEL_PASSWORD) {
    req.session.authed = true;
    return res.json({ ok: true });
  }
  return res.status(401).json({ ok: false, error: 'Incorrect password' });
});

app.post('/api/logout', (req, res) => {
  req.session.destroy(() => res.json({ ok: true }));
});

app.get('/api/session', (req, res) => {
  res.json({ authed: !!(req.session && req.session.authed) });
});

// ---- Protected static + API ----
app.use('/login.html', express.static(path.join(__dirname, 'public', 'login.html')));
app.use('/style.css', express.static(path.join(__dirname, 'public', 'style.css')));
app.use('/login.js', express.static(path.join(__dirname, 'public', 'login.js')));

app.use(requireAuth);
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/status', (req, res) => {
  res.json(bot.getStatus());
});

app.get('/api/logs', (req, res) => {
  res.json({ logs: bot.logs });
});

app.get('/api/logs/stream', (req, res) => {
  res.set({
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  });
  res.flushHeaders();

  const send = (entry) => {
    res.write(`data: ${JSON.stringify(entry)}\n\n`);
  };
  bot.logs.slice(-100).forEach(send);

  const onLog = (entry) => send(entry);
  bot.on('log', onLog);

  req.on('close', () => {
    bot.off('log', onLog);
  });
});

app.post('/api/start', (req, res) => {
  const result = bot.start();
  res.json(result);
});

app.post('/api/stop', (req, res) => {
  const result = bot.stop();
  res.json(result);
});

app.post('/api/restart', (req, res) => {
  const result = bot.restart();
  res.json(result);
});

app.post('/api/logs/clear', (req, res) => {
  bot.clearLogs();
  res.json({ ok: true });
});

// ---- Bot config file editor (optional config.json inside bot dir) ----
const CONFIG_PATH = path.join(BOT_CWD, 'config.json');

app.get('/api/config', (req, res) => {
  if (!fs.existsSync(CONFIG_PATH)) {
    return res.json({ exists: false, content: '' });
  }
  const content = fs.readFileSync(CONFIG_PATH, 'utf-8');
  res.json({ exists: true, content });
});

app.post('/api/config', (req, res) => {
  const { content } = req.body;
  try {
    JSON.parse(content); // validate it's valid JSON before saving
    fs.writeFileSync(CONFIG_PATH, content, 'utf-8');
    res.json({ ok: true });
  } catch (err) {
    res.status(400).json({ ok: false, error: `Invalid JSON: ${err.message}` });
  }
});

app.listen(PORT, () => {
  console.log(`botpanel running at http://localhost:${PORT}`);
  console.log(`Controlling: ${BOT_COMMAND} ${BOT_ARGS.join(' ')} (cwd: ${BOT_CWD})`);
});
