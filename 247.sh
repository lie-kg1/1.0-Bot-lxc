#!/bin/bash
exec </dev/tty 2>/dev/null

if [ -d "vps-deploy" ]; then
    ENV_DIR="vps-deploy"
elif [ -f "bot.py" ]; then
    ENV_DIR="."
else
    ENV_DIR="vps-deploy"
fi

while true; do
    clear
    echo "⚡ =========================================="
    echo "    247 SPEED MANAGER (100% RELIABLE)        "
    echo "============================================"
    echo ""
    echo "1. 🚀 Start Bot (24/7 Background)"
    echo "2. 🔄 Restart Bot"
    echo "3. 🛑 Stop Bot"
    echo "4. 📊 Live Status & Logs"
    echo "5. ❌ Exit"
    echo "--------------------------------------------"
    read -p "Enter choice [1-5]: " choice

    if [ ! -d "$ENV_DIR" ] && [ "$ENV_DIR" != "." ]; then
        echo "⚠️ 'vps-deploy' directory missing! Run install first."
        read -p "Press Enter..."
        continue
    fi

    case $choice in
        1)
            cd "$ENV_DIR" || exit
            if systemctl is-active --quiet bot 2>/dev/null; then
                echo "⚠️ Bot is already running via systemd!"
            elif [ -f "bot.pid" ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
                echo "⚠️ Bot is already running in background!"
            else
                echo "🚀 Launching bot 24/7..."
                nohup python3 bot.py > bot.log 2>&1 &
                echo $! > bot.pid
                sleep 0.5
                if kill -0 "$(cat bot.pid)" 2>/dev/null; then
                    echo "✅ Bot is online and running 24/7!"
                else
                    echo "❌ Failed to start. Check option 4 for logs."
                fi
            fi
            cd - > /dev/null
            read -p "Press Enter..."
            ;;
        2)
            echo "🔄 Restarting bot instantly..."
            cd "$ENV_DIR" || exit
            sudo systemctl restart bot 2>/dev/null
            if [ -f "bot.pid" ]; then
                kill "$(cat bot.pid)" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "python3 bot.py" 2>/dev/null
            sleep 0.5
            nohup python3 bot.py > bot.log 2>&1 &
            echo $! > bot.pid
            echo "✅ Bot restarted successfully!"
            cd - > /dev/null
            read -p "Press Enter..."
            ;;
        3)
            echo "🛑 Stopping bot..."
            cd "$ENV_DIR" || exit
            sudo systemctl stop bot 2>/dev/null
            if [ -f "bot.pid" ]; then
                kill "$(cat bot.pid)" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "python3 bot.py" 2>/dev/null
            echo "✅ Bot completely stopped (offline)."
            cd - > /dev/null
            read -p "Press Enter..."
            ;;
        4)
            echo "📊 Live Status Check:"
            cd "$ENV_DIR" || exit
            ONLINE=false
            if systemctl is-active --quiet bot 2>/dev/null; then
                ONLINE=true
            elif [ -f "bot.pid" ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
                ONLINE=true
            elif pgrep -f "python3 bot.py" > /dev/null; then
                ONLINE=true
            fi

            if [ "$ONLINE" = true ]; then
                echo "🟢 Status: ONLINE (24/7 AFK Active)"
            else
                echo "🔴 Status: OFFLINE (Stopped)"
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
            read -p "Press Enter..."
            ;;
        5)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "❌ Invalid option!"
            sleep 1
            ;;
    esac
done
