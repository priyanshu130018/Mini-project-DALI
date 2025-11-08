"""Rasa chatbot integration"""

import requests
import logging

logger = logging.getLogger(__name__)

def get_rasa_reply(message, rasa_url, retries=2, timeout=5):
    """Get reply from Rasa chatbot with retry logic"""
    for attempt in range(retries):
        payload = {"sender": "voice_user", "message": message}
        
        try:
            response = requests.post(rasa_url, json=payload, timeout=timeout)
            
            if response.ok:
                data = response.json()
                if data:
                    replies = [d.get("text") for d in data if "text" in d]
                    if replies:
                        return " ".join(replies)
                
                logger.warning("Rasa returned empty response")
                return "I'm not sure how to respond to that."
            else:
                logger.error(f"Rasa error: HTTP {response.status_code}")
        
        except requests.exceptions.Timeout:
            logger.error(f"Rasa timeout (attempt {attempt + 1}/{retries})")
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Rasa (attempt {attempt + 1}/{retries})")
        except Exception as e:
            logger.error(f"Rasa error (attempt {attempt + 1}/{retries}): {e}")
        
        if attempt < retries - 1:
            continue
    
    return "Sorry, I couldn't reach the assistant right now. Please check if Rasa is running."
