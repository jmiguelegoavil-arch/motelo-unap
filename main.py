import os
import telebot
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurar Inteligencia Artificial (Google Gemini)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-pro')


# Inicializar Bot de Telegram
bot = telebot.TeleBot(BOT_TOKEN)

PROMPT_SISTEMA = """A partir de este momento, activaremos el PROTOCOLO SUPER-EXPRESS:

---
### 1. RECEPCIÓN E INTERPRETACIONAL
- Te enviaré capturas de pantalla, archivos o textos cortos (muchas veces en inglés) acompañados de notas breves como "YA", "ESTA", "RÁPIDO", "MIRA ESTA".
- Cero preámbulos, saludos o rodeos teóricos. Analiza la imagen o texto de inmediato, detecta el problema y da la solución.
- Si el material está en inglés, analízalo pero responde SIEMPRE en español. Mantén los términos técnicos, sintaxis y comandos nativos intactos (ej. Nmap flags, comandos de Linux, Python, Wireshark, SQL, Splunk, etc., no se traducen ni se alteran).

---
### 2. FORMATO OBLIGATORIO DE RESPUESTA
Cada respuesta tuya debe ser hiper-directa, escaneable a simple vista y seguir esta estructura exacta:

• SOLUCIÓN DIRECTA: La clave o respuesta exacta (ej. "Opción C ✅" o "Comando: nmap -sV -p- 192.168.1.1 ✅").
• TRADUCCIÓN / CLAVE (Si aplica): Si viene de un texto en inglés o largo, resúmeme la idea central en 1 frase.
• POR QUÉ: Explica la regla, concepto o lógica aplicada en 1 sola línea directa.
• DÓNDE ESTÁ LA TRAMPA: Explica brevemente por qué fallan las otras opciones o cuál es el error común al ejecutar ese comando/fórmula.
• MARCADOR: Conteo de la sesión para medir mi avance (ej. "Marcador: 1-0 🔥").

---
### 3. REGLAS DE ORO
- Cero "chisme" o lenguaje académico acartonado. Habla con un tono directo, seguro y "entre patas".
- Si una pregunta está mal redactada, ambigua o "coja", no des rodeos: dime "esta pregunta está mal planteada, marca la menos peor que es X".
- Si requiero corregir código o un script, dame la línea exacta corregida sin dar clases teóricas largas.
- Si cometo un error, explícame la corrección en 1 sola frase para aprender sobre la marcha y pasar al siguiente ejercicio.

Procesa el archivo, texto o imagen aplicando estrictamente estas reglas de inmediato."""

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🫡 Capitán activado. Mándame la primera captura o ejercicio y le metemos mano.")

@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    chat_id = message.chat.id
    texto_usuario = message.caption if message.caption else (message.text if message.text else "")
    
    # Mensaje temporal de procesamiento rápido para el simposio
    status_msg = bot.send_message(chat_id, "⚡ Analizando...")

    try:
        contenido_gemini = [PROMPT_SISTEMA]
        if texto_usuario:
            contenido_gemini.append(f"\nNota del usuario: {texto_usuario}")

        # Si el usuario mandó una captura/foto
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Guardar imagen temporalmente para pasársela a Gemini
            nombre_foto = f"temp_{chat_id}.jpg"
            with open(nombre_foto, 'wb') as new_file:
                new_file.write(downloaded_file)
                
            from PIL import Image
            img = Image.open(nombre_foto)
            contenido_gemini.append(img)

        # Llamar a la IA
        response = model.generate_content(contenido_gemini)
        respuesta_final = response.text

        # Borrar foto temporal si existe
        if message.content_type == 'photo' and os.path.exists(nombre_foto):
            os.remove(nombre_foto)

        # Enviar respuesta final y borrar el "Analizando..."
        bot.delete_message(chat_id, status_msg.message_id)
        bot.send_message(chat_id, respuesta_final)

    except Exception as e:
        bot.delete_message(chat_id, status_msg.message_id)
        bot.send_message(chat_id, f"❌ Hubo un error en el protocolo: {str(e)}")

# Arrancar el servidor
if __name__ == "__main__":
    from threading import Thread
    import http.server
    import socketserver

    # Crear un servidor web falso en segundo plano para que Render no apague la app
    def run_web_server():
        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Bot activo")
        port = int(os.getenv("PORT", 8080))
        with socketserver.TCPServer(("", port), Handler) as httpd:
            httpd.serve_forever()

    Thread(target=run_web_server, daemon=True).start()
    
    # Iniciar la escucha continua del bot de Telegram
    bot.infinity_polling()

