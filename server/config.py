"""
Configuration settings for SwarSetu Server
"""

import os
from typing import Dict, Any

# Server Configuration
HOST: str = "0.0.0.0"  # Listen on all available network interfaces
PORT: int = int(os.getenv("SWARSETU_PORT", "8000"))  # Default port 8000

# Audio Configuration
AUDIO_SAMPLE_RATE: int = 16000  # 16 kHz sampling rate (standard for voice)
AUDIO_CHUNK_SIZE: int = 1024  # Bytes per chunk
AUDIO_CHANNELS: int = 1  # Mono audio (1 channel)
AUDIO_BYTES_PER_SAMPLE: int = 2  # 16-bit audio (2 bytes per sample)

# WebSocket Configuration
MAX_CONNECTIONS: int = 50  # Maximum concurrent connections
HEARTBEAT_INTERVAL: int = 30  # Seconds between heartbeat messages

# Logging Configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
DEBUG_MODE: bool = os.getenv("DEBUG", "false").lower() == "true"

# CORS Configuration (for cross-origin requests)
CORS_ORIGINS: list = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
]

# Additional CORS origins from environment variable (comma-separated IPs)
additional_origins = os.getenv("CORS_ORIGINS", "")
if additional_origins:
    CORS_ORIGINS.extend(additional_origins.split(","))

# Allow all local network IPs
CORS_ORIGINS.append("*")  # In production, specify exact IPs

# Application metadata
APP_TITLE: str = "SwarSetu - Local Audio Announcement System"
APP_DESCRIPTION: str = "Real-time audio streaming over local network using WebSockets"
APP_VERSION: str = "1.0.0"

# Configuration dictionary for easy access
CONFIG: Dict[str, Any] = {
    "host": HOST,
    "port": PORT,
    "audio_sample_rate": AUDIO_SAMPLE_RATE,
    "audio_chunk_size": AUDIO_CHUNK_SIZE,
    "audio_channels": AUDIO_CHANNELS,
    "audio_bytes_per_sample": AUDIO_BYTES_PER_SAMPLE,
    "max_connections": MAX_CONNECTIONS,
    "debug": DEBUG_MODE,
}
