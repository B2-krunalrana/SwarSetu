import os

# Server Network Settings
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

# Audio Playback Config
DEFAULT_SAMPLE_RATE = 16000  # 16 kHz is standard for clean, low-bandwidth voice
DEFAULT_CHANNELS = 1         # Mono audio

# Debug Mode
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
