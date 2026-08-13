#!/bin/bash
exec </dev/tty

# Smart directory detection (works whether run from root or inside vps-deploy)
if [ -f "bot.py" ]; then
    TARGET_DIR="."
elif [ -f "vps-deploy/bot.py" ]; then
    TARGET_DIR="vps-deploy"
elif [ -d "vps-deploy" ]; then
    TARGET_DIR="vps-deploy"
else
    TARGET_DIR="."
fi

BOT_PATTERN="python3[[:space:]]\+bot\.py"

is_online() {
    if [ -f "bot.pid" ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
        return 0
    elif pgrep -f "$BOT_PATTERN" > /dev/null; then
        return 0
    fi
    return 1
}

# Waits up to $1 seconds for the bot to stop responding to kill -0 / pgrep
wait_for_stop() {
    local timeout="${1:-5}"
    local waited=0
    while is_online && [ "$waited" -lt "$timeout" ]; do
        sleep 0.5
        waited=$((waited + 1))
    done
    ! is_online
}

while true; do
    clear
    echo "⚡ ─────────────────────────────────────────"
    echo "                24/7 MANAGER                 "
    echo "────────────────────────────────────────────"
    echo ""
    echo "1. 🚀  Start Bot (24/7 Background)"
    echo "2. 🔄  Restart Bot"
    echo "3. 🛑  Stop Bot"
    echo "4. 📊  Live Status & Logs"
    echo "5. ❌  Exit"
    echo "────────────────────────────────────────────"
    read -p "Enter choice [1-5]: " choice

    case $choice in
        1)
            cd "$TARGET_DIR" || { echo "❌ Could not enter $TARGET_DIR"; read -p "Press Enter..."; continue; }
            if is_online; then
                echo "⚠️  Bot is already running in background!"
            else
                echo "🚀  Launching bot 24/7..."
                nohup python3 bot.py > bot.log 2>&1 &
                echo $! > bot.pid
                sleep 0.5
                if kill -0 "$(cat bot.pid)" 2>/dev/null; then
                    echo "✅  Bot is online and running 24/7!"
                else
                    echo "❌  Failed to start. Check option 4 for logs."
                    rm -f bot.pid
                fi
            fi
            cd - > /dev/null || true
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "🔄  Restarting bot..."
            cd "$TARGET_DIR" || { echo "❌ Could not enter $TARGET_DIR"; read -p "Press Enter..."; continue; }

            if [ -f "bot.pid" ]; then
                kill "$(cat bot.pid)" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "$BOT_PATTERN" 2>/dev/null

            if wait_for_stop 5; then
                nohup python3 bot.py > bot.log 2>&1 &
                echo $! > bot.pid
                sleep 0.5
                if kill -0 "$(cat bot.pid)" 2>/dev/null; then
                    echo "✅  Bot restarted successfully!"
                else
                    echo "❌  Restart failed to start a new process. Check option 4 for logs."
                    rm -f bot.pid
                fi
            else
                echo "❌  Old bot process wouldn't stop in time — aborting restart to avoid running two copies."
                echo "    Try option 3 (Stop) manually, then option 1 (Start)."
            fi

            cd - > /dev/null || true
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "🛑  Stopping bot..."
            cd "$TARGET_DIR" || { echo "❌ Could not enter $TARGET_DIR"; read -p "Press Enter..."; continue; }

            if [ -f "bot.pid" ]; then
                PID=$(cat bot.pid)
                kill "$PID" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "$BOT_PATTERN" 2>/dev/null

            if wait_for_stop 5; then
                echo "✅  Bot stopped successfully (Offline)."
            else
                echo "⚠️  Bot didn't stop gracefully — sending SIGKILL..."
                pkill -9 -f "$BOT_PATTERN" 2>/dev/null
                sleep 0.5
                if is_online; then
                    echo "❌  Bot still appears to be running. Check manually with: ps aux | grep bot.py"
                else
                    echo "✅  Bot force-stopped."
                fi
            fi

            cd - > /dev/null || true
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "📊  Live Status Check:"
            cd "$TARGET_DIR" || { echo "❌ Could not enter $TARGET_DIR"; read -p "Press Enter..."; continue; }

            if is_online; then
                echo "🟢  Status: ONLINE (24/7 AFK Active)"
            else
                echo "🔴  Status: OFFLINE (Stopped)"
            fi
            echo ""
            echo "--- Recent Logs (bot.log) ---"
            if [ -f "bot.log" ]; then
                tail -n 12 bot.log
            else
                echo "No logs found yet."
            fi

            cd - > /dev/null || true
            echo ""
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "❌  Invalid option!"
            sleep 1
            ;;
    esac
done
