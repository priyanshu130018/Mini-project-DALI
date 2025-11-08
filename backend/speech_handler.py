"""Speech and TTS handler for DALI Voice Assistant (Offline Vosk + pyttsx3)"""

import pyttsx3
import threading

tts_lock = threading.Lock()

def speak_async(text, lang="english", rate=170):
    """Speak asynchronously with pyttsx3."""
    def run():
        with tts_lock:
            try:
                tts = pyttsx3.init(driverName='sapi5')
                tts.setProperty("rate", rate)
                voices = tts.getProperty('voices')
                if lang == "hindi" and len(voices) > 1:
                    tts.setProperty("voice", voices[1].id)
                else:
                    tts.setProperty("voice", voices[0].id)
                tts.say(text)
                tts.runAndWait()
            except Exception as e:
                print(f"TTS error: {e}")
    threading.Thread(target=run, daemon=True).start()


def cleanup_audio(stream, mic):
    """Safely close the audio stream."""
    try:
        stream.stop_stream()
        stream.close()
        mic.terminate()
    except Exception as e:
        print(f"Audio cleanup error: {e}")
