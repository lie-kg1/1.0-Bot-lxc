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
ADMIN_ID = int(admin_env) if admin_env.strip().isdigit() else 0  # Admin user ID for checks
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
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m"
    except Exception as e:
        logger.error(f"Uptime error for {container_id}: {e}")
        return "Unknown"

def get_stats(container_id):
    try:
        output = subprocess.check_output([
            "docker", "stats", "--no-stream", "--format",
            "{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}",
            container_id
        ], stderr=subprocess.STDOUT).decode().strip()
        parts = output.split('\t')
        if len(parts) == 3:
            cpu, mem, net = parts
            return {'cpu': cpu, 'mem': mem, 'net': net}
    except Exception as e:
        logger.error(f"Stats error for {container_id}: {e}")
    return {'cpu': 'N/A', 'mem': 'N/A', 'net': 'N/A'}

def get_logs(container_id, lines=50):
    try:
        output = subprocess.check_output(["docker", "logs", "--tail", str(lines), container_id], stderr=subprocess.STDOUT).decode()
        return output[-2000:]
    except Exception as e:
        logger.error(f"Logs error for {container_id}: {e}")
        return "Failed to fetch logs"

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

# Helper functions for management
async def regen_ssh_command(interaction: discord.Interaction, vps_identifier, send_response=True, target_user=None):
    if target_user is None:
        target_user = interaction.user
    vps = get_vps_by_identifier(target_user.id, vps_identifier)
    if not vps:
        embed = discord.Embed(description="No active VPS found.", color=discord.Color.red())
        if send_response:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    if vps['status'] != "running":
        embed = discord.Embed(description="VPS must be running to generate SSH.", color=discord.Color.red())
        if send_response:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    if send_response:
        await interaction.response.defer(ephemeral=True)
    container_id = vps['container_id']
    exec_process = await docker_exec_tmate(container_id)
    if exec_process:
        ssh_line = await capture_ssh_session_line(exec_process)
        if ssh_line:
            update_vps_ssh(container_id, ssh_line)
            embed = discord.Embed(title="New SSH Session Generated", description=f"```{ssh_line}```", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
            embed.set_footer(text=WATERMARK, icon_url=bot.user.avatar.url if bot.user.avatar else None)
            try:
                await target_user.send(embed=embed)
            except discord.Forbidden:
                if send_response:
                    embed_dm_fail = discord.Embed(description="New SSH session generated but could not send to DMs (privacy settings).", color=discord.Color.orange())
                    await interaction.followup.send(embed=embed_dm_fail, ephemeral=True)
                return True
            if send_response:
                embed_success = discord.Embed(description="New SSH session sent to your DMs.", color=discord.Color.green())
                await interaction.followup.send(embed=embed_success, ephemeral=True)
            return True
        else:
            embed = discord.Embed(description="Failed to generate SSH session.", color=discord.Color.red())
            if send_response:
                await interaction.followup.send(embed=embed, ephemeral=True)
            return False
    else:
        embed = discord.Embed(description="Failed to execute tmate.", color=discord.Color.red())
        if send_response:
            await interaction.followup.send(embed=embed, ephemeral=True)
        return False

async def manage_vps(interaction: discord.Interaction, vps_identifier, action, target_user=None):
    if target_user is None:
        target_user = interaction.user
    await interaction.response.defer(ephemeral=True)
    vps = get_vps_by_identifier(target_user.id, vps_identifier)
    if not vps:
        embed = discord.Embed(description="No VPS found.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    if action == "start" and vps['suspended'] and target_user == interaction.user:
        embed = discord.Embed(description="This VPS is suspended by an admin. Contact support.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    container_id = vps['container_id']
    success = False
    if action == "start":
        success = await async_docker_start(container_id)
        if success:
            update_vps_status(container_id, "running")
    elif action == "stop":
        success = await async_docker_stop(container_id)
        if success:
            update_vps_status(container_id, "stopped")
    elif action == "restart":
        success = await async_docker_restart(container_id)
        if success:
            update_vps_status(container_id, "running")
    if success:
        embed = discord.Embed(title=f"VPS {action.title()}ed Successfully", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.set_footer(text=WATERMARK, icon_url=bot.user.avatar.url if bot.user.avatar else None)
        if action in ["start", "restart"]:
            await regen_ssh_command(interaction, vps_identifier, send_response=False, target_user=target_user)
            embed.description = "New SSH session sent to DMs."
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(description=f"Failed to {action} the VPS.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

async def create_vps(interaction: discord.Interaction, os_type, ram=DEFAULT_RAM, cpu=DEFAULT_CPU, disk=DEFAULT_DISK, target_user=None):
    if target_user is None:
        target_user = interaction.user
    user_id = target_user.id
    username = str(target_user)
    add_user(user_id, username)
    
    if is_banned(user_id):
        return await interaction.response.send_message("You are banned from creating VPS instances.", ephemeral=True)
    if count_user_vps(user_id) >= SERVER_LIMIT:
        return await interaction.response.send_message(f"You have reached your limit of {SERVER_LIMIT} VPS.", ephemeral=True)
    if get_total_instances() >= TOTAL_SERVER_LIMIT:
        return await interaction.response.send_message("Global server limit reached.", ephemeral=True)
    
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
            await target_user.send(embed=embed)
        except Exception:
            pass
        await interaction.followup.send("VPS is ready! Check your DMs for SSH access.", ephemeral=True)
    else:
        await async_docker_rm(container_id)
        await interaction.followup.send("Failed to generate SSH session.", ephemeral=True)

# Bot Groups & Commands
vps_group = app_commands.Group(name="vps", description="Manage your VPS instances")
admin_group = app_commands.Group(name="admin", description="Admin controls")

@bot.event
async def on_ready():
    change_status.start()
    sync_statuses.start()
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
    await bot.change_presence(activity=discord.Game(name=BOT_STATUS_NAME))

@tasks.loop(seconds=10)
async def change_status():
    try:
        count = get_total_instances()
        status = f"{BOT_STATUS_NAME} | {count} Active"
        await bot.change_presence(activity=discord.Game(name=status))
    except Exception as e:
        logger.error(f"Status task error: {e}")

@tasks.loop(seconds=30)
async def sync_statuses():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT container_id, status FROM vps')
    for row in cursor.fetchall():
        cid = row['container_id']
        stat = row['status']
        try:
            out = subprocess.check_output(["docker", "inspect", "-f", "{{.State.Status}}", cid]).decode().strip()
            if out != stat:
                update_vps_status(cid, out)
        except subprocess.CalledProcessError:
            if stat != "stopped":
                update_vps_status(cid, "stopped")
        except Exception as e:
            logger.error(f"Status sync error for {cid}: {e}")
    conn.close()

@vps_group.command(name="create", description="Create a new VPS instance")
@app_commands.choices(os_type=[
    app_commands.Choice(name="Ubuntu 24.04 LTS (Noble)", value="ubuntu-24.04"),
    app_commands.Choice(name="Ubuntu 22.04 LTS (Jammy)", value="ubuntu-22.04"),
    app_commands.Choice(name="Debian 13 (Trixie)", value="debian-13"),
    app_commands.Choice(name="Debian 12 (Bookworm)", value="debian-12")
])
async def vps_create(interaction: discord.Interaction, os_type: str, ram: str = DEFAULT_RAM, cpu: str = DEFAULT_CPU, disk: str = DEFAULT_DISK):
    await create_vps(interaction, os_type, ram, cpu, disk)

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
    await manage_vps(interaction, vps_identifier, "start")

@vps_group.command(name="stop", description="Stop a running VPS")
@app_commands.describe(vps_identifier="Container ID or Name")
async def vps_stop(interaction: discord.Interaction, vps_identifier: str = None):
    await manage_vps(interaction, vps_identifier, "stop")

@vps_group.command(name="restart", description="Restart a VPS")
@app_commands.describe(vps_identifier="Container ID or Name")
async def vps_restart(interaction: discord.Interaction, vps_identifier: str = None):
    await manage_vps(interaction, vps_identifier, "restart")

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
