import os
import logging
import psutil
import docker
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Cargar las variables del archivo .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID_AUTORIZADO = os.getenv("TELEGRAM_CHAT_ID")
DISK_PATH = os.getenv("DISK_PATH", "/")

# Validación rápida por si olvidaste configurar el .env
if not TOKEN or not CHAT_ID_AUTORIZADO:
    raise ValueError("Faltan configurar TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en el archivo .env")

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Inicializar cliente de Docker
client = docker.from_env()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de bienvenida"""
    await update.message.reply_text(
        "¡Hola! Soy tu bot de monitoreo. Usa /stats para ver el estado del servidor y los contenedores."
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obtiene y envía estadísticas del servidor y contenedores"""
    # Verificar si quien escribe es el administrador autorizado
    if str(update.effective_chat.id) != CHAT_ID_AUTORIZADO:
        await update.message.reply_text("No tienes autorización para usar este bot.")
        return

    # --- 1. Estadísticas del Servidor ---
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()

    try:
        disk = psutil.disk_usage(DISK_PATH)
        disk_text = (
            f"• **Disco:** {disk.percent}% "
            f"({round(disk.used / (1024**3), 2)} GB / {round(disk.total / (1024**3), 2)} GB)\n"
        )
    except OSError:
        disk_text = f"• **Disco:** no disponible en `{DISK_PATH}`\n"

    server_text = (
        f"🖥 **ESTADO DEL SERVIDOR**\n"
        f"• **CPU:** {cpu_usage}%\n"
        f"• **RAM:** {memory.percent}% ({round(memory.used / (1024**3), 2)} GB / {round(memory.total / (1024**3), 2)} GB)\n"
        f"{disk_text}\n"
    )

    # --- 2. Estadísticas de Contenedores Docker ---
    containers_text = "🐳 **CONTENEDORES DOCKER**\n"
    try:
        containers = client.containers.list(all=True)
        if not containers:
            containers_text += "No hay contenedores encontrados.\n"
        else:
            for c in containers:
                status_emoji = "🟢" if c.status == "running" else "🔴"
                containers_text += f"{status_emoji} `{c.name}` — *{c.status}*\n"
    except Exception as e:
        containers_text += f"Error al conectar con Docker: {str(e)}\n"

    # Combinar mensajes y enviar
    mensaje_final = server_text + containers_text
    await update.message.reply_text(mensaje_final, parse_mode="Markdown")

def main():
    """Función principal para correr el bot"""
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))

    print("Bot corriendo... Presiona Ctrl+C para detener.")
    app.run_polling()

if __name__ == '__main__':
    main()
