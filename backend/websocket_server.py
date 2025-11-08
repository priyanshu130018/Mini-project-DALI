"""WebSocket server for DALI Voice Assistant with TTS Support"""

import asyncio
import websockets
import json
import os
from datetime import datetime
import uuid
import requests
import logging

from language_handler import load_models, detect_language
from database_handler import ConversationDB
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

# Initialize
db = ConversationDB(config['database']['path'])

# Load models (optional)
try:
    models = load_models(config['model_paths'])
    logger.info("Vosk models loaded")
except Exception as e:
    logger.warning(f"Vosk models not loaded: {e}")
    models = {}

# Connected clients
clients = {}


def get_rasa_reply(message, rasa_url, timeout=5):
    """Get reply from Rasa with error handling"""
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
    """Handle WebSocket client connection"""
    client_id = str(uuid.uuid4())
    session_id = f"web_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{client_id[:8]}"
    
    clients[client_id] = {
        "websocket": websocket,
        "session_id": session_id,
        "language": "english",
        "connected_at": datetime.now(),
        "tts_enabled": True  # TTS enabled by default
    }
    
    db.start_session(session_id)
    logger.info(f"✅ Client {client_id[:8]} connected")
    
    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "system",
            "message": "Connected to DALI Voice Assistant",
            "session_id": session_id
        }))
        
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "text":
                    user_message = data.get("message", "").strip()
                    
                    if not user_message:
                        continue
                    
                    logger.info(f"[{client_id[:8]}] User: {user_message}")
                    
                    # Detect language
                    current_lang = clients[client_id]["language"]
                    detected_lang = detect_language(user_message, current_lang)
                    
                    if detected_lang != current_lang:
                        clients[client_id]["language"] = detected_lang
                        db.log_language_switch(session_id, current_lang, detected_lang)
                        logger.info(f"Language: {current_lang} -> {detected_lang}")
                    
                    # Get Rasa response
                    bot_reply = get_rasa_reply(user_message, config['rasa_url'])
                    logger.info(f"[{client_id[:8]}] Bot: {bot_reply}")
                    
                    # Save to database
                    db.add_conversation(
                        session_id=session_id,
                        user_input=user_message,
                        bot_response=bot_reply,
                        language=detected_lang,
                        confidence_score=1.0
                    )
                    
                    # Send response with TTS flag
                    await websocket.send(json.dumps({
                        "type": "response",
                        "message": bot_reply,
                        "language": detected_lang,
                        "speak": clients[client_id]["tts_enabled"],  # Tell browser to speak
                        "timestamp": datetime.now().isoformat()
                    }))
                
                elif msg_type == "toggle_tts":
                    # Toggle TTS on/off
                    clients[client_id]["tts_enabled"] = data.get("enabled", True)
                    logger.info(f"TTS {'enabled' if clients[client_id]['tts_enabled'] else 'disabled'}")
                
                elif msg_type == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {client_id[:8]}")
            except Exception as e:
                logger.error(f"Error: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"👋 Client {client_id[:8]} disconnected")
    finally:
        db.end_session(session_id)
        if client_id in clients:
            del clients[client_id]


async def main():
    """Start WebSocket server"""
    host = "localhost"
    port = 8765
    
    logger.info("=" * 60)
    logger.info(f"🚀 DALI WebSocket Server: ws://{host}:{port}")
    logger.info("=" * 60)
    
    async with websockets.serve(handle_client, host, port):
        logger.info("✅ Server running with TTS support")
        logger.info("✅ Waiting for connections...")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped")
