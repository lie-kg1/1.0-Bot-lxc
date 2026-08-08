#!/bin/bash
exec </dev/tty 2>/dev/null

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

while true; do
    clear
    echo "⚡  ========================================="
    echo "                24/7 MANAGER                 "
    echo "============================================"
    echo ""
    echo "1. 🚀  Start Bot (24/7 Background)"
    echo "2. 🔄  Restart Bot"
    echo "3. 🛑  Stop Bot"
    echo "4. 📊  Live Status & Logs"
    echo "5. ❌  Exit"
    echo "--------------------------------------------"
    read -p "Enter choice [1-5]: " choice

    case $choice in
        1)
            cd "$TARGET_DIR" || exit
            if [ -f "bot.pid" ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
                echo "⚠️  Bot is already running in background!"
            elif pgrep -f "python3 bot.py" > /dev/null; then
                echo "⚠️  Bot process is already active!"
            else
                echo "🚀  Launching bot 24/7..."
                nohup python3 bot.py > bot.log 2>&1 &
                echo $! > bot.pid
                sleep 0.5
                if kill -0 "$(cat bot.pid)" 2>/dev/null; then
                    echo "✅  Bot is online and running 24/7!"
                else
                    echo "❌  Failed to start. Check option 4 for logs."
                fi
            fi
            cd - > /dev/null
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "🔄  Restarting bot instantly..."
            cd "$TARGET_DIR" || exit
            if [ -f "bot.pid" ]; then
                kill "$(cat bot.pid)" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "python3 bot.py" 2>/dev/null
            sleep 0.5
            nohup python3 bot.py > bot.log 2>&1 &
            echo $! > bot.pid
            echo "✅  Bot restarted successfully!"
            cd - > /dev/null
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "🛑  Stopping bot completely..."
            cd "$TARGET_DIR" || exit
            if [ -f "bot.pid" ]; then
                PID=$(cat bot.pid)
                kill "$PID" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "python3 bot.py" 2>/dev/null
            echo "✅  Bot stopped successfully (Offline)."
            cd - > /dev/null
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "📊  Live Status Check:"
            cd "$TARGET_DIR" || exit
            ONLINE=false
            if [ -f "bot.pid" ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
                ONLINE=true
            elif pgrep -f "python3 bot.py" > /dev/null; then
                ONLINE=true
            fi

            if [ "$ONLINE" = true ]; then
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
            cd - > /dev/null
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
