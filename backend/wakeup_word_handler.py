import pvporcupine
import pyaudio
import struct
import threading
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

class WakeWordDetector:
    def __init__(self, config, on_wake_callback, loop=None):
        """
        Initialize wake word detector using config dictionary
        
        Args:
            config: Configuration dictionary from config.json
            on_wake_callback: Async callback function
            loop: asyncio event loop reference
        """
        # Get Porcupine settings from config
        access_key = config.get("picovoice_access_key")
        keyword_paths = config.get("picovoice_keyword_paths", [])
        sensitivity = config.get("wake_word_sensitivity", 0.8)
        timeout = config.get("command_timeout", 10)
        
        if not access_key:
            raise ValueError("picovoice_access_key not found in config")
        
        if not keyword_paths:
            raise ValueError("picovoice_keyword_paths not found in config")
        
        # Verify keyword files exist
        for path in keyword_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Keyword file not found: {path}")
        
        # Create Porcupine instance
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=keyword_paths,
            sensitivities=[sensitivity] * len(keyword_paths)
        )
        
        # Initialize PyAudio
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )
        
        self.on_wake_callback = on_wake_callback
        self.timeout_seconds = timeout
        self._listening = False
        self._timer = None
        self.loop = loop
        
        logger.info(f"Porcupine initialized:")
        logger.info(f"  - Keywords: {len(keyword_paths)}")
        logger.info(f"  - Sensitivity: {sensitivity}")
        logger.info(f"  - Sample rate: {self.porcupine.sample_rate} Hz")
        logger.info(f"  - Timeout: {timeout}s")

    def _safe_process(self, pcm):
        """Safely process audio frame"""
        try:
            return self.porcupine.process(pcm)
        except Exception as e:
            logger.warning(f"Wake word processing error: {e}")
            return -1

    def _reset_timer(self):
        """Reset the voice mode timeout timer"""
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self.timeout_seconds, self._timeout)
        self._timer.start()

    def _timeout(self):
        """Called when timeout is reached - disable voice mode"""
        logger.info("Voice mode timeout reached, disabling voice mode")
        if self.loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.on_wake_callback(enable=False), 
                    self.loop
                )
                future.result(timeout=2.0)
            except Exception as e:
                logger.error(f"Timeout callback error: {e}")

    def start(self):
        """Start wake word detection in background thread"""
        self._listening = True
        threading.Thread(target=self._detect_loop, daemon=True).start()

    def _detect_loop(self):
        """Main detection loop - runs in separate thread"""
        logger.info("Wake word detection started")
        self._reset_timer()
        
        while self._listening:
            try:
                pcm = self.stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                result = self._safe_process(pcm)
                
                # result >= 0 means wake word detected
                if result >= 0:
                    logger.info(f"Wake word detected! (keyword index: {result})")
                    self._reset_timer()
                    
                    if self.loop:
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                self.on_wake_callback(enable=True), 
                                self.loop
                            )
                            future.result(timeout=1.0)
                        except Exception as e:
                            logger.error(f"Wake callback error: {e}")
                            
            except Exception as e:
                logger.error(f"Mic stream error: {e}")
                import time
                time.sleep(0.1)

    def stop(self):
        """Stop wake word detection and cleanup resources"""
        self._listening = False
        if self._timer:
            self._timer.cancel()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pa:
            self.pa.terminate()
        if self.porcupine:
            self.porcupine.delete()
        
        logger.info("Wake word detector stopped")
