#!/usr/bin/env bash
# ==============================================================================
# Script de Respaldo Automatizado por Cron (Raspberry Pi OS / Linux)
# Proyecto: MAMA-Vial (Asistente de Laboratorio Vial y Software)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${SCRIPT_DIR}"

"${SCRIPT_DIR}/.venv/bin/python" -c "from services.backup_service import BackupService; bs = BackupService(); z = bs.create_backup_zip(); print('✓ Backup generado con éxito:', z)"
