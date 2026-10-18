@echo off
title Mari - Asistente 24/7
echo =====================================================================
echo   Iniciando a Mari (Asistente de Laboratorio Vial y Software)
echo   Bot en Telegram: https://t.me/Asistente_labotario_bot
echo =====================================================================
echo.
call .\.venv\Scripts\activate.bat
python telegram_bot.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] El bot se ha detenido con codigo %ERRORLEVEL%.
    pause
)
