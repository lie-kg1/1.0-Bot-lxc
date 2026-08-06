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
        return output[-2000:]  # Truncate for Discord limit
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
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        # Increased timeout to 180 seconds to allow smooth image pulling for Ubuntu 24 / Debian 13
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180.0)
        if proc.returncode != 0:
            logger.error(f"Docker run failed: {stderr.decode()}")
            return None
        return stdout.decode().strip()
    except asyncio.TimeoutError:
        logger.error("Docker run timed out (exceeded 180s)")
        return None
    except Exception as e:
        logger.error(f"Docker run error: {e}")
        return None

async def async_docker_start(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "start", container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)
        return proc.returncode == 0
    except asyncio.TimeoutError:
        logger.warning(f"Docker start timeout for {container_id}")
        return False
    except Exception as e:
        logger.error(f"Docker start error for {container_id}: {e}")
        return False

async def async_docker_stop(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "stop", container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)
        return proc.returncode == 0
    except asyncio.TimeoutError:
        logger.warning(f"Docker stop timeout for {container_id}")
        try:
            await asyncio.create_subprocess_exec("docker", "kill", container_id, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL).communicate()
        except:
            pass
        return False
    except Exception as e:
        logger.error(f"Docker stop error for {container_id}: {e}")
        return False

async def async_docker_restart(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "restart", container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.communicate(), timeout=30.0)
        return proc.returncode == 0
    except asyncio.TimeoutError:
        logger.warning(f"Docker restart timeout for {container_id}")
        return False
    except Exception as e:
        logger.error(f"Docker restart error for {container_id}: {e}")
        return False

async def async_docker_rm(container_id):
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        return proc.returncode == 0
    except Exception as e:
        logger.error(f"Docker rm error for {container_id}: {e}")
        return False

async def async_install_tmate(container_id, os_type):
    install_cmd = "apt-get update && apt-get install -y tmate curl wget sudo openssh-client"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "bash", "-c", install_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        if proc.returncode != 0:
            logger.warning(f"Tmate install warning for {container_id}: {stderr.decode()}")
        else:
            logger.info(f"Tmate installed in {container_id}")
    except asyncio.TimeoutError:
        logger.error(f"Tmate install timeout for {container_id}")
    except Exception as e:
        logger.error(f"Failed to install tmate in {container_id}: {e}")

# SSH capture
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
        exec_cmd = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "tmate", "-F",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        return exec_cmd
    except Exception as e:
        logger.error(f"Tmate exec failed: {e}")
        return None

# Generic regen SSH
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
                logger.warning(f"Cannot DM user {target_user.id}")
                if send_response:
                    embed_dm_fail = discord.Embed(description="New SSH session generated but could not send to DMs (privacy settings).", color=discord.Color.orange())
                    await interaction.followup.send(embed=embed_dm_fail, ephemeral=True)
                else:
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

