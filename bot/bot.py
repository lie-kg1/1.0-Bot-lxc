import random
import logging
import subprocess
import sys
import os
import re
import time
import discord
from discord.ext import commands, tasks
import docker
import asyncio
from discord import app_commands
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Configuration from .env
TOKEN = os.getenv('TOKEN', 'DISCORD_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))  # Admin user ID for checks
BOT_STATUS_NAME = os.getenv('BOT_STATUS_NAME', 'UnixNodes')
WATERMARK = os.getenv('WATERMARK', 'Powered by UnixNodes VPS Bot')
# VPS Defaults from .env
DEFAULT_RAM = os.getenv('DEFAULT_RAM', '2g')  # e.g., '2g', '4G'
DEFAULT_CPU = os.getenv('DEFAULT_CPU', '1')  # Lowered default to '1' to avoid common errors
DEFAULT_DISK = os.getenv('DEFAULT_DISK', '10G')  # e.g., '20G' - Note: Disk limit not enforced in container
VPS_HOSTNAME = os.getenv('VPS_HOSTNAME', 'unix-free')  # Base hostname, append user ID
SERVER_LIMIT = int(os.getenv('SERVER_LIMIT', 1))
TOTAL_SERVER_LIMIT = int(os.getenv('TOTAL_SERVER_LIMIT', 50))  # Global total running server limit
DATABASE_FILE = os.getenv('DATABASE_FILE', 'vps_bot.db')

# Centralized OS Mapping for Docker Images and Display Names
OS_MAPPING = {
    "ubuntu_22": ("ubuntu:22.04", "Ubuntu 22.04 LTS"),
    "ubuntu_24": ("ubuntu:24.04", "Ubuntu 24.04 LTS"),
    "debian_12": ("debian:bookworm", "Debian 12 (Bookworm)"),
    "debian_13": ("debian:trixie", "Debian 13 (Trixie)"),
    # Fallback / legacy short keys
    "ubuntu": ("ubuntu:22.04", "Ubuntu 22.04 LTS"),
    "debian": ("debian:bookworm", "Debian 12 (Bookworm)")
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vps_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)
client = docker.from_env()

def is_admin(member):
    if not isinstance(member, discord.Member):
        logger.warning("is_admin called with non-Member object")
        return False
    return member.id == ADMIN_ID

# Database setup with SQLite3
def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    default_ram = DEFAULT_RAM
    default_cpu = DEFAULT_CPU
    default_disk = DEFAULT_DISK
    sql = f'''
        CREATE TABLE IF NOT EXISTS vps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            container_id TEXT UNIQUE NOT NULL,
            container_name TEXT NOT NULL,
            os_type TEXT NOT NULL,
            hostname TEXT NOT NULL,
            status TEXT DEFAULT 'stopped',
            ssh_command TEXT,
            ram TEXT DEFAULT '{default_ram}',
            cpu TEXT DEFAULT '{default_cpu}',
            disk TEXT DEFAULT '{default_disk}',
            suspended INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    '''
    cursor.execute(sql)
    cursor.execute("PRAGMA table_info(vps)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'suspended' not in columns:
        cursor.execute("ALTER TABLE vps ADD COLUMN suspended INTEGER DEFAULT 0")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def add_user(user_id, username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def add_ban(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO bans (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_ban(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bans WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def is_banned(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM bans WHERE user_id = ?', (user_id,))
    banned = cursor.fetchone() is not None
    conn.close()
    return banned

def add_vps(user_id, container_id, container_name, os_type, hostname, ssh_command, ram=DEFAULT_RAM, cpu=DEFAULT_CPU, disk=DEFAULT_DISK):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vps (user_id, container_id, container_name, os_type, hostname, status, ssh_command, ram, cpu, disk, suspended)
        VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?, ?, 0)
    ''', (user_id, container_id, container_name, os_type, hostname, ssh_command, ram, cpu, disk))
    conn.commit()
    conn.close()

def get_user_vps(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vps WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    vps_list = cursor.fetchall()
    conn.close()
    return vps_list

def count_user_vps(user_id):
    return len(get_user_vps(user_id))

def get_vps_by_container_id(container_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vps WHERE container_id = ?', (container_id,))
    vps = cursor.fetchone()
    conn.close()
    return vps

def get_vps_by_identifier(user_id, identifier):
    vps_list = get_user_vps(user_id)
    if not identifier:
        return vps_list[0] if vps_list else None
    identifier_lower = identifier.lower()
    for vps in vps_list:
        if (identifier_lower in vps['container_id'].lower() or
            identifier_lower in vps['container_name'].lower()):
            return vps
    return None

def update_vps_status(container_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE vps SET status = ? WHERE container_id = ?', (status, container_id))
    conn.commit()
    conn.close()

def update_vps_ssh(container_id, ssh_command):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE vps SET ssh_command = ? WHERE container_id = ?', (ssh_command, container_id))
    conn.commit()
    conn.close()

def update_vps_suspended(container_id, suspended):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE vps SET suspended = ? WHERE container_id = ?', (suspended, container_id))
    conn.commit()
    conn.close()

def delete_vps(container_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vps WHERE container_id = ?', (container_id,))
    conn.commit()
    conn.close()

def get_total_instances():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM vps WHERE status = "running"')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def parse_gb(resource_str):
    match = re.match(r'(\d+(?:\.\d+)?)([mMgG])?', resource_str.lower())
    if match:
        num = float(match.group(1))
        unit = match.group(2) or 'g'
        if unit in ['g', '']:
            return num
        elif unit in ['m']:
            return num / 1024.0
    return 0.0

def get_uptime(container_id):
    try:
        output = subprocess.check_output(["docker", "inspect", "-f", "{{.State.StartedAt}}", container_id], stderr=subprocess.STDOUT).decode().strip()
        if output == "<no value>":
            return "Not running"
        start_time = datetime.fromisoformat(output.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        uptime = now - start_time
        days = uptime.days
        hours, remainder = divmod(u
