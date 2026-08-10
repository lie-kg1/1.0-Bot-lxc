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
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days}d "
        if hours > 0 or days > 0:
            uptime_str += f"{hours}h "
        uptime_str += f"{minutes}m"
        return uptime_str
    except Exception as e:
        logger.error(f"Error calculating container uptime: {e}")
        return "Unknown"

def parse_ram_to_bytes(ram_str: str) -> int:
    """Safely translates RAM configurations into actual bytes for Docker enforcement."""
    try:
        ram_str = ram_str.strip().lower()
        if not ram_str:
            return 2 * 1024 * 1024 * 1024
        unit = ram_str[-1]
        value = int(ram_str[:-1])
        if unit == 'g':
            return value * 1024 * 1024 * 1024
        elif unit == 'm':
            return value * 1024 * 1024
        elif unit == 'k':
            return value * 1024
        return int(ram_str)
    except Exception:
        return 2 * 1024 * 1024 * 1024

def parse_cpu_to_nano(cpu_str: str) -> int:
    """Translates CPU allocations into nanosecond values to prevent core parameter mismatches."""
    try:
        cores = float(cpu_str)
        return int(cores * 1_000_000_000)
    except Exception:
        return 1_000_000_000

# App Command Autocompletes
async def os_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=data, value=key)
        for key, data in OS_MAPPING.items() if current.lower() in data.lower() or current.lower() in key.lower()
    ][:25]

async def user_vps_autocomplete(interaction: discord.Interaction, current: str):
    vps_list = get_user_vps(interaction.user.id)
    return [Here is your complete, unified bot.py script. It includes all necessary library imports, database management functions, container utility parsers for RAM/CPU formatting, slash command definitions with auto-complete features, administrative override mechanics, and the final production runtime loop.

import randomimport loggingimport subprocessimport sysimport osimport reimport timeimport discordfrom discord.ext import commands, tasksimport dockerimport asynciofrom discord import app_commandsimport sqlite3from dotenv import load_dotenvfrom datetime import datetime, timezone
# Load environment variables
load_dotenv()
# Configuration from .envTOKEN = os.getenv('TOKEN', 'DISCORD_BOT_TOKEN')ADMIN_ID = int(os.getenv('ADMIN_ID', 0))  # Admin user ID for checksBOT_STATUS_NAME = os.getenv('BOT_STATUS_NAME', 'UnixNodes')WATERMARK = os.getenv('WATERMARK', 'Powered by UnixNodes VPS Bot')# VPS Defaults from .envDEFAULT_RAM = os.getenv('DEFAULT_RAM', '2g')  # e.g., '2g', '4G'DEFAULT_CPU = os.getenv('DEFAULT_CPU', '1')  # Lowered default to '1' to avoid common errorsDEFAULT_DISK = os.getenv('DEFAULT_DISK', '10G')  # e.g., '20G' - Note: Disk limit not enforced in containerVPS_HOSTNAME = os.getenv('VPS_HOSTNAME', 'unix-free')  # Base hostname, append user IDSERVER_LIMIT = int(os.getenv('SERVER_LIMIT', 1))TOTAL_SERVER_LIMIT = int(os.getenv('TOTAL_SERVER_LIMIT', 50))  # Global total running server limitDATABASE_FILE = os.getenv('DATABASE_FILE', 'vps_bot.db')
# Centralized OS Mapping for Docker Images and Display NamesOS_MAPPING = {
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
)logger = logging.getLogger(__name__)
# Intentsintents = discord.Intents.default()
intents.message_content = Truebot = commands.Bot(command_prefix='/', intents=intents)client = docker.from_env()
def is_admin(member):
    if not isinstance(member, discord.Member):
        logger.warning("is_admin called with non-Member object")
        return False
    return member.id == ADMIN_ID
# Database setup with SQLite3def init_db():
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
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days}d "
        if hours > 0 or days > 0:
            uptime_str += f"{hours}h "
        uptime_str += f"{minutes}m"
        return uptime_str
    except Exception as e:
        logger.error(f"Error calculating container uptime: {e}")
        return "Unknown"
