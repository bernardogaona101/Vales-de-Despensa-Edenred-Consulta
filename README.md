# 🛒 Edenred Telegram Balance Bot

Bot automatizado para consultar el saldo de tarjetas de despensa Edenred directamente desde Telegram. Está diseñado utilizando **Playwright** para web scraping headless, un mini-servidor **Flask** para mantener compatibilidad con plataformas de hosting en la nube, y un sistema de persistencia de sesión para evitar inicios de sesión constantes.

---

## ⚡ Características Principales

- **Consulta On-Demand:** Responde con el saldo actual al recibir palabras clave como `saldo`.
- **Bypass de Autenticación:** Guarda y reutiliza el `storage_state` (cookies) en un JSON para saltarse la pantalla de login.
- **Auto-Recuperación:** Detecta si la sesión expiró e inicia sesión desde cero de forma automática y silenciosa.
- **Manejo de Bloqueos en la Nube:** Lógica integrada para esperar y cerrar banners de cookies (OneTrust) adaptándose a la latencia de servidores gratuitos.
- **Capturas de Diagnóstico Remoto:** Si el scraping falla, el bot toma una captura de pantalla del error y la envía al chat de Telegram para depuración visual.
- **Keep-Alive 24/7:** Integra un servidor web falso que engaña a Render para evitar que la plataforma mate el proceso.

---

## 🏗️ Arquitectura del Sistema

```text
[Usuario / Telegram]
        │
        ▼ (Mensaje: "saldo")
[Telegram Bot API]
        │  (Polling Asíncrono)
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Render Web Service (Contenedor Linux / Python 3.11.x)       │
│                                                             │
│  ┌───────────────────────┐       ┌───────────────────────┐  │
│  │   Hilo Secundario     │       │     Hilo Principal    │  │
│  │     (Dummy Flask)     │       │   (Telegram Polling)  │  │
│  │  Puerto: $PORT        │       │  python-telegram-bot  │  │
│  │  Salud: GET / -> 200  │       └───────────┬───────────┘  │
│  └───────────▲───────────┘                   │              │
│              │                               │ Invoca       │
│ (Ping cada 5 min)                            ▼              │
│        [UptimeRobot]             ┌───────────────────────┐  │
│                                  │   Módulo Scraping     │  │
│                                  │  (Playwright Chromium)│  │
│                                  └───────────┬───────────┘  │
└──────────────────────────────────────────────┼──────────────┘
                                               │
                                               ▼ (HTTPS)
                                    [Portal Web Edenred]