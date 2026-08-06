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
admin_env = os.getenv('ADMIN_ID', '0')
ADMIN_ID = int(admin_env) if admin_env.strip().isdigit() else 0
BOT_STATUS_NAME = os.getenv('BOT_STATUS_NAME', 'UnixNodes')
WATERMARK = os.getenv('WATERMARK', 'Powered by UnixNodes VPS Bot')

# VPS Defaults from .env
DEFAULT_RAM = os.getenv('DEFAULT_RAM', '2g')
DEFAULT_CPU = os.getenv('DEFAULT_CPU', '1')
DEFAULT_DISK = os.getenv('DEFAULT_DISK', '10G')
VPS_HOSTNAME = os.getenv('VPS_HOSTNAME', 'unix-free')
SERVER_LIMIT = int(os.getenv('SERVER_LIMIT', 1))
TOTAL_SERVER_LIMIT = int(os.getenv('TOTAL_SERVER_LIMIT', 50))
DATABASE_FILE = os.getenv('DATABASE_FILE', 'vps_bot.db')

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

try:
    client = docker.from_env()
except Exception as e:
    logger.warning(f"Docker client initialization warning: {e}")

def is_admin(member):
    if not isinstance(member, discord.Member):
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
    cursor.execute(f'''
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
    ''')
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

def delete_vps(container_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vps WHERE container_id = ?', (container_id,))
    conn.commit()
    conn.close()

# Async Docker helpers
async def async_docker_run(image, hostname, ram, cpu, disk, container_name):
    cmd = [
        "docker", "run", "-d",
        "--privileged", "--cap-add=ALL",
        "--restart", "unless-stopped",
        f"--memory={ram}",
        f"--cpus={cpu}",
        f"--hostname={hostname}",
        f"--name={container_name}",
        image,
        "tail", "-f", "/dev/null"
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
        if proc.returncode != 0:
            logger.error(f"Docker run failed: {stderr.decode()}")
            return None
        return stdout.decode().strip()
    except Exception as e:
        logger.error(f"Docker run error: {e}")
        return None

async def async_docker_start(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "start", container_id,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)
        return proc.returncode == 0
    except Exception:
        return False

async def async_docker_stop(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "stop", container_id,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)
        return proc.returncode == 0
    except Exception:
        return False

async def async_docker_restart(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "restart", container_id,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)
        return proc.returncode == 0
    except Exception:
        return False

async def async_docker_rm(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_id,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False

async def async_install_tmate(container_id, os_type):
    install_cmd = "apt-get update && apt-get install -y tmate curl wget sudo openssh-client"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "bash", "-c", install_cmd,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.communicate(), timeout=120.0)
    except Exception as e:
        logger.error(f"Tmate install error: {e}")

async def capture_ssh_session_line(process):
    while True:
        try:
            output = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
            if not output:
                break
            output = output.decode('utf-8').strip()
            if "ssh session:" in output.lower():
                return output.split("ssh session:")[-1].strip()
        except asyncio.TimeoutError:
            break
    return None

async def docker_exec_tmate(container_id):
    try:
        return await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "tmate", "-F",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except Exception:
        return None

# Bot Groups & Commands
vps_group = app_commands.Group(name="vps", description="Manage your VPS instances")
admin_group = app_commands.Group(name="admin", description="Admin controls")

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name=BOT_STATUS_NAME))

