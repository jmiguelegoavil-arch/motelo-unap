import os
import time
import logging
from io import BytesIO
from threading import Thread

import telebot
from dotenv import load_dotenv
from flask import Flask
from google import genai
from google.genai import errors, types
from PIL import Image

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Modelo principal y respaldos (se pueden cambiar desde Render sin tocar el código)
MODELO_PRINCIPAL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MODELOS_RESPALDO = os.getenv("GEMINI_FALLBACKS", "gemini-2.5-flash,gemini-2.5-flash-lite").split(",")
MODELOS = [MODELO_PRINCIPAL] + [m.strip() for m in MODELOS_RESPALDO if m.strip()]

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ==========================================
# 1. SERVIDOR FLASK (para que Render no lo suspenda)
# ==========================================
app = Flask(__name__)

@app.route("/")
def home():
    return "¡Tutor de bots UNAP Iquitos activo y corriendo! 🚀"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web_server, daemon=True).start()
print(">> Servidor de mantenimiento Flask iniciado correctamente.")

# ==========================================
# 2. PROMPT DEL SISTEMA
# ==========================================
PROMPT_SISTEMA = """A partir de este momento, activaremos el PROTOCOLO SUPER-EXPRESS:

---
### 1. RECEPCIÓN E INTERPRETACIONAL
- Te enviaré capturas de pantalla, archivos o textos cortos (muchas veces en inglés) acompañados de notas breves como "YA", "ESTA", "RÁPIDO", "MIRA ESTA".
- Cero preámbulos, saludos o rodeos teóricos. Analiza la imagen o texto de inmediato, detecta el problema y da la solución.
- Si el material está en inglés, analízalo pero responde SIEMPRE en español. Mantén los términos técnicos, sintaxis y comandos nativos intactos (ej. Nmap flags, comandos de Linux, Python, Wireshark, SQL, Splunk, etc., no se traducen ni se alteran).

---
### 2. FORMATO OBLIGATORIO DE RESPUESTA
Cada respuesta tuya debe ser hiper-directa, escaneable a simple vista y seguir esta estructura exacta:

- SOLUCIÓN DIRECTA: La clave o respuesta exacta (ej. "Opción C ✅" o "Comando: nmap -sV -p- 192.168.1.1 ✅").
- TRADUCCIÓN / CLAVE (Si aplica): Si viene de un texto en inglés o largo, resúmeme la idea central en 1 frase.
- POR QUÉ: Explica la regla, concept u lógica aplicada en 1 sola línea directa.
- DÓNDE ESTÁ LA TRAMPA: Explica brevemente por qué fallan las otras opciones o cuál es el error común al ejecutar ese comando/fórmula.
- MARCADOR: Conteo de la sesión para medir mi avance (ej. "Marcador: 1-0 🔥").

---
### 3. REGLAS DE ORO
- Cero "chisme" o lenguaje académico acartonado. Habla con un tono directo, seguro y "entre patas".
- Si una pregunta está mal redactada, ambigua o "coja", no des rodeos: dime "esta pregunta está mal planteada, marca la menos peor que es X".
- Si requiero corregir código o un script, dame la línea exacta corregida sin dar clases teóricas largas.
- Si cometo un error, explícame la corrección en 1 sola frase para aprender sobre la marcha y pasar al siguiente ejercicio.

Procesa el archivo, texto o imagen aplicando estrictamente estas reglas de inmediato."""

# ==========================================
# 3. LLAMADA A GEMINI CON REINTENTOS Y RESPALDO
# ==========================================
CODIGOS_REINTENTABLES = (429, 500, 502, 503, 504)

def consultar_gemini(contenido, intentos_por_modelo=3):
    config = types.GenerateContentConfig(system_instruction=PROMPT_SISTEMA)

    for modelo in MODELOS:
        for intento in range(intentos_por_modelo):
            try:
                r = client.models.generate_content(
                    model=modelo,
                    contents=contenido,
                    config=config,
                )
                if r.text:
                    return r.text
                log.warning("Respuesta vacía de %s", modelo)
                break  # pasar al siguiente modelo
            except errors.APIError as e:
                log.warning("%s falló (intento %d): %s %s", modelo, intento + 1, e.code, e.message)
                if e.code in CODIGOS_REINTENTABLES:
                    time.sleep(2 ** intento)  # 1s, 2s, 4s
                    continue
                if e.code == 404:
                    break  # el modelo no existe, pasar al siguiente
                raise
    return None

# ==========================================
# 4. HANDLERS
# ==========================================
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(message, "🫡 Capitán activado. Mándame la primera captura o ejercicio y le metemos mano.")

@bot.message_handler(content_types=["text", "photo"])
def handle_message(message):
    chat_id = message.chat.id
    texto_usuario = message.caption or message.text or ""
    status_msg = bot.send_message(chat_id, "⚡ Analizando...")

    try:
        contenido = []
        if texto_usuario:
            contenido.append(f"Nota del usuario: {texto_usuario}")

        if message.content_type == "photo":
            file_info = bot.get_file(message.photo[-1].file_id)
            datos = bot.download_file(file_info.file_path)
            img = Image.open(BytesIO(datos))  # en memoria, sin archivos temporales
            img.load()
            contenido.append(img)

        if not contenido:
            contenido.append("Analiza y responde.")

        respuesta = consultar_gemini(contenido)

        if respuesta is None:
            respuesta = "⚠️ Gemini está saturado en este momento. Reenvíame la captura en unos segundos."

    except Exception as e:
        log.exception("Error inesperado")
        respuesta = "❌ Algo falló procesando eso. Reenvíamelo en unos segundos."

    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
        pass

    # Telegram limita a 4096 caracteres por mensaje
    for i in range(0, len(respuesta), 4000):
        bot.send_message(chat_id, respuesta[i:i + 4000])

if __name__ == "__main__":
    print(">> Bot escuchando peticiones de Telegram...")
    bot.infinity_polling(skip_pending=True)
