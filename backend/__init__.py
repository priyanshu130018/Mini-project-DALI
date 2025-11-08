"""DALI Voice Assistant - Backend Module"""
from .speech_handler import speak_async, cleanup_audio
from .language_handler import load_models, detect_language, switch_language
from .database_handler import ConversationDB
from .rasa_handler import get_rasa_reply

__version__ = "1.0.0"
