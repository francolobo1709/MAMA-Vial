# 🍓 Guía de Instalación de Mari en Raspberry Pi

Esta guía te permite desplegar a **Mari (Asistente de Laboratorio Vial y Software)** en tu Raspberry Pi (Raspberry Pi OS / Debian / Ubuntu) para que funcione **24/7 de forma autónoma**.

---

## ⚡ Método 1: Instalación Rápida con Script (Recomendado)

En tu Raspberry Pi, abre una terminal y ejecuta:

```bash
# 1. Clonar el repositorio (si aún no lo clonaste en la Raspberry)
git clone https://github.com/francolobo1709/MAMA-Vial.git
cd MAMA-Vial

# 2. Dar permisos de ejecución al instalador
chmod +x deploy/instalar_raspberry.sh

# 3. Ejecutar el script automatizado
./deploy/instalar_raspberry.sh
```

El script se encargará automáticamente de:
- Instalar paquetes del sistema (`python3-venv`, `ffmpeg`, `libmagic1`, `build-essential`).
- Crear el entorno virtual `.venv` e instalar todas las librerías.
- Configurar y registrar el servicio **systemd** para que Mari arranque sola cada vez que enciendas la Raspberry Pi.

---

## ⚙️ Configuración del archivo `.env`

Asegúrate de que el archivo `.env` en `/home/pi/MAMA-Vial/.env` (o la ruta donde esté clonado) contenga tus claves de producción:

```ini
GEMINI_API_KEY=tu_clave_de_gemini
GOOGLE_API_KEY=tu_clave_de_gemini
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
ALLOWED_USER=Franco,Mari
ACCESS_PASSWORD=MariLab2026
```

Si editaste el archivo `.env`, reinicia el servicio:
```bash
sudo systemctl restart mari.service
```

---

## 🛠️ Comandos de Control del Servicio en Raspberry Pi

| Acción | Comando |
|---|---|
| **Ver logs en tiempo real** | `sudo journalctl -u mari.service -f` |
| **Ver estado del bot** | `sudo systemctl status mari.service` |
| **Reiniciar a Mari** | `sudo systemctl restart mari.service` |
| **Detener a Mari** | `sudo systemctl stop mari.service` |
| **Iniciar a Mari** | `sudo systemctl start mari.service` |

---

## 🐳 Método 2: Despliegue con Docker (Alternativa aislada)

Si tienes Docker instalado en la Raspberry Pi:

```bash
docker compose up -d --build
```

Para ver los registros del contenedor:
```bash
docker compose logs -f
```

---

## 🩺 Verificación en Telegram

Una vez encendida la Raspberry Pi, puedes enviar a [@Asistente_labotario_bot](https://t.me/Asistente_labotario_bot):
- `/ping`: Para corroborar que responde inmediatamente.
- `/health`: Para ver el diagnóstico completo (temperatura/CPU, RAM utilizada en la Raspberry Pi, latencia de IA Gemini y estado general).
