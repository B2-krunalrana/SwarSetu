# 🔧 SwarSetu Complete Setup Guide

Detailed step-by-step setup instructions for Windows, Mac, and Linux.

## Table of Contents

- [System Requirements](#system-requirements)
- [Windows Setup](#windows-setup)
- [Mac Setup](#mac-setup)
- [Linux Setup](#linux-setup)
- [Verification Steps](#verification-steps)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Python | 3.8 or higher |
| RAM | 2 GB minimum |
| Storage | 500 MB free |
| Network | WiFi or Ethernet |

### Audio Requirements

| Component | Requirement |
|-----------|-------------|
| Laptop Speakers | Any working audio output |
| Phone Microphone | Any standard smartphone mic |
| Network | Same WiFi network |

### Browser Requirements (on Phone)

| Browser | OS | Status |
|---------|-----|--------|
| Chrome | Android 8+ | ✅ Full support |
| Safari | iOS 14+ | ✅ Full support |
| Firefox | Android | ⚠️ Not tested |
| Edge | Any | ⚠️ Not tested |

---

## Windows Setup

### Prerequisites

Before starting, install these on your Windows laptop:

1. **Python 3.8+**
2. **Git** (optional, for downloading SwarSetu)
3. **pip** (comes with Python)

### Step 1: Install Python

1. Download Python from https://www.python.org/downloads/
2. **Important:** Check "Add Python to PATH" during installation
3. Click "Install Now"

**Verify Installation:**

Open Command Prompt and type:
```cmd
python --version
```

Should show: `Python 3.x.x`

### Step 2: Download SwarSetu

Choose one of these methods:

**Method A: Using Git (Recommended)**

```cmd
# Open Command Prompt
cd C:\Users\YourUsername

# Clone the repository (if you have Git installed)
git clone https://github.com/yourusername/SwarSetu.git
cd SwarSetu
```

**Method B: Download ZIP**

1. Download SwarSetu as ZIP from GitHub
2. Extract to `C:\Users\YourUsername\SwarSetu`
3. Open Command Prompt in that folder

**Method C: Manual Setup**

Create folder `C:\Users\YourUsername\SwarSetu` and copy files there.

### Step 3: Create and Activate Virtual Environment

It is recommended to use a Python virtual environment to keep dependencies isolated:

```cmd
# Navigate to SwarSetu directory
cd C:\Users\YourUsername\SwarSetu

# Create virtual environment
python -m venv venv

# Activate virtual environment
# If using Command Prompt:
venv\Scripts\activate

# If using PowerShell:
.\venv\Scripts\activate
```

### Step 4: Set Up Environment Variables

Initialize your configuration file by copying the example environment file:

```cmd
# Copy the example .env file to create your active configuration
copy .env.example .env
```

### Step 5: Install Python Dependencies

With your virtual environment activated, install the required libraries:

```cmd
# Install dependencies
pip install -r requirements.txt
```

**Verify Installation:**

```cmd
python -c "import fastapi; import sounddevice; import websockets; print('✓ All dependencies installed')"
```

Should show: `✓ All dependencies installed`

### Step 6: Configure Firewall (if needed)

If Windows Firewall blocks Python:

1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Find Python and click "Allow"
4. Restart the server

### Step 7: Start Server

Open Command Prompt in SwarSetu folder:

```cmd
cd server
python main.py
```

**Expected output:**
```
🎙️  SwarSetu Server Starting
============================================================
Server running on http://0.0.0.0:8000
```

### Step 8: Start Receiver (New Command Prompt)

Open a **new** Command Prompt:

```cmd
cd C:\Users\YourUsername\SwarSetu\receiver
python receiver.py
```

**Expected output:**
```
✓ Connected to server
🎧 Listening for audio...
```

### Step 9: Find Your IP Address

In Command Prompt, type:

```cmd
ipconfig
```

Look for your WiFi adapter (usually "Wireless LAN adapter WiFi") and find:
```
IPv4 Address . . . . . . . . . . . : 192.168.1.100
```

Note this IP address!

### Step 10: Phone Setup

1. On your phone, open Chrome (Android) or Safari (iPhone)
2. Type in address bar: `http://192.168.1.100:8000`
3. Replace `192.168.1.100` with your laptop's IP from Step 9
4. Press Enter

---

## Mac Setup

### Prerequisites

Before starting, ensure you have:

1. **Python 3.8+**
2. **Homebrew** (optional, makes installation easier)
3. **Terminal** (built-in)

### Step 1: Install Python

**Using Homebrew (Recommended):**

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11
```

**Without Homebrew:**

Download from https://www.python.org/downloads/mac

### Step 2: Verify Python Installation

Open Terminal and type:

```bash
python3 --version
```

Should show: `Python 3.x.x`

### Step 3: Download SwarSetu

Open Terminal:

```bash
# Navigate to home directory
cd ~

# Clone SwarSetu
git clone https://github.com/yourusername/SwarSetu.git
cd SwarSetu
```

Or download ZIP and extract to `~/SwarSetu`

### Step 4: Create Virtual Environment (Optional but Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### Step 5: Set Up Environment Variables

Initialize your configuration file by copying the example environment file:

```bash
# Copy the example .env file to create your active configuration
cp .env.example .env
```

### Step 6: Install Dependencies

```bash
# Navigate to SwarSetu directory
cd ~/SwarSetu

# Install all requirements
pip3 install -r requirements.txt
```

**Verify:**

```bash
python3 -c "import fastapi; import sounddevice; print('✓ All installed')"
```

### Step 7: Allow Audio Permissions

macOS may ask for audio permissions:

1. When you first run the receiver, macOS will ask for microphone access
2. Click "Allow" or go to System Preferences > Security & Privacy
3. Allow Terminal/Python to access microphone and speakers

### Step 8: Start Server

Open Terminal:

```bash
cd ~/SwarSetu/server
python3 main.py
```

### Step 9: Start Receiver (New Terminal Tab)

Press `Cmd+T` to open new Terminal tab:

```bash
cd ~/SwarSetu/receiver
python3 receiver.py
```

### Step 10: Find Your IP Address

In Terminal, type:

```bash
ifconfig | grep inet
```

Look for your WiFi interface IP (usually `192.168.x.x`):

```
inet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255
```

### Step 11: Phone Setup

1. On your phone, open Safari
2. Type: `http://192.168.1.100:8000` (use your IP from Step 10)
3. Tap "Go"

---

## Linux Setup

### Prerequisites

Linux support requires:

1. **Python 3.8+**
2. **pip3**
3. **ALSA** (audio system)
4. **PortAudio** (optional, for better audio support)

### Step 1: Install Python and Dependencies

**Ubuntu/Debian:**

```bash
# Update package manager
sudo apt-get update

# Install Python and build tools
sudo apt-get install python3 python3-pip python3-dev

# Install audio libraries
sudo apt-get install libasound2-dev libportaudio2

# Install audio utilities
sudo apt-get install alsa-utils pulseaudio
```

**Fedora/RHEL:**

```bash
# Install Python
sudo dnf install python3 python3-devel python3-pip

# Install audio libraries
sudo dnf install alsa-lib-devel portaudio-devel
```

**Arch Linux:**

```bash
# Install Python
sudo pacman -S python python-pip base-devel

# Install audio libraries
sudo pacman -S alsa-lib portaudio
```

### Step 2: Verify Installation

```bash
python3 --version
pip3 --version
arecord --version
```

### Step 3: Download SwarSetu

```bash
# Clone repository
git clone https://github.com/yourusername/SwarSetu.git
cd SwarSetu

# Or extract ZIP file
cd ~/SwarSetu
```

### Step 4: Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate
```

### Step 5: Set Up Environment Variables

Initialize your configuration file by copying the example environment file:

```bash
# Copy the example .env file to create your active configuration
cp .env.example .env
```

### Step 6: Install Python Dependencies

```bash
# Install requirements
pip3 install -r requirements.txt
```

### Step 7: Configure Audio (if needed)

Check available audio devices:

```bash
# List audio devices
arecord -l
aplay -l
```

### Step 8: Add User to Audio Group (if needed)

```bash
# Add current user to audio group
sudo usermod -a -G audio $USER

# Log out and log back in for changes to take effect
```

### Step 9: Start Server

```bash
cd server
python3 main.py
```

### Step 10: Start Receiver (New Terminal)

```bash
cd receiver
python3 receiver.py
```

### Step 11: Find Your IP Address

```bash
# Find IP address
hostname -I

# Or use ifconfig if available
ifconfig
```

### Step 12: Phone Setup

1. Open browser on phone
2. Type: `http://192.168.x.x:8000` (use your IP)
3. Press Enter

---

## Verification Steps

After setup, verify everything is working:

### 1. Check Python Installation

```bash
# Windows
python --version

# Mac/Linux
python3 --version
```

Should show Python 3.8 or higher.

### 2. Check Dependencies

```bash
# Windows
pip list | find "fastapi"

# Mac/Linux
pip3 list | grep fastapi
```

Should show all required packages.

### 3. Test Server Connectivity

```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "status": "healthy",
  "active_senders": 0,
  "active_receivers": 0
}
```

### 4. Test Phone Connection

On your phone:
1. Open browser
2. Visit `http://LAPTOP_IP:8000`
3. Should see SwarSetu "Hold to Talk" interface
4. Connection status should show "Connected to Server"

### 5. Test Audio

1. Hold mic button on phone
2. Speak clearly
3. Release button
4. Listen for audio through laptop speakers

---

## Troubleshooting

### "Python not found" or "Command not recognized"

**Windows:**
- Python not added to PATH
- Solution: Reinstall Python and check "Add Python to PATH"

**Mac/Linux:**
- Using wrong command
- Solution: Use `python3` instead of `python`

### "Module not found" (numpy, sounddevice, etc.)

**Solution:**
```bash
# Reinstall all dependencies
pip install --upgrade -r requirements.txt

# Or for specific package
pip install sounddevice --upgrade
```

### "Port 8000 already in use"

**Solution 1:** Kill the process

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :8000
kill -9 <PID>
```

**Solution 2:** Use different port

Edit `server/config.py`:
```python
PORT = 9000  # Change this
```

### "Microphone permission denied" (Mac)

**Solution:**
1. Go to System Preferences > Security & Privacy
2. Click "Microphone"
3. Allow Python/Terminal
4. Restart server

### "No audio devices found" (Linux)

**Solution:**
1. Check audio devices: `aplay -l`
2. Install missing drivers: `sudo apt-get install alsa-base`
3. Restart PulseAudio: `pulseaudio --kill && pulseaudio --start`

### "Connection refused" on phone

**Solutions:**
1. Check server is running (see Terminal 1)
2. Verify IP address is correct
3. Check both devices on same WiFi
4. Try different network if using guest WiFi

### "Cannot detect microphone" on phone

**Solutions:**
1. Grant microphone permission to browser
2. Restart phone and browser
3. Check microphone is not muted
4. Try different browser (Chrome vs Safari)

### "Audio cutting out"

**Solutions:**
1. Move closer to WiFi router
2. Close other network-heavy apps
3. Reduce WiFi interference (fewer devices)
4. Use wired Ethernet if possible

---

## Environment Variables

Optional configuration via `.env` file:

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your settings
nano .env
```

Available variables:

```bash
SWARSETU_PORT=8000
AUDIO_SAMPLE_RATE=16000
DEBUG=false
LOG_LEVEL=INFO
```

---

## Getting Help

If you're still stuck:

1. Check the **Troubleshooting** section above
2. Read `README.md` for more details
3. Enable debug logging: `python receiver.py --debug`
4. Check server health: `curl localhost:8000/health`
5. Review server logs in Terminal 1

---

## Next Steps

Once everything is working:

1. **Customize** - Edit `server/config.py`
2. **Explore** - Read the code and comments
3. **Extend** - Add new features
4. **Learn** - Check VBAN guide for advanced topics

---

**You're ready! Start announcing!** 🎙️
