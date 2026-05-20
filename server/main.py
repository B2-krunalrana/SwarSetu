"""
SwarSetu FastAPI Server
A simple local-network real-time announcement system using WebSockets

This server:
1. Serves a mobile-friendly web interface for the sender
2. Accepts incoming audio chunks from the browser via WebSocket
3. Broadcasts audio to all connected receiver clients
4. Maintains connection logs for debugging
"""

import logging
import asyncio
from datetime import datetime
from typing import Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import configuration
from config import (
    HOST, PORT, AUDIO_SAMPLE_RATE, AUDIO_CHUNK_SIZE,
    CORS_ORIGINS, APP_TITLE, APP_DESCRIPTION, APP_VERSION,
    LOG_LEVEL, DEBUG_MODE
)

# ============================================================================
# LOGGING SETUP
# ============================================================================

# Configure logging for debugging and monitoring
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL STATE MANAGEMENT
# ============================================================================

# Set to store active WebSocket connections
# We'll use separate sets for senders and receivers
active_senders: Set[WebSocket] = set()  # Phone/browser clients sending audio
active_receivers: Set[WebSocket] = set()  # Laptop clients receiving audio

# Connection metadata for logging
connection_log: list = []

# ============================================================================
# CONNECTION LOGGING HELPER
# ============================================================================

def log_connection(event: str, client_type: str, client_id: str):
    """
    Log connection events for debugging and monitoring
    
    Args:
        event: "connected" or "disconnected"
        client_type: "sender" or "receiver"
        client_id: unique identifier for the client
    """
    timestamp = datetime.now().isoformat()
    sender_count = len(active_senders)
    receiver_count = len(active_receivers)
    
    log_entry = {
        "timestamp": timestamp,
        "event": event,
        "type": client_type,
        "client_id": client_id,
        "active_senders": sender_count,
        "active_receivers": receiver_count,
    }
    
    connection_log.append(log_entry)
    
    logger.info(
        f"[{event.upper()}] {client_type.upper()} {client_id} | "
        f"Senders: {sender_count}, Receivers: {receiver_count}"
    )

# ============================================================================
# LIFESPAN CONTEXT MANAGER (FastAPI startup/shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🎙️  SwarSetu Server Starting")
    logger.info("=" * 60)
    logger.info(f"Server running on http://{HOST}:{PORT}")
    logger.info(f"Debug mode: {DEBUG_MODE}")
    logger.info(f"Audio settings - Sample rate: {AUDIO_SAMPLE_RATE} Hz, "
                f"Chunk size: {AUDIO_CHUNK_SIZE} bytes")
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 SwarSetu Server Shutting Down")
    logger.info("=" * 60)
    logger.info(f"Total connection events: {len(connection_log)}")

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    debug=DEBUG_MODE
)

# Add CORS middleware to allow requests from other devices on the network
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    """
    Serve the mobile-friendly sender web interface
    This is the page users open on their phones
    """
    return open("../frontend/index.html", encoding="utf-8").read()

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    Returns server status and current connections
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_senders": len(active_senders),
        "active_receivers": len(active_receivers),
        "total_connections": len(active_senders) + len(active_receivers),
        "version": APP_VERSION,
    }

@app.get("/stats")
async def get_stats():
    """
    Get detailed statistics about server and connections
    """
    return {
        "active_senders": len(active_senders),
        "active_receivers": len(active_receivers),
        "connection_events": len(connection_log),
        "recent_connections": connection_log[-20:] if connection_log else [],
        "uptime": datetime.now().isoformat(),
    }

# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/ws/sender")
async def websocket_sender_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for audio senders (phone/browser microphone)
    
    Flow:
    1. Phone browser connects here
    2. Captures microphone audio
    3. Sends audio chunks as binary data
    4. Server broadcasts to all receivers
    """
    # Generate unique client ID
    client_id = f"sender_{id(websocket)}"
    
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        active_senders.add(websocket)
        
        log_connection("connected", "sender", client_id)
        
        logger.debug(f"Sender {client_id} connected. "
                    f"Total senders: {len(active_senders)}")
        
        # Keep connection open and listen for incoming audio
        while True:
            try:
                # Receive audio chunk (binary data from browser MediaRecorder)
                data = await websocket.receive_bytes()
                
                if data:
                    logger.debug(f"Received {len(data)} bytes from {client_id}")
                    
                    # Broadcast audio chunk to all connected receivers
                    # This happens for every chunk received from the sender
                    disconnected_receivers = set()
                    
                    for receiver in active_receivers:
                        try:
                            # Send the audio chunk to each receiver
                            await receiver.send_bytes(data)
                        except Exception as e:
                            logger.error(f"Error sending to receiver: {e}")
                            disconnected_receivers.add(receiver)
                    
                    # Clean up disconnected receivers
                    for receiver in disconnected_receivers:
                        active_receivers.discard(receiver)
                        log_connection("disconnected", "receiver", 
                                      f"receiver_{id(receiver)}")
                    
                    # Send confirmation back to sender (optional)
                    try:
                        await websocket.send_json({"status": "received"})
                    except:
                        pass
                        
            except asyncio.CancelledError:
                logger.debug(f"Sender {client_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in sender loop: {e}")
                break
                
    except WebSocketDisconnect:
        logger.debug(f"Sender {client_id} disconnected")
    except Exception as e:
        logger.error(f"Unexpected error in sender endpoint: {e}")
    finally:
        # Clean up when sender disconnects
        active_senders.discard(websocket)
        log_connection("disconnected", "sender", client_id)
        logger.info(f"Sender {client_id} removed. "
                   f"Total senders: {len(active_senders)}")
        
        try:
            await websocket.close()
        except:
            pass

@app.websocket("/ws/receiver")
async def websocket_receiver_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for audio receivers (Python client or web receiver)
    
    Flow:
    1. Receiver client connects here
    2. Waits for audio chunks from senders
    3. Receives and processes audio chunks
    4. Maintains connection until disconnected
    """
    # Generate unique client ID
    client_id = f"receiver_{id(websocket)}"
    
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        active_receivers.add(websocket)
        
        log_connection("connected", "receiver", client_id)
        
        logger.debug(f"Receiver {client_id} connected. "
                    f"Total receivers: {len(active_receivers)}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to SwarSetu server",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Keep connection open and handle incoming messages
        while True:
            try:
                # Receivers mainly receive data, but can also send keep-alive messages
                message = await websocket.receive_text()
                
                if message == "ping":
                    # Respond to ping with pong
                    await websocket.send_text("pong")
                else:
                    logger.debug(f"Received message from {client_id}: {message}")
                    
            except asyncio.CancelledError:
                logger.debug(f"Receiver {client_id} cancelled")
                break
            except Exception as e:
                if "Receiving client is disconnected" not in str(e):
                    logger.error(f"Error in receiver loop: {e}")
                break
                
    except WebSocketDisconnect:
        logger.debug(f"Receiver {client_id} disconnected")
    except Exception as e:
        logger.error(f"Unexpected error in receiver endpoint: {e}")
    finally:
        # Clean up when receiver disconnects
        active_receivers.discard(websocket)
        log_connection("disconnected", "receiver", client_id)
        logger.info(f"Receiver {client_id} removed. "
                   f"Total receivers: {len(active_receivers)}")
        
        try:
            await websocket.close()
        except:
            pass

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    Global exception handler for unexpected errors
    """
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "detail": str(exc) if DEBUG_MODE else "An error occurred",
    }

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting SwarSetu server on {HOST}:{PORT}")
    
    # Start the FastAPI server using uvicorn
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG_MODE,
        log_level=LOG_LEVEL.lower(),
    )
