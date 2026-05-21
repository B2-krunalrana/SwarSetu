import sys
import os
import socket
import threading
import queue
import time
import webbrowser
import logging
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta

# Handle PyInstaller paths
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Insert the server directory into the path so config and main imports work
sys.path.insert(0, os.path.join(bundle_dir, "server"))

# Thread-safe queue for logs
log_queue = queue.Queue()

# Intercept byte-level writes when stdout/stderr buffer is wrapped (e.g. by TextIOWrapper)
class BinaryWriteStream:
    def __init__(self, q, original_buffer):
        self.q = q
        self.original_buffer = original_buffer
    def write(self, b):
        if b:
            try:
                # Decode bytes to text and enqueue for GUI
                text = b.decode("utf-8", errors="replace")
                self.q.put(text)
            except Exception:
                pass
            try:
                self.original_buffer.write(b)
            except Exception:
                pass
    def flush(self):
        try:
            self.original_buffer.flush()
        except Exception:
            pass
    def readable(self):
        return False
    def writable(self):
        return True
    def seekable(self):
        return False
    @property
    def closed(self):
        return False

# Thread-safe write stream to redirect stdout/stderr to both GUI and console
class WriteStream:
    def __init__(self, q, original_stream):
        self.q = q
        self.original_stream = original_stream
        if hasattr(original_stream, "buffer") and original_stream.buffer:
            self.buffer = BinaryWriteStream(q, original_stream.buffer)
    def write(self, text):
        if text:
            self.q.put(text)
            try:
                self.original_stream.write(text)
            except Exception:
                pass
    def flush(self):
        try:
            self.original_stream.flush()
        except Exception:
            pass
    def readable(self):
        return False
    def writable(self):
        return True
    def seekable(self):
        return False
    @property
    def closed(self):
        return False

# Configure logging before importing server.main to intercept logs
sys.stdout = WriteStream(log_queue, sys.__stdout__)
sys.stderr = WriteStream(log_queue, sys.__stderr__)

# Set up logging to push to our queue
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SwarSetu")
queue_handler = logging.StreamHandler(sys.stdout)
queue_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(queue_handler)

# Import backend dependencies after path redirection
try:
    import numpy as np
    import sounddevice as sd
    import uvicorn
    import qrcode
    from PIL import Image, ImageTk
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    import ipaddress
except Exception as e:
    # Print to actual stderr in case GUI has not loaded yet
    sys.__stderr__.write(f"Import error: {e}\n")
    sys.exit(1)

# Configuration Helpers
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".swarsetu_config.json")

def read_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def write_config(config_data):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to write config: {e}")

# Helper: Bind button hover effects
def bind_hover(btn, normal_bg, hover_bg, normal_fg, hover_fg):
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg, fg=hover_fg) if btn.cget("state") != "disabled" else None)
    btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg, fg=normal_fg) if btn.cget("state") != "disabled" else None)

# Helper: Get Local LAN IP Address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to connect, just opens a socket to resolve internal IP routing
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Helper: Auto-generate self-signed SSL Certificate for local secure context (HTTPS)
def ensure_ssl_certs(cert_path="cert.pem", key_path="key.pem"):
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path
    
    logger.info("SSL certificates not found. Generating self-signed certificates...")
    try:
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        local_ip = get_local_ip()
        
        # Build self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"SwarSetu"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow() - timedelta(days=1)
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=3650)  # 10 years validity
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
                x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address(local_ip)),
            ]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        # Write private key file
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
            
        # Write cert file
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(
                encoding=serialization.Encoding.PEM,
            ))
            
        logger.info("Successfully generated cert.pem and key.pem.")
        return cert_path, key_path
    except Exception as e:
        logger.error(f"Failed to generate SSL certificate: {e}")
        messagebox.showerror("SSL Error", f"Failed to generate SSL certificates: {e}")
        sys.exit(1)

# Import the FastAPI app
try:
    from server.main import app
except Exception as e:
    logger.error(f"Failed to load server.main: {e}")
    sys.exit(1)

