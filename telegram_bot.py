"""Mari Telegram Bot - Asistente de Laboratorio Vial, Topografía y Software para Franco y su equipo.

Enrutamiento Contextual Inteligente:
1. Nota de voz -> Respuesta ÚNICAMENTE en nota de voz (guion conversacional sin tablas).
2. Texto estándar -> Respuesta ÚNICAMENTE en texto (con tablas, matrices y formato visual).
3. Texto pidiendo voz ("audio", "voz", "háblame") -> Respuesta ÚNICAMENTE en audio conversacional.
4. Fotografías de campo -> Visión multimodal + inyección Excel con openpyxl + Certificado PDF oficial.
5. Planillas (.xlsx, .csv) -> Procesamiento con Pandas y respuesta ÚNICAMENTE en texto técnico.
6. Seguridad y Acceso: Whitelist para Franco y desbloqueo por contraseña (/acceso MariLab2026).
7. Resiliencia Anti-503: Cascada multi-modelo (gemini-3.1-flash-lite -> preview -> 3.5 -> 3.8).
"""

from __future__ import annotations

import os
import re
import json
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from google import genai
from google.genai import types

from services.auth_service import AuthService
from services.excel_injector import ExcelInjectorService
from services.lab_calculator import LabSpreadsheetService
from services.pdf_generator import LabPdfReportService, generar_informe_pdf

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("MariBot")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

MEMORY_FILE = DATA_DIR / "memory_mari.json"
SETTINGS_FILE = DATA_DIR / "settings_mari.json"

SYSTEM_PROMPT = (
    "Eres Mari, la asistente personal de laboratorio vial, topografía y desarrollo de software de Franco y de su equipo de trabajo.\n"
    "Franco es Analista de Estructuras Viales y de Transporte (Matrícula Profesional MP: 2205). REGLA ESTRICTA: Franco NO es ingeniero, es Analista matriculado. Por lo tanto, NUNCA te dirijas a Franco como 'ingeniero' ni uses el prefijo 'Ing.', trátalo siempre como 'Franco' o con su titulación de Analista matriculado.\n"
    "Tu nombre es Mari (en homenaje a la madre de Franco). Debes tratar a Franco siempre por su nombre ('Franco') con respeto, calidez, "
    "excelencia técnica y pragmatismo. A los demás miembros autorizados del equipo, trátalos de forma profesional y cordial por su nombre.\n"
    "Tienes voz y personalidad femenina, cálida, segura, rigurosa y con alta solvencia técnica.\n\n"
    "Tus capacidades son integrales y de alto nivel científico/técnico:\n"
    "1. INGENIERÍA VIAL Y ASFALTOS: Actúas como Ingeniera Civil Senior especialista en tecnología del asfalto. "
    "Dominas el diseño volumétrico (Marshall, Superpave), cálculo de densidades (teórica máxima Rice, Gmb), "
    "análisis granulométrico, control de calidad en planta/frente de obra, y normativas argentinas (DNV, IRAM).\n"
    "2. TOPOGRAFÍA Y GEODESIA: Asistencia en cálculos de coordenadas, transformaciones POSGAR 04, y procesamiento "
    "de datos para AutoCAD Civil 3D y equipos GNSS RTK.\n"
    "3. PROGRAMACIÓN Y SISTEMAS BACKEND: Escritura, arquitectura y depuración de código (Node.js, TypeScript, "
    "Express, JavaScript), manejo de bases de datos (PostgreSQL, MongoDB, MySQL), entornos Linux y despliegues.\n"
    "4. RESOLUCIÓN GENERAL: Redacción técnica de informes de laboratorio, detección de patologías en pavimentos, "
    "diagnóstico de fallas y asistencia en la toma de decisiones críticas de obra.\n\n"
    "REGLA ESTRICTA DE FORMATO: NUNCA uses acotaciones teatrales, asteriscos entre paréntesis, ni describas tu tono de voz (ej. *(Sonríe)* o *(Voz suave)*).\n"
    "Escribe ÚNICAMENTE las palabras exactas que vas a pronunciar, ya que tu respuesta pasará directamente a un motor de síntesis de voz (TTS).\n\n"
    "Estilo de comunicación: Claro, profesional, riguroso, estructurado, directo al grano y siempre en español."
)

AVAILABLE_VOICES: Dict[str, Dict[str, str]] = {
    "elena": {
        "name": "🇦🇷 Elena (Argentina - Adulta / Fluida / Local)",
        "edge_voice": "es-AR-ElenaNeural",
        "tld": "com.ar",
    },
    "elvira": {
        "name": "🇪🇸 Elvira (España - Adulta / Formal / Técnica)",
        "edge_voice": "es-ES-ElviraNeural",
        "tld": "es",
    },
    "dalia": {
        "name": "🇲🇽 Dalia (México - Adulta / Cálida / Expresiva)",
        "edge_voice": "es-MX-DaliaNeural",
        "tld": "com.mx",
    },
    "salome": {
        "name": "🇨🇴 Salomé (Colombia - Adulta / Pausada)",
        "edge_voice": "es-CO-SalomeNeural",
        "tld": "com.co",
    },
    "gtts_ar": {
        "name": "🌐 Google Argentina (Femenina estándar)",
        "edge_voice": "gtts",
        "tld": "com.ar",
    },
    "gtts_es": {
        "name": "🌐 Google España (Femenina estándar)",
        "edge_voice": "gtts",
        "tld": "es",
    },
}


