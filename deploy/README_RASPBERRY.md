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

## 🛡️ Protección por Hardware Watchdog (Anti-Cuelgues)

Para evitar que la Raspberry Pi quede inaccesible en caso de cuelgues del sistema operativo o picos eléctricos en el laboratorio, se incluye un watchdog a nivel de silicio (Broadcom BCM2835):

```bash
# Se configura automáticamente al correr ./deploy/instalar_raspberry.sh
# O puedes ejecutarlo manualmente cuando quieras:
chmod +x deploy/configurar_watchdog.sh
sudo ./deploy/configurar_watchdog.sh
```

Si el kernel o sistema operativo no responde por más de 15 segundos, el microcontrolador de la Raspberry Pi ejecuta un reinicio en frío seguro y levanta a Mari nuevamente.

---

## ⚡ Supervisión Continua de Alimentación y Alertas Térmicas

Mari monitorea el hardware en segundo plano permanentemente:
1. **Alerta de Subvoltaje / Alimentación:** Si la fuente entrega menos de 4.63V o se detecta throttling por caída de tensión, Mari te enviará una notificación preventiva directa a Telegram para advertirte antes de que se corrompa la tarjeta MicroSD.
2. **Alerta Térmica Preventiva:** Si la temperatura del CPU supera los 75 °C por calor en obra o ensayos intensivos, Mari te alertará para revisar la ventilación del gabinete.
3. **Respaldo Automático Diario (20:00 hs):** Mari genera automáticamente una copia de seguridad comprimida `.zip` y te la envía a tu chat de Telegram todas las noches.

---

## 🩺 Verificación y Comandos en Telegram

Una vez encendida la Raspberry Pi, Mari enviará automáticamente un mensaje a Telegram avisando que el sistema inició tras el encendido o reinicio. También dispones de estos comandos:
- `/ping`: Para corroborar que responde inmediatamente y ver latencia en ms.
- `/health`: Diagnóstico completo en vivo (temperatura térmica en °C, estado de voltaje/fuente de la Raspberry Pi, RAM utilizada, CPU, latencia de IA Gemini y estado general).
- `/backup`: Genera una copia de seguridad comprimida ZIP con tu historial, memoria, usuarios autorizados y planillas Excel para descargarla directo en Telegram.
