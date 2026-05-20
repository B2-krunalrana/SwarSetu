import argparse
import asyncio
import logging
import os
import queue
import sys
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from fastapi.staticfiles import StaticFiles

from config import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_SAMPLE_RATE, DEFAULT_CHANNELS, DEBUG

# Fix Windows terminal encoding to UTF-8 (prevents crash on emoji in logs)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("SwarSetu")

# Determine project directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define FastAPI application
app = FastAPI(title="SwarSetu Real-Time Voice Bridge")

# Enable CORS for frontend cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for state and command line parameters
device_index: Optional[int] = None
active_connections = 0
total_packets_received = 0
total_bytes_received = 0


def get_audio_device_index(device_arg: Optional[str]) -> Optional[int]:
    """Helper to resolve audio device index from string or int argument."""
    if device_arg is None:
        return None
    try:
        # If it's a direct digit, return it as integer
        if device_arg.isdigit():
            return int(device_arg)
        
        # Otherwise search by name substring
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if device_arg.lower() in dev["name"].lower() and dev["max_output_channels"] > 0:
                logger.info(f"Matched device name '{device_arg}' to index {idx}: {dev['name']}")
                return idx
        
        logger.warning(f"Could not find output device matching name '{device_arg}'. Using default.")
        return None
    except Exception as e:
        logger.error(f"Error resolving audio device index: {e}")
        return None


def playback_worker(
    q: queue.Queue,
    sample_rate: int,
    channels: int,
    dev_idx: Optional[int],
    stop_event: threading.Event
):
    """
    Background worker thread that reads raw 16-bit PCM chunks from a queue
    and writes them directly to the sounddevice OutputStream.
    """
    logger.info(f"Starting playback worker thread (Rate: {sample_rate}Hz, Channels: {channels}, Device: {dev_idx if dev_idx is not None else 'Default'})")
    
    try:
        # Resolve active device index and query details
        resolved_device = dev_idx if dev_idx is not None else sd.default.device[1]
        try:
            device_info = sd.query_devices(resolved_device)
            logger.info(f"[AUDIO] Output device: [{resolved_device}] {device_info['name']}")
        except Exception as e:
            logger.warning(f"Could not query audio device details for index {resolved_device}: {e}")

        # Open output stream
        with sd.OutputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=resolved_device,
            latency="low"
        ) as stream:
            logger.info("Audio output stream successfully opened.")
            while not stop_event.is_set():
                try:
                    # Get chunk with small timeout to check stop_event frequently
                    data = q.get(timeout=0.1)
                    if data is None:
                        break
                    
                    # Convert raw bytes to numpy 16-bit integers
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    
                    # Calculate volume (RMS) of the chunk to display level meter
                    if len(audio_chunk) > 0:
                        rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
                    else:
                        rms = 0.0
                    
                    # Generate simple level bar (max 20 blocks)
                    bar_length = int(min(20, rms / 150))
                    level_bar = "█" * bar_length + "░" * (20 - bar_length)
                    
                    logger.info(f"[AUDIO] Playing {len(audio_chunk)} samples | RMS: {rms:6.1f} | [{level_bar}]")
                    
                    # Write block to speakers (blocking write)
                    stream.write(audio_chunk)
                    q.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error during audio playback stream write: {e}")
                    break
    except Exception as e:
        logger.error(f"Failed to open audio output stream: {e}")
        logger.error("Please verify that your speakers are connected and the device selection is correct.")
    
    logger.info("Playback worker thread terminated.")


