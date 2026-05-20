import argparse
import json
import os
import random
import sys
import urllib.parse
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCHEDULED_MESSAGES_PATH = BASE_DIR / "config" / "scheduled_messages.json"
REPLIES_PATH = BASE_DIR / "config" / "replies.json"
STATE_PATH = BASE_DIR / "state" / "telegram_offset.json"


class BotConfigError(RuntimeError):
    pass


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise BotConfigError(f"Falta configurar la variable de entorno: {name}")
    return value


def telegram_request(method, payload):
    token = get_required_env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")

    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")

    result = json.loads(body)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram respondio con error: {result}")
    return result


def load_state():
    if not STATE_PATH.exists():
        return {"offset": None}
    return load_json(STATE_PATH)


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)
        file.write("\n")


def send_message(chat_id, text, reply_to_message_id=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }

    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id

    return telegram_request("sendMessage", payload)


def delete_webhook():
    return telegram_request("deleteWebhook", {"drop_pending_updates": "false"})


def send_scheduled_message(message_id):
    config = load_json(SCHEDULED_MESSAGES_PATH)
    messages = config.get("messages", [])
    match = next((item for item in messages if item.get("id") == message_id), None)

    if not match:
        available = ", ".join(item.get("id", "<sin id>") for item in messages)
        raise BotConfigError(
            f"No existe el mensaje programado '{message_id}'. Disponibles: {available}"
        )

    chat_id = match.get("chat_id") or os.getenv("TELEGRAM_DEFAULT_CHAT_ID")
    if not chat_id:
        raise BotConfigError(
            "El mensaje no tiene chat_id y falta TELEGRAM_DEFAULT_CHAT_ID."
        )

    text = match.get("text", "").strip()
    if not text:
        raise BotConfigError(f"El mensaje '{message_id}' no tiene texto.")

    send_message(chat_id, text)
    print(f"Mensaje programado enviado: {message_id}")


def normalize_text(text):
    return " ".join(text.lower().strip().split())


def build_reply(input_text):
    config = load_json(REPLIES_PATH)
    normalized_input = normalize_text(input_text)

    invocation_prefixes = [
        normalize_text(prefix) for prefix in config.get("invocation_prefixes", [])
    ]

    is_invoked = any(
        normalized_input.startswith(prefix) for prefix in invocation_prefixes
    )

    if not is_invoked:
        return None

    rules = config.get("rules", [])
    for rule in rules:
        triggers = [normalize_text(trigger) for trigger in rule.get("triggers", [])]
        if any(trigger in normalized_input for trigger in triggers):
            responses = rule.get("responses", [])
            if responses:
                return random.choice(responses)

    fallback_responses = config.get("fallback_responses", [])
    if fallback_responses:
        return random.choice(fallback_responses)

    return "Fui invocado, pero nadie configuro que debo decir. Dramatico."


def poll_updates():
    delete_webhook()

    state = load_state()
    payload = {
        "timeout": 0,
        "limit": 100,
        "allowed_updates": json.dumps(["message"]),
    }

    if state.get("offset") is not None:
        payload["offset"] = state["offset"]

    result = telegram_request("getUpdates", payload)
    updates = result.get("result", [])

    if not updates:
        print("No hay mensajes nuevos.")
        return

    next_offset = state.get("offset")
    replies_sent = 0

    for update in updates:
        update_id = update.get("update_id")
        if update_id is not None:
            next_offset = max(next_offset or 0, update_id + 1)

        message = update.get("message") or {}
        sender = message.get("from") or {}
        if sender.get("is_bot"):
            continue

        text = message.get("text")
        message_id = message.get("message_id")
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        if not text or chat_id is None:
            continue

        reply = build_reply(text)
        if not reply:
            continue

        send_message(chat_id, reply, reply_to_message_id=message_id)
        replies_sent += 1

    if next_offset is not None:
        save_state({"offset": next_offset})

    print(f"Mensajes revisados: {len(updates)}. Respuestas enviadas: {replies_sent}.")


def invoke(text, chat_id):
    reply = build_reply(text)
    if not reply:
        print("El texto no invoca al bot. No se envio respuesta.")
        return

    if chat_id:
        send_message(chat_id, reply)
        print("Respuesta enviada.")
    else:
        print(reply)


def parse_args():
    parser = argparse.ArgumentParser(description="Bot simple de Telegram.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scheduled_parser = subparsers.add_parser(
        "send-scheduled", help="Envia un mensaje programado por id."
    )
    scheduled_parser.add_argument("--message-id", required=True)

    invoke_parser = subparsers.add_parser(
        "invoke", help="Genera o envia una respuesta segun texto de entrada."
    )
    invoke_parser.add_argument("--text", required=True)
    invoke_parser.add_argument(
        "--chat-id",
        default=os.getenv("TELEGRAM_DEFAULT_CHAT_ID"),
        help="Chat destino. Si se omite, imprime la respuesta en consola.",
    )

    subparsers.add_parser(
        "poll-updates", help="Revisa mensajes pendientes y responde invocaciones."
    )

    return parser.parse_args()


def main():
    args = parse_args()

    try:
        if args.command == "send-scheduled":
            send_scheduled_message(args.message_id)
        elif args.command == "invoke":
            invoke(args.text, args.chat_id)
        elif args.command == "poll-updates":
            poll_updates()
    except BotConfigError as error:
        print(f"Error de configuracion: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"Error inesperado: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
