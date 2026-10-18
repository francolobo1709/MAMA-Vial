# MAMA-Vial 🚧🔬
### Asistente Inteligente de Laboratorio Vial, Topografía y Control de Calidad

MAMA-Vial es un sistema autónomo de asistencia técnica para ingenieros, laboratoristas viales y topógrafos. Integra visión artificial multimodal, procesamiento conversacional por notas de voz y texto técnico, inyección automática en planillas Excel normadas y generación determinística de certificados oficiales en PDF (ensayos Marshall, granulometría, densidades y control de obra).

---

## 🚀 Características Principales

1. **Enrutamiento Contextual Inteligente**:
   - **Notas de voz**: Respuestas sintetizadas exclusivamente en audio conversacional (Edge-TTS / gTTS) sin tablas ni ruido visual.
   - **Texto técnico**: Respuestas estructuradas con tablas, matrices, fórmulas y recomendaciones normativas.
   - **Solicitud de audio**: Si se solicita voz por texto ("audio", "voz"), responde en audio fluido.

2. **Visión Multimodal & Inyección Excel**:
   - Detección de lecturas de campo, balanzas, termómetros y probetas.
   - Inyección sin pérdida de formato en planillas Excel (`12-10-26.xlsx`) preservando fórmulas y estilos de celda.

3. **Certificados PDF Automatizados**:
   - Emisión instantánea de certificados técnicos oficiales con sellos, validaciones y firmas digitales.

4. **Resiliencia Anti-503**:
   - Cascada multi-modelo de respaldo ante caídas de latencia o rate limits de Google Gemini (`gemini-3.1-flash-lite` -> fallbacks automáticos).

5. **Seguridad y Control de Acceso**:
   - Whitelist nativa para operadores autorizados y desbloqueo seguro mediante token/clave con comando `/acceso`.

---

## 🛠️ Requisitos Previos

- Python 3.10 o superior
- Token de Telegram provisto por [@BotFather](https://t.me/BotFather)
- API Key de Google Gemini obtenida en [Google AI Studio](https://aistudio.google.com/)

---

## ⚙️ Instalación y Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone https://github.com/francolobo1709/MAMA-Vial.git
cd MAMA-Vial
```

### 2. Configurar el entorno virtual
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Copiar el archivo de plantilla y completar las credenciales:
```bash
cp .env.example .env
```
Editar `.env`:
```ini
GEMINI_API_KEY=tu_api_key_aqui
GOOGLE_API_KEY=tu_api_key_aqui
TELEGRAM_BOT_TOKEN=tu_telegram_bot_token_aqui
ALLOWED_USER=Franco,Mari
ACCESS_PASSWORD=MariLab2026
```

### 5. Iniciar el Asistente
```bash
python telegram_bot.py
```

---

## 🍓 Despliegue 24/7 en Raspberry Pi (Servicio Autónomo)

Para que Mari funcione continuamente en una Raspberry Pi y arranque automáticamente al encenderla:

```bash
# 1. Dar permisos de ejecución al instalador
chmod +x deploy/instalar_raspberry.sh

# 2. Ejecutar instalación desatendida y alta en systemd
./deploy/instalar_raspberry.sh
```

Comandos útiles de gestión en la Raspberry Pi:
```bash
sudo journalctl -u mari.service -f     # Ver logs en vivo
sudo systemctl restart mari.service     # Reiniciar
sudo systemctl status mari.service      # Estado del proceso
```

---

## 🩺 Diagnóstico, Notificaciones y Backups en Telegram

El bot cuenta con herramientas integradas de supervisión y resguardo:
- **Aviso automático de reinicio**: Notifica al administrador al encender o reiniciar la Raspberry Pi.
- `/ping`: Verifica conectividad con Telegram y latencia en milisegundos.
- `/health`: Reporte integral de consumo de CPU, temperatura térmica en °C (Raspberry Pi), RAM del sistema y del proceso, latencia real contra Google Gemini API, turnos de memoria activa y locutora en uso.
- `/backup`: Genera una copia de seguridad comprimida ZIP con tu historial de memoria, ajustes, usuarios autorizados y planillas Excel para descargarla directo en Telegram.

---

## 🐳 Despliegue con Docker (Producción / Beta)

Para mantener el bot corriendo en un contenedor aislado:

```bash
docker compose up -d --build
```

Para ver los registros en tiempo real:
```bash
docker compose logs -f
```

---

## 📁 Estructura del Proyecto

```text
├── deploy/
│   ├── mari.service          # Unidad systemd para Raspberry Pi / Linux
│   ├── instalar_raspberry.sh # Script automatizado de aprovisionamiento
│   └── README_RASPBERRY.md   # Guía paso a paso para Raspberry Pi
├── services/
│   ├── auth_service.py       # Control de accesos y persistencia de usuarios
│   ├── excel_injector.py     # Inyección en planillas Excel sin romper formatos
│   ├── lab_calculator.py     # Motor de cálculos volumétricos y granulométricos
│   └── pdf_generator.py      # Generador de certificados y reportes PDF
├── data/
│   └── cola_uploads/         # Almacenamiento temporal de archivos de campo
├── 12-10-26.xlsx             # Planilla Excel base de ensayos de laboratorio
├── telegram_bot.py           # Orquestador del bot de Telegram y cascada Gemini
├── requirements.txt          # Dependencias fijadas para producción
├── Dockerfile                # Imagen Docker optimizada (AMD64 / ARM)
├── docker-compose.yml        # Orquestación de contenedores
├── .env.example              # Plantilla de variables de entorno seguras
└── .gitignore                # Reglas de exclusión de secretos y temporales
```