# ---------------------------------------------------------------------------
# Utilidades de Limpieza de Texto para Audio
# ---------------------------------------------------------------------------
def clean_text_for_tts(text: str) -> str:
    """Elimina acotaciones teatrales, asteriscos y formato markdown para dicción natural."""
    t = re.sub(r'\*[^\*]*\([^\)]*\)[^\*]*\*', '', text)
    t = re.sub(r'\([^\)]*(?:voz|tono|sonr|pausa|gesto|profesional|cálid|calid|femenina)[^\)]*\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[[^\]]*(?:voz|tono|sonr|pausa|gesto|profesional|cálid|calid|femenina)[^\]]*\]', '', t, flags=re.IGNORECASE)
    t = t.replace('*', '').replace('#', '')
    t = re.sub(r'[`_~>]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


# ---------------------------------------------------------------------------
# Repositorio de Ajustes
# ---------------------------------------------------------------------------
class SettingsRepository:
    def __init__(self, filepath: Path = SETTINGS_FILE) -> None:
        self.filepath = filepath

    def get_settings(self) -> Dict[str, Any]:
        default = {
            "voice_key": "elena",
            "always_voice": os.environ.get("ALWAYS_VOICE", "false").lower() == "true",
        }
        if not self.filepath.exists():
            return default
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default, **data}
        except Exception:
            return default

    def update(self, **kwargs: Any) -> Dict[str, Any]:
        current = self.get_settings()
        current.update(kwargs)
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Error guardando ajustes: %s", exc)
        return current


# ---------------------------------------------------------------------------
# Repositorio de Memoria Persistente
# ---------------------------------------------------------------------------
class MemoryRepository:
    def __init__(self, filepath: Path = MEMORY_FILE, max_turns: int = 35) -> None:
        self.filepath = filepath
        self.max_turns = max_turns

    def load_history(self) -> List[Dict[str, str]]:
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def save_turn(self, user_text: str, model_text: str) -> None:
        history = self.load_history()
        history.append({"role": "user", "text": user_text})
        history.append({"role": "model", "text": model_text})
        if len(history) > self.max_turns * 2:
            history = history[-(self.max_turns * 2) :]
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Error al guardar memoria: %s", exc)

    def count_turns(self) -> int:
        return len(self.load_history()) // 2

    def clear(self) -> None:
        if self.filepath.exists():
            try:
                self.filepath.unlink()
            except Exception as exc:
                logger.error("Error al borrar memoria: %s", exc)


# ---------------------------------------------------------------------------
# Servicio TTS (Voz Femenina Adulta de Mari)
# ---------------------------------------------------------------------------
class TTSService:
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self.settings_repo = settings_repo

    async def synthesize(self, text: str, output_path: str = "mari_response.mp3") -> str:
        settings = self.settings_repo.get_settings()
        voice_key = settings.get("voice_key", "elena")
        voice_info = AVAILABLE_VOICES.get(voice_key, AVAILABLE_VOICES["elena"])
        edge_voice, tld = voice_info["edge_voice"], voice_info["tld"]

        if edge_voice == "gtts":
            from gtts import gTTS
            tts = gTTS(text=text, lang="es", tld=tld)
            tts.save(output_path)
            return output_path

        try:
            import edge_tts
            communicate = edge_tts.Communicate(text=text, voice=edge_voice)
            await communicate.save(output_path)
            return output_path
        except Exception as exc:
            logger.warning("Edge-TTS (%s) no disponible (%s); conmutando a gTTS fallback", edge_voice, exc)
            from gtts import gTTS
            tts = gTTS(text=text, lang="es", tld=tld)
            tts.save(output_path)
            return output_path


