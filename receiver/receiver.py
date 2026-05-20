#!/usr/bin/env python3
"""
SwarSetu Python Receiver Client
Connects to the FastAPI server, receives audio chunks, and plays them through speakers

Usage:
    python receiver.py [--host 192.168.1.100] [--port 8000]

Features:
    - Auto-reconnect if connection drops
    - Real-time audio playback through speakers
    - Connection status logging
    - Low latency audio streaming
"""

import asyncio
import logging
import argparse
from datetime import datetime
from typing import Optional
import sys

import websockets
import numpy as np
import sounddevice as sd

# ============================================================================
# CONFIGURATION
# ============================================================================

# Audio playback settings
SAMPLE_RATE: int = 16000  # 16 kHz (standard for voice)
CHANNELS: int = 1  # Mono audio
BUFFER_SIZE: int = 4096  # Audio buffer size

# Connection settings
RECONNECT_ATTEMPTS: int = 5
RECONNECT_DELAY: int = 2  # seconds
CONNECTION_TIMEOUT: int = 5  # seconds

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# AUDIO PLAYBACK
# ============================================================================

class AudioPlayer:
    """
    Handles audio playback through system speakers using sounddevice
    """
    
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        """
        Initialize audio player
        
        Args:
            sample_rate: Sample rate in Hz (default: 16000)
        """
        self.sample_rate = sample_rate
        self.stream = None
        self.is_initialized = False
        
        # Try to initialize the audio stream
        self._initialize_stream()
    
    def _initialize_stream(self):
        """
        Initialize the audio output stream
        """
        try:
            # Create output stream for speaker playback
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                blocksize=BUFFER_SIZE,
                latency='low',  # Minimize latency
            )
            self.stream.start()
            self.is_initialized = True
            logger.info("✓ Audio player initialized")
            logger.info(f"  Sample rate: {self.sample_rate} Hz")
            logger.info(f"  Channels: {CHANNELS}")
            logger.info(f"  Buffer size: {BUFFER_SIZE}")
            
        except Exception as e:
            logger.error(f"✗ Failed to initialize audio player: {e}")
            self.is_initialized = False
    
    def play_audio(self, audio_data: bytes) -> bool:
        """
        Play audio data through speakers
        
        Args:
            audio_data: Raw audio bytes (WebM format)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized or self.stream is None:
            logger.warning("Audio player not initialized")
            return False
        
        try:
            # For WebM audio, we need to decode it
            # For now, we'll handle raw PCM data
            # In production, use a proper audio decoder library
            
            # Convert bytes to numpy array (16-bit signed PCM)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize to [-1, 1] range for sounddevice
            audio_normalized = audio_array.astype(np.float32) / 32768.0
            
            # Write to output stream
            self.stream.write(audio_normalized)
            
            logger.debug(f"Played {len(audio_data)} bytes of audio")
            return True
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            return False
    
    def close(self):
        """
        Close the audio stream
        """
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
                logger.info("Audio stream closed")
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")
            finally:
                self.stream = None
                self.is_initialized = False

# ============================================================================
# WEBSOCKET RECEIVER CLIENT
# ============================================================================

class SwarSetuReceiver:
    """
    WebSocket client that receives audio from SwarSetu server and plays it
    
    Connection flow:
    1. Connect to WebSocket /ws/receiver endpoint
    2. Receive audio chunks as binary data
    3. Play audio through speakers
    4. Reconnect if connection drops
    """
    
    def __init__(self, host: str, port: int):
        """
        Initialize the receiver client
        
        Args:
            host: Server hostname or IP address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.ws_uri = f"ws://{host}:{port}/ws/receiver"
        
        self.ws_connection = None
        self.audio_player = AudioPlayer(SAMPLE_RATE)
        
        self.is_connected = False
        self.reconnect_attempts = 0
        
        # Statistics
        self.chunks_received = 0
        self.bytes_received = 0
        self.start_time = None
    
    async def connect(self) -> bool:
        """
        Connect to the WebSocket server
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.ws_uri}...")
            
            # Connect with timeout
            self.ws_connection = await asyncio.wait_for(
                websockets.connect(self.ws_uri),
                timeout=CONNECTION_TIMEOUT
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0  # Reset reconnect counter
            
            logger.info("✓ Connected to server")
            logger.info(f"  Host: {self.host}")
            logger.info(f"  Port: {self.port}")
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout after {CONNECTION_TIMEOUT}s")
            return False
        except Exception as e:
            logger.error(f"✗ Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """
        Disconnect from the WebSocket server
        """
        if self.ws_connection:
            try:
                await self.ws_connection.close()
                logger.info("Disconnected from server")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self.ws_connection = None
                self.is_connected = False
    
    async def receive_audio(self):
        """
        Listen for incoming audio chunks from the server
        
        This is the main loop that:
        1. Waits for incoming messages
        2. Handles binary audio data
        3. Plays audio through speakers
        """
        if not self.is_connected or not self.ws_connection:
            logger.error("Not connected to server")
            return
        
        try:
            logger.info("🎧 Listening for audio...")
            
            async for message in self.ws_connection:
                # Check message type
                if isinstance(message, bytes):
                    # Binary audio data
                    self.chunks_received += 1
                    self.bytes_received += len(message)
                    
                    logger.debug(
                        f"Received audio chunk #{self.chunks_received}: "
                        f"{len(message)} bytes"
                    )
                    
                    # Play the audio
                    self.audio_player.play_audio(message)
                    
                else:
                    # Text message (status/metadata)
                    logger.info(f"Server message: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by server")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self.is_connected = False
    
    async def send_keep_alive(self):
        """
        Send periodic keep-alive messages to maintain connection
        """
        while self.is_connected and self.ws_connection:
            try:
                await asyncio.sleep(30)  # Send every 30 seconds
                await self.ws_connection.send("ping")
                logger.debug("Sent keep-alive ping")
            except Exception as e:
                logger.error(f"Error sending keep-alive: {e}")
                break
    
    async def attempt_reconnect(self):
        """
        Attempt to reconnect with exponential backoff
        """
        if self.reconnect_attempts >= RECONNECT_ATTEMPTS:
            logger.error(
                f"Failed to reconnect after {RECONNECT_ATTEMPTS} attempts. "
                "Please check if the server is running."
            )
            return False
        
        self.reconnect_attempts += 1
        delay = RECONNECT_DELAY * (2 ** (self.reconnect_attempts - 1))
        
        logger.info(
            f"Reconnect attempt {self.reconnect_attempts}/{RECONNECT_ATTEMPTS} "
            f"in {delay} seconds..."
        )
        
        await asyncio.sleep(delay)
        
        # Try to connect again
        if await self.connect():
            return True
        else:
            return await self.attempt_reconnect()
    
    async def run(self):
        """
        Main run loop - connect and listen for audio
        """
        self.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("🎙️  SwarSetu Python Receiver Starting")
        logger.info("=" * 60)
        
        # Connect to server
        if not await self.connect():
            # Try to reconnect
            if not await self.attempt_reconnect():
                logger.error("Failed to establish connection. Exiting.")
                return
        
        try:
            # Run main loop with keep-alive and audio reception
            await asyncio.gather(
                self.receive_audio(),
                self.send_keep_alive(),
                return_exceptions=True
            )
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopping receiver...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            # Clean up
            await self.disconnect()
            self.audio_player.close()
            
            # Print statistics
            if self.start_time:
                duration = (datetime.now() - self.start_time).total_seconds()
                logger.info("=" * 60)
                logger.info("📊 Statistics")
                logger.info("=" * 60)
                logger.info(f"Duration: {duration:.2f}s")
                logger.info(f"Chunks received: {self.chunks_received}")
                logger.info(f"Bytes received: {self.bytes_received:,}")
                if duration > 0:
                    logger.info(
                        f"Average bitrate: "
                        f"{(self.bytes_received * 8 / duration / 1000):.2f} kbps"
                    )

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """
    Parse arguments and start the receiver client
    """
    parser = argparse.ArgumentParser(
        description='SwarSetu Python Receiver - Play audio from local network',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python receiver.py                    # Connect to localhost:8000
  python receiver.py --host 192.168.1.100  # Connect to specific IP
  python receiver.py --host 192.168.1.100 --port 8000  # Custom port
        """
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='Server hostname or IP address (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Server port number (default: 8000)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Create and run receiver
    receiver = SwarSetuReceiver(args.host, args.port)
    
    try:
        await receiver.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Check for required dependencies
    try:
        import websockets
        import sounddevice
        import numpy
    except ImportError as e:
        logger.error(f"Missing required package: {e}")
        logger.error("Install with: pip install -r requirements.txt")
        sys.exit(1)
    
    # Run the async main function
    asyncio.run(main())
