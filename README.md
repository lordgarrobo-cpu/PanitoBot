# Telegram Fun Bot

Bot de Telegram simple para mensajes programados y respuestas por invocacion, pensado para correr sin hosting externo usando GitHub Actions.

## Que hace esta primera version

- Envia mensajes programados configurados en `config/scheduled_messages.json`.
- Responde a frases cuando alguien lo invoca con `/bot`, `bot` u `oye bot`.
- Puede revisar mensajes pendientes con `poll-updates`, sin hosting externo.
- Usa solo Python estandar, sin instalar dependencias.
- Lee el token de Telegram desde variables de entorno, no desde el codigo.

## Variables necesarias

- `TELEGRAM_BOT_TOKEN`: token del bot entregado por BotFather.
- `TELEGRAM_DEFAULT_CHAT_ID`: chat o grupo donde se enviaran los mensajes programados.

## Uso local

```powershell
$env:TELEGRAM_BOT_TOKEN="123456:ABC..."
$env:TELEGRAM_DEFAULT_CHAT_ID="-1001234567890"
python bot.py send-scheduled --message-id saludo_lunes
python bot.py invoke --text "/bot hola"
python bot.py poll-updates
```

## Uso en GitHub

1. Sube este proyecto a un repositorio.
2. En GitHub, entra a `Settings > Secrets and variables > Actions`.
3. Agrega estos secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_DEFAULT_CHAT_ID`
4. Entra a la pestaña `Actions`.
5. Puedes ejecutar manualmente `Telegram bot` para probar invocaciones.
6. Los mensajes programados se ejecutan con el horario definido en `.github/workflows/telegram-bot.yml`.
7. El polling revisa el chat cada 30 minutos. Puedes ajustar ese intervalo en el cron `*/30 * * * *`.

## Nota importante

Sin hosting externo, el bot no puede escuchar mensajes en tiempo real todo el dia. Esta version usa GitHub Actions para simular esa escucha revisando mensajes pendientes cada cierto tiempo.

- mandar mensajes en horarios definidos;
- simular invocaciones mediante ejecucion manual;
- consultar mensajes pendientes con polling.

Si quieres respuestas casi inmediatas, baja el intervalo del polling. Si quieres ahorrar minutos de GitHub Actions, subelo.
