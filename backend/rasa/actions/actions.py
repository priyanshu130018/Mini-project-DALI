# See this guide on how to implement these actions:
# https://rasa.com/docs/rasa/custom-actions

"""Custom Rasa actions for DALI Voice Assistant"""

import os
import datetime
import subprocess
import random
import threading
import webbrowser
import time
import logging
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import pyautogui
import pyttsx3
import psutil

logger = logging.getLogger(__name__)

# Thread-safe TTS with global engine
tts_lock = threading.Lock()
_tts_engine = None

def get_tts_engine():
    """Get or create global TTS engine"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = pyttsx3.init(driverName='sapi5')
    return _tts_engine

def speak(text):
    """Speak text safely and asynchronously"""
    def run():
        with tts_lock:
            try:
                engine = get_tts_engine()
                engine.setProperty('rate', 170)
                voices = engine.getProperty('voices')
                engine.setProperty('voice', voices[0].id)
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")
    
    threading.Thread(target=run, daemon=True).start()

# --- Custom Actions ---

class ActionTellFact(Action):
    def name(self) -> Text:
        return "action_tell_fact"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        facts = [
            "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs that's still edible.",
            "A day on Venus is longer than its year.",
            "Bananas are berries, but strawberries aren't.",
            "Octopuses have three hearts and blue blood.",
            "The Eiffel Tower can grow taller in summer due to thermal expansion."
        ]
        fact = random.choice(facts)
        dispatcher.utter_message(text=fact)
        speak(fact)
        return []

class ActionPlayMusic(Action):
    def name(self) -> Text:
        return "action_play_music"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        song = tracker.get_slot("song")
        
        if song:
            message = f"Playing {song}"
        else:
            message = "Playing music"
        
        dispatcher.utter_message(text=message)
        speak(message)
        
        # Open default music player or YouTube
        try:
            webbrowser.open("https://www.youtube.com/")
        except Exception as e:
            logger.error(f"Error opening music: {e}")
        
        return []

class ActionChangeMusic(Action):
    def name(self) -> Text:
        return "action_change_music"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            pyautogui.press('nexttrack')
            message = "Skipping to next track"
        except Exception as e:
            logger.error(f"Error changing music: {e}")
            message = "Could not change the track"
        
        dispatcher.utter_message(text=message)
        speak(message)
        return []

class ActionOpenApp(Action):
    def name(self) -> Text:
        return "action_open_app"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        app = tracker.get_slot("app")
        
        app_paths = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "chrome.exe",
            "browser": "chrome.exe",
            "excel": "excel.exe",
            "word": "winword.exe"
        }
        
        if app and app.lower() in app_paths:
            try:
                subprocess.Popen(app_paths[app.lower()])
                message = f"Opening {app}"
            except Exception as e:
                logger.error(f"Error opening {app}: {e}")
                message = f"Could not open {app}"
        else:
            message = "Please specify which app to open"
        
        dispatcher.utter_message(text=message)
        speak(message)
        return []

class ActionCloseApp(Action):
    def name(self) -> Text:
        return "action_close_app"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        app = tracker.get_slot("app")
        
        if app:
            try:
                for proc in psutil.process_iter(['name']):
                    if app.lower() in proc.info['name'].lower():
                        proc.terminate()
                        message = f"Closing {app}"
                        break
                else:
                    message = f"{app} is not running"
            except Exception as e:
                logger.error(f"Error closing {app}: {e}")
                message = f"Could not close {app}"
        else:
            message = "Please specify which app to close"
        
        dispatcher.utter_message(text=message)
        speak(message)
        return []

class ActionTellTime(Action):
    def name(self) -> Text:
        return "action_tell_time"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        message = f"The time is {time_str}"
        
        dispatcher.utter_message(text=message)
        speak(message)
        return []

class ActionTellDate(Action):
    def name(self) -> Text:
        return "action_tell_date"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        today = datetime.date.today()
        date_str = today.strftime("%B %d, %Y")
        message = f"Today is {date_str}"
        
        dispatcher.utter_message(text=message)
        speak(message)
        return []

class ActionShutdownPC(Action):
    def name(self) -> Text:
        return "action_shutdown_pc"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        message = "Shutting down in 60 seconds. Say cancel shutdown to abort."
        dispatcher.utter_message(text=message)
        speak(message)
        
        try:
            os.system("shutdown /s /t 60")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
        
        return []

class ActionRestartPC(Action):
    def name(self) -> Text:
        return "action_restart_pc"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        message = "Restarting in 60 seconds"
        dispatcher.utter_message(text=message)
        speak(message)
        
        try:
            os.system("shutdown /r /t 60")
        except Exception as e:
            logger.error(f"Restart error: {e}")
        
        return []
