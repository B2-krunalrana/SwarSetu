# 🎙️ SwarSetu - Local Network Audio Announcement System

**SwarSetu** is a simple, beginner-friendly real-time audio announcement system that lets you speak into your phone and instantly hear yourself through your laptop speakers—all over your local WiFi network!

## 🎯 Features

✨ **Simple to Use**
- Hold-to-talk button on your phone (just like a walkie-talkie)
- Instant audio playback on laptop speakers
- No complex setup or configuration

🔄 **Real-Time Streaming**
- WebSocket-based audio streaming
- Low-latency audio transmission over LAN
- Automatic reconnection on network issues

📱 **Mobile-Friendly**
- Works on Android Chrome and iPhone Safari
- PWA-like interface with modern UI
- Touch-optimized controls

🛠️ **Developer-Friendly**
- Clean, well-commented code
- Easy to understand and extend
- Production-style architecture
- Comprehensive logging

## 📋 Requirements

### Hardware
- One laptop/desktop with speakers (receiver)
- One smartphone with microphone (sender)
- Both devices on the same WiFi network

### Software
- **Python 3.8+** (for server and receiver)
- **Modern web browser** on phone (Chrome, Safari)
- **pip** for Python package management

### System Audio
- Working speakers/headphones on laptop
- Microphone on phone

## 🚀 Quick Start (5 Minutes)

### Step 1: Set Up Virtual Environment & Dependencies

Choose the command block for your operating system:

**On Windows:**
```powershell
# Navigate to SwarSetu directory
cd SwarSetu

# Create virtual environment
python -m venv venv

# Activate virtual environment (Command Prompt)
venv\Scripts\activate
# OR Activate virtual environment (PowerShell)
.\venv\Scripts\activate

# Initialize configuration
copy .env.example .env

# Install required packages
pip install -r requirements.txt
```

**On Mac/Linux:**
```bash
# Navigate to SwarSetu directory
cd SwarSetu

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Initialize configuration
cp .env.example .env

# Install required packages
pip install -r requirements.txt
```

### Step 2: Start the Server (on Laptop)

```bash
# From SwarSetu directory
cd server
python main.py
```

You should see:
```
🎙️  SwarSetu Server Starting
Server running on http://0.0.0.0:8000
```

### Step 3: Start the Receiver (on Laptop)

Open a **new terminal** and run:

```bash
cd receiver
python receiver.py --host localhost
```

You should see:
```
✓ Connected to server
🎧 Listening for audio...
```

### Step 4: Open Phone Browser

1. **Find your laptop's local IP address:**

   **On Windows (in command prompt):**
   ```
   ipconfig
   ```
   Look for "IPv4 Address" under your WiFi adapter (e.g., `192.168.1.100`)

   **On Mac/Linux (in terminal):**
   ```
   ifconfig
   ```
   Look for `inet` address of your WiFi interface (e.g., `192.168.1.100`)

2. **On your phone:**
   - Open Chrome (Android) or Safari (iPhone)
   - Go to: `http://192.168.1.100:8000` (replace with your IP)
   - Wait for connection status to show "Connected to Server"

### Step 5: Test Audio

1. **Allow microphone permission** when your phone asks
2. **Hold down the "Hold to Talk" button** on your phone
3. **Speak** into your phone's microphone
4. **Release** the button
5. **Listen** - your voice should play through your laptop speakers!

## 📁 Project Structure

```
SwarSetu/
├── server/                    # FastAPI server
│   ├── main.py               # Main server application
│   ├── config.py             # Server configuration
│   └── __init__.py
├── receiver/                  # Python receiver client
│   └── receiver.py           # Audio playback client
├── frontend/                  # Mobile web interface
│   └── index.html            # "Hold to Talk" web app
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── VBAN_AND_AUDIO_NETWORKING_GUIDE.md  # Advanced audio guide
```

## 🔧 Configuration

### Server Configuration (server/config.py)

Edit these settings to customize:

```python
HOST = "0.0.0.0"              # Listen on all network interfaces
PORT = 8000                    # Server port
AUDIO_SAMPLE_RATE = 16000     # Audio quality (16 kHz = voice quality)
AUDIO_CHUNK_SIZE = 1024       # Bytes per chunk
```

### Receiver Settings (receiver/receiver.py)

```python
SAMPLE_RATE = 16000           # Must match server sample rate
RECONNECT_ATTEMPTS = 5        # Auto-reconnect attempts
RECONNECT_DELAY = 2           # Delay between reconnects (seconds)
```