@app.get("/health")
async def health_check():
    """Rest Endpoint for server health and connectivity diagnostics."""
    return JSONResponse(
        content={
            "status": "healthy",
            "active_connections": active_connections,
            "total_packets_received": total_packets_received,
            "total_bytes_received": total_bytes_received,
            "device": sd.query_devices(device_index)["name"] if device_index is not None else "Default",
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint accepting raw binary PCM audio chunks.
    Reads config from query parameters.
    """
    global active_connections, total_packets_received, total_bytes_received
    
    await websocket.accept()
    active_connections += 1

    # Read query parameters with fallbacks
    query_params = websocket.query_params
    sample_rate = int(query_params.get("sampleRate", DEFAULT_SAMPLE_RATE))
    channels = int(query_params.get("channels", DEFAULT_CHANNELS))

    logger.info(f"[WS] Client connected - playing at {sample_rate} Hz, {channels}ch | Active: {active_connections}")
    
    # Initialize queue and stop signal for playback
    audio_queue = queue.Queue()
    stop_event = threading.Event()
    
    # Start thread
    worker_thread = threading.Thread(
        target=playback_worker,
        args=(audio_queue, sample_rate, channels, device_index, stop_event),
        daemon=True
    )
    worker_thread.start()
    
    try:
        while True:
            # Wait for binary message
            data = await websocket.receive_bytes()
            
            # Update stats
            total_packets_received += 1
            total_bytes_received += len(data)
            
            # Enqueue raw data
            audio_queue.put(data)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket loop encountered error: {e}")
    finally:
        active_connections = max(0, active_connections - 1)
        # Gracefully stop the worker thread
        audio_queue.put(None)
        stop_event.set()
        worker_thread.join(timeout=1.0)
        logger.info(f"Session closed. Active connections: {active_connections}")


# --- Mount React production build assets ---
dist_path = os.path.join(PROJECT_ROOT, "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
    logger.info(f"Mounted React production build directory: {dist_path}")
else:
    logger.warning(f"React production build directory NOT found at: {dist_path}. Please compile the frontend using 'npm run build' inside the 'frontend/' folder.")


def main():
    global device_index
    
    parser = argparse.ArgumentParser(description="🎙️ SwarSetu: Live Voice Bridge System Backend")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Host network interface to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to run the FastAPI server on")
    parser.add_argument("--device", type=str, default=None, help="Output audio device index or partial name")
    parser.add_argument("--list-devices", action="store_true", help="List all available audio devices and exit")
    parser.add_argument("--ssl-keyfile", type=str, default=None, help="Path to SSL key file (for HTTPS/WSS on LAN)")
    parser.add_argument("--ssl-certfile", type=str, default=None, help="Path to SSL cert file (for HTTPS/WSS on LAN)")
    
    args = parser.parse_args()
    
    if args.list_devices:
        print("\n=== SwarSetu Audio Device Utility ===")
        try:
            devices = sd.query_devices()
            default_out = sd.default.device[1]
            print(f"Default Output Device Index: {default_out}\n")
            print("Available Devices:")
            for idx, dev in enumerate(devices):
                is_out = dev["max_output_channels"] > 0
                out_tag = " [OUTPUT]" if is_out else ""
                default_tag = " (DEFAULT)" if idx == default_out else ""
                print(f" [{idx}] {dev['name']} - Channels: In={dev['max_input_channels']}, Out={dev['max_output_channels']}{out_tag}{default_tag}")
        except Exception as e:
            print(f"Error querying audio devices: {e}")
        print("======================================\n")
        sys.exit(0)
    
    # Resolve and set the device index
    device_index = get_audio_device_index(args.device)

    # Fix: Windows requires ProactorEventLoop for SSL/WebSocket support.
    # Without this, uvicorn silently exits when --ssl-keyfile is provided.
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Applied WindowsProactorEventLoopPolicy for SSL support.")

    proto = "https" if args.ssl_keyfile else "http"
    logger.info(f"[SERVER] SwarSetu starting at {proto}://{args.host}:{args.port}")
    logger.info(f"[SERVER] Open on your phone: {proto}://<YOUR-LAN-IP>:{args.port}")

    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info",   # Show uvicorn 'Uvicorn running on...' startup line
            ssl_keyfile=args.ssl_keyfile,
            ssl_certfile=args.ssl_certfile,
        )
    except Exception as e:
        logger.error(f"[SERVER] Failed to start: {e}")
        logger.error("[SERVER] Common causes:")
        logger.error("  - SSL cert/key files not found (check path)")
        logger.error("  - Port 8000 already in use (stop old server with Ctrl+C first)")
        logger.error("  - cert.pem / key.pem format invalid (regenerate them)")
        sys.exit(1)


if __name__ == "__main__":
    main()
