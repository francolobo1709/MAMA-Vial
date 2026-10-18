#!/usr/bin/env bash
# ==============================================================================
# Script de Configuración de Hardware Watchdog para Raspberry Pi
# Reinicia la Raspberry Pi automáticamente por hardware si el sistema se congela.
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}  Configuración del Hardware Watchdog en Raspberry Pi                ${NC}"
echo -e "${BLUE}=====================================================================${NC}"

# 1. Determinar archivo config.txt (soporta Bookworm / Bullseye / Buster)
CONFIG_TXT=""
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_TXT="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_TXT="/boot/config.txt"
fi

if [ -n "$CONFIG_TXT" ]; then
    echo -e "${GREEN}[1/3] Habilitando módulo de Watchdog en ${CONFIG_TXT}...${NC}"
    if ! grep -q "^dtparam=watchdog=on" "$CONFIG_TXT"; then
        sudo bash -c "echo 'dtparam=watchdog=on' >> $CONFIG_TXT"
        echo -e "${GREEN}✓ Parámetro 'dtparam=watchdog=on' añadido.${NC}"
    else
        echo -e "${GREEN}✓ Parámetro 'dtparam=watchdog=on' ya estaba activo.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ No se encontró config.txt (¿no es una Raspberry Pi física?). Continuando...${NC}"
fi

# 2. Instalar demonio watchdog
echo -e "\n${GREEN}[2/3] Instalando demonio watchdog de Linux...${NC}"
sudo apt-get update -y
sudo apt-get install -y watchdog

# 3. Configurar /etc/watchdog.conf
echo -e "\n${GREEN}[3/3] Configurando parámetros de watchdog.conf...${NC}"
WATCHDOG_CONF="/etc/watchdog.conf"

sudo bash -c "cat <<EOF > ${WATCHDOG_CONF}
# Configuración de Hardware Watchdog para Raspberry Pi - MAMA-Vial
watchdog-device = /dev/watchdog
watchdog-timeout = 15
max-load-1 = 24
min-memory = 1
realtime = yes
priority = 1
EOF"

sudo systemctl enable watchdog
sudo systemctl restart watchdog

echo -e "\n${GREEN}=====================================================================${NC}"
echo -e "${GREEN}✓ Hardware Watchdog configurado y activo.${NC}"
echo -e "${GREEN}  Si el procesador o kernel se congela por más de 15 segundos,${NC}"
echo -e "${GREEN}  el chip Broadcom reiniciará la Raspberry Pi de forma segura.${NC}"
echo -e "${GREEN}=====================================================================${NC}\n"
