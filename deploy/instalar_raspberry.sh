#!/usr/bin/env bash
# ==============================================================================
# Script de Instalación Automatizada de Mari en Raspberry Pi (Raspberry Pi OS / Debian)
# Proyecto: MAMA-Vial (Asistente de Laboratorio Vial y Software)
# ==============================================================================

set -euo pipefail

# Colores para salida de terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # Sin color

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}   Instalador de Mari - Asistente 24/7 para Raspberry Pi             ${NC}"
echo -e "${BLUE}=====================================================================${NC}"

# Detectar usuario actual y ruta del proyecto
ACTUAL_USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${GREEN}[1/6] Directorio de instalación:${NC} ${SCRIPT_DIR}"
echo -e "${GREEN}[1/6] Usuario del sistema:${NC} ${ACTUAL_USER}"

# 1. Actualizar repositorios e instalar paquetes del sistema
echo -e "\n${YELLOW}[2/6] Instalando dependencias del sistema operativo...${NC}"
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    ffmpeg \
    libmagic1 \
    curl \
    git

# 2. Configurar entorno virtual de Python
echo -e "\n${YELLOW}[3/6] Creando entorno virtual (.venv)...${NC}"
cd "${SCRIPT_DIR}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓ Entorno virtual creado exitosamente.${NC}"
else
    echo -e "${GREEN}✓ Entorno virtual existente detectado.${NC}"
fi

# 3. Instalar librerías de Python
echo -e "\n${YELLOW}[4/6] Instalando requerimientos de Python...${NC}"
"${SCRIPT_DIR}/.venv/bin/pip" install --upgrade pip
"${SCRIPT_DIR}/.venv/bin/pip" install -r requirements.txt

# 4. Asegurar archivo .env
echo -e "\n${YELLOW}[5/6] Verificando variables de entorno (.env)...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️ Se ha creado un archivo .env desde .env.example.${NC}"
        echo -e "${YELLOW}   Por favor, edita .env con tus claves de Telegram y Google Gemini.${NC}"
    else
        touch .env
        echo -e "${RED}⚠️ No se encontró .env ni .env.example.${NC}"
    fi
else
    echo -e "${GREEN}✓ Archivo .env detectado.${NC}"
fi

# Crear directorio de datos
mkdir -p data/cola_uploads

# 5. Configurar servicio systemd para ejecución 24/7
echo -e "\n${YELLOW}[6/7] Configurando servicio Systemd para arranque automático...${NC}"
SERVICE_DEST="/etc/systemd/system/mari.service"

# Adaptar mari.service dinámicamente al usuario y ruta actual
sudo bash -c "cat <<EOF > ${SERVICE_DEST}
[Unit]
Description=Mari - Asistente de Laboratorio Vial y Software
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${ACTUAL_USER}
Group=${ACTUAL_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${SCRIPT_DIR}/.venv/bin/python ${SCRIPT_DIR}/telegram_bot.py
Restart=always
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=10
EnvironmentFile=${SCRIPT_DIR}/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable mari.service
sudo systemctl restart mari.service

# 6. Configurar Hardware Watchdog contra cuelgues del procesador
echo -e "\n${YELLOW}[7/7] Verificando protección por Hardware Watchdog...${NC}"
if [ -f "${SCRIPT_DIR}/deploy/configurar_watchdog.sh" ]; then
    chmod +x "${SCRIPT_DIR}/deploy/configurar_watchdog.sh"
    bash "${SCRIPT_DIR}/deploy/configurar_watchdog.sh" || echo -e "${YELLOW}⚠️ Watchdog omitido o no compatible con este entorno.${NC}"
fi

echo -e "\n${GREEN}=====================================================================${NC}"
echo -e "${GREEN}✓ ¡Instalación de Mari completada con éxito!${NC}"
echo -e "${GREEN}  El servicio 'mari.service' ya está activo y configurado para iniciar${NC}"
echo -e "${GREEN}  automáticamente cada vez que enciendas la Raspberry Pi.${NC}"
echo -e "${GREEN}=====================================================================${NC}"
echo -e "Comandos útiles de gestión:"
echo -e "  • Ver logs en tiempo real : ${BLUE}sudo journalctl -u mari.service -f${NC}"
echo -e "  • Reiniciar el bot        : ${BLUE}sudo systemctl restart mari.service${NC}"
echo -e "  • Detener el bot          : ${BLUE}sudo systemctl stop mari.service${NC}"
echo -e "  • Ver estado del servicio : ${BLUE}sudo systemctl status mari.service${NC}"
echo -e "=====================================================================\n"
