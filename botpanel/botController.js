const { spawn } = require('child_process');
const { EventEmitter } = require('events');
const path = require('path');

const MAX_LOG_LINES = 500;

class BotController extends EventEmitter {
  constructor({ command, args, cwd }) {
    super();
    this.command = command;
    this.args = args;
    this.cwd = cwd;
    this.proc = null;
    this.status = 'stopped'; // stopped | running | crashed
    this.startedAt = null;
    this.logs = [];
    this.restartCount = 0;
  }

  _pushLog(line, stream = 'stdout') {
    const entry = { line, stream, ts: Date.now() };
    this.logs.push(entry);
    if (this.logs.length > MAX_LOG_LINES) this.logs.shift();
    this.emit('log', entry);
  }

  getStatus() {
    return {
      status: this.status,
      pid: this.proc ? this.proc.pid : null,
      startedAt: this.startedAt,
      uptimeSeconds: this.startedAt ? Math.floor((Date.now() - this.startedAt) / 1000) : 0,
      restartCount: this.restartCount,
      command: `${this.command} ${this.args.join(' ')}`,
      cwd: this.cwd,
    };
  }

  start() {
    if (this.proc) {
      return { ok: false, error: 'Bot is already running.' };
    }

    try {
      this.proc = spawn(this.command, this.args, {
        cwd: this.cwd,
        env: process.env,
        shell: false,
      });
    } catch (err) {
      this._pushLog(`Failed to start: ${err.message}`, 'error');
      this.status = 'crashed';
      return { ok: false, error: err.message };
    }

    this.status = 'running';
    this.startedAt = Date.now();
    this._pushLog(`Started (${this.command} ${this.args.join(' ')}) with PID ${this.proc.pid}`, 'system');

    this.proc.stdout.on('data', (data) => {
      data.toString().split(/\r?\n/).filter(Boolean).forEach((l) => this._pushLog(l, 'stdout'));
    });

    this.proc.stderr.on('data', (data) => {
      data.toString().split(/\r?\n/).filter(Boolean).forEach((l) => this._pushLog(l, 'stderr'));
    });

    this.proc.on('exit', (code, signal) => {
      this._pushLog(`Process exited (code ${code}, signal ${signal})`, 'system');
      this.status = code === 0 || signal === 'SIGTERM' ? 'stopped' : 'crashed';
      this.proc = null;
      this.emit('status-change', this.getStatus());
    });

    this.emit('status-change', this.getStatus());
    return { ok: true };
  }

  stop() {
    if (!this.proc) {
      return { ok: false, error: 'Bot is not running.' };
    }
    this._pushLog('Stopping bot...', 'system');
    this.proc.kill('SIGTERM');
    return { ok: true };
  }

  restart() {
    if (this.proc) {
      this._pushLog('Restarting bot...', 'system');
      this.restartCount += 1;
      const onExit = () => {
        this.start();
      };
      this.proc.once('exit', onExit);
      this.proc.kill('SIGTERM');
      return { ok: true };
    }
    return this.start();
  }

  clearLogs() {
    this.logs = [];
  }
}

module.exports = BotController;