# Start/Stop/Restart helpers
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
    os_type = vps['os_type']
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
        os_name = OS_MAPPING.get(os_type, ("ubuntu:22.04", "Ubuntu 22.04 LTS"))[1]
        embed = discord.Embed(title=f"VPS {action.title()}ed Successfully", description=f"OS: {os_name}", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.set_footer(text=WATERMARK, icon_url=bot.user.avatar.url if bot.user.avatar else None)
        if action in ["start", "restart"]:
            regen_success = await regen_ssh_command(interaction, vps_identifier, send_response=False, target_user=target_user)
            if regen_success:
                embed.description += "\nNew SSH session sent to DMs."
            else:
                embed.description += "\nFailed to generate new SSH session."
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(description=f"Failed to {action} the VPS.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

# Reinstall helper
async def reinstall_vps(interaction: discord.Interaction, vps_identifier, os_type, target_user=None):
    if target_user is None:
        target_user = interaction.user
    await interaction.response.defer(ephemeral=True)
    vps = get_vps_by_identifier(target_user.id, vps_identifier)
    if not vps:
        embed = discord.Embed(description="No VPS found.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
    container_id = vps['container_id']
    user_id = vps['user_id']
    hostname = vps['hostname']
    ram, cpu, disk = vps['ram'], vps['cpu'], vps['disk']
    
    # Stop and remove
    await async_docker_stop(container_id)
    await asyncio.sleep(2)
    await async_docker_rm(container_id)
    delete_vps(container_id)
    
    # Create new with unique name
    suffix = random.randint(1000, 9999)
    new_container_name = f"{os_type}-vps-{user_id}-{suffix}"
    image, os_name = OS_MAPPING.get(os_type, ("ubuntu:22.04", "Ubuntu 22.04 LTS"))
    
    new_container_id = await async_docker_run(image, hostname, ram, cpu, disk, new_container_name)
    if new_container_id:
        await async_install_tmate(new_container_id, os_type)
        await asyncio.sleep(10)  # Wait longer for install
        exec_process = await docker_exec_tmate(new_container_id)
        ssh_line = await capture_ssh_session_line(exec_process)
        if ssh_line:
            add_vps(user_id, new_container_id, new_container_name, os_type, hostname, ssh_line, ram, cpu, disk)
            embed = discord.Embed(title="VPS Reinstalled Successfully", description=f"OS: {os_name}\n```{ssh_line}```", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
            embed.set_footer(text=WATERMARK, icon_url=bot.user.avatar.url if bot.user.avatar else None)
            try:
                await target_user.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Cannot DM user {target_user.id} for reinstall")
            embed_success = discord.Embed(description="VPS has been reinstalled. Check your DMs for details.", color=discord.Color.green())
            await interaction.followup.send(embed=embed_success, ephemeral=True)
        else:
            embed = discord.Embed(description="Reinstall failed: Unable to generate SSH.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            await async_docker_rm(new_container_id)
    else:
        embed = discord.Embed(description="Reinstall failed: Docker creation error.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

# Create VPS helper
async def create_vps(interaction: discord.Interaction, os_type, ram=DEFAULT_RAM, cpu=DEFAULT_CPU, disk=DEFAULT_DISK, target_user=None):
    if target_user is None:
        target_user = interaction.user
    user_id = target_user.id
    username = str(target_user)
    add_user(user_id, username)
    if is_banned(user_id):
        embed = discord.Embed(description="You are banned from creating VPS instances.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if count_user_vps(user_id) >= SERVER_LIMIT:
        embed = discord.Embed(description=f"You have reached the limit of {SERVER_LIMIT} VPS instances.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if get_total_instances() >= TOTAL_SERVER_LIMIT:
        embed = discord.Embed(description=f"Global server limit reached: {TOTAL_SERVER_LIMIT} total running instances.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    # Validate resources against host
    try:
        host_info = client.info()
        host_cpus = host_info['NCPU']
        host_mem_gb = host_info['MemTotal'] / (1024 ** 3)
        req_cpu = float(cpu)
        req_ram = parse_gb(ram)
        if req_cpu > host_cpus:
            embed = discord.Embed(description=f"Requested CPU ({req_cpu}) exceeds host limit ({host_cpus}).", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if req_ram > host_mem_gb:
            embed = discord.Embed(description=f"Requested RAM ({req_ram}GB) exceeds host limit ({host_mem_gb:.1f}GB).", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    except Exception as e:
        logger.error(f"Resource validation failed: {e}")
        embed = discord.Embed(description="Resource validation failed. Please contact an admin.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Creating your VPS instance...", ephemeral=True)
    
    hostname = f"{VPS_HOSTNAME}-{user_id}"
    suffix = random.randint(1000, 9999)
    container_name = f"{os_type}-vps-{user_id}-{suffix}"
    
    image, os_name = OS_MAPPING.get(os_type, ("ubuntu:22.04", "Ubuntu 22.04 LTS"))
    container_id = await async_docker_run(image, hostname, ram, cpu, disk, container_name)
    
    if not container_id:
        embed = discord.Embed(description="Failed to create Docker container. (Check logs for details)", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        return
        
    await asyncio.sleep(5)  # Wait for container to start
    await async_install_tmate(container_id, os_type)
    await asyncio.sleep(10)  # Wait for install
    exec_process = await docker_exec_tmate(container_id)
    ssh_line = await capture_ssh_session_line(exec_process)
    
    if ssh_line:
        add_vps(user_id, container_id, container_name, os_type, hostname, ssh_line, ram, cpu, disk)
        embed = discord.Embed(title="VPS Instance Created", description=f"OS: {os_name}\nRAM: {ram} | CPU: {cpu} | Disk: {disk}\n```{ssh_line}```", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.set_footer(text=WATERMARK, icon_url=bot.user.avatar.url if bot.user.avatar else None)
        try:
            await target_user.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"Cannot DM user {target_user.id} for creation")
        embed_success = discord.Embed(description="Your VPS is ready! Check your DMs for access details.", color=discord.Color.green())
        await interaction.followup.send(embed=embed_success, ephemeral=True)
    else:
        embed = discord.Embed(description="Creation failed: Unable to generate SSH session.", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)
        await async_docker_stop(container_id)
        await asyncio.sleep(2)
        await async_docker_rm(container_id)

# Admin helpers
async def admin_manage_vps(interaction: discord.Interaction, target_user_id: int, vps_identifier: str, action: str):
    if not is_admin(interaction.user):
        embed = discord.Embed(description="This command is restricted to admins only.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    target_user = await bot.fetch_user(target_user_id)
    if not target_user:
        embed = discord.Embed(description="User not found.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    vps = get_vps_by_identifier(target_user_id, vps_identifier)
    if not vps:
        embed = discord.Embed(description="VPS not found for this user.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    container_id = vps['container_id']
    success = False
    if action == "delete":
        await async_docker_stop(container_id)
        await asyncio.sleep(2)
        await async_docker_rm(container_id)
        delete_vps(container_id)
        success = True
        msg = f"Deleted VPS for {target_user}"
    elif action in ["start", "stop", "restart"]:
        if action == "start":
            success = await async_docker_start(container_id)
            update_vps_status(container_id, "running")
        elif action == "stop":
            success = await async_docker_stop(container_id)
            update_vps_status(container_id, "stopped")
        elif action == "restart":
            success = await async_docker_restart(container_id)
            update_vps_status(container_id, "running")
        msg = f"{action.title()}ed VPS for {target_user}"
    elif action == "suspend":
        success = await async_docker_stop(container_id)
        if success:
            update_vps_status(container_id, "stopped")
            update_vps_suspended(container_id, 1)
        msg = f"Suspended VPS for {target_user}"
    elif action == "unsuspend":
        update_vps_suspended(container_id, 0)
        success = True
        msg = f"Unsuspended VPS for {target_user}. You can now start it."
    if success:
        embed = discord.Embed(title="Admin Action Completed", description=msg, color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.set_footer(text=WATERMARK, icon_url=bot.user.avatar.url if bot.user.avatar else None)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(description="Action failed.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

async def admin_kill_all(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        embed = discord.Embed(description="This command is restricted to admins only.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.defer()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT container_id FROM vps WHERE status = "running"')
    running = cursor.fetchall()
    conn.close()
    stopped = 0
    for row in running:
        cid = row['container_id']
        if await async_docker_stop(cid):
            update_vps_status(cid, "stopped")
            stopped += 1
            logger.info(f"Stopped {cid}")
    embed = discord.Embed(title="Admin: Kill All Running VPS", description=f"Successfully stopped {stopped} running VPS instances.", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=WATERMARK, icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="admin-list", description="Admin: List all VPS instances")
@app_commands.guild_only()
async def admin_list(interaction: discord.Interaction):
    if not is_admin(interaction.user):
        embed = discord.Embed(description="This command is restricted to admins only.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, v.container_id, v.container_name, v.os_type, v.hostname, v.status, v.ram, v.cpu, v.disk, v.suspended
        FROM vps v JOIN users u ON v.user_id = u.user_id
        ORDER BY v.created_at DESC
    ''')
    all_vps = cursor.fetchall()
    conn.close()
    if not all_vps:
        embed = discord.Embed(description="No VPS instances found.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    embed = discord.Embed(title="All VPS Instances", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))
    embed.set_author(name=bot.user.name, icon_url=bot.user.avatar.url if bot.user.avatar else None)
    for row in all_vps[:25]:
        username = row['username']
        container_id = row['container_id']
        container_name = row['container_name']
        os_type = row['os_type']
        hostname = row['hostname']
        status = row['status']
        ram = row['ram']
        cpu = row['cpu']
        disk = row['disk']
        suspended = row['suspended']
        status_emoji = "🟢" if status == "running" else "🔴"
        suspended_text = "(Suspended)" if suspended else ""
        os_name = OS_MAPPING.get(os_type, ("ubuntu:22.04", "Ubuntu 22.04 LTS"))[1]
        embed.add_field(
            name=f"{status_emoji} {username} - {container_name} ({os_name}) {suspended_text}",
            value=f"ID: 
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1
