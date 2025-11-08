import os
from vosk import Model, KaldiRecognizer
import logging

try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logging.warning("langdetect not installed. Using script-based detection only.")

logger = logging.getLogger(__name__)

def load_models(model_paths):
    """Load all Vosk models"""
    models = {}
    for lang, path in model_paths.items():
        if not path or not os.path.exists(path):
            logger.warning(f"Model not found: {path}")
            continue
        try:
            models[lang] = Model(path)
            logger.info(f"Loaded {lang} model from {path}")
        except Exception as e:
            logger.error(f"Failed to load {lang} model: {e}")
    return models

def detect_language(text, current_lang="english"):
    """
    Detect language from text
    """
    if not text or len(text.strip()) < 3:
        logger.debug(f"Text too short, keeping {current_lang}")
        return current_lang

    # Check for Devanagari Unicode range for Hindi
    hindi_chars = 0
    total_alpha = 0

    for char in text:
        if char.isalpha():
            total_alpha += 1
            if '\u0900' <= char <= '\u097F':
                hindi_chars += 1

    if total_alpha > 0 and (hindi_chars / total_alpha) > 0.2:
        logger.info(f"✅ Detected Hindi by script ({hindi_chars}/{total_alpha}): {text[:50]}")
        return 'hindi'

    if LANGDETECT_AVAILABLE:
        try:
            detected = detect(text)
            if detected == 'hi':
                logger.info(f"✅ Detected Hindi by langdetect: {text[:50]}")
                return 'hindi'
            elif detected in ['en', 'en-us', 'en-gb']:
                logger.info(f"✅ Detected English by langdetect: {text[:50]}")
                return 'english'
            else:
                logger.debug(f"Langdetect returned '{detected}', using {current_lang}")
        except Exception as e:
            logger.debug(f"Langdetect failed: {e}")

    hindi_keywords = ['namaste', 'dhanyavaad', 'kaise', 'kya', 'hai', 'hain',
                     'aap', 'tum', 'main', 'hum', 'kahan', 'kab']

    text_lower = text.lower()
    for keyword in hindi_keywords:
        if keyword in text_lower:
            logger.info(f"✅ Detected Hindi by keyword '{keyword}': {text[:50]}")
            return 'hindi'

    logger.info(f"✅ Keeping {current_lang}: {text[:50]}")
    return current_lang

def switch_language(new_lang, models, current_lang, recognizer, sample_rate, stream, speak_func):
    """
    Switch the ASR recognizer to a new language model.
    """
    if new_lang == current_lang:
        return current_lang, recognizer

    try:
        stream.stop_stream()
        stream.close()
    except Exception:
        pass

    new_stream = stream._parent.open(
        rate=sample_rate,
        channels=1,
        format=stream._format,
        input=True,
        frames_per_buffer=8000
    )
    new_stream.start_stream()

    from vosk import KaldiRecognizer
    new_recognizer = KaldiRecognizer(models[new_lang], sample_rate)

    speak_func(f"Language switched to {new_lang}", new_lang)

    return new_lang, new_recognizer
