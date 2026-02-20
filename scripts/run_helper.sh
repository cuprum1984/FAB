#!/bin/bash
# scripts/run_helper.sh
# Запуск бота-помощника отдельно от основного

cd "$(dirname "$0")/.."

# Активация виртуального окружения
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "venv/Scripts" ]; then
    source venv/Scripts/activate  # для Windows
fi

# Запуск
python bot/helper_main.py