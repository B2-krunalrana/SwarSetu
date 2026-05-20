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
├── frontend/                 # React PWA Frontend
│   ├── public/              # PWA assets & app icons
│   ├── src/                 # React source code
│   │   ├── App.jsx          # Main client UI & audio streaming logic
│   │   ├── index.css        # Walkie-talkie styling & animations
│   │   └── main.jsx         # React entrypoint
│   ├── index.html           # HTML template
   ├── vite.config.js       # Vite config (React + PWA plugin)
   └── package.json         # Frontend dependencies
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

### Step 2: Build the React PWA Frontend
The FastAPI backend serves the React application directly. You must first install dependencies and compile the production build:
```bash
# Navigate to the frontend folder
cd frontend

# Install node dependencies
npm install

# Compile the optimized production build with PWA features
npm run build

# Return to root directory
cd ..
```

---

### Step 3: Start the Backend Server (Two Options)

#### Option A: Local Network (LAN) Testing (Using Self-Signed SSL)
Modern mobile browsers require a secure context (HTTPS) to allow microphone access. You can easily set this up on your local network:

1. **Find your machine's local IP address**:
   - **Windows**: Run `ipconfig` in Command Prompt (look for "IPv4 Address" under your Wi-Fi/Ethernet adapter, e.g., `192.168.1.100`).
   - **Linux / Raspberry Pi**: Run `ifconfig` or `ip a` (look for `inet`, e.g., `192.168.1.100`).

2. **Generate a local self-signed SSL certificate** using OpenSSL:
   ```bash
   # In Git Bash or MSYS2 (Windows), use a double slash to prevent path conversion:
   openssl req -newkey rsa:2048 -new -nodes -x509 -days 365 -keyout key.pem -out cert.pem -subj "//CN=SwarSetu"
   
   # Or run interactively (press Enter to accept defaults):
   openssl req -newkey rsa:2048 -new -nodes -x509 -days 365 -keyout key.pem -out cert.pem
   ```
   *(This creates `key.pem` and `cert.pem` files in your active folder)*

3. **Start the FastAPI backend with the SSL keys**:
   ```bash
   python server/main.py --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```
   *(If you want to play audio through a specific speaker card, run `python server/main.py --list-devices` first, then run starting with `--device <id>`)*

4. **Connect from your smartphone**:
   - Open your browser on a phone connected to the **same WiFi network**.
   - Navigate to `https://<YOUR-PC-IP>:8000` (e.g., `https://192.168.1.100:8000`).
   - *Note:* Since the certificate is self-signed, click **Advanced** and select **Proceed to <IP> (unsafe)**.
   - Once loaded, click **Connect Server**, accept the microphone permission, and start broadcasting! The app automatically resolves the secure WebSocket port (`wss://<YOUR-PC-IP>:8000/ws/stream`) under the HTTPS context.

#### Option B: Cloudflare Pages Deployment (Production)
1. Push your repository (including `frontend/` and `server/` folders) to GitHub.
2. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/) ➔ **Workers & Pages** ➔ **Create Application** ➔ **Pages** ➔ **Connect to Git**.
3. Select your repository. Configure the following build settings:
   - **Root directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output directory**: `dist`
   - Click **Save and Deploy**.
4. Set up a **Cloudflare Tunnel** for your backend (see [CLOUDFLARE_TUNNEL_SETUP.md](file:///d:/SwarSetu-app/SwarSetu/CLOUDFLARE_TUNNEL_SETUP.md)) so you can map your local server to a secure WebSocket (`wss://swarsetu.yourdomain.com/ws/stream`).
5. Open your Cloudflare Pages URL on your phone, click **Connect Server**, grant mic permission, and speak!

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