# ---------------------------------------------------------------------------
# Servicio de Inteligencia con Cascada Multi-Modelo Resiliente (Anti-503)
# ---------------------------------------------------------------------------
class GeminiAssistantService:
    MODEL_CASCADE = [
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]

    def __init__(self, memory_repo: MemoryRepository) -> None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada.")
        self.client = genai.Client(api_key=api_key)
        self.preferred_model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.memory = memory_repo

    def _get_ordered_models(self) -> List[str]:
        ordered = [self.preferred_model]
        for m in self.MODEL_CASCADE:
            if m not in ordered:
                ordered.append(m)
        return ordered

    def _build_contents(self, prompt_input: Any) -> List[types.Content]:
        contents: List[types.Content] = []
        for msg in self.memory.load_history():
            role = "model" if msg.get("role") == "model" else "user"
            msg_text = msg.get("text", "")
            if msg_text:
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg_text)]))

        def _to_part(item: Any) -> types.Part:
            if isinstance(item, types.Part):
                return item
            if isinstance(item, str):
                return types.Part.from_text(text=item)
            if isinstance(item, bytes):
                return types.Part.from_bytes(data=item, mime_type="application/octet-stream")
            if hasattr(item, "to_part"):
                return item.to_part()
            return types.Part.from_text(text=str(item))

        parts: List[types.Part] = []
        if isinstance(prompt_input, str):
            parts.append(types.Part.from_text(text=prompt_input))
        elif isinstance(prompt_input, list):
            for elem in prompt_input:
                parts.append(_to_part(elem))
        else:
            parts.append(_to_part(prompt_input))

        if parts:
            contents.append(types.Content(role="user", parts=parts))

        return contents

    async def generate_response(self, prompt_input: Any, raw_user_text: str) -> str:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.15,
        )
        contents = self._build_contents(prompt_input)
        models_to_try = self._get_ordered_models()

        last_error = None
        for model_name in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                reply_text = (response.text or "").strip()
                if reply_text:
                    self.memory.save_turn(raw_user_text, reply_text)
                    return reply_text
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "503" in err_str:
                    await asyncio.sleep(0.4)
                continue

        logger.error("Todos los modelos del pool fallaron. Último error: %s", last_error)
        raise RuntimeError(
            "Servidores de Google temporalmente saturados (503). Por favor reintenta en unos instantes."
        )

    async def extract_field_data_from_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Extrae variables de laboratorio vial en formato JSON con temperatura 0.0 y cascada anti-503."""
        prompt = (
            "Analiza con rigurosidad técnica esta imagen de apuntes manuscritos de laboratorio vial, libreta de campo o balanza digital.\n"
            "Extrae los valores numéricos correspondientes y devuélvelos ESTRICTAMENTE en formato JSON plano, sin bloques de código ```json ni comentarios.\n\n"
            "Busca las siguientes variables clave de dosificación y ensayo:\n"
            "- \"peso_seco\": peso de la probeta seca al aire (g)\n"
            "- \"peso_sumergido\": peso de la probeta sumergida en agua (g)\n"
            "- \"peso_sss\": peso saturado con superficie seca (g)\n"
            "- \"temperatura\": temperatura de mezcla o compactación (°C)\n"
            "- \"Gmm\": densidad teórica máxima Rice (g/cm³)\n\n"
            "Si hay múltiples probetas en la imagen (ej. Probeta 1, Probeta 2, Probeta 3), organízalas en un arreglo 'series'.\n"
            "Si es una sola probeta, devuélvelos directamente en el objeto principal.\n\n"
            "Ejemplo de formato con serie:\n"
            "{\n"
            '    "Gmm": 2.485,\n'
            '    "series": [\n'
            '        {"probeta": 1, "peso_seco": 1205.4, "peso_sumergido": 680.2, "peso_sss": 1210.1, "temperatura": 145.0},\n'
            '        {"probeta": 2, "peso_seco": 1208.1, "peso_sumergido": 681.0, "peso_sss": 1212.5, "temperatura": 146.0}\n'
            "    ]\n"
            "}\n"
            "O probeta individual:\n"
            "{\n"
            '    "peso_seco": 1205.4,\n'
            '    "peso_sumergido": 680.2,\n'
            '    "peso_sss": 1210.1,\n'
            '    "temperatura": 145.0,\n'
            '    "Gmm": 2.485\n'
            "}"
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    types.Part.from_text(text=prompt),
                ],
            )
        ]

        config = types.GenerateContentConfig(temperature=0.0)
        models_to_try = self._get_ordered_models()
        last_error = None

        for model_name in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                raw_text = (response.text or "").strip()
                match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                clean_json = match.group(1) if match else raw_text
                data = json.loads(clean_json)
                if isinstance(data, dict):
                    return data
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "503" in err_str:
                    await asyncio.sleep(0.4)
                continue

        logger.error("Error en extracción multimodal de datos: %s", last_error)
        raise RuntimeError(f"No se pudieron extraer los datos numéricos de la imagen: {last_error}")


# Instancias globales de servicios
settings_repo = SettingsRepository()
memory_repo = MemoryRepository()
tts_service = TTSService(settings_repo)
mari_service = GeminiAssistantService(memory_repo)
auth_service = AuthService()


# ---------------------------------------------------------------------------
# Seguridad y Autenticación con Contraseña
# ---------------------------------------------------------------------------
def is_authorized(update: Update) -> bool:
    if not update.effective_user:
        return False
    user = update.effective_user
    return auth_service.is_user_authorized(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


async def send_unauthorized_message(update: Update) -> None:
    if update.message:
        await update.message.reply_text(
            "🔒 *Acceso Protegido - Asistente Mari*\n\n"
            "Hola, soy Mari, la asistente técnica de laboratorio vial de Franco.\n"
            "Este bot es de acceso privado para el equipo de trabajo.\n\n"
            "Para desbloquear el acceso, ingresa la clave de autorización enviando:\n"
            "`/acceso <contraseña>`\n\n"
            "*(Solicita la clave al Analista Franco - MP: 2205)*",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# Enrutamiento de Respuestas: Separación Estricta Texto vs Audio
# ---------------------------------------------------------------------------
async def responder_con_texto(update: Update, texto: str) -> None:
    """Envía exclusivamente respuesta textual a Telegram dividiendo en bloques seguros de <= 4000 caracteres."""
    if not update.message or not texto:
        return

    max_len = 4000
    if len(texto) <= max_len:
        await update.message.reply_text(texto)
        return

    chunks: List[str] = []
    current_chunk = ""
    for paragraph in texto.split("\n"):
        if len(current_chunk) + len(paragraph) + 1 > max_len:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            if len(paragraph) > max_len:
                for i in range(0, len(paragraph), max_len):
                    chunks.append(paragraph[i : i + max_len])
            else:
                current_chunk = paragraph + "\n"
        else:
            current_chunk += paragraph + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    for chunk in chunks:
        if chunk:
            await update.message.reply_text(chunk)


async def responder_con_voz(update: Update, texto: str, caption: str = "🎙️ Mari") -> None:
    """Envía exclusivamente respuesta por nota de voz en MP3 nativo sin texto duplicado."""
    if not update.message or not update.effective_chat:
        return

    texto_limpio = clean_text_for_tts(texto)
    if not texto_limpio.strip():
        await update.message.reply_text(texto)
        return

    if len(texto_limpio) > 1200:
        texto_limpio = texto_limpio[:1190] + "... Para detalles numéricos extensos, pídeme el informe escrito."

    archivo_salida = f"respuesta_mari_{update.effective_chat.id}.mp3"

    try:
        await tts_service.synthesize(texto_limpio, archivo_salida)

        if os.path.exists(archivo_salida) and os.path.getsize(archivo_salida) > 0:
            with open(archivo_salida, "rb") as audio:
                await update.message.reply_voice(voice=audio, caption=caption)
        else:
            raise FileNotFoundError("Archivo de audio no generado.")

    except Exception as exc:
        logger.error("ERROR AL GENERAR O ENVIAR AUDIO: %s", exc)
        await update.message.reply_text(f"⚠️ Falló el TTS: {exc}\n\n{texto}")
    finally:
        if os.path.exists(archivo_salida):
            try:
                os.remove(archivo_salida)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Handlers de Telegram con Decisiones Inteligentes por Contexto
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    if not is_authorized(update):
        await send_unauthorized_message(update)
        return

    settings = settings_repo.get_settings()
    voice_name = AVAILABLE_VOICES.get(settings.get("voice_key", "elena"), {}).get("name", "Elena")
    caller_name = update.effective_user.first_name if update.effective_user else "Franco"

    saludo = (
        f"🏗️ *¡Hola, {caller_name}! Soy Mari, tu asistente de laboratorio vial, topografía y sistemas.*\n\n"
        "Estoy a tu entera disposición para control de calidad, cálculos de dosificación y procesamiento de datos.\n\n"
        "Comportamiento dinámico según el medio que utilices:\n"
        "• 🎙️ *Si me hablas por audio:* Te responderé únicamente con una nota de voz clara y al grano.\n"
        "• 💬 *Si me escribes por texto:* Te responderé únicamente por texto con tablas y fórmulas.\n"
        "• 🔊 *Si pides voz por texto:* (ej. 'contéstame por voz'), te responderé en audio.\n"
        "• 📸 *Si envías una foto:* (libreta o balanza), extraeré los datos, inyectaré el Excel sin romper formato y generaré el Certificado PDF oficial.\n"
        "• 📊 *Si envías una planilla:* (Excel o CSV), procesaré los datos con Pandas y responderé por texto.\n\n"
        f"• *Voz Activa:* {voice_name}\n"
        f"• *Memoria:* {memory_repo.count_turns()} turnos\n\n"
        "Comandos disponibles:\n"
        "• `/voces`: Elegir locutora\n"
        "• `/limpiar`: Reiniciar memoria de conversación\n"
        "• `/clave`: Consultar clave de acceso para colaboradores\n"
        "• `/analizar_lote`: Cruzar y procesar todas las planillas Excel en cola y generar informe PDF\n"
        "• `/limpiar_lote`: Vaciar la cola de planillas temporal"
    )
    await update.message.reply_text(saludo, parse_mode="Markdown")


async def access_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Permite a cualquier persona desbloquear el acceso enviando /acceso <contraseña>."""
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    args = context.args or []
    provided_password = " ".join(args).strip()

    if not provided_password:
        await update.message.reply_text(
            "🔑 *Ingreso de Clave de Acceso:*\n"
            "Para autorizarte, envía el comando con la contraseña:\n"
            "`/acceso <contraseña>`\n\n"
            "Ejemplo: `/acceso MariLab2026`",
            parse_mode="Markdown",
        )
        return

    if auth_service.verify_and_register(user.id, provided_password, user.first_name or "", user.username or ""):
        await update.message.reply_text(
            f"✅ *¡Acceso Concedido, {user.first_name or 'Compañero'}!*\n\n"
            "Te doy la bienvenida al sistema de laboratorio vial de Mari.\n"
            "Tu cuenta ha quedado autorizada permanentemente.\n\n"
            "Escribe `/start` para conocer las funciones o envíame tus notas de voz, fotos de libreta o consultas técnicas.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "❌ *Clave incorrecta.*\nVerifica la contraseña con Franco (Analista de Estructuras Viales MP: 2205) e intenta nuevamente.",
            parse_mode="Markdown",
        )