@vps_group.command(name="create", description="Create a new VPS instance")
@app_commands.choices(os_type=[
    app_commands.Choice(name="Ubuntu 24.04 LTS (Noble)", value="ubuntu-24.04"),
    app_commands.Choice(name="Ubuntu 22.04 LTS (Jammy)", value="ubuntu-22.04"),
    app_commands.Choice(name="Debian 13 (Trixie)", value="debian-13"),
    app_commands.Choice(name="Debian 12 (Bookworm)", value="debian-12")
])
async def vps_create(interaction: discord.Interaction, os_type: str, ram: str = DEFAULT_RAM, cpu: str = DEFAULT_CPU, disk: str = DEFAULT_DISK):
    user_id = interaction.user.id
    username = str(interaction.user)
    add_user(user_id, username)
    
    if is_banned(user_id):
        return await interaction.response.send_message("You are banned from creating VPS instances.", ephemeral=True)
    if count_user_vps(user_id) >= SERVER_LIMIT:
        return await interaction.response.send_message(f"You have reached your limit of {SERVER_LIMIT} VPS.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    hostname = f"{VPS_HOSTNAME}-{user_id}"
    suffix = random.randint(1000, 9999)
    container_name = f"{os_type}-vps-{user_id}-{suffix}"
    
    image_map = {
        "ubuntu-24.04": "ubuntu:24.04",
        "ubuntu-22.04": "ubuntu:22.04",
        "debian-13": "debian:trixie",
        "debian-12": "debian:bookworm"
    }
    image = image_map.get(os_type, "debian:bookworm")
    
    container_id = await async_docker_run(image, hostname, ram, cpu, disk, container_name)
    if not container_id:
        return await interaction.followup.send("Failed to create Docker container.", ephemeral=True)
    
    await asyncio.sleep(5)
    await async_install_tmate(container_id, os_type)
    await asyncio.sleep(8)
    
    exec_process = await docker_exec_tmate(container_id)
    ssh_line = await capture_ssh_session_line(exec_process) if exec_process else None
    
    if ssh_line:
        add_vps(user_id, container_id, container_name, os_type, hostname, ssh_line, ram, cpu, disk)
        embed = discord.Embed(title="VPS Created", description=f"OS: {os_type}\n```{ssh_line}```", color=discord.Color.green())
        try:
            await interaction.user.send(embed=embed)
        except Exception:
            pass
        await interaction.followup.send("VPS is ready! Check your DMs for SSH access.", ephemeral=True)
    else:
        await async_docker_rm(container_id)
        await interaction.followup.send("Failed to generate SSH session.", ephemeral=True)

@vps_group.command(name="list", description="List your VPS instances")
async def vps_list(interaction: discord.Interaction):
    vps_list = get_user_vps(interaction.user.id)
    if not vps_list:
        return await interaction.response.send_message("You don't have any active VPS instances.", ephemeral=True)
    
    embed = discord.Embed(title="Your VPS Instances", color=discord.Color.blue())
    for vps in vps_list:
        embed.add_field(
            name=f"{vps['container_name']} ({vps['os_type']})",
            value=f"Status: **{vps['status']}**\nRAM: {vps['ram']} | CPU: {vps['cpu']}\nID: `{vps['container_id'][:12]}`",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@vps_group.command(name="start", description="Start a stopped VPS")
@app_commands.describe(vps_identifier="Container ID or Name")
async def vps_start(interaction: discord.Interaction, vps_identifier: str = None):
    vps = get_vps_by_identifier(interaction.user.id, vps_identifier)
    if not vps:
        return await interaction.response.send_message("VPS not found.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    success = await async_docker_start(vps['container_id'])
    if success:
        update_vps_status(vps['container_id'], "running")
        await interaction.followup.send("VPS started successfully!", ephemeral=True)
    else:
        await interaction.followup.send("Failed to start VPS.", ephemeral=True)

@vps_group.command(name="stop", description="Stop a running VPS")
@app_commands.describe(vps_identifier="Container ID or Name")
async def vps_stop(interaction: discord.Interaction, vps_identifier: str = None):
    vps = get_vps_by_identifier(interaction.user.id, vps_identifier)
    if not vps:
        return await interaction.response.send_message("VPS not found.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    success = await async_docker_stop(vps['container_id'])
    if success:
        update_vps_status(vps['container_id'], "stopped")
        await interaction.followup.send("VPS stopped successfully!", ephemeral=True)
    else:
        await interaction.followup.send("Failed to stop VPS.", ephemeral=True)

@admin_group.command(name="list", description="List all VPS instances (Admin)")
async def admin_list(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        return await interaction.response.send_message("Restricted to admins.", ephemeral=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, v.container_name, v.os_type, v.status, v.container_id 
        FROM vps v JOIN users u ON v.user_id = u.user_id
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return await interaction.response.send_message("No active VPS instances found.", ephemeral=True)
    
    embed = discord.Embed(title="All VPS Instances", color=discord.Color.blue())
    for r in rows[:25]:
        embed.add_field(name=f"{r['username']} - {r['container_name']}", value=f"Status: {r['status']}\nID: `{r['container_id'][:12]}`", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.tree.add_command(vps_group)
bot.tree.add_command(admin_group)

if __name__ == '__main__':
    bot.run(TOKEN)
