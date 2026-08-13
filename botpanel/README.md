# botpanel

A small web control panel for managing a bot process: start/stop/restart, live log streaming, and a config.json editor — password protected.

## Setup

```bash
npm install
cp .env.example .env
```

Edit `.env`:

```
PANEL_PASSWORD=pick-a-real-password
SESSION_SECRET=pick-a-long-random-string
PORT=3000
BOT_COMMAND=python3
BOT_ARGS=bot.py
BOT_CWD=./bot
```

`BOT_COMMAND` / `BOT_ARGS` / `BOT_CWD` control what the panel actually launches — point them at your bot. For this repo's bot, that's likely something like:

```
BOT_COMMAND=python3
BOT_ARGS=bot.py
BOT_CWD=./bot
```

matching the `bot/` folder structure in `1.0-Bot-lxc`.

## Run

```bash
npm start
```

Then open `http://localhost:3000` (or `http://<server-ip>:3000` if running on an LXC container/remote host) and sign in with `PANEL_PASSWORD`.

## What it does

- **Control** — Start, stop, restart the bot process from the browser
- **Status** — PID, uptime, restart count, live state indicator
- **Logs** — Live-streamed stdout/stderr via Server-Sent Events, pause/clear
- **Config** — Reads/writes a `config.json` inside the bot's working directory (validated as JSON before saving)

## Notes on running on an LXC container

- Run `npm start` inside the container (or under a process manager like `pm2` or a systemd unit so it survives reboots)
- Expose the port (default 3000) either directly or behind a reverse proxy (nginx/Caddy) if you want a real domain + HTTPS
- Change `PANEL_PASSWORD` and `SESSION_SECRET` before exposing this to the internet — the current auth is a single shared password, suitable for personal/small-team use, not multi-user access control
- If you put this behind a public URL, use HTTPS (e.g. via Caddy or nginx + Let's Encrypt) since the login password is otherwise sent in plaintext

## Security note

This panel can start/stop arbitrary processes and write files. Keep `PANEL_PASSWORD` private, don't expose port 3000 to the open internet without a reverse proxy + HTTPS, and review any script (including this repo's own quick-install script) before running it.