## 🌐 Network Configuration

### Finding Your Laptop's IP Address

**Windows:**
```powershell
# Command Prompt or PowerShell
ipconfig

# Look for: IPv4 Address under your WiFi adapter
# Example: 192.168.1.100
```

**Mac/Linux:**
```bash
# Terminal
ifconfig

# Look for inet address (not 127.0.0.1)
# Example: 192.168.1.100
```

### Connecting Phone to Server

**Android:**
1. Open Chrome
2. Type your laptop IP in address bar: `http://192.168.1.100:8000`
3. Press Enter

**iPhone:**
1. Open Safari
2. Type your laptop IP: `http://192.168.1.100:8000`
3. Tap Go

**Important:** Phone must be on the same WiFi as your laptop!

## 📊 Usage Examples

### Basic Usage

```bash
# Terminal 1: Start server
cd server
python main.py

# Terminal 2: Start receiver
cd receiver
python receiver.py

# Terminal 3 (optional): Check server health
curl http://localhost:8000/health
```

### Advanced Usage

```bash
# Connect to specific IP
python receiver.py --host 192.168.1.100 --port 8000

# Enable debug logging
python receiver.py --debug

# Connect from different machine
python receiver.py --host <laptop-ip> --port 8000
```

### Checking Server Status

```bash
# Health check endpoint
curl http://localhost:8000/health

# Detailed statistics
curl http://localhost:8000/stats

# Example response:
# {
#   "status": "healthy",
#   "active_senders": 1,
#   "active_receivers": 1,
#   "total_connections": 2
# }
```

## 🐛 Troubleshooting

### Phone Can't Connect to Server

**Problem:** "Failed to connect" or "Connecting..." forever

**Solutions:**
1. ✅ Check both devices are on **same WiFi** (not guest network)
2. ✅ Verify server is running: `python server/main.py`
3. ✅ Use correct IP address (not `localhost` on phone)
4. ✅ Firewall might be blocking: Disable temporarily or allow Python
5. ✅ Try: Refresh phone browser or restart server

**Debugging:**
```bash
# From phone, test connection:
ping 192.168.1.100

# From laptop, check port is listening:
netstat -an | grep 8000
```

### Audio Not Playing

**Problem:** Connection works but no sound

**Solutions:**
1. ✅ Check **receiver is running**: `python receiver.py`
2. ✅ Verify laptop **speakers are enabled** and not muted
3. ✅ Test speakers: `python -m sounddevice` (lists audio devices)
4. ✅ Check phone **microphone is working** (tap Allow when prompted)
5. ✅ Watch **receiver console** for "Received audio chunk" messages

**Debugging:**
```bash
# List audio devices on laptop
python -c "import sounddevice; print(sounddevice.query_devices())"

# Start receiver with debug logging
python receiver.py --debug
```

### Server Crashes or Won't Start

**Problem:** Port already in use or dependency missing

**Solutions:**
1. ✅ Try different port:
   ```bash
   # In server/config.py, change PORT = 9000
   ```
2. ✅ Kill process using port 8000:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   
   # Mac/Linux
   lsof -i :8000
   kill <PID>
   ```
3. ✅ Reinstall dependencies:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

### Microphone Permission Denied

**Problem:** Phone browser won't let you access microphone

**Solutions:**
1. ✅ Tap "Allow" when browser asks
2. ✅ Check browser permissions:
   - **Android:** Settings > Apps > Chrome > Permissions > Microphone > Allow
   - **iPhone:** Settings > Safari > Microphone > Allow
3. ✅ Try different browser
4. ✅ Clear browser cache

### High Latency / Echo

**Problem:** Noticeable delay between speaking and hearing

**Solutions:**
1. ✅ Check WiFi signal strength
2. ✅ Close other bandwidth-heavy applications
3. ✅ Try wired connection if possible
4. ✅ Reduce audio chunk size (in config.py)

## 📈 Performance Metrics

Expected performance on typical home WiFi:

| Metric | Value |
|--------|-------|
| Latency | 100-500ms |
| Bitrate | ~128 kbps |
| Audio Quality | Voice quality (16 kHz) |
| Max Connections | 50 concurrent |
| Bandwidth per Stream | ~16 KB/s |

## 🔐 Security Note

⚠️ **Important:** This prototype is designed for local networks only!

**For local networks (same WiFi):**
- ✅ Safe to use
- ✅ No internet exposure
- ✅ No authentication needed

**For internet/production use:**
- ⚠️ Add HTTPS/WSS encryption
- ⚠️ Implement authentication
- ⚠️ Add rate limiting
- ⚠️ Validate all inputs

See `VBAN_AND_AUDIO_NETWORKING_GUIDE.md` for advanced security topics.

## 📚 API Reference

### WebSocket Endpoints

#### `/ws/sender` (Phone/Browser)
Sends audio from microphone to server

**Connection flow:**
1. Browser connects
2. Sends binary audio chunks
3. Server broadcasts to receivers

#### `/ws/receiver` (Laptop Python Client)
Receives audio from server and plays through speakers

**Connection flow:**
1. Python client connects
2. Receives binary audio chunks
3. Plays through speakers

### HTTP Endpoints

#### `GET /` 
Returns the mobile web interface

#### `GET /health`
Returns server health status

**Response:**
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

#### `GET /stats`
Returns detailed connection statistics

**Response:**
```json
{
  "active_senders": 1,
  "active_receivers": 1,
  "connection_events": 10,
  "recent_connections": [...]
}
```

## 🛠️ Development

### Running Tests

```bash
pytest tests/ -v
```

### Enabling Debug Mode

```bash
# Set environment variable
export DEBUG=true

