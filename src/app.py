import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright
import time
from dotenv import load_dotenv
import json
import threading
from flask import Flask

load_dotenv()

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "¡El bot está vivo y funcionando!"

def iniciar_servidor_web():
    # Render asigna un puerto automáticamente a través de la variable PORT
    puerto = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=puerto)



# --- TUS CREDENCIALES ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
CORREO = os.getenv("CORREO")
PASSWORD = os.getenv("PASSWORD")

async def obtener_saldo_edenred():
    saldo = "No se pudo obtener el saldo"
    archivo_sesion = "sesion_edenred.json"

    # Reconstruir la sesión en la nube
    sesion_texto = os.getenv("SESION_JSON")
    if sesion_texto and not os.path.exists("sesion_edenred.json"):
        with open("sesion_edenred.json", "w") as f:
            f.write(sesion_texto)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',               # Desactiva la seguridad que choca con Linux
                '--disable-dev-shm-usage',    # Evita que se sature la memoria RAM del servidor
                '--disable-gpu'               # Render no tiene tarjeta gráfica, esto lo acelera
            ]
        )
        
        # Validación clave: Revisamos si el archivo de sesión existe[cite: 2]
        if os.path.exists(archivo_sesion):
            context = await browser.new_context(storage_state=archivo_sesion)
        else:
            context = await browser.new_context()
            
        page = await context.new_page()
        
        try:
            await page.goto("https://www.edenredwallet.mx/Login")
            
            # 1. Lidiar con el anuncio de cookies de forma agresiva
            try:
                print("Buscando anuncio de cookies...")
                boton_cookies = page.locator('#onetrust-accept-btn-handler')
                
                # Esperamos hasta 5 segundos a que el botón sea realmente visible
                await boton_cookies.wait_for(state="visible", timeout=5000)
                
                print("Aceptando las cookies...")
                # force=True obliga a Playwright a hacer clic sin importar si hay animaciones
                await boton_cookies.click(force=True) 
                
                # Esperamos 2 segundos a que la animación de cierre termine y despegue la pantalla
                await page.wait_for_timeout(2000) 
            except Exception as e:
                # Si a los 5 segundos no salió nada, asumimos que no hay banner y continuamos
                print("No apareció el banner de cookies o ya estaba cerrado.")

            # 2. Iniciar sesión y lidiar con las cookies en la nube
            necesita_login = False
            
            # PASO A: Destruir el banner de cookies pacientemente
            try:
                print("Buscando el banner de cookies...")
                boton_cookies = page.locator('#onetrust-accept-btn-handler')
                # Le damos hasta 10 segundos para que el banner termine de salir
                await boton_cookies.wait_for(state="visible", timeout=10000)
                await boton_cookies.click(force=True)
                print("¡Banner de cookies cerrado!")
                # Pausa de 2 segundos para que la sombra de la animación desaparezca
                await page.wait_for_timeout(2000) 
            except:
                print("No apareció el banner de cookies o ya estaba aceptado.")

            # PASO B: Buscar las cajas de texto
            try:
                print("Esperando el formulario de login...")
                await page.wait_for_selector('input[type="email"]', state="visible", timeout=15000)
                necesita_login = True
            except:
                print("No apareció la caja de correo a tiempo. Asumiendo sesión activa.")

            # PASO C: Inyectar credenciales
            if necesita_login:
                print("Iniciando sesión forzada...")
                await page.fill('input[type="email"]', CORREO, force=True)
                await page.fill('input[type="password"]', PASSWORD, force=True)
                await page.click('button[type="submit"]', force=True)
                
                print("Esperando a que cargue el tablero principal...")
                await page.wait_for_timeout(10000)
                await context.storage_state(path=archivo_sesion)
                print("¡Sesión guardada exitosamente!")

            # se agrega una espera porque aveces no da tiempo de cargar por el servidor
            await page.wait_for_timeout(4000)

            # 3. Buscar el saldo
            await page.wait_for_selector('.card-balance', timeout=15000)
            elemento = await page.query_selector('.card-balance')
            
            if elemento:
                saldo = await elemento.inner_text()
                
        except Exception as e:
            print(f"Error en scraping: {e}")
            # Tomamos una foto de la pantalla para diagnosticar el problema
            await page.screenshot(path="error_nube.png")
            return "FOTO"
            
        finally:
            await browser.close()
            
    return saldo

async def responder_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id_actual = update.effective_chat.id
    mensaje = update.message.text.lower()

    if chat_id_actual == CHAT_ID:
        if "saldo" in mensaje:
            await update.message.reply_text("Consultando a Edenred, dame un momento...")

            saldo_actual = await obtener_saldo_edenred()
            if saldo_actual == "FOTO":
                await update.message.reply_text("Me atoré en esta pantalla. Esto es lo que estoy viendo:")
                # Enviamos la captura de pantalla al chat
                with open("error_nube.png", "rb") as foto:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=foto)
            elif saldo_actual:
                        await update.message.reply_text(f"💳 Hola, el saldo de la tarjeta de Bernardo es:\n* {saldo_actual} *")
            else:
                await update.message.reply_text("No se pudo obtener saldo")
        else:
            await update.message.reply_text("¡Hola! Escribe la palabra 'saldo' para consultar la tarjeta.")
    else:
        await update.message.reply_text("Lo siento, acceso denegado.")


if __name__ == "__main__":
    print("Iniciando servidor web para Render...")
    # Ejecutamos el servidor web en un hilo paralelo para que no bloquee al bot
    hilo_web = threading.Thread(target=iniciar_servidor_web)
    hilo_web.start()

    print("Bot encendido y escuchando mensajes...")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensaje))
    app.run_polling()
