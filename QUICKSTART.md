# 🚀 SwarSetu Quick Start Guide

Get SwarSetu running in under 5 minutes!

## Prerequisites

Before starting, make sure you have:
- ✅ Python 3.8 or higher installed
- ✅ Your laptop and phone on the same WiFi network
- ✅ A working microphone on your phone
- ✅ Working speakers on your laptop

## Step 1: Set Up Virtual Environment & Dependencies (1 min)

Open a terminal and run the commands for your operating system:

### On Windows:
```powershell
# Navigate to the SwarSetu directory
cd path/to/SwarSetu

# Create virtual environment
python -m venv venv

# Activate virtual environment (Command Prompt)
venv\Scripts\activate
# OR Activate virtual environment (PowerShell)
.\venv\Scripts\activate

# Initialize configuration
copy .env.example .env

# Install all required packages
pip install -r requirements.txt
```

### On Mac/Linux:
```bash
# Navigate to the SwarSetu directory
cd path/to/SwarSetu

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Initialize configuration
cp .env.example .env

# Install all required packages
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed fastapi uvicorn websockets sounddevice numpy...
```

## Step 2: Find Your Laptop's IP Address (1 min)

### On Windows:

Open Command Prompt and type:
```cmd
ipconfig
```

Look for your WiFi adapter and find the **IPv4 Address** (e.g., `192.168.1.100`)

### On Mac/Linux:

Open Terminal and type:
```bash
ifconfig
```

Look for your WiFi interface and find the **inet** address (e.g., `192.168.1.100`)

**Write down your IP address - you'll need it for your phone!**

## Step 3: Start the Server (1 min)

Open a terminal and run:

```bash
cd server
python main.py
```

You should see:
```
🎙️  SwarSetu Server Starting
============================================================
Server running on http://0.0.0.0:8000
```

✅ Leave this running!

## Step 4: Start the Receiver (1 min)

Open a **new terminal** and run:

```bash
cd receiver
python receiver.py
```

You should see:
```
✓ Connected to server
🎧 Listening for audio...
```

✅ Leave this running!

## Step 5: Open Phone Browser (1 min)

1. **On your phone**, open Chrome (Android) or Safari (iPhone)
2. In the address bar, type your laptop's IP: `http://192.168.1.100:8000`
3. Press Enter

**Wait for the page to load** - it should show:
- 🎙️ SwarSetu
- Green status: "Connected to Server"

✅ If you see this, you're ready!

## Step 6: Test Audio

1. **Make sure your speakers are ON and not muted**
2. **Allow microphone permission** when your phone asks
3. **Hold down the big mic button** and speak clearly
4. **Release the button**
5. **Listen** - your voice should play through your laptop speakers!

## 🎉 Success!

If you heard your voice through the speakers, **you did it!** 🎙️

### If it didn't work:

Check [Troubleshooting](#troubleshooting) section below.

---

## Example Commands by Operating System

### Windows Commands

```powershell
# Navigate to SwarSetu folder
cd C:\Users\YourUsername\SwarSetu

# Create virtual environment
python -m venv venv

# Activate virtual environment
# If using Command Prompt:
venv\Scripts\activate
# If using PowerShell:
.\venv\Scripts\activate

# Initialize configuration
copy .env.example .env

# Install dependencies
pip install -r requirements.txt

# Terminal 1: Start server
cd server
python main.py

# Terminal 2: Start receiver
cd receiver
python receiver.py

# Terminal 3: Check server health
curl http://localhost:8000/health
```

### Mac/Linux Commands

```bash
# Navigate to SwarSetu folder
cd ~/SwarSetu

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Initialize configuration
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Terminal 1: Start server
cd server
python3 main.py

# Terminal 2: Start receiver
cd receiver
python3 receiver.py

# Terminal 3: Check server health
curl http://localhost:8000/health
```

---

## Troubleshooting

### "Can't find Python"

**Solution:**
- Windows: Make sure Python is added to PATH during installation
- Mac/Linux: Use `python3` instead of `python`

### "Connection refused"

**Solutions:**
1. Make sure server is running in Terminal 1
2. Check you typed the IP correctly (not localhost)
3. Both devices must be on same WiFi

### "Microphone permission denied"

**Solutions:**
1. Tap "Allow" when the browser asks
2. Check browser settings:
   - Android Chrome: Settings > Apps > Permissions > Microphone
   - iPhone Safari: Settings > Safari > Microphone

### "No audio output"

**Solutions:**
1. Check receiver is running in Terminal 2
2. Make sure speakers are enabled and not muted
3. Try different output device: `python receiver.py --debug`

### "Port 8000 already in use"

**Solution:**
1. Kill the process using port 8000
2. Or change port in `server/config.py` (change `PORT = 9000`)

---

## 📱 Phone Connection Troubleshooting

### Phone can't find the server

| Problem | Solution |
|---------|----------|
| "Cannot reach server" | Use correct IP from `ipconfig` |
| "Failed to connect" | Both devices on same WiFi? |
| "Timeout" | Server running? Check Terminal 1 |
| "Connection refused" | Is port 8000 blocked? |

### Audio quality issues

| Problem | Solution |
|---------|----------|
| Delayed audio | Normal for WiFi, try moving closer |
| Audio cuts out | Server or receiver might have crashed |
| Echo/feedback | Move speaker away from microphone |
| Low volume | Check phone and laptop volume |

---

## Advanced Testing

### Check Server Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "active_senders": 1,
  "active_receivers": 1
}
```

### Debug Logging

```bash
# Start receiver with debug output
python receiver.py --debug

# Start server with debug mode
# Edit server/config.py: DEBUG=true
```

### Test from Different Machine

```bash
# From another computer on network
python receiver.py --host 192.168.1.100 --port 8000
```

---

## Next Steps

Once you have it working:

1. **Explore the code** - See `server/main.py` and `receiver/receiver.py`
2. **Read the guide** - Check `VBAN_AND_AUDIO_NETWORKING_GUIDE.md` for advanced topics
3. **Customize** - Edit `server/config.py` to adjust settings
4. **Extend** - Add new features or integrate with other systems

---

## Stopping SwarSetu

To stop all processes:

1. **Terminal 1 (server):** Press `Ctrl+C`
2. **Terminal 2 (receiver):** Press `Ctrl+C`
3. **Phone:** Just close the browser tab

All connections will close cleanly.

---

## Support

If you get stuck:

1. **Check README.md** - Comprehensive documentation
2. **Check VBAN guide** - Advanced networking concepts
3. **Enable debug mode** - More verbose logging
4. **Check server status** - `curl localhost:8000/health`

---

**You're all set! Start announcing!** 🎙️