# Then start server
cd server && python main.py
```

### Adding New Features

1. **Add WebSocket endpoint** in `server/main.py`
2. **Update frontend** in `frontend/index.html`
3. **Test with receiver** using `receiver/receiver.py`
4. **Document changes** in README

## 📖 Architecture Overview

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│                   LOCAL WIFI NETWORK                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐              ┌────────────────────┐   │
│  │              │              │                    │   │
│  │   PHONE      │  WebSocket   │   LAPTOP           │   │
│  │              │◄─────────────►│                    │   │
│  │  - Browser   │   Audio      │  - Server (8000)   │   │
│  │  - Microphone│   Streaming  │  - Receiver.py     │   │
│  │  - "Hold to  │              │  - Speakers        │   │
│  │   Talk"      │              │                    │   │
│  │              │              │                    │   │
│  └──────────────┘              └────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘

Flow:
1. Phone microphone captures audio
2. Browser streams audio chunks via WebSocket
3. Server receives and broadcasts to all listeners
4. Receiver.py client gets audio chunks
5. Audio plays through laptop speakers
```

### Audio Flow

```
Phone Microphone
       ↓
MediaRecorder API (JavaScript)
       ↓
WebSocket to Server (ws://laptop:8000/ws/sender)
       ↓
FastAPI Server (broadcasts to receivers)
       ↓
WebSocket from Server (ws://laptop:8000/ws/receiver)
       ↓
Python Receiver Client
       ↓
sounddevice Library
       ↓
Laptop Speakers
```

## 🎓 Learning Resources

### Inside This Project

- **server/main.py** - Learn FastAPI, WebSockets, async Python
- **receiver/receiver.py** - Learn asyncio, audio I/O, websockets
- **frontend/index.html** - Learn MediaRecorder API, WebSockets in JavaScript

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [WebSockets Guide](https://websockets.readthedocs.io)
- [MediaRecorder API](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder)
- [sounddevice Documentation](https://python-sounddevice.readthedocs.io)
- [asyncio Guide](https://docs.python.org/3/library/asyncio.html)

## 🚀 Future Enhancements

See `VBAN_AND_AUDIO_NETWORKING_GUIDE.md` for detailed roadmap

Potential improvements:
- [ ] VBAN protocol support (VB-Audio)
- [ ] Multiple audio channels (stereo)
- [ ] Audio recording to file
- [ ] Web-based receiver dashboard
- [ ] Real-time audio visualization
- [ ] Noise cancellation
- [ ] Echo detection
- [ ] Bandwidth optimization
- [ ] Mobile app wrapper (Electron)
- [ ] Cloud deployment support

## 📄 License

This project is provided as-is for educational and personal use.

## 👥 Contributing

Feel free to:
- 🐛 Report bugs
- 💡 Suggest improvements
- 🔧 Submit pull requests
- 📝 Improve documentation

## 📞 Support

Having issues? Check:
1. 🔍 Troubleshooting section above
2. 📖 Server console logs
3. 📊 `curl localhost:8000/health`
4. 🔧 Receiver debug mode: `python receiver.py --debug`

## ✨ Credits

Built with:
- 🐍 Python & FastAPI
- 🌐 WebSockets & async/await
- 🎤 MediaRecorder API
- 🔊 sounddevice library

---

**Happy Announcing! 🎙️**

Made with ❤️ for local network audio streaming.
