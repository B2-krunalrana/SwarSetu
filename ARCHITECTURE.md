# 🏗️ SwarSetu Architecture Guide

Comprehensive documentation of the SwarSetu system architecture, design patterns, and component interactions.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [API Design](#api-design)
5. [Design Patterns](#design-patterns)
6. [Concurrency Model](#concurrency-model)
7. [Error Handling](#error-handling)
8. [Performance Considerations](#performance-considerations)
9. [Security Architecture](#security-architecture)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         LOCAL WIFI NETWORK                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────┐    ┌──────────────────────┐   │
│  │    PHONE (Sender)        │    │   LAPTOP (Receiver)  │   │
│  │                          │    │                      │   │
│  │  ┌──────────────────┐    │    │  ┌────────────────┐  │   │
│  │  │  Browser UI      │    │    │  │  FastAPI Server   │  │   │
│  │  │  - Mic Button    │    │    │  │  - WebSocket Mgmt │  │   │
│  │  │  - Status Display│    │    │  │  - Connection Log │  │   │
│  │  └─────────┬────────┘    │    │  └────────┬─────────┘  │   │
│  │            │             │    │           │            │   │
│  │  ┌─────────▼────────┐    │    │  ┌────────▼─────────┐  │   │
│  │  │ MediaRecorder    │    │    │  │  Python Receiver  │  │   │
│  │  │ - Audio Capture  │    │    │  │  - Audio Playback │  │   │
│  │  │ - Chunk Assembly │    │    │  │  - Reconnect Logic│  │   │
│  │  └─────────┬────────┘    │    │  └────────┬─────────┘  │   │
│  │            │             │    │           │            │   │
│  │  ┌─────────▼────────┐    │    │  ┌────────▼─────────┐  │   │
│  │  │ WebSocket Client │    │    │  │  sounddevice      │  │   │
│  │  │ (Browser API)    │    │    │  │  (Speaker I/O)    │  │   │
│  │  └─────────┬────────┘    │    │  └────────┬─────────┘  │   │
│  │            │             │    │           │            │   │
│  └────────────┼─────────────┘    └───────────┼────────────┘   │
│               │ ws://LAPTOP_IP:8000/       │                │
│               │ ws/sender                   │                │
│               │                             │                │
│  ─────────────┴─────────────────────────────┴─────────────   │
│           WebSocket Connection (Binary Audio)               │
│               │ ws://LAPTOP_IP:8000/                        │
│               │ ws/receiver                                 │
│  ─────────────┬─────────────────────────────┬─────────────   │
│               │                             │                │
│               │                    ┌────────▼──────────┐     │
│               │                    │  Audio Processing │     │
│               │                    │  - Buffering      │     │
│               │                    │  - Format Convert │     │
│               │                    └────────┬──────────┘     │
│               │                             │                │
│               │                    ┌────────▼──────────┐     │
│               │                    │  Laptop Speakers  │     │
│               │                    │  (Audio Output)   │     │
│               │                    └───────────────────┘     │
│               │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

### System Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Server | FastAPI | HTTP and WebSocket endpoint |
| Frontend | HTML/CSS/JS | Mobile-friendly UI |
| JavaScript Client | MediaRecorder API | Audio capture and streaming |
| Python Receiver | asyncio + websockets | Audio reception and playback |
| Audio Engine | sounddevice | Speaker output |

---

## Component Architecture

### 1. FastAPI Server (`server/main.py`)

**Responsibilities:**
- Serve frontend webpage
- Manage WebSocket connections
- Route audio data between senders and receivers
- Handle connection lifecycle
- Provide health/stats endpoints

**Key Classes:**
```python
# Global state management
active_senders: Set[WebSocket]
active_receivers: Set[WebSocket]
connection_log: list

# Main endpoint functions
async def websocket_sender_endpoint(ws)
async def websocket_receiver_endpoint(ws)
```

**Architecture Pattern:** Hub-and-Spoke
```
Phone 1 ┐
        ├─→ Server (FastAPI) ──→ Receiver 1
Phone 2 ┘                    ├─→ Receiver 2
```

### 2. Frontend (`frontend/index.html`)

**Responsibilities:**
- Render mobile UI
- Request microphone access
- Capture and chunk audio
- Maintain WebSocket connection
- Display connection status

**Key JavaScript Objects:**
```javascript
State = {
  isConnected,
  isRecording,
  mediaStream,
  mediaRecorder,
  ws
}

CONFIG = {
  audio: { sampleRate, echoCancellation, ... },
  server: { reconnectAttempts, reconnectDelay }
}
```

**Architecture Pattern:** State Machine
```
Disconnected → Connecting → Connected → Recording → Playing Back
```

### 3. Python Receiver (`receiver/receiver.py`)

**Responsibilities:**
- Connect to WebSocket server
- Receive audio chunks
- Decode audio format
- Play through speakers
- Handle reconnection

**Key Classes:**
```python
class AudioPlayer:
    - Initialize sounddevice stream
    - Play audio chunks
    - Handle cleanup

class SwarSetuReceiver:
    - Connect to server
    - Listen for audio
    - Send keep-alive
    - Manage reconnection
```

**Architecture Pattern:** Async Consumer
```
Receive Audio → Buffer → Decode → Normalize → Play
```

### 4. Configuration (`server/config.py`)

**Purpose:**
- Centralized configuration
- Environment variable support
- Default values
- Type safety

**Hierarchy:**
```
Environment Variables → config.py → Application
```

---

## Data Flow

### Sender Audio Flow (Phone → Server → Receiver)

```
1. USER ACTION (Phone)
   ├─ User holds mic button
   └─ JavaScript event handler triggered

2. MICROPHONE ACCESS (Phone)
   ├─ getUserMedia() called
   ├─ Browser requests permission
   └─ Audio stream initialized

3. AUDIO CAPTURE (Phone Browser)
   ├─ MediaRecorder starts recording
   ├─ Audio samples collected in buffer
   └─ Every 100ms, dataavailable event fires

4. AUDIO ENCODING (Phone Browser)
   ├─ WebM/audio codec compression
   ├─ Audio chunks stored
   └─ Chunk size: ~1-10 KB

5. WEBSOCKET TRANSMISSION (Phone → Server)
   ├─ WebSocket connection established
   ├─ Binary audio chunk sent
   ├─ Header: VBAN/WebSocket format
   └─ Payload: Encoded audio data

6. SERVER ROUTING (FastAPI Server)
   ├─ Receive binary data from sender
   ├─ Iterate through all connected receivers
   ├─ Send audio chunk to each receiver
   └─ Log connection event

7. WEBSOCKET RECEPTION (Server → Receiver)
   ├─ Python client receives binary data
   ├─ Audio chunk buffered
   └─ Playback triggered

8. AUDIO DECODING (Python Receiver)
   ├─ WebM/codec decompression
   ├─ Convert to PCM format
   └─ Normalize audio level

9. AUDIO PLAYBACK (Python → Speakers)
   ├─ sounddevice writes to stream
   ├─ Audio buffer filled
   ├─ Speaker driver plays audio
   └─ Speakers emit sound

10. USER HEARS (Laptop)
    └─ Audio audible through speakers
```

### Timeline Diagram

```
Time:    0ms    100ms   200ms   300ms   400ms   500ms
Phone:   │ ▲━━━━━█ ▲━━━━━█ ▲━━━━━█ ▼━━━ 
         │ ╰─Capture─╯ ╰─Capture─╯
         │
Network: │    ╔════╗    ╔════╗    ╔════╗
         │    ║ Ch1║    ║ Ch2║    ║ Ch3║
         │    ╚════╝    ╚════╝    ╚════╝
         │
Server:  │           ▼         ▼         ▼
         │        Forward   Forward   Forward
         │
Receiver:│              ▼         ▼         ▼
         │           Buffer   Buffer   Buffer
         │
Speaker: │                 ▼─────────▼─────────▼
         │                 Playing audio...
         │
Latency: 30-50ms per hop × ~3-4 hops = 100-200ms
```

---

## API Design

### WebSocket API

#### Sender Endpoint: `/ws/sender`

**Connection Flow:**
```
1. Browser connects to ws://server:8000/ws/sender
2. Server accepts connection
3. Client assigned unique sender ID
4. Server broadcasts audio to all receivers
5. Connection maintained until disconnect
```

**Message Types:**

| Direction | Type | Format | Purpose |
|-----------|------|--------|---------|
| Send | Binary | Raw PCM/WebM | Audio data |
| Receive | JSON | `{"status": "received"}` | Acknowledgment |

**Example Connection:**
```javascript
// Client side
const ws = new WebSocket('ws://192.168.1.100:8000/ws/sender');

ws.onopen = () => console.log('Connected');
ws.send(audioBuffer);  // Binary data

// Server side
await sender.send_bytes(audio_data)
```

#### Receiver Endpoint: `/ws/receiver`

**Connection Flow:**
```
1. Python client connects to ws://server:8000/ws/receiver
2. Server accepts connection
3. Client assigned unique receiver ID
4. Server sends welcome message
5. Audio chunks streamed to client
6. Client sends periodic keep-alive
```

**Message Types:**

| Direction | Type | Format | Purpose |
|-----------|------|--------|---------|
| Receive | Binary | PCM/WebM audio | Audio data |
| Receive | JSON | Connection metadata | Initial greeting |
| Send | Text | "ping" | Keep-alive |
| Receive | Text | "pong" | Keep-alive response |

**Example Connection:**
```python
# Client side
async with websockets.connect('ws://localhost:8000/ws/receiver') as ws:
    async for message in ws:
        if isinstance(message, bytes):
            play_audio(message)
```

### HTTP API

#### GET `/health`

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123456",
  "active_senders": 1,
  "active_receivers": 1,
  "total_connections": 2,
  "version": "1.0.0"
}
```

#### GET `/stats`

```json
{
  "active_senders": 1,
  "active_receivers": 1,
  "connection_events": 42,
  "recent_connections": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "event": "connected",
      "type": "sender",
      "client_id": "sender_12345"
    }
  ]
}
```

---

## Design Patterns

### 1. Hub-and-Spoke Pattern

**Location:** Server audio routing

```python
# Server maintains sets of senders and receivers
active_senders: Set[WebSocket]
active_receivers: Set[WebSocket]

# When audio received from sender:
for receiver in active_receivers:
    await receiver.send_bytes(audio_data)
```

**Benefits:**
- Simple, centralized routing
- Easy to broadcast to multiple receivers
- Scales to moderate load

### 2. State Machine Pattern

**Location:** Frontend connection management

```javascript
State Transitions:
Disconnected → Connecting → Connected
                    ↓
              Failed → Attempting Reconnect

Recording:
Idle → Recording → Stopped → Sending → Idle
```

### 3. Async/Await Pattern

**Location:** FastAPI and Python receiver

```python
async def websocket_endpoint(ws):
    await ws.accept()
    while True:
        data = await ws.receive_bytes()
        # Process asynchronously
```

**Benefits:**
- Handles multiple concurrent connections
- Non-blocking I/O
- Efficient resource usage

### 4. Connection Pool Pattern

**Location:** Multiple WebSocket connections

```python
# Implicit connection pool through sets
active_senders = set()  # ~50 max connections
active_receivers = set()

# Connection pooling happens naturally
# New connections added, old ones removed
```

### 5. Observer Pattern

**Location:** WebSocket message broadcasting

```python
# Receivers "observe" sender data
# When sender sends audio, all receivers notified

class AudioBroadcaster:
    def broadcast(self, audio_data):
        for observer in self.receivers:
            observer.notify(audio_data)
```

### 6. Singleton Pattern

**Location:** FastAPI application instance

```python
# Single app instance
app = FastAPI()

# Single configuration
CONFIG = {...}

# Shared state
active_senders = set()
active_receivers = set()
```

---

## Concurrency Model

### Multi-Connection Handling

**Architecture:** Async concurrent connections

```
Server can handle multiple senders and receivers simultaneously:

Sender 1 ──┐
Sender 2 ──┤─→ FastAPI (asyncio event loop)
Sender 3 ──┘
            ├─→ Receiver 1
            ├─→ Receiver 2
            └─→ Receiver 3
```

### Event Loop Model

```
┌─────────────────────────────────────┐
│     Async Event Loop (asyncio)      │
├─────────────────────────────────────┤
│                                     │
│  Task 1: Accept connections         │
│  Task 2: Receive from Sender A      │
│  Task 3: Receive from Sender B      │
│  Task 4: Send to Receiver 1         │
│  Task 5: Send to Receiver 2         │
│  Task 6: Health check endpoint      │
│  ...                                │
│                                     │
│  (All run cooperatively)            │
└─────────────────────────────────────┘
```

### Python Receiver Concurrency

```python
asyncio.gather(
    self.receive_audio(),      # Task 1: Receive audio
    self.send_keep_alive(),    # Task 2: Keep-alive
    return_exceptions=True
)

# Both run concurrently
```

### Connection Lifecycle

```
SENDER:                     SERVER:                     RECEIVER:

WebSocket                   Accept                      WebSocket
Connect                     ─────────────────→          Connect
   │                           │                          │
   │ Audio                      │                          │
   ├──────────────────→ Receive audio               
   │                      ├─────────────────────→ Receive audio
   │                      │                       ├─→ Play
   │                                              │
   │ More audio                                   │
   ├──────────────────→ Receive audio            
   │                      ├─────────────────────→ Receive audio
   │                      │                       ├─→ Play
   │                                              │
   │ Disconnect                                   │
   ├──────────────────→ Close                    
   │                                              ├─→ Still playing
   │                                              │
   │                                              Disconnect
   │                                              ├──────────→
```

---

## Error Handling

### Graceful Degradation

```
Error Scenarios:

1. Connection Loss (Sender)
   ├─ Server detects disconnect
   ├─ Stops forwarding from that sender
   └─ Other senders continue working

2. Connection Loss (Receiver)
   ├─ Server detects disconnect
   ├─ Audio buffered for other receivers
   └─ Sender continues sending

3. Network Interruption
   ├─ WebSocket auto-reconnect (client-side)
   ├─ Python receiver retries connection
   └─ Limited by RECONNECT_ATTEMPTS
```

### Error Recovery

**Frontend:**
```javascript
// Automatic reconnection
attemptReconnect() {
    // Exponential backoff
    delay = 2000 * Math.pow(2, attempts)
    
    // Max attempts: CONFIG.server.reconnectAttempts
}
```

**Python Receiver:**
```python
async def attempt_reconnect(self):
    for attempt in range(RECONNECT_ATTEMPTS):
        delay = RECONNECT_DELAY * (2 ** attempt)
        
        if await self.connect():
            return True
```

### Error Logging

```python
logger.error(f"[ERROR] Connection lost: {error}")
logger.warning(f"[WARNING] Attempting reconnect {attempt}/{max}")
logger.info(f"[INFO] Successfully reconnected")
```

---

## Performance Considerations

### Latency Optimization

```
Total Latency = Capture + Encode + Network + Decode + Playback

Capture Delay: 10-20ms
├─ MediaRecorder buffer size
├─ Phone audio hardware
└─ Browser implementation

Encode Delay: 5-10ms
├─ WebM codec compression
└─ Browser WebRTC stack

Network Delay: 5-50ms
├─ WiFi: 5-20ms typical
├─ Wired: <5ms
└─ Interference: 20-50ms

Decode Delay: 5-10ms
├─ Audio codec decompression
└─ Python audio processing

Playback Delay: 20-40ms
├─ sounddevice buffer
├─ Audio driver
└─ Hardware latency

TOTAL: 50-150ms (acceptable for voice)
```

### Memory Usage

```
Per Connection:
├─ Sender: ~2-5 MB (WebSocket buffer + audio chunks)
├─ Receiver: ~5-10 MB (incoming queue + buffer)
└─ Server: ~1 MB (metadata + connection tracking)

For 50 Connections:
├─ Senders: 100-250 MB
├─ Receivers: 250-500 MB
└─ Total: ~400-750 MB (on server)
```

### CPU Usage

```
Server:
├─ Idle: <1% CPU
├─ One sender to one receiver: 2-5% CPU
├─ Ten senders to ten receivers: 15-25% CPU
└─ Bottleneck: Audio copying/broadcasting

Python Receiver:
├─ Idle: <1% CPU
├─ Active: 5-10% CPU
└─ Bottleneck: Audio decoding/playback
```

### Bandwidth Usage

```
Per Stream:
├─ Sample Rate: 16 kHz
├─ Channels: 1 (mono)
├─ Bit Depth: 16-bit
├─ Uncompressed: 256 kbps (32 KB/s)
├─ WebM Compressed: ~128 kbps (16 KB/s)
├─ Packet Overhead: ~10%
└─ Effective: ~18 KB/s per stream

For 5 Concurrent Streams:
└─ ~90 KB/s total
```

---

## Security Architecture

### Current State (Local Network Only)

✅ **Implemented:**
- CORS enabled for local IPs
- Connection validation
- Basic input validation

⚠️ **Not Implemented:**
- Encryption (unencrypted WebSocket)
- Authentication
- Rate limiting
- Input sanitization

### Security Layers (Future)

```
Layer 1: Transport Security
├─ WSS (WebSocket over TLS)
├─ HTTPS for frontend
└─ Firewall rules

Layer 2: Application Security
├─ User authentication
├─ Authorization checks
├─ Rate limiting
└─ Input validation

Layer 3: Monitoring
├─ Activity logging
├─ Anomaly detection
└─ Security alerts
```

### Network Isolation

```
┌─────────────────────────────────┐
│   Local Private Network         │
│   (192.168.1.0/24)              │
│                                 │
│   ┌────────────┐  ┌──────────┐ │
│   │   Phone    │  │  Laptop  │ │
│   └────────────┘  └──────────┘ │
│                                 │
│   ✓ Isolated from Internet      │
│   ✓ No external access          │
│   ✓ Safe for development        │
│                                 │
└─────────────────────────────────┘

For Production:
- Add firewall rules
- Use VPN for remote access
- Implement TLS/encryption
- Add authentication
```

---

## Deployment Architecture

### Development Deployment

```
Same Machine Setup:
┌──────────────────────────────────┐
│         Laptop                   │
│  ┌────────────────────────────┐  │
│  │   Terminal 1: Server       │  │
│  │   python server/main.py    │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │   Terminal 2: Receiver     │  │
│  │   python receiver.py       │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │   Phone Browser            │  │
│  │   http://localhost:8000    │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

### Multi-Machine Deployment

```
Laptop (Server):
└─ FastAPI Server (0.0.0.0:8000)
   ├─ Sender WebSocket Endpoint
   └─ Receiver WebSocket Endpoint

Phone (Sender):
└─ Browser Client
   └─ Connect to Laptop IP:8000

Laptop (Receiver):
└─ Python Client
   └─ Connect to localhost:8000
      └─ Output through speakers
```

### Raspberry Pi Deployment

```
Raspberry Pi:
├─ Python FastAPI Server (port 8000)
├─ USB Audio Interface (input/output)
└─ Network connectivity

Phone:
└─ Browser (http://raspberrypi.local:8000)

Other Laptops:
└─ Python receiver.py (point to Pi IP)
```

---

## Scaling Considerations

### Horizontal Scaling

**Current Architecture Limits:**
- Single server handles ~50 concurrent connections
- Limited by machine resources

**Scaling Strategy:**
```
Option 1: Load Balancer
Phone → Load Balancer ──→ Server 1
                    └──→ Server 2
                    └──→ Server 3

Option 2: Dedicated Servers
Senders → Ingress Server → Receiver Servers
```

### Vertical Scaling

**Optimization Points:**
```
CPU: More cores for async processing
├─ uvicorn workers: 4-8 workers
└─ asyncio optimization

Memory: Larger buffers
├─ Audio buffering: 100-500 MB
└─ Connection tracking: 10-50 MB

Network: Higher bandwidth
├─ Multiple NICs
└─ Jumbo frames (9000 MTU)
```

---

## Monitoring & Observability

### Health Checks

```python
# Built-in endpoints
GET /health         # Basic health
GET /stats          # Detailed statistics
```

### Logging

```python
# Structured logging
log_connection("connected", "sender", client_id)
log_connection("disconnected", "receiver", client_id)

# Level-based
logger.debug()   # Detailed tracing
logger.info()    # Important events
logger.warning() # Potential issues
logger.error()   # Error conditions
```

### Metrics

```
Key Metrics:
├─ Connection count
├─ Audio chunks transmitted
├─ Bytes streamed
├─ CPU usage
├─ Memory usage
├─ Network latency
└─ Error rate
```

---

## Future Architecture Improvements

1. **VBAN Support** - UDP-based streaming for lower latency
2. **Load Balancing** - Horizontal scaling with Redis
3. **Message Queue** - Kafka/RabbitMQ for buffering
4. **Database** - Connection history and analytics
5. **Monitoring** - Prometheus/Grafana integration
6. **API Gateway** - Kong or similar for advanced routing

---

**Architecture Designed for Simplicity, Scalable for Growth** 🚀
