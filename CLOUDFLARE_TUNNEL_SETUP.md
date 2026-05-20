# 🌐 Cloudflare Tunnel Setup Guide for SwarSetu

To expose your local SwarSetu FastAPI server (running on your PC or Raspberry Pi) to the internet securely without port forwarding or exposing your IP address, you should use **Cloudflare Tunnel**.

This allows the frontend hosted on **Cloudflare Pages** (HTTPS) to connect to your local backend via a secure WebSocket (`wss://`) connection.

---

## 🛠️ Prerequisites
1. A free **Cloudflare Account**.
2. A **Custom Domain** added to your Cloudflare account (e.g., `yourdomain.com`).
3. Your local SwarSetu server running (typically on `http://localhost:8000`).

---

## 🚀 Option 1: Cloudflare Dashboard Method (Recommended & Easiest)

This method manages the tunnel configuration through the Cloudflare Zero Trust web dashboard. It is beginner-friendly and automatically handles installation as a system service.

### Step 1: Access Zero Trust Dashboard
1. Go to the [Cloudflare Dashboard](https://dash.cloudflare.com/) and log in.
2. Click on **Zero Trust** in the left sidebar.
3. If this is your first time, set up a team name (free of charge) and select the free plan.
4. Navigate to **Networks** ➔ **Tunnels** in the sidebar.
5. Click **Create a tunnel**.

### Step 2: Create and Name the Tunnel
1. Select **Cloudflare Tunnel (Connector)** and click Next.
2. Name your tunnel (e.g., `swarsetu-bridge`) and click **Save tunnel**.

### Step 3: Install the Connector on your PC/Raspberry Pi
Choose your operating system on the screen to view the custom command:

#### **For Raspberry Pi (Debian/Raspbian) / Linux PC:**
Copy the command provided by Cloudflare. It will look like this:
```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm.deb
sudo dpkg -i cloudflared.deb
sudo cloudflared service install eyJ... (your unique token)
```
*(Make sure to use the correct architecture: arm64/armhf for Pi, amd64 for PC)*

#### **For Windows:**
1. Download the Windows installer (`.msi`) from the link shown in the dashboard.
2. Open PowerShell as Administrator and run the install command shown in the dashboard, e.g.:
```powershell
cloudflared.exe service install eyJ... (your unique token)
```

Verify that the tunnel shows as **Active** or **Healthy** in the dashboard.

### Step 4: Route the Traffic (Create Public Hostname)
1. On the **Public Hostname** tab in the dashboard, click **Add a public hostname**.
2. Fill in the routing details:
   - **Subdomain**: e.g., `swarsetu`
   - **Domain**: Select your domain from the dropdown (e.g., `yourdomain.com`).
   - **Path**: Leave empty.
   - **Type**: Select **HTTP** (do NOT select HTTPS; the tunnel communicates with the local server over HTTP, and Cloudflare handles the HTTPS encryption on the public end).
   - **URL**: `localhost:8000` (or `127.0.0.1:8000`)
3. Click **Save hostname**.

Now, your server is accessible at `https://swarsetu.yourdomain.com` and its WebSocket is at `wss://swarsetu.yourdomain.com/ws/stream`.

---

## 💻 Option 2: Command Line (CLI) Method

If you prefer configuring tunnels directly via your machine's command line, follow these steps.

### Step 1: Install cloudflared
- **macOS**: `brew install cloudflare/cloudflare/cloudflared`
- **Linux/Pi**: `sudo apt-get install cloudflared`
- **Windows**: Download the binary from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases) and add it to your System PATH.

### Step 2: Login and Authenticate
Run the login command in your terminal:
```bash
cloudflared tunnel login
```
A browser window will open. Select your domain to authorize the connector.

### Step 3: Create the Tunnel
Run the creation command:
```bash
cloudflared tunnel create swarsetu-local
```
This generates a tunnel ID and a credentials file (`<TUNNEL-ID>.json`) stored in your `.cloudflared` directory.

### Step 4: Write Configuration File
Create a `config.yml` file in your `.cloudflared` directory (located at `~/.cloudflared/config.yml` on Linux/macOS or `%USERPROFILE%\.cloudflared\config.yml` on Windows):

```yaml
tunnel: <YOUR-TUNNEL-ID>
credentials-file: /absolute/path/to/.cloudflared/<YOUR-TUNNEL-ID>.json

ingress:
  - hostname: swarsetu.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

### Step 5: Route DNS to Your Domain
Map your subdomain to the tunnel:
```bash
cloudflared tunnel route dns swarsetu-local swarsetu.yourdomain.com
```

### Step 6: Start the Tunnel
Run your tunnel client:
```bash
cloudflared tunnel run swarsetu-local
```

---

## 🔗 Connecting the Frontend Web App

Once the tunnel is active:
1. Open your SwarSetu Frontend (hosted on Cloudflare Pages or run locally).
2. Open the **Connection Settings** drawer (the gear icon ⚙️).
3. Set the **Server WebSocket URL** to your tunnel subdomain, using the secure WebSocket protocol:
   `wss://swarsetu.yourdomain.com/ws/stream`
4. Click **Apply Settings**.
5. Click **Connect Server**. The indicator will turn green, indicating a live, encrypted voice bridge!