async def clave_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la contraseña actual a los usuarios autorizados para compartir con colaboradores."""
    if not update.message or not is_authorized(update):
        return

    pwd = auth_service.get_password()
    await update.message.reply_text(
        f"🔐 *Clave de Acceso para Colaboradores:*\n\n"
        f"Contraseña activa: `{pwd}`\n\n"
        f"Cualquier colaborador puede habilitar el bot en su Telegram enviando:\n"
        f"`/acceso {pwd}`",
        parse_mode="Markdown",
    )


async def voices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    if not is_authorized(update):
        await send_unauthorized_message(update)
        return

    keyboard = [
        [
            InlineKeyboardButton("🇦🇷 Elena (Argentina)", callback_data="voice:elena"),
            InlineKeyboardButton("🇪🇸 Elvira (España)", callback_data="voice:elvira"),
        ],
        [
            InlineKeyboardButton("🇲🇽 Dalia (México)", callback_data="voice:dalia"),
            InlineKeyboardButton("🇨🇴 Salomé (Colombia)", callback_data="voice:salome"),
        ],
        [
            InlineKeyboardButton("🌐 Google Argentina", callback_data="voice:gtts_ar"),
            InlineKeyboardButton("🌐 Google España", callback_data="voice:gtts_es"),
        ],
    ]
    current_key = settings_repo.get_settings().get("voice_key", "elena")
    current_name = AVAILABLE_VOICES.get(current_key, {}).get("name", "Elena")

    await update.message.reply_text(
        f"🎙️ *Selector de Voz Femenina de Mari*\n\nVoz actual: *{current_name}*\n\nToca una opción para cambiarla:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def voice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not is_authorized(update):
        return
    await query.answer()

    if query.data.startswith("voice:"):
        key = query.data.split(":", 1)[1]
        if key in AVAILABLE_VOICES:
            settings_repo.update(voice_key=key)
            voice_name = AVAILABLE_VOICES[key]["name"]
            await query.edit_message_text(f"✅ *Voz actualizada:* {voice_name}", parse_mode="Markdown")
            sample_text = "Hola, he configurado esta voz femenina para responder tus notas de voz."
            sample_path = "sample_voice.mp3"
            try:
                await tts_service.synthesize(sample_text, sample_path)
                if os.path.exists(sample_path):
                    with open(sample_path, "rb") as f:
                        await context.bot.send_voice(chat_id=query.message.chat_id, voice=f, caption=f"🎙️ Muestra: {voice_name}")
                    os.remove(sample_path)
            except Exception as exc:
                logger.error("Error al enviar muestra: %s", exc)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message or not is_authorized(update):
        return
    memory_repo.clear()
    await update.message.reply_text("🧹 Memoria de conversación reiniciada en blanco.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa texto: si pide voz responde en audio; de lo contrario responde SOLO en texto."""
    if not update.message or not update.message.text or not update.effective_chat:
        return

    # Si no está autorizado, chequear si escribió la clave directamente
    if not is_authorized(update):
        user = update.effective_user
        raw_text = update.message.text.strip()
        if user and raw_text == auth_service.get_password():
            auth_service.verify_and_register(user.id, raw_text, user.first_name or "", user.username or "")
            await update.message.reply_text(
                f"✅ *¡Acceso Concedido, {user.first_name or 'Compañero'}!*\n\n"
                "Te doy la bienvenida al sistema de laboratorio vial de Mari.\n"
                "Tu cuenta ha quedado autorizada permanentemente.\n\n"
                "Escribe `/start` para conocer las funciones o envíame tus fotos, audios y consultas.",
                parse_mode="Markdown",
            )
            return

        await send_unauthorized_message(update)
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Detección de solicitud explícita de audio
    wants_voice = any(k in user_text.lower() for k in [
        "por voz", "en voz", "con voz", "hablame", "háblame",
        "nota de voz", "mándame un audio", "mandame un audio",
        "en audio", "con audio", "audio"
    ])

    if wants_voice:
        await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
        prompt = (
            "[INSTRUCCIÓN INTERNA: El usuario solicitó escuchar tu respuesta por voz. "
            "Responde de forma 100% conversacional, fluida y directa. "
            "Prohibido usar tablas de markdown, bloques de código, asteriscos de tono teatral o viñetas complejas.]\n\n"
            f"Consulta: {user_text}"
        )
        try:
            respuesta = await mari_service.generate_response(prompt, user_text)
            await responder_con_voz(update, respuesta)
        except Exception as exc:
            logger.error("Error procesando audio solicitado: %s", exc)
            await update.message.reply_text(f"⚠️ Error al generar respuesta de voz: {exc}")
    else:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        try:
            respuesta = await mari_service.generate_response(user_text, user_text)
            await responder_con_texto(update, respuesta)
        except Exception as exc:
            logger.error("Error procesando texto: %s", exc)
            await update.message.reply_text(f"⚠️ Error al generar respuesta: {exc}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa nota de voz recibida y responde EXCLUSIVAMENTE con nota de voz conversacional."""
    if not update.message or not update.message.voice or not update.effective_chat:
        return

    if not is_authorized(update):
        await send_unauthorized_message(update)
        return

    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        audio_bytes = bytes(await voice_file.download_as_bytearray())

        prompt_parts = [
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg"),
            (
                "[INSTRUCCIÓN INTERNA: El usuario te está hablando por nota de voz desde el laboratorio o la obra. "
                "Responde ÚNICAMENTE de forma conversacional, natural, técnica y al grano. "
                "Prohibido usar tablas, código, fórmulas en formato LaTeX o viñetas complejas. "
                "Tu respuesta será sintetizada y enviada exclusivamente como nota de voz.]"
            ),
        ]

        respuesta = await mari_service.generate_response(prompt_parts, "[Nota de voz del usuario]")
        await responder_con_voz(update, respuesta)

    except Exception as exc:
        logger.error("Error al procesar nota de voz: %s", exc)
        await update.message.reply_text(
            "⚠️ Los servidores tuvieron una saturación momentánea al procesar el audio (503). "
            "Por favor reenvíame la nota de voz en unos segundos."
        )


COLA_UPLOADS_DIR = DATA_DIR / "cola_uploads"
COLA_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe planillas de laboratorio (.xlsx, .xls, .csv), las guarda en cola y notifica al usuario."""
    if not update.message or not update.message.document or not update.effective_chat:
        return

    if not is_authorized(update):
        await send_unauthorized_message(update)
        return

    doc = update.message.document
    filename = doc.file_name or "planilla.xlsx"

    # Validar extensión de archivo de planilla
    if not filename.lower().endswith((".xlsx", ".xls", ".csv")):
        await update.message.reply_text(
            "⚠️ Por favor, envía archivos de planilla (.xlsx, .xls o .csv) para el análisis técnico de laboratorio."
        )
        return

    chat_id = update.effective_chat.id
    chat_folder = COLA_UPLOADS_DIR / str(chat_id)
    chat_folder.mkdir(parents=True, exist_ok=True)
    destino_archivo = chat_folder / filename

    try:
        doc_file = await context.bot.get_file(doc.file_id)
        await doc_file.download_to_drive(str(destino_archivo))

        if "cola_archivos" not in context.user_data or not isinstance(context.user_data["cola_archivos"], list):
            context.user_data["cola_archivos"] = []

        # Evitar duplicados por nombre de archivo en la misma sesión
        cola: List[Dict[str, str]] = context.user_data["cola_archivos"]
        cola = [item for item in cola if item.get("filename") != filename]
        cola.append({"filename": filename, "path": str(destino_archivo)})
        context.user_data["cola_archivos"] = cola

        total = len(cola)
        await update.message.reply_text(
            f"📥 *Planilla '{filename}' añadida a la cola.* (Total acumulado: *{total}*)\n\n"
            f"• Envía más planillas (ej. del mes de septiembre) o escribe `/analizar_lote` para procesar y generar el informe consolidado en PDF.\n"
            f"• Para descartar la cola actual, usa `/limpiar_lote`.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error al descargar planilla para cola: %s", exc)
        await update.message.reply_text(f"⚠️ Error al recibir la planilla: {exc}")


async def handle_analizar_lote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa el lote completo de planillas en cola, cruza datos de laboratorio y genera el reporte PDF consolidado."""
    if not update.message or not update.effective_chat:
        return

    if not is_authorized(update):
        await send_unauthorized_message(update)
        return

    cola: List[Dict[str, str]] = context.user_data.get("cola_archivos", [])
    if not cola:
        await update.message.reply_text(
            "⚠️ No hay planillas en la cola. Por favor, sube los archivos de Excel primero (ej. 30-09-26.xlsx) y luego ejecuta `/analizar_lote`.",
            parse_mode="Markdown",
        )
        return

    chat_id = update.effective_chat.id
    caller_name = update.effective_user.first_name if update.effective_user else "Franco"
    total_docs = len(cola)

    await update.message.reply_text(
        f"⚙️ *Procesando lote de {total_docs} planillas de laboratorio...*\n"
        "Analizando densidades Rice (Gmm) y Bulk (Gmb), vacíos de aire (%Va), tendencias volumétricas y redactando el informe consolidado en PDF. Esto tomará unos segundos...",
        parse_mode="Markdown",
    )
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    archivos_procesados: List[str] = []
    datos_consolidados = ""
    resumen_series_total: List[Dict[str, Any]] = []

    try:
        for idx, item in enumerate(cola, start=1):
            fpath = Path(item["path"])
            fname = item["filename"]
            if not fpath.exists():
                continue

            with open(fpath, "rb") as f:
                fbytes = f.read()

            parsed = LabSpreadsheetService.inspect_and_parse(fbytes, fname)
            marshall = LabSpreadsheetService.extract_marshall_parameters(fbytes, fname)
            if marshall:
                marshall["archivo"] = fname
                resumen_series_total.append(marshall)

            tabla_resumen = ""
            for table in parsed.get("preview_tables", []):
                tabla_resumen += f"Hoja '{table['sheet']}' ({table['row_count']} filas):\n{table['head_markdown']}\n"

            datos_consolidados += (
                f"\n========================================\n"
                f"ARCHIVO {idx}/{total_docs}: {fname}\n"
                f"========================================\n"
                f"Hojas: {', '.join(parsed.get('sheets', []))}\n"
                f"{tabla_resumen}\n"
            )
            if marshall:
                datos_consolidados += (
                    f"Cálculos Marshall detectados:\n"
                    f"- Gmm (Rice): {marshall.get('Gmm')}\n"
                    f"- Gmb Promedio: {marshall.get('promedio_gmb')}\n"
                    f"- Vacíos %Va Promedio: {marshall.get('promedio_va')}%\n"
                    f"- Series evaluadas: {len(marshall.get('series', []))}\n"
                )
            archivos_procesados.append(str(fpath))

        # Instrucción maestra estricta para rol QA Asfalto Senior
        instruccion = (
            "Actúa en tu rol de Ingeniera Civil Senior especialista en tecnología del asfalto. "
            "Realiza un INFORME TÉCNICO EXHAUSTIVO Y PROFUNDO del lote de planillas adjunto. "
            "PROHIBIDO hacer resúmenes genéricos. Quiero especificidad absoluta y datos duros:\n\n"
            "1. TABLAS CONSOLIDADAS: Estructura los datos de Gmb, Gmm, %Va, Estabilidad y Fluencia por fecha y progresiva.\n"
            "2. ANÁLISIS ESTADÍSTICO: Evalúa la media, desviación y variabilidad del contenido de asfalto y vacíos.\n"
            "3. EVALUACIÓN NORMATIVA ESTRICTA: Compara los resultados numéricamente contra las tolerancias de los pliegos DNV/IRAM.\n"
            "4. DIAGNÓSTICO PATOLÓGICO: Si un Va es del 7.8%, explica térmicamente o volumétricamente por qué falló la compactación en esa progresiva exacta.\n"
            "5. RECOMENDACIONES DE PLANTA Y PISTA: Acciones correctivas exactas (temperaturas, dosificación de filler, patrón de rodillo).\n\n"
            "Usa formato Markdown profesional con tablas bien estructuradas. Tu respuesta será impresa directamente como un informe de laboratorio oficial."
        )

        prompt_final = f"{instruccion}\n\n{datos_consolidados}"

        # Generar diagnóstico consolidado con Gemini (usando _build_contents corregido)
        prompt_parts: List[Any] = [prompt_final]
        respuesta_texto = await mari_service.generate_response(
            prompt_parts, f"[Lote Mensual: {len(archivos_procesados)} planillas]"
        )

        # 1. Enviar informe técnico detallado por Telegram en bloques seguros
        await responder_con_texto(update, respuesta_texto)

        # 2. Generar el PDF consolidado oficial utilizando el motor de impresión FPDF
        nombre_pdf = f"Resumen_Mensual_Laboratorio_{len(archivos_procesados)}_Planillas.pdf"
        ruta_pdf = generar_informe_pdf(respuesta_texto, nombre_pdf)

        if os.path.exists(ruta_pdf):
            with open(ruta_pdf, "rb") as documento:
                await update.message.reply_document(
                    document=documento,
                    caption=f"✅ Franco, aquí tienes el análisis consolidado de las {len(archivos_procesados)} planillas procesadas.",
                )

        # 3. Limpieza de archivos temporales de la cola
        for p in archivos_procesados:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        context.user_data["cola_archivos"] = []

    except Exception as exc:
        logger.error("Error al procesar lote de planillas: %s", exc)
        await update.message.reply_text(f"⚠️ Ocurrió un error al procesar el lote de planillas: {exc}")


async def handle_limpiar_lote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Vacía la cola de planillas temporal de la sesión del usuario."""
    if not update.message or not update.effective_chat:
        return

    if not is_authorized(update):
        await send_unauthorized_message(update)
        return

    cola: List[Dict[str, str]] = context.user_data.get("cola_archivos", [])
    for item in cola:
        p = item.get("path")
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    context.user_data["cola_archivos"] = []
    await update.message.reply_text(
        "🗑️ *Cola de planillas vaciada correctamente.* Puedes enviar nuevas planillas cuando desees.",
        parse_mode="Markdown",
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa fotografías de campo: visión Gemini + inyección Excel multiserie con openpyxl + Certificado PDF."""
    if not update.message or not update.message.photo or not update.effective_chat:
        return

    if not is_authorized(update):
        await send_unauthorized_message(update)
        return

    chat_id = update.effective_chat.id
    photo = update.message.photo[-1]
    caption = (update.message.caption or "").strip()
    caller_name = update.effective_user.first_name if update.effective_user else "Franco"

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    await update.message.reply_text(
        "📸 *Fotografía de campo recibida.* Mari está analizando la libreta/balanza con visión computacional...",
        parse_mode="Markdown",
    )

    try:
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = bytes(await photo_file.download_as_bytearray())

        # 1. Extracción multimodal con Gemini (temperatura 0.0 y cascada anti-503)
        datos_campo = await mari_service.extract_field_data_from_image(photo_bytes)

        # Verificar si hay al menos una variable útil extraída
        has_series = bool(datos_campo.get("series"))
        has_direct = any(v is not None for k, v in datos_campo.items() if k != "series")

        if not has_series and not has_direct:
            prompt_parts = [
                types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg"),
                f"Fotografía técnica: {caption or 'Analiza la imagen'}\n"
                "[INSTRUCCIÓN INTERNA: No se identificaron números de pesaje ni variables de ensayo en la foto. "
                "Proporciona un diagnóstico visual técnico de la imagen (ej. equipo, fisuras o pavimento).]",
            ]
            resp = await mari_service.generate_response(prompt_parts, f"[Foto técnica] - {caption}")
            await responder_con_texto(update, resp)
            return

        # 2. Inyección con mapeo dinámico y soporte multiserie usando openpyxl
        template_excel = "12-10-26.xlsx"
        output_excel = "12-10-26_Actualizada.xlsx"

        resultado = ExcelInjectorService.inject_field_data(
            field_data=datos_campo,
            template_path=template_excel,
            output_path=output_excel,
            sheet_name="marshall",
        )

        # 3. Generación automática del Certificado PDF oficial
        output_pdf = "Certificado_Marshall_Mari.pdf"
        LabPdfReportService.generate_marshall_certificate(
            summary_data=resultado,
            output_path=output_pdf,
            operator_name=caller_name,
        )

        # 4. Construir reporte técnico desglosado para Telegram
        num_probetas = len(resultado.get("series", []))
        reporte_lineas = [
            f"📋 *Reporte de Ensayo Marshall procesado por Mari*",
            f"Operador: *{caller_name}* | Muestras detectadas: *{num_probetas}*\n",
            "He inyectado los datos en las celdas correspondientes de tu planilla sin alterar el formato ni fórmulas preexistentes:\n",
        ]

        for s in resultado.get("series", []):
            num_p = s.get("probeta", 1)
            reporte_lineas.append(f"🔬 *Probeta {num_p}:*")
            if s.get("peso_seco") is not None:
                reporte_lineas.append(f"  • Peso Seco: `{s['peso_seco']} g`")
            if s.get("peso_sumergido") is not None:
                reporte_lineas.append(f"  • Peso Sumergido: `{s['peso_sumergido']} g`")
            if s.get("peso_sss") is not None:
                reporte_lineas.append(f"  • Peso SSS: `{s['peso_sss']} g`")
            if s.get("temperatura") is not None:
                reporte_lineas.append(f"  • Temperatura: `{s['temperatura']} °C`")
            if s.get("Gmb") is not None:
                reporte_lineas.append(f"  • *Gmb calculado:* `{s['Gmb']} g/cm³`")
            if s.get("Va") is not None:
                reporte_lineas.append(f"  • *Vacíos %Va:* `{s['Va']}%`")
            reporte_lineas.append("")

        if resultado.get("Gmm") is not None:
            reporte_lineas.append(f"⚖️ *Densidad Teórica Máxima (Rice / Gmm):* `{resultado['Gmm']} g/cm³`")

        if num_probetas > 1 and resultado.get("promedio_gmb") is not None:
            reporte_lineas.append(f"📊 *Promedio Serie Gmb:* `{resultado['promedio_gmb']} g/cm³`")
            if resultado.get("promedio_va") is not None:
                reporte_lineas.append(f"📊 *Promedio Serie Vacíos %Va:* `{resultado['promedio_va']}%`")

        reporte_lineas.append("\n📄 *Archivos generados y adjuntos:*")
        reporte_lineas.append("1. Planilla Excel oficial actualizada (`.xlsx`)")
        reporte_lineas.append("2. Certificado de ensayo formal listo para firmar o imprimir (`.pdf`)")

        mensaje_final = "\n".join(reporte_lineas)
        await update.message.reply_text(mensaje_final, parse_mode="Markdown")

        # 5. Enviar planilla Excel actualizada
        if os.path.exists(output_excel):
            with open(output_excel, "rb") as doc_excel:
                await update.message.reply_document(
                    document=doc_excel,
                    filename=output_excel,
                    caption="📑 Planilla Marshall actualizada por Mari (formato y fórmulas preservados).",
                )

        # 6. Enviar certificado PDF oficial
        if os.path.exists(output_pdf):
            with open(output_pdf, "rb") as doc_pdf:
                await update.message.reply_document(
                    document=doc_pdf,
                    filename=output_pdf,
                    caption="📄 Certificado de ensayo de laboratorio vial (Normas DNV / IRAM).",
                )

    except json.JSONDecodeError:
        await update.message.reply_text(
            "⚠️ Mari no pudo estructurar los datos en formato numérico legible. Asegúrate de que los números de la libreta o display sean nítidos."
        )
    except Exception as exc:
        logger.error("Error al procesar foto con openpyxl y reportlab: %s", exc)
        await update.message.reply_text(f"⚠️ Error al procesar la fotografía y generar reportes: {exc}")


def run_bot() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()

    # Comandos
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("voces", voices_command))
    app.add_handler(CommandHandler("limpiar", reset_command))
    app.add_handler(CommandHandler("acceso", access_command))
    app.add_handler(CommandHandler("clave", clave_command))
    app.add_handler(CommandHandler("analizar_lote", handle_analizar_lote))
    app.add_handler(CommandHandler("limpiar_lote", handle_limpiar_lote))

    # Botones interactivos
    app.add_handler(CallbackQueryHandler(voice_callback))

    # Handlers Enrutados por Contexto
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print(">> Mari Bot en línea: Enrutamiento contextual inteligente y control de acceso activos...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
