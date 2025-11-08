import asyncio
import websockets
import json
import os
from datetime import datetime
import uuid
import logging
import requests

from wake_word_handler import WakeWordDetector  # Your wake word detection module
from language_handler import load_models, detect_language
from database_handler import ConversationDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

db = ConversationDB(config['database']['path'])

try:
    models = load_models(config['model_paths'])
    logger.info("Vosk models loaded")
except Exception as e:
    logger.warning(f"Vosk models not loaded: {e}")
    models = {}

clients = {}  # client_id -> { websocket, session_id, ... }
voice_mode = False  # Global voice mode state

# Functions to notify connected clients about voice mode state changes
async def notify_voice_mode(enabled: bool):
    global voice_mode
    voice_mode = enabled
    message = json.dumps({"event": "voice_mode", "enabled": voice_mode})
    if clients:
        await asyncio.wait([client["websocket"].send(message) for client in clients.values()])

# Callback when wake word is detected
async def on_wake_word_detected(enable: bool):
    global voice_mode
    voice_mode = enable
    message = json.dumps({"event": "voice_mode", "enabled": voice_mode})
    if clients:
        await asyncio.wait([client["websocket"].send(message) for client in clients.values()])
    logger.info(f"Voice mode {'enabled' if enable else 'disabled'} notified to clients")


# Initialize and start wake word detector
def start_wake_word_detector():
    access_key = config.get("picovoice_access_key")  # Get from config.json
    keyword_paths = [
        'path/to/hey_dali.ppn',
        'path/to/oy_hello_dali.ppn',
        'path/to/oiii_dali.ppn'
    ]
    sensitivities = [0.7] * len(keyword_paths)
    detector = WakeWordDetector(keyword_paths, sensitivities, on_wake_word_detected, access_key)
    detector.start()
    return detector


ww_detector = start_wake_word_detector()


def get_rasa_reply(message, rasa_url, timeout=5):
    try:
        payload = {"sender": "web_user", "message": message}
        response = requests.post(rasa_url, json=payload, timeout=timeout)
        if response.ok:
            data = response.json()
            if data and len(data) > 0:
                replies = [d.get("text") for d in data if "text" in d]
                if replies:
                    return " ".join(replies)
        logger.warning("Rasa returned empty response")
        return "I'm not sure how to respond to that."
    except requests.exceptions.Timeout:
        logger.error("Rasa request timeout")
        return "Sorry, I'm taking too long to respond."
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Rasa server")
        return "Sorry, I couldn't reach the assistant. Please check if Rasa is running."
    except Exception as e:
        logger.error(f"Rasa error: {e}")
        return "An error occurred while processing your request."

async def handle_client(websocket, path):
    client_id = str(uuid.uuid4())
    session_id = f"web_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{client_id[:8]}"
    clients[client_id] = {
        "websocket": websocket,
        "session_id": session_id,
        "language": "english",
        "connected_at": datetime.now(),
        "tts_enabled": True
    }
    db.start_session(session_id)
    logger.info(f"Client {client_id[:8]} connected")

    try:
        await websocket.send(json.dumps({
            "type": "system",
            "message": "Connected to DALI Voice Assistant",
            "session_id": session_id
        }))

        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            # Only process voice input if voice_mode is enabled, else accept typed input
            if msg_type == "text":
                user_message = data.get("message", "").strip()
                if not user_message:
                    continue

                logger.info(f"[{client_id[:8]}] User: {user_message}")

                current_lang = clients[client_id]["language"]
                detected_lang = detect_language(user_message, current_lang)
                if detected_lang != current_lang:
                    clients[client_id]["language"] = detected_lang
                    db.log_language_switch(session_id, current_lang, detected_lang)
                    logger.info(f"Language switched: {current_lang} -> {detected_lang}")

                bot_reply = get_rasa_reply(user_message, config['rasa_url'])
                logger.info(f"[{client_id[:8]}] Bot: {bot_reply}")

                db.add_conversation(
                    session_id=session_id,
                    user_input=user_message,
                    bot_response=bot_reply,
                    language=detected_lang,
                    confidence_score=1.0
                )

                await websocket.send(json.dumps({
                    "type": "response",
                    "message": bot_reply,
                    "language": detected_lang,
                    "speak": clients[client_id]["tts_enabled"],
                    "timestamp": datetime.now().isoformat()
                }))
            elif msg_type == "toggle_tts":
                clients[client_id]["tts_enabled"] = data.get("enabled", True)
                logger.info(f"TTS {'enabled' if clients[client_id]['tts_enabled'] else 'disabled'}")
            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {client_id[:8]} disconnected")
    finally:
        db.end_session(session_id)
        if client_id in clients:
            del clients[client_id]

async def main():
    host = "localhost"
    port = 8765
    logger.info(f"DALI WebSocket Server running on ws://{host}:{port}")
    async with websockets.serve(handle_client, host, port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")
