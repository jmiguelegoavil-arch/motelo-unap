import os
import google.generativeai as genai
from telegram.ext import Application, MessageHandler, filters

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
TOKEN = os.environ.get("BOT_TOKEN")

async def estudiar(update, context):
    r = model.generate_content(f"Eres tutor UNAP, enseña paso a paso: {update.message.text}")
    await update.message.reply_text(r.text[:4000])

app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, estudiar))
app.run_polling()
