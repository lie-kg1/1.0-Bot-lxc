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
    echo "🛠️ =========================================="
    echo "       247 BACKGROUND BOT MANAGER            "
    echo "============================================"
    echo ""
    echo "1. 🚀 Start Bot"
    echo "2. 🔄 Restart Bot"
    echo "3. 🛑 Stop Bot"
    echo "4. 📊 24/7 Status & Logs"
    echo "5. ❌ Exit"
    echo "--------------------------------------------"
    read -p "Enter your choice [1-5]: " choice

    if [ ! -d "$ENV_DIR" ] && [ "$ENV_DIR" != "." ]; then
        echo "⚠️ 'vps-deploy' directory not found! Please run option 1 (install) first."
        read -p "Press Enter to continue..."
        continue
    fi

    case $choice in
        1)
            cd "$ENV_DIR" || exit
            if [ -f "bot.pid" ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
                echo "⚠️ Bot is already running!"
            else
                echo "🚀 Starting bot in background..."
                nohup python3 bot.py > bot.log 2>&1 &
                echo $! > bot.pid
                sleep 1
                if kill -0 "$(cat bot.pid)" 2>/dev/null; then
                    echo "✅ Bot started successfully!"
                else
                    echo "❌ Bot failed to start! Check option 4 for error logs."
                fi
            fi
            cd - > /dev/null
            read -p "Press Enter to continue..."
            ;;
        2)
            echo "🔄 Restarting bot..."
            cd "$ENV_DIR" || exit
            if [ -f "bot.pid" ]; then
                PID=$(cat bot.pid)
                kill "$PID" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "python3 bot.py" 2>/dev/null
            sleep 1
            nohup python3 bot.py > bot.log 2>&1 &
            echo $! > bot.pid
            echo "✅ Bot restarted successfully!"
            cd - > /dev/null
            read -p "Press Enter to continue..."
            ;;
        3)
            echo "🛑 Stopping bot..."
            cd "$ENV_DIR" || exit
            if [ -f "bot.pid" ]; then
                PID=$(cat bot.pid)
                kill "$PID" 2>/dev/null
                rm -f bot.pid
            fi
            pkill -f "python3 bot.py" 2>/dev/null
            echo "✅ Bot stopped successfully!"
            cd - > /dev/null
            read -p "Press Enter to continue..."
            ;;
        4)
            echo "📊 Checking 24/7 status and logs..."
            cd "$ENV_DIR" || exit
            RUNNING=false
            if [ -f "bot.pid" ]; then
                PID=$(cat bot.pid)
                if kill -0 "$PID" 2>/dev/null; then
                    RUNNING=true
                fi
            fi

            if [ "$RUNNING" = true ]; then
                echo "🟢 Status: RUNNING (24/7 background mode active)"
            else
                echo "🔴 Status: STOPPED"
            fi
            echo ""
            echo "--- Last 10 lines of bot.log ---"
            if [ -f "bot.log" ]; then
                tail -n 10 bot.log
            else
                echo "No log file found yet."
            fi
            cd - > /dev/null
            echo ""
            read -p "Press Enter to continue..."
            ;;
        5)
            echo "Exiting manager..."
            exit 0
            ;;
        *)
            echo "❌ Invalid choice! Please enter a number between 1 and 5."
            sleep 2
            ;;
    esac
done
