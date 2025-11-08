"""Main Offline Voice Assistant (Vosk wake word + Rasa + TTS)"""

import os
import json
import uuid
import pyaudio
import queue
import time
from datetime import datetime
from vosk import Model, KaldiRecognizer
import json as js
import re

from backend.speech_handler import speak_async, cleanup_audio
from backend.language_handler import load_models, detect_language, switch_language
from backend.database_handler import ConversationDB
from backend.rasa_handler import get_rasa_reply

def main():
    # Load configuration
    with open("backend/config.json", "r") as f:
        config = json.load(f)

    db_path = config.get('database', {}).get('path', 'conversations.db')
    db = ConversationDB(db_path)

    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    db.start_session(session_id)
    print(f"🆔 Session started: {session_id}")

    # Load Vosk models
    models = load_models(config['model_paths'])
    current_lang = "english"
    recognizer = KaldiRecognizer(models[current_lang], config['sample_rate'])

    mic = pyaudio.PyAudio()
    stream = mic.open(
        rate=16000,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=8000
    )
    stream.start_stream()

    print("🎤 DALI is ready. Say 'Hey Dali' or 'Hello Dali' to wake me up.")
    speak_async("Voice assistant Dali initialized and listening.", current_lang, config['tts_rate'])

    conversation_count = 0

    # --- Helper functions ---
    def detect_wake_word(text):
        """Detects 'hey dali' or 'hello dali' in the recognized text"""
        return re.search(r"\b(hey|hello)\s*dali\b", text.lower())

    def listen_for_command():
        """Listens for a command after wake word"""
        print("🎧 Listening for your command...")
        speak_async("I'm listening.", current_lang, config['tts_rate'])
        recog = KaldiRecognizer(models[current_lang], 16000)
        text = ""
        start_time = time.time()

        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if recog.AcceptWaveform(data):
                result = js.loads(recog.Result())
                text = result.get("text", "")
                if text:
                    break
            if time.time() - start_time > 8:  # timeout
                break
        return text.strip()

    # --- Main Loop ---
    try:
        partial_text = ""
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "")
                if detect_wake_word(text):
                    print("🎯 Wake word detected!")
                    command = listen_for_command()
                    if command:
                        print(f"🧑 You said: {command}")
                        conversation_count += 1

                        detected_lang = detect_language(command, current_lang)
                        if detected_lang != current_lang:
                            old_lang = current_lang
                            current_lang, recognizer = switch_language(
                                detected_lang, models, current_lang,
                                recognizer, config['sample_rate'], stream,
                                lambda txt, lang: speak_async(txt, lang, config['tts_rate'])
                            )
                            db.log_language_switch(session_id, old_lang, current_lang)

                        if command.lower() in ["exit", "quit", "stop", "bye"]:
                            speak_async("Goodbye!", current_lang, config['tts_rate'])
                            break

                        reply = get_rasa_reply(command, config['rasa_url'])
                        print(f"🤖 DALI: {reply}")
                        speak_async(reply, current_lang, config['tts_rate'])
                        db.add_conversation(
                            session_id=session_id,
                            language=current_lang,
                            user_text=command,
                            bot_reply=reply,
                        )
                    else:
                        speak_async("I didn’t catch that.", current_lang, config['tts_rate'])

    except KeyboardInterrupt:
        print("\n🛑 Stopping DALI...")

    finally:
        cleanup_audio(stream, mic)
        db.end_session(session_id)
        stats = db.get_statistics()
        print("\n📊 SESSION SUMMARY")
        print("=" * 60)
        print(f"Total conversations: {conversation_count}")
        print(f"Languages used: {', '.join(stats['conversations_by_language'].keys())}")
        print("=" * 60)
        print("✓ DALI session ended successfully.")


if __name__ == "__main__":
    main()
