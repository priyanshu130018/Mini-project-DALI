"""Language detection and model switching"""

import os
from vosk import Model, KaldiRecognizer
import logging

# Try to import langdetect, but make it optional
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
    
    Supports English and Hindi detection using:
    1. langdetect library (if installed)
    2. Devanagari script detection (Unicode range)
    3. Common Hindi words
    
    Args:
        text: Input text
        current_lang: Current language (fallback)
    
    Returns:
        str: 'english' or 'hindi'
    """
    if not text or len(text.strip()) < 3:
        logger.debug(f"Text too short, keeping {current_lang}")
        return current_lang
    
    # Method 1: Check for Devanagari script (Unicode U+0900 to U+097F)
    # This is the most reliable for Hindi
    hindi_chars = 0
    total_alpha = 0
    
    for char in text:
        if char.isalpha():
            total_alpha += 1
            # Devanagari Unicode range
            if '\u0900' <= char <= '\u097F':
                hindi_chars += 1
    
    # If more than 20% Hindi characters, it's Hindi
    if total_alpha > 0 and (hindi_chars / total_alpha) > 0.2:
        logger.info(f"✅ Detected Hindi by script ({hindi_chars}/{total_alpha}): {text[:50]}")
        return 'hindi'
    
    # Method 2: Use langdetect if available
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
    
    # Method 3: Check for common Hindi words (romanized or not)
    hindi_keywords = ['namaste', 'dhanyavaad', 'kaise', 'kya', 'hai', 'hain', 
                      'aap', 'tum', 'main', 'hum', 'kahan', 'kab']
    
    text_lower = text.lower()
    for keyword in hindi_keywords:
        if keyword in text_lower:
            logger.info(f"✅ Detected Hindi by keyword '{keyword}': {text[:50]}")
            return 'hindi'
    
    # Default: Keep current language
    logger.info(f"✅ Keeping {current_lang}: {text[:50]}")
    return current_lang
