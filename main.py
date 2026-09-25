import os, time, threading, base64
from flask import Flask
import telebot
from groq import Groq

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

PROMPT = """A partir de este momento, activaremos el PROTOCOLO SUPER-EXPRESS:
### 1. RECEPCIÓN E INTERPRETACIONAL
- Te enviaré capturas de pantalla, archivos o textos cortos (muchas veces en inglés) acompañados de notas breves como "YA", "ESTA", "RÁPIDO", "MIRA ESTA".
- Cero preámbulos, saludos o rodeos teóricos. Analiza la imagen o texto de inmediato, detecta el problema y da la solución.
- Si el material está en inglés, analízalo pero responde SIEMPRE en español. Mantén los términos técnicos, sintaxis y comandos nativos intactos.

### 2. FORMATO OBLIGATORIO DE RESPUESTA
- SOLUCIÓN DIRECTA: La clave o respuesta exacta
- TRADUCCIÓN / CLAVE: Resumen en 1 frase si es en inglés
- POR QUÉ: 1 línea directa
- DÓNDE ESTÁ LA TRAMPA: Por qué fallan las otras
- MARCADOR: Conteo de sesión

### 3. REGLAS DE ORO
- Tono directo, entre patas, cero chisme académico.
- Si está mal planteada di "esta pregunta está mal planteada, marca la menos peor que es X".
- Si es código, da la línea exacta corregida.
- Si me equivoco, corrige en 1 frase.
"""

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
contador = {"n": 0}

@app.route('/')
def home(): return "Capitan ON"

@bot.message_handler(content_types=['photo'])
def foto(m):
    try:
        client = Groq(api_key=GROQ_KEY)
        f = bot.get_file(m.photo[-1].file_id)
        d = bot.download_file(f.file_path)
        b64 = base64.b64encode(d).decode()
        contador["n"] += 1
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role":"system","content": PROMPT + f" Marcador: {contador['n']}"},
                {"role":"user","content":[{"type":"text","text": m.caption or "YA"},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}
            ]
        )
        bot.reply_to(m, r.choices[0].message.content)
    except Exception as e:
        bot.reply_to(m, f"Error: {e}")

@bot.message_handler(func=lambda m: True)
def texto(m):
    try:
        client = Groq(api_key=GROQ_KEY)
        if "INICIAR" in m.text.upper():
            contador["n"] = 0
            bot.reply_to(m, "🫡 Capitán activado. Mándame la primera captura o ejercicio y le metemos mano.")
            return
        contador["n"] += 1
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"system","content": PROMPT + f" Marcador: {contador['n']}"},{"role":"user","content": m.text}])
        bot.reply_to(m, r.choices[0].message.content)
    except Exception as e:
        bot.reply_to(m, f"Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(2)
    bot.infinity_polling()
