"""Servicio de autenticación y control de acceso persistente para el Bot de Telegram de Mari.

Permite acceso automático para Franco/Mari y desbloqueo mediante contraseña para colaboradores autorizados.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger("MariAuth")


class AuthService:
    """Gestiona la lista blanca de usuarios autorizados y la validación de claves de acceso."""

    DEFAULT_AUTH_FILE = Path(__file__).resolve().parent.parent / "data" / "authorized_users.json"
    DEFAULT_PASSWORD = "MariLab2026"

    def __init__(self, auth_file: Optional[Path] = None) -> None:
        self.auth_file = auth_file or self.DEFAULT_AUTH_FILE
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        self.password = os.environ.get("ACCESS_PASSWORD", self.DEFAULT_PASSWORD).strip()

    def _load_authorized_ids(self) -> Dict[str, Dict[str, str]]:
        if not self.auth_file.exists():
            return {}
        try:
            with open(self.auth_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.error("Error leyendo archivo de usuarios autorizados: %s", exc)
            return {}

    def _save_authorized_ids(self, data: Dict[str, Dict[str, str]]) -> None:
        try:
            with open(self.auth_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Error guardando usuario autorizado: %s", exc)

    def is_user_authorized(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> bool:
        """Verifica si el usuario tiene acceso por lista fija o por contraseña previamente validada."""
        allowed_raw = os.environ.get("ALLOWED_USER", "Franco,Mari")
        allowed_list = [u.strip().lower() for u in allowed_raw.split(",") if u.strip()]

        if "*" in allowed_list:
            return True

        u_name = (username or "").lower()
        f_name = (first_name or "").lower()
        l_name = (last_name or "").lower()
        uid_str = str(user_id)

        # Chequeo directo por nombre/username de Franco o Mari
        for allowed in allowed_list:
            if allowed in u_name or allowed in f_name or allowed in l_name or allowed == uid_str:
                return True

        # Chequeo por registro persistente en base de datos local
        authorized_records = self._load_authorized_ids()
        return uid_str in authorized_records

    def verify_and_register(
        self,
        user_id: int,
        provided_password: str,
        first_name: str = "",
        username: str = "",
    ) -> bool:
        """Compara la contraseña provista y, si es correcta, autoriza al usuario de forma permanente."""
        if not provided_password:
            return False

        if provided_password.strip() == self.password:
            records = self._load_authorized_ids()
            records[str(user_id)] = {
                "first_name": first_name,
                "username": username,
            }
            self._save_authorized_ids(records)
            return True
        return False

    def get_password(self) -> str:
        """Retorna la contraseña activa actual."""
        return self.password
