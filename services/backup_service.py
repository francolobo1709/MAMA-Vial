"""Servicio de Respaldo y Recuperación (Backups) para Mari - MAMA-Vial.

Empaqueta de forma compacta y segura los datos de memoria, ajustes, usuarios autorizados,
cola de uploads y planillas base para guardado en tarjeta SD o envío directo a Telegram.
"""

from __future__ import annotations

import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("MariBackup")


class BackupService:
    """Gestiona copias de seguridad de datos de laboratorio, memoria y configuraciones."""

    def __init__(self, base_dir: Optional[Path] = None, max_backups: int = 5) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.data_dir = self.base_dir / "data"
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = max_backups

    def create_backup_zip(self) -> Path:
        """Crea un archivo ZIP con timestamp que contiene data/ y las planillas base."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"mari_backup_{timestamp}.zip"
        zip_path = self.backup_dir / zip_filename

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # 1. Incluir archivos de datos relevantes
                if self.data_dir.exists():
                    for item in self.data_dir.rglob("*"):
                        if item.is_file():
                            # Evitar incluir copias de seguridad dentro de sí mismas
                            if "backups" in item.parts:
                                continue
                            rel_path = item.relative_to(self.base_dir)
                            zipf.write(item, arcname=str(rel_path))

                # 2. Incluir planillas base de laboratorio si existen
                for excel_file in self.base_dir.glob("*.xlsx"):
                    zipf.write(excel_file, arcname=excel_file.name)

            self._rotate_old_backups()
            logger.info("Backup generado con éxito: %s (%d bytes)", zip_path.name, zip_path.stat().st_size)
            return zip_path

        except Exception as exc:
            logger.error("Error al crear copia de seguridad: %s", exc)
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"Falla al generar backup comprimido: {exc}")

    def _rotate_old_backups(self) -> None:
        """Mantiene únicamente los últimos `max_backups` archivos para no saturar almacenamiento."""
        try:
            backups = sorted(
                self.backup_dir.glob("mari_backup_*.zip"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old_backup in backups[self.max_backups :]:
                try:
                    old_backup.unlink()
                    logger.info("Backup antiguo rotado y eliminado: %s", old_backup.name)
                except Exception as del_exc:
                    logger.warning("No se pudo eliminar backup antiguo %s: %s", old_backup.name, del_exc)
        except Exception as exc:
            logger.warning("Error durante la rotación de backups: %s", exc)

    def get_backup_list(self) -> List[Path]:
        """Retorna la lista ordenada de respaldos disponibles."""
        if not self.backup_dir.exists():
            return []
        return sorted(
            self.backup_dir.glob("mari_backup_*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