# Color Constants for Rich Aesthetics
BG_DARK = "#090d16"      # Deep space blue-black
BG_CARD = "#151b2c"      # Dark slate card background
FG_LIGHT = "#f8fafc"     # High-contrast white/slate 50
FG_MUTED = "#64748b"     # Muted gray/slate 400
ACCENT = "#06b6d4"       # Cyber Cyan
ACCENT_HOVER = "#0891b2" # Deep Cyan
EMERALD = "#10b981"      # Pulse green
RED = "#ef4444"          # Warning red
BORDER = "#1e293b"       # Card border

class WelcomeFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        
        # Canvas for animated logo
        self.canvas = tk.Canvas(self, width=200, height=200, bg=BG_DARK, bd=0, highlightthickness=0)
        self.canvas.pack(pady=(40, 20))
        
        # Title
        title_label = tk.Label(self, text="SwarSetu", font=("Segoe UI", 28, "bold"), fg=ACCENT, bg=BG_DARK)
        title_label.pack(pady=5)
        
        # Subtitle
        subtitle_label = tk.Label(self, text="Real-Time Voice Bridge", font=("Segoe UI", 12, "bold"), fg=FG_LIGHT, bg=BG_DARK)
        subtitle_label.pack(pady=(0, 20))
        
        # Description Card
        desc_card = tk.Frame(self, bg=BG_CARD, bd=1, relief="flat", highlightbackground=BORDER, highlightthickness=1)
        desc_card.pack(fill="x", padx=30, pady=10)
        
        desc_text = (
            "SwarSetu bridges your mobile browser's microphone "
            "directly to your PC speakers in real-time over Wi-Fi.\n\n"
            "• Zero cables or external apps required\n"
            "• Secure local connection via SSL (HTTPS)\n"
            "• Ultra-low latency voice broadcasting"
        )
        desc_label = tk.Label(desc_card, text=desc_text, font=("Segoe UI", 10), fg=FG_LIGHT, bg=BG_CARD, justify="left", wraplength=400, padx=15, pady=15)
        desc_label.pack()
        
        # Button
        self.start_btn = tk.Button(
            self,
            text="Get Started  ➔",
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT,
            fg=BG_DARK,
            activebackground=ACCENT_HOVER,
            activeforeground=BG_DARK,
            bd=0,
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=controller.show_permissions
        )
        self.start_btn.pack(pady=40)
        bind_hover(self.start_btn, ACCENT, ACCENT_HOVER, BG_DARK, BG_DARK)
        
        # Logo pulse animation attributes
        self.logo_pulse_radius = 40
        self.pulse_dir = 1
        self.animate_logo()
        
    def animate_logo(self):
        if not self.winfo_exists():
            return
        
        self.canvas.delete("all")
        
        # Draw expanding wave rings
        # Outer ring
        r = self.logo_pulse_radius
        self.canvas.create_oval(100 - r, 100 - r, 100 + r, 100 + r, outline=ACCENT, width=2)
        
        # Inner ring
        r2 = (r - 20)
        if r2 > 10:
            self.canvas.create_oval(100 - r2, 100 - r2, 100 + r2, 100 + r2, outline=EMERALD, width=1)
            
        # Draw microphone silhouette inside the circle
        # Mic capsule
        self.canvas.create_oval(85, 60, 115, 90, fill=BG_CARD, outline=ACCENT, width=3)
        self.canvas.create_rectangle(85, 75, 115, 110, fill=BG_CARD, outline=ACCENT, width=3)
        self.canvas.create_line(86, 75, 114, 75, fill=BG_CARD, width=3) # remove overlapping line
        self.canvas.create_line(86, 90, 114, 90, fill=FG_LIGHT, width=2) # grid line
        
        # U-shaped neck
        self.canvas.create_arc(75, 75, 125, 125, start=180, extent=180, outline=FG_LIGHT, width=3, style="arc")
        
        # Base
        self.canvas.create_line(100, 125, 100, 145, fill=FG_LIGHT, width=4)
        self.canvas.create_line(80, 145, 120, 145, fill=FG_LIGHT, width=4)
        
        # Update radius
        self.logo_pulse_radius += 1 * self.pulse_dir
        if self.logo_pulse_radius >= 75:
            self.pulse_dir = -1
        elif self.logo_pulse_radius <= 40:
            self.pulse_dir = 1
            
        self.after(50, self.animate_logo)


class PermissionsFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        
        # Title
        title_label = tk.Label(self, text="System Permissions", font=("Segoe UI", 20, "bold"), fg=ACCENT, bg=BG_DARK)
        title_label.pack(pady=(30, 10))
        
        desc_label = tk.Label(
            self,
            text="Please review the network and hardware requirements to run the voice bridge:",
            font=("Segoe UI", 10),
            fg=FG_MUTED,
            bg=BG_DARK,
            wraplength=440,
            justify="center"
        )
        desc_label.pack(pady=(0, 20))
        
        # Cards for Requirements
        requirements = [
            ("📡 Local Network Access", "Allows other devices on your Wi-Fi/LAN network to connect to this server on Port 8000. Firewall permission might be prompted."),
            ("🔒 Local SSL (HTTPS) Context", "Generates self-signed SSL certificates automatically. Secure context is mandatory for browsers to allow microphone streaming."),
            ("🔊 Audio Playback Speaker", "Accesses your system speaker outputs to play the voice streams received from client browser in real-time.")
        ]
        
        for title, desc in requirements:
            card = tk.Frame(self, bg=BG_CARD, bd=1, relief="flat", highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", padx=30, pady=6)
            
            lbl_title = tk.Label(card, text=title, font=("Segoe UI", 11, "bold"), fg=ACCENT, bg=BG_CARD, anchor="w")
            lbl_title.pack(fill="x", padx=15, pady=(10, 2))
            
            lbl_desc = tk.Label(card, text=desc, font=("Segoe UI", 9), fg=FG_LIGHT, bg=BG_CARD, justify="left", wraplength=400, anchor="w")
            lbl_desc.pack(fill="x", padx=15, pady=(0, 10))
            
        # Agreement section
        self.agree_var = tk.BooleanVar(value=False)
        
        agree_frame = tk.Frame(self, bg=BG_DARK)
        agree_frame.pack(fill="x", padx=30, pady=25)
        
        self.agree_check = tk.Checkbutton(
            agree_frame,
            text="I authorize these requirements and want to continue",
            variable=self.agree_var,
            font=("Segoe UI", 10, "bold"),
            fg=FG_LIGHT,
            bg=BG_DARK,
            activeforeground=ACCENT,
            activebackground=BG_DARK,
            selectcolor=BG_CARD,
            bd=0,
            command=self.toggle_next_btn
        )
        self.agree_check.pack(anchor="center")
        
        # Buttons frame (Back and Next)
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=30, pady=10)
        
        self.back_btn = tk.Button(
            btn_frame,
            text="Back",
            font=("Segoe UI", 11, "bold"),
            bg=BORDER,
            fg=FG_LIGHT,
            activebackground="#334155",
            activeforeground=FG_LIGHT,
            bd=0,
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=controller.show_welcome
        )
        self.back_btn.pack(side="left", padx=5)
        bind_hover(self.back_btn, BORDER, "#334155", FG_LIGHT, FG_LIGHT)
        
        self.next_btn = tk.Button(
            btn_frame,
            text="Continue  ➔",
            font=("Segoe UI", 11, "bold"),
            bg=FG_MUTED,
            fg=BG_DARK,
            bd=0,
            relief="flat",
            padx=25,
            pady=8,
            state="disabled",
            command=controller.show_loader
        )
        self.next_btn.pack(side="right", padx=5)
        
    def toggle_next_btn(self):
        if self.agree_var.get():
            self.next_btn.config(state="normal", bg=ACCENT, cursor="hand2")
            bind_hover(self.next_btn, ACCENT, ACCENT_HOVER, BG_DARK, BG_DARK)
        else:
            self.next_btn.config(state="disabled", bg=FG_MUTED, cursor="arrow")
            self.next_btn.unbind("<Enter>")
            self.next_btn.unbind("<Leave>")


class LoaderFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        
        # Title
        title_label = tk.Label(self, text="Setting Up SwarSetu", font=("Segoe UI", 20, "bold"), fg=ACCENT, bg=BG_DARK)
        title_label.pack(pady=(60, 20))
        
        # Loading Card
        card = tk.Frame(self, bg=BG_CARD, bd=1, relief="flat", highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=30, pady=10)
        
        # Status rows list
        self.status_labels = []
        steps = [
            "🔒 Generating SSL certificates...",
            "🔊 Querying audio output devices...",
            "🚀 Starting local voice bridge server..."
        ]
        
        for step in steps:
            lbl = tk.Label(card, text=f"  ⌛  {step}", font=("Segoe UI", 11), fg=FG_MUTED, bg=BG_CARD, anchor="w")
            lbl.pack(fill="x", padx=20, pady=12)
            self.status_labels.append((step, lbl))
            
        # Custom Canvas Progress Bar
        self.progress_canvas = tk.Canvas(self, width=380, height=12, bg=BG_CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
        self.progress_canvas.pack(pady=40)
        
        # Draw background of progress bar
        self.progress_canvas.create_rectangle(0, 0, 380, 12, fill=BG_CARD, outline="")
        self.progress_fill = self.progress_canvas.create_rectangle(0, 0, 0, 12, fill=ACCENT, outline="")
        
        self.progress_percent = 0
        self.current_step_idx = 0
        
    def start_loading(self):
        self.progress_percent = 0
        self.current_step_idx = 0
        self.update_progress()
        
    def update_progress(self):
        if not self.winfo_exists():
            return
        
        # Fill progress bar smoothly
        self.progress_percent += 2
        fill_width = int((self.progress_percent / 100) * 380)
        self.progress_canvas.coords(self.progress_fill, 0, 0, fill_width, 12)
        
        # Update text/colors based on step progression
        # Step 1: SSL generation (completed at 30%)
        if self.progress_percent >= 30 and self.current_step_idx == 0:
            step_text, label = self.status_labels[0]
            label.config(text=f"  ✓  {step_text.replace('Generating', 'Generated')}", fg=EMERALD)
            self.controller.cert_path, self.controller.key_path = ensure_ssl_certs()
            self.current_step_idx = 1
            
        # Step 2: Speaker query (completed at 60%)
        elif self.progress_percent >= 60 and self.current_step_idx == 1:
            step_text, label = self.status_labels[1]
            label.config(text=f"  ✓  {step_text.replace('Querying', 'Refreshed')}", fg=EMERALD)
            self.controller.refresh_devices()
            self.current_step_idx = 2
            
        # Step 3: Server startup (completed at 90%)
        elif self.progress_percent >= 90 and self.current_step_idx == 2:
            step_text, label = self.status_labels[2]
            label.config(text=f"  ✓  {step_text.replace('Starting', 'Started')}", fg=EMERALD)
            self.controller.start_server_thread()
            self.current_step_idx = 3
            
        if self.progress_percent < 100:
            self.after(40, self.update_progress)
        else:
            self.controller.complete_setup()


class SwarSetuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎙️ SwarSetu Voice Bridge")
        self.root.geometry("520x790")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)
        
        # Configure app font
        self.root.option_add('*font', ('Segoe UI', 10))
        
        self.local_ip = get_local_ip()
        self.port = 8000
        self.server_url = f"https://{self.local_ip}:{self.port}"
        
        # Audio device lists
        self.audio_devices = []
        self.default_device_idx = None
        
        self.cert_path = None
        self.key_path = None
        
        self.pulse_state = True
        
        # Set up styles
        self.setup_styles()
        
        # Read Config
        self.config = read_config()
        self.setup_completed = self.config.get("setup_completed", False)
        
        # Create container for frames
        self.container = tk.Frame(self.root, bg=BG_DARK)
        self.container.pack(fill="both", expand=True)
        
        # Exit handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        if self.setup_completed:
            self.run_direct_setup()
            self.show_dashboard()
        else:
            self.show_welcome()
            
    def run_direct_setup(self):
        self.cert_path, self.key_path = ensure_ssl_certs()
        self.refresh_devices()
        self.start_server_thread()
        
    def show_welcome(self):
        self.clear_container()
        self.welcome_frame = WelcomeFrame(self.container, self)
        self.welcome_frame.pack(fill="both", expand=True)
        
    def show_permissions(self):
        self.clear_container()
        self.permissions_frame = PermissionsFrame(self.container, self)
        self.permissions_frame.pack(fill="both", expand=True)
        
    def show_loader(self):
        self.clear_container()
        self.loader_frame = LoaderFrame(self.container, self)
        self.loader_frame.pack(fill="both", expand=True)
        self.loader_frame.start_loading()
        
    def show_dashboard(self):
        self.clear_container()
        self.dashboard_frame = tk.Frame(self.container, bg=BG_DARK)
        self.dashboard_frame.pack(fill="both", expand=True)
        self.create_widgets(self.dashboard_frame)
        self.refresh_devices()
        
        # Start GUI updates
        self.poll_logs()
        self.poll_stats()
        self.animate_pulse()
        
    def clear_container(self):
        for child in self.container.winfo_children():
            child.destroy()
            
    def complete_setup(self):
        self.config["setup_completed"] = True
        write_config(self.config)
        self.show_dashboard()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Combobox dark-mode styling
        self.style.configure(
            "TCombobox",
            fieldbackground=BG_CARD,
            background=BORDER,
            foreground=FG_LIGHT,
            arrowcolor=FG_LIGHT,
            bordercolor=BORDER,
            darkcolor=BORDER,
            lightcolor=BORDER
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[('readonly', BG_CARD)],
            foreground=[('readonly', FG_LIGHT)]
        )
        
    def create_widgets(self, parent):
        # --- Top Header ---
        header_frame = tk.Frame(parent, bg=BG_DARK)
        header_frame.pack(fill="x", padx=24, pady=(20, 10))
        
        title_label = tk.Label(
            header_frame,
            text="🎙️ SwarSetu",
            font=("Segoe UI", 24, "bold"),
            bg=BG_DARK,
            fg=ACCENT
        )
        title_label.pack(anchor="w")
        
        subtitle_label = tk.Label(
            header_frame,
            text="Real-Time Voice Broadcasting System Server",
            font=("Segoe UI", 10),
            bg=BG_DARK,
            fg=FG_MUTED
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))
        
        # Divider Line
        divider = tk.Frame(parent, height=1, bg=BORDER)
        divider.pack(fill="x", padx=24, pady=10)
        
        # --- Main Console Card ---
        card = tk.Frame(parent, bg=BG_CARD, bd=1, relief="flat", highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=24, pady=10)
        
        # QR Code Frame Container
        qr_container = tk.Frame(card, bg=BG_CARD)
        qr_container.pack(pady=(20, 10))
        
        # Render QR Code
        try:
            qr_img = self.generate_qr_image(self.server_url)
            self.qr_photo = ImageTk.PhotoImage(qr_img)
            self.qr_label = tk.Label(qr_container, image=self.qr_photo, bg=BG_CARD, bd=0, highlightthickness=0)
            self.qr_label.pack()
        except Exception as e:
            self.qr_label = tk.Label(qr_container, text=f"[QR Generation Error: {e}]", fg=RED, bg=BG_CARD)
            self.qr_label.pack()
            logger.error(f"QR code render failed: {e}")
            
        # Address Details
        address_label = tk.Label(
            card,
            text="Scan QR code with your phone to broadcast voice",
            font=("Segoe UI", 10, "italic"),
            bg=BG_CARD,
            fg=FG_MUTED
        )
        address_label.pack()
        
        url_frame = tk.Frame(card, bg=BG_CARD)
        url_frame.pack(pady=10)
        
        self.url_display = tk.Entry(
            url_frame,
            font=("Consolas", 11, "bold"),
            bg=BG_DARK,
            fg=FG_LIGHT,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            justify="center",
            width=28
        )
        self.url_display.insert(0, self.server_url)
        self.url_display.config(state="readonly")
        self.url_display.pack(side="left", padx=(0, 5), ipady=4)
        
        self.copy_btn = tk.Button(
            url_frame,
            text="📋 Copy",
            font=("Segoe UI", 9, "bold"),
            bg=ACCENT,
            fg=BG_DARK,
            activebackground=ACCENT_HOVER,
            activeforeground=BG_DARK,
            bd=0,
            relief="flat",
            padx=10,
            cursor="hand2",
            command=self.copy_url
        )
        self.copy_btn.pack(side="left", ipady=4)
        
        # Instructions Warning Box
        ssl_warn_frame = tk.Frame(card, bg=BG_CARD)
        ssl_warn_frame.pack(fill="x", padx=20, pady=5)
        ssl_warn_label = tk.Label(
            ssl_warn_frame,
            text="⚠️ Note: Skip the SSL/Self-signed cert warning on your phone's browser\n(click 'Advanced' -> 'Proceed'). Required to enable microphone access.",
            font=("Segoe UI", 8),
            justify="center",
            bg=BG_CARD,
            fg=FG_MUTED
        )
        ssl_warn_label.pack()
 
        # --- Audio Device Selector Panel ---
        device_frame = tk.Frame(card, bg=BG_CARD)
        device_frame.pack(fill="x", padx=20, pady=10)
        
        device_title = tk.Label(
            device_frame,
            text="🔊 Playback Output Speaker Device:",
            font=("Segoe UI", 10, "bold"),
            bg=BG_CARD,
            fg=FG_LIGHT
        )
        device_title.pack(anchor="w", pady=(0, 5))
        
        combo_container = tk.Frame(device_frame, bg=BG_CARD)
        combo_container.pack(fill="x")
        
        self.device_combo = ttk.Combobox(combo_container, state="readonly", font=("Segoe UI", 9))
        self.device_combo.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_changed)
        
        refresh_btn = tk.Button(
            combo_container,
            text="🔄",
            bg=BORDER,
            fg=FG_LIGHT,
            activebackground="#334155",
            activeforeground=FG_LIGHT,
            bd=0,
            relief="flat",
            padx=8,
            cursor="hand2",
            command=self.refresh_devices
        )
        refresh_btn.pack(side="right")
        
        # --- Connection Stats Dashboard ---
        stats_frame = tk.Frame(card, bg=BG_CARD)
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        # Left Stat
        self.status_indicator = tk.Label(
            stats_frame,
            text="●",
            font=("Segoe UI", 14),
            bg=BG_CARD,
            fg=EMERALD
        )
        self.status_indicator.pack(side="left", padx=(0, 5))
        
        self.status_txt = tk.Label(
            stats_frame,
            text="Server Live | Active Connections: 0",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=FG_LIGHT
        )
        self.status_txt.pack(side="left")
        
        # Right Stat
        self.packet_txt = tk.Label(
            stats_frame,
            text="Packets: 0 (0.0 MB)",
            font=("Segoe UI", 9),
            bg=BG_CARD,
            fg=FG_MUTED
        )
        self.packet_txt.pack(side="right")
        
        # --- Developer Log Console ---
        console_frame = tk.Frame(parent, bg=BG_DARK)
        console_frame.pack(fill="both", expand=True, padx=24, pady=(10, 20))
        
        console_label = tk.Label(
            console_frame,
            text="🖥️ Server Activity Logs",
            font=("Segoe UI", 10, "bold"),
            bg=BG_DARK,
            fg=FG_LIGHT
        )
        console_label.pack(anchor="w", pady=(0, 5))
        
        self.log_area = scrolledtext.ScrolledText(
            console_frame,
            font=("Consolas", 8),
            bg="#030712",
            fg="#10b981",
            insertbackground="white",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            padx=10,
            pady=10
        )
        self.log_area.pack(fill="both", expand=True)
        
        # Insert greeting log
        self.log_area.insert(tk.END, "=== SwarSetu Desktop Service Initialized ===\n")
        self.log_area.insert(tk.END, f"Host LAN IP address: {self.local_ip}\n")
        self.log_area.insert(tk.END, f"Local Server URL: {self.server_url}\n")
        self.log_area.insert(tk.END, "Waiting for client connection...\n\n")
        self.log_area.see(tk.END)
        
    def generate_qr_image(self, url):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        return qr.make_image(fill_color="white", back_color=BG_CARD)
        
    def copy_url(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.server_url)
        self.copy_btn.config(text="✓ Copied", bg=EMERALD)
        self.root.after(1500, lambda: self.copy_btn.config(text="📋 Copy", bg=ACCENT))
        
    def refresh_devices(self):
        try:
            devices = sd.query_devices()
            default_out = sd.default.device[1]
            self.default_device_idx = default_out
            
            output_devices = []
            selected_idx = 0
            
            for idx, dev in enumerate(devices):
                if dev["max_output_channels"] > 0:
                    name = dev["name"]
                    display_name = f"[{idx}] {name}"
                    if idx == default_out:
                        display_name += " (Default)"
                    output_devices.append(display_name)
                    
                    if idx == default_out:
                        selected_idx = len(output_devices) - 1
            
            if hasattr(self, 'device_combo'):
                self.device_combo['values'] = output_devices
                if output_devices:
                    self.device_combo.current(selected_idx)
            
            import server.main
            server.main.device_index = default_out
                
            logger.info("Refreshed output audio devices list.")
        except Exception as e:
            logger.error(f"Failed to query sound devices: {e}")
            if hasattr(self, 'log_area'):
                self.log_area.insert(tk.END, f"[ERROR] Failed to query sound devices: {e}\n")
            
    def on_device_changed(self, event):
        selected = self.device_combo.get()
        try:
            idx_str = selected.split("]")[0].replace("[", "").strip()
            idx = int(idx_str)
            import server.main
            server.main.device_index = idx
            logger.info(f"User changed audio playback device to: {selected}")
        except Exception as e:
            logger.error(f"Failed to parse selected device index: {e}")
            
    def start_server_thread(self):
        def run_server():
            if sys.platform == "win32":
                import asyncio
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                
            try:
                uvicorn.run(
                    app,
                    host="0.0.0.0",
                    port=self.port,
                    ssl_keyfile=self.key_path,
                    ssl_certfile=self.cert_path,
                    log_level="info",
                    log_config=None,
                    ws_max_size=16 * 1024 * 1024
                )
            except Exception as e:
                logger.error(f"Uvicorn server crashed: {e}")
                
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info("FastAPI Uvicorn server started in background thread.")
        
    def poll_logs(self):
        while not log_queue.empty():
            try:
                message = log_queue.get_nowait()
                if hasattr(self, 'log_area'):
                    self.log_area.insert(tk.END, message)
                    self.log_area.see(tk.END)
                log_queue.task_done()
            except queue.Empty:
                break
        self.root.after(100, self.poll_logs)
        
    def poll_stats(self):
        try:
            import server.main
            active = server.main.active_connections
            packets = server.main.total_packets_received
            bytes_received = server.main.total_bytes_received
            mb_received = bytes_received / (1024 * 1024)
            
            if hasattr(self, 'status_txt') and hasattr(self, 'packet_txt'):
                self.status_txt.config(text=f"Server Live | Active Connections: {active}")
                self.packet_txt.config(text=f"Packets: {packets} ({mb_received:.2f} MB)")
        except Exception:
            pass
            
        self.root.after(1000, self.poll_stats)
        
    def animate_pulse(self):
        try:
            import server.main
            active = server.main.active_connections
            
            if active > 0:
                color = EMERALD if self.pulse_state else "#047857"
            else:
                color = EMERALD if self.pulse_state else "#065f46"
                
            if hasattr(self, 'status_indicator'):
                self.status_indicator.config(fg=color)
            self.pulse_state = not self.pulse_state
        except Exception:
            pass
            
        self.root.after(750, self.animate_pulse)
        
    def on_closing(self):
        logger.info("Window closing. Shutting down SwarSetu backend server...")
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = SwarSetuApp(root)
    root.mainloop()
