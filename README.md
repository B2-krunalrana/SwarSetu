# 🎙️ SwarSetu - Live Voice Bridge System

**SwarSetu** ("Swar" = Voice/Sound, "Setu" = Bridge) is a lightweight, low-latency real-time voice broadcasting application. It allows you to speak into your smartphone microphone via a web browser and instantly hear your voice play back on a remote Raspberry Pi or PC speaker.

The system acts like a walkie-talkie, intercom, or live announcement setup. It uses raw PCM streaming over WebSockets to deliver near zero-latency audio playback without heavy container encodings.

---

## 📐 Architecture Overview

```
[Phone Browser (Cloudflare Pages)]
               ↓
    (Secure WebSocket - WSS)
               ↓
      [Cloudflare Tunnel]
               ↓
   [FastAPI Server (Pi/PC)]
               ↓
     (sounddevice / NumPy)
               ↓
       [Local Speakers]
```

1. **Frontend**: Captures raw audio via the browser's `AudioContext` and `AudioWorklet` APIs, transforms the Float32 microphone data into 16-bit PCM bytes, and sends the raw binary chunks over WebSockets.
2. **Networking**: Uses **Cloudflare Tunnel** to securely map a public domain (`wss://...`) to the local port without port forwarding or exposing router ports.
3. **Backend**: FastAPI receives binary frames on a WebSocket socket, queues them in a thread-safe buffer, and plays them instantly in a background worker thread via `sounddevice` and `numpy`.

---

## 📁 Folder Structure

```
SwarSetu/
├── server/                   # Python Backend
│   ├── __init__.py
│   ├── config.py            # Centralized settings (sample rate, etc.)
│   └── main.py              # FastAPI server & audio playback thread
├── frontend/                 # Web Interface (host on Cloudflare Pages)
│   ├── index.html           # App page layout
│   ├── style.css            # Glowing dark-mode walkie-talkie styling
│   ├── app.js               # Audio pipeline, WS life cycle, & visualizer
│   └── audio-processor.js   # Worklet audio processor file (fallback)
├── requirements.txt         # Python libraries
├── CLOUDFLARE_TUNNEL_SETUP.md # Detailed tunnel mapping instructions
└── README.md                # General setup and deployment guide
```

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Python Dependencies
Open your terminal inside the `SwarSetu` folder and run:

**On Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv venv
# Activate virtual environment
.\venv\Scripts\activate
# Install requirements
pip install -r requirements.txt
```

**On Linux / Raspberry Pi:**
```bash
# Install system audio dependency (often required for PortAudio/sounddevice)
sudo apt-get install portaudio19-dev python3-pyaudio

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

### Step 2: Start the Backend Server
Run the FastAPI application from the project root:

```bash
python server/main.py
```

#### Audio Device Configuration:
If your machine has multiple speakers or sound cards (e.g. HDMI vs 3.5mm jack), you can list devices and bind to a specific one:

```bash
# List available audio interfaces
python server/main.py --list-devices

# Run binding to device ID 2 (or a specific device name)
python server/main.py --device 2
# Or by name
python server/main.py --device "External"
```

---

### Step 3: Run the Web Frontend (Two Options)

#### Option A: Local Network Testing
The FastAPI backend is pre-configured to host the frontend assets locally for testing.
1. Find your machine's local IP address (e.g., `192.168.1.100` via `ipconfig` on Windows or `ifconfig` on Linux).
2. Open a web browser on a smartphone or laptop connected to the **same WiFi network**.
3. Navigate to: `http://192.168.1.100:8000`.
4. Open the **Connection Settings** (gear icon ⚙️), ensure the URL points to your server (e.g. `ws://192.168.1.100:8000/ws/stream`), click **Apply Settings**, and press **Connect Server**.

#### Option B: Cloudflare Pages Deployment (Production)
1. Push the `frontend` folder to a GitHub repository.
2. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/) ➔ **Workers & Pages** ➔ **Create Application** ➔ **Pages** ➔ **Connect to Git**.
3. Select your repository. Set the **Build Command** to empty (static site), and **Output directory** to `frontend`. Click Deploy.
4. Set up a **Cloudflare Tunnel** for your backend (see [CLOUDFLARE_TUNNEL_SETUP.md](file:///d:/SwarSetu-app/SwarSetu/CLOUDFLARE_TUNNEL_SETUP.md)) so you can map your local server to a secure URL (e.g., `wss://swarsetu.yourdomain.com/ws/stream`).
5. Open your Cloudflare Pages URL on your phone, open the Settings menu, paste your secure WebSocket URL, click Save, and speak!

---

## 🎙️ Using SwarSetu

1. Click **Connect Server**. The top status dot will turn green (`Connected`).
2. **Grant Microphone Permission** to the browser when prompted.
3. Choose your preferred broadcasting mode:
   - **Push-To-Talk (PTT)**: Press and hold the big circular mic button to stream your voice. Release it to stop.
   - **Continuous**: Tap the mic button once to toggle continuous streaming on ("ON AIR"). Tap again to toggle off.
4. Look at the canvas visualizer: it displays a live audio wave when capturing sound.

---

## ⚡ Performance Optimizations

If you experience audio cracks, pops, or latency:
- **Change Chunk Size**: Open settings (gear icon) and increase the chunk size to `2048` or `4096` for better stability on unstable connections, or decrease to `512` for lower latency.
- **WiFi Quality**: Ensure your device has strong WiFi signal strength.
- **Tunnels**: Make sure your Cloudflare Tunnel is hosted in a region close to your physical location to minimize round-trip times.
