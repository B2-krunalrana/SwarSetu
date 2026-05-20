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

from config import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_SAMPLE_RATE, DEFAULT_CHANNELS, DEBUG

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
        # Open output stream
        with sd.OutputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=dev_idx,
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


# --- Static frontend files serving routes for local setup support ---

@app.get("/")
async def get_index():
    index_path = os.path.join(PROJECT_ROOT, "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("Frontend files not found. Please ensure the frontend/ directory is placed alongside the server/ directory.", status_code=404)


@app.get("/style.css")
async def get_style():
    path = os.path.join(PROJECT_ROOT, "frontend", "style.css")
    if os.path.exists(path):
        return FileResponse(path, media_type="text/css")
    return JSONResponse({"error": "CSS File not found"}, status_code=404)


@app.get("/app.js")
async def get_app_js():
    path = os.path.join(PROJECT_ROOT, "frontend", "app.js")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/javascript")
    return JSONResponse({"error": "JS File not found"}, status_code=404)


@app.get("/audio-processor.js")
async def get_audio_processor_js():
    path = os.path.join(PROJECT_ROOT, "frontend", "audio-processor.js")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/javascript")
    return JSONResponse({"error": "Audio processor JS File not found"}, status_code=404)


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint accepting raw binary PCM audio chunks.
    Reads config from query parameters.
    """
    global active_connections, total_packets_received, total_bytes_received
    
    await websocket.accept()
    active_connections += 1
    logger.info(f"WebSocket client connected. Active connections: {active_connections}")
    
    # Read query parameters with fallbacks
    query_params = websocket.query_params
    sample_rate = int(query_params.get("sampleRate", DEFAULT_SAMPLE_RATE))
    channels = int(query_params.get("channels", DEFAULT_CHANNELS))
    
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


def main():
    global device_index
    
    parser = argparse.ArgumentParser(description="🎙️ SwarSetu: Live Voice Bridge System Backend")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Host network interface to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to run the FastAPI server on")
    parser.add_argument("--device", type=str, default=None, help="Output audio device index or partial name")
    parser.add_argument("--list-devices", action="store_true", help="List all available audio devices and exit")
    
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
    
    logger.info("🎙️ Starting SwarSetu Server...")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