def parse_ram_to_bytes(ram_str: str) -> int:
    """Safely translates RAM configurations into actual bytes for Docker enforcement."""
    try:
        ram_str = ram_str.strip().lower()
        if not ram_str:
            return 2 * 1024 * 1024 * 1024
        unit = ram_str[-1]
        value = int(ram_str[:-1])
        if unit == 'g':
            return value * 1024 * 1024 * 1024
        elif unit == 'm':
            return value * 1024 * 1024
        elif unit == 'k':
            return value * 1024
        return int(ram_str)
    except Exception:
        return 2 * 1024 * 1024 * 1024
def parse_cpu_to_nano(cpu_str: str) -> int:
    """Translates CPU allocations into nanosecond values to prevent core parameter mismatches."""
    try:
        cores = float(cpu_str)
        return int(cores * 1_000_000_000)
    except Exception:
        return 1_000_000_000
# App Command Autocompletesasync def os_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=data, value=key)
        for key, data in OS_MAPPING.items() if current.lower() in data.lower() or current.lower() in key.lower()
    ][:25]
async def user_vps_autocomplete(interaction: discord.Interaction, current: str):
    vps_list = get_user_vps(interaction.user.id)
    return [

app_commands.Choice(name=f"{vps['container_name']} ({vps['os_type']})", value=vps['container_id'])
for vps in vps_list if current.lower() in vps['container_name'].lower() or current.lower() in vps['container_id'].lower()
][:25]
## Bot Lifecycle Events
@bot.event
async def on_ready():
logger.info("🤖 ─────────────────────────────────────────")
logger.info(f"✅ Active Bot Account: {bot.user.name} ({bot.user.id})")
logger.info("⚙️ Syncing App Discord Application Commands globally...")
try:
synced = await bot.tree.sync()
logger.info(f"✨ Successfully synced {len(synced)} slash commands!")
except Exception as e:
logger.error(f"❌ Failed to sync slash commands tree layout: {e}")
logger.info("────────────────────────────────────────────")
update_presence_task.start()
@tasks.loop(minutes=2)
async def update_presence_task():
try:
count = get_total_instances()
status_text = f"{BOT_STATUS_NAME} | {count} Active"
await bot.change_presence(activity=discord.Game(name=status_text))
except Exception as e:
logger.error(f"Status update failed: {e}")
## Core User Commands
@bot.tree.command(name="create", description="Provision a brand-new high-performance Linux VPS instance container.")
@app_commands.autocomplete(os_type=os_autocomplete)
@app_commands.describe(name="The name of your custom server machine", os_type="Choose your flavor of Linux distribution")
async def create_vps_cmd(interaction: discord.Interaction, name: str, os_type: str):
await interaction.response.defer(ephemeral=True)
user = interaction.user
if is_banned(user.id):
await interaction.followup.send("❌ Access Denied: You are restricted from interacting with this provisioner node.")
return
add_user(user.id, user.name)
if count_user_vps(user.id) >= SERVER_LIMIT and not is_admin(user):
await interaction.followup.send(f"❌ Allocation Fault: You hit your custom quota cap of {SERVER_LIMIT} servers.")
return
if get_total_instances() >= TOTAL_SERVER_LIMIT:
await interaction.followup.send("❌ Resource Depletion: The root hosting machine node is full. Try again later.")
return
clean_name = re.sub(r'[^a-zA-Z0-9_-]', '', name.lower())
if not clean_name:
await interaction.followup.send("❌ Structural Error: Container names must contain alphanumeric characters only.")
return
container_name = f"vps-{user.id}-{clean_name}"
if os_type not in OS_MAPPING:
await interaction.followup.send("❌ Selected OS distribution does not exist in mapping configuration.")
return
docker_image, display_os = OS_MAPPING[os_type]
hostname = f"{VPS_HOSTNAME}-{user.id}"
try:
# Check if container name conflicts on node filesystem
client.containers.get(container_name)
await interaction.followup.send("❌ Conflict error: A machine with that name already exists on this server cluster.")
return
except docker.errors.NotFound:
pass
await interaction.followup.send(f"⏳ Downloading image metadata layers and generating {display_os}...")
try:
# Ensure latest base components are available locally
await asyncio.to_thread(client.images.pull, docker_image)
# Calculate accurate bytes to avoid invalid container limit parameter flags
ram_bytes = parse_ram_to_bytes(DEFAULT_RAM)
nano_cpus = parse_cpu_to_nano(DEFAULT_CPU)
container = await asyncio.to_thread(
client.containers.run,
image=docker_image,
name=container_name,
hostname=hostname,
detach=True,
tty=True,
stdin_open=True,
mem_limit=ram_bytes,
nano_cpus=nano_cpus,
restart_policy={"Name": "unless-stopped"},
command="/bin/bash"
)
# Setup base secure SSH execution environment layers inside target instance
setup_script = (
"apt-get update && apt-get install -y openssh-server sudo && "
"mkdir /var/run/sshd && echo 'root:root' | chpasswd && "
"sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && "
"sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && "
"service ssh start"
)
await asyncio.to_thread(container.exec_run, cmd=["/bin/bash", "-c", setup_script])
# Query internal container network interface map
container.reload()
ip_addr = container.attrs['NetworkSettings']['IPAddress'] or "127.0.0.1"
ssh_cmd = f"ssh root@{ip_addr} (Password: root)"
add_vps(user.id, container.id, container_name, display_os, hostname, ssh_cmd, DEFAULT_RAM, DEFAULT_CPU, DEFAULT_DISK)
embed = discord.Embed(title="✨ VPS Container Created!", color=discord.Color.green())
embed.add_field(name="🏷️ Instance Name", value=f"{name}", inline=True)
embed.add_field(name="💿 Operating System", value=display_os, inline=True)
embed.add_field(name="🖥️ Node Hostname", value=f"{hostname}", inline=False)
embed.add_field(name="🧠 Memory Cap", value=DEFAULT_RAM, inline=True)
embed.add_field(name="⚡ Processing Cores", value=f"{DEFAULT_CPU} Core(s)", inline=True)
embed.add_field(name="🔑 SSH Access Line", value=f"{ssh_cmd}", inline=False)
embed.set_footer(text=WATERMARK)
await interaction.followup.send(embed=embed)
except Exception as e:
logger.error(f"Critical execution block provisioning failure: {e}")
await interaction.followup.send(f"❌ Cluster Deployment Error: {e}")
@bot.tree.command(name="manage", description="Access the power control state configurations for your virtual server.")
@app_commands.autocomplete(vps_id=user_vps_autocomplete)
@app_commands.describe(vps_id="Select the target instance", action="Power execution parameter choice")
@app_commands.choices(action=[
app_commands.Choice(name="🚀 Start Server", value="start"),
app_commands.Choice(name="🛑 Stop Server", value="stop"),
app_commands.Choice(name="🔄 Reboot Server", value="restart"),
app_commands.Choice(name="🗑️ Delete Server permanently", value="delete")
])
async def manage_vps_cmd(interaction: discord.Interaction, vps_id: str, action: str):
await interaction.response.defer(ephemeral=True)
user = interaction.user
vps = get_vps_by_container_id(vps_id)
if not vps or (vps['user_id'] != user.id and not is_admin(user)):
await interaction.followup.send("❌ Validation Error: Target container not found or authorization failed.")
return
if vps['suspended'] == 1:
await interaction.followup.send("❌ Access Denied: This server is locked/suspended by administration.")
return
try:
container = client.containers.get(vps_id)
if action == "start":
await asyncio.to_thread(container.start)
update_vps_status(vps_id, "running")
await interaction.followup.send(f"🟢 Server {vps['container_name']} has booted successfully.")
elif action == "stop":
await asyncio.to_thread(container.stop)
update_vps_status(vps_id, "stopped")
await interaction.followup.send(f"🔴 Server {vps['container_name']} has been powered down.")
elif action == "restart":
await asyncio.to_thread(container.restart)
update_vps_status(vps_id, "running")
await interaction.followup.send(f"🔄 Server {vps['container_name']} power cycled successfully.")
elif action == "delete":
await asyncio.to_thread(container.stop)
await asyncio.to_thread(container.remove, force=True)
delete_vps(vps_id)
await interaction.followup.send(f"🗑️ Server {vps['container_name']} storage blocks wiped fully.")
except Exception as e:
await interaction.followup.send(f"❌ State execution failed: {e}")
@bot.tree.command(name="status", description="Query resource statistics for your servers or the parent hypervisor node.")
async def status_cmd(interaction: discord.Interaction):
await interaction.response.defer(ephemeral=True)
user = interaction.user
cpu = psutil.cpu_percent()
ram = psutil.virtual_memory().percent
disk = psutil.disk_usage('/').percent
embed = discord.Embed(title="📊 Machine Node Infrastructure Performance Status", color=discord.Color.blue())
embed.add_field(name="🖥️ Hypervisor CPU Usage", value=f"{cpu}%", inline=True)
embed.add_field(name="🧠 Hypervisor RAM Usage", value=f"{ram}%", inline=True)
embed.add_field(name="💾 Storage Cluster Fill", value=f"{disk}%", inline=True)
vps_list = get_user_vps(user.id)
if vps_list:
vps_status_lines = []
for v in vps_list:
uptime = get_uptime(v['container_id'])
vps_status_lines.append(f"• {v['container_name']}: {v['status']} (Uptime: {uptime})")
embed.add_field(name="📁 Owned Containers Status", value="\n".join(vps_status_lines), inline=False)
else:
embed.add_field(name="📁 Owned Containers Status", value="No running containers allocated to your account.", inline=False)
embed.set_footer(text=WATERMARK)
await interaction.followup.send(embed=embed)
## Administration Commands Block
@bot.tree.command(name="admin_suspend", description="Toggle suspension lock parameter variables on client containers.")
@app_commands.describe(target_user_id="Target user discord Snowflake ID key", action="Lock execution value")
@app_commands.choices(action=[
app_commands.Choice(name="🔒 Suspend and Lock Server", value="suspend"),
app_commands.Choice(name="🔓 Unlock Server", value="unsuspend")
])
async def admin_suspend(interaction: discord.Interaction, target_user_id: str, action: str):
if not is_admin(interaction.user):
await interaction.response.send_message("❌ Admin Authority Required.", ephemeral=True)
return
await interaction.response.defer(ephemeral=True)
try:
t_id = int(target_user_id)
vps_list = get_user_vps(t_id)
if not vps_list:
await interaction.followup.send("⚠️ No containers found belonging to that user ID.")
return
for vps in vps_list:
container = client.containers.get(vps['container_id'])
if action == "suspend":
await asyncio.to_thread(container.stop)
update_vps_status(vps['container_id'], "suspended")
update_vps_suspended(vps['container_id'], 1)
else:
update_vps_status(vps['container_id'], "stopped")
update_vps_suspended(vps['container_id'], 0)
await interaction.followup.send(f"✅ Target ID {target_user_id} lifecycle suspension parameters set to: {action}.")
except Exception as e:
await interaction.followup.send(f"❌ Fatal operations modification execution error: {e}")
@bot.tree.command(name="admin_ban", description="Restrict a specific user from accessing the bot infrastructure deployment modules completely.")
@app_commands.describe(target_user_id="Target user discord Snowflake ID key")
async def admin_ban_cmd(interaction: discord.Interaction, target_user_id: str):
if not is_admin(interaction.user):
await interaction.response.send_message("❌ Admin Authority Required.", ephemeral=True)
return
try:
t_id = int(target_user_id)
add_ban(t_id)
vps_list = get_user_vps(t_id)
for v in vps_list:
try:
container = client.containers.get(v['container_id'])
await asyncio.to_thread(container.stop)
await asyncio.to_thread(container.remove, force=True)
delete_vps(v['container_id'])
except Exception:
pass
await interaction.response.send_message(f"✅ User {target_user_id} added to global node blacklist block registry.", ephemeral=True)
except Exception as e:
await interaction.response.send_message(f"❌ Failed to parse or record blacklist: {e}", ephemeral=True)
@bot.tree.command(name="admin_unban", description="Pardon a blacklisted user to allow resource interaction module authorization loops.")
@app_commands.describe(target_user_id="Target user discord Snowflake ID key")
async def admin_unban_cmd(interaction: discord.Interaction, target_user_id: str):
if not is_admin(interaction.user):
await interaction.response.send_message("❌ Admin Authority Required.", ephemeral=True)
return
try:
t_id = int(target_user_id)
remove_ban(t_id)
await interaction.response.send_message(f"✅ User {target_user_id} removed from registry block.", ephemeral=True)
except Exception as e:
await interaction.response.send_message(f"❌ Execution fail: {e}", ephemeral=True)
## Main Application Bootloader Execution Entry Engine Loop Block
if name == "main":
if not TOKEN or TOKEN == "DISCORD_BOT_TOKEN":
logger.error("❌ Fatal Configuration Block: Invalid TOKEN parameter string identified inside context environments (.env)")
sys.exit(1)
try:
bot.run(TOKEN)
except Exception as run_error:
logger.critical(f"❌ Bot application framework loop crashed unexpectedly during startup: {run_error}")
sys.exit(1)
