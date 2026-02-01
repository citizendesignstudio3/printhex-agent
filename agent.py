# agent.py
# -*- coding: utf-8 -*-
"""
Agent v2.1 - Ultimate Professional Edition.
---------------------------------------------------------
LOGIC INCLUDED:
1. ✅ Flex Machine: Real-time Log Monitoring (Size-based & Robust).
2. ✅ Konica Minolta: SNMP Monitoring (IP based).
3. ✅ Laser Machine: Serial Port Monitoring.
4. ✅ System Health: CPU & RAM Usage.
5. ✅ Auto-Updater: Checks for new version on startup.
6. ✅ Auto-Startup: Adds to Windows Registry.
7. ✅ Kill Switch: Auto-Reset if Device ID is removed from server.
8. ✅ Dashboard: Shows Status when clicking shortcut.
---------------------------------------------------------
"""
import time
import json
import threading
import logging
import os
import sys
import subprocess
import queue
import requests

# ---------------------------------------------------------
# DEPENDENCIES CHECK
# ---------------------------------------------------------
try:
    from socketio import Client, exceptions
except ImportError:
    print("Error: 'python-socketio' not found. Run: pip install python-socketio[client]")
    sys.exit(1)

# Optional: System Health (CPU/RAM)
try:
    import psutil
except ImportError:
    psutil = None

# Local Modules
try:
    from version import VERSION
    from updater import check_update_loop
    from parsers.loader import load_parser
    from parsers.SnmpParser import SnmpParser
except ImportError as e:
    VERSION = "2.5.1"
    SnmpParser = None
    def check_update_loop(): pass

# Windows Registry
try:
    import winreg
except ImportError:
    winreg = None

# UI Imports
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog, ttk
except Exception:
    tk = messagebox = filedialog = ttk = None

# Serial handling
try:
    import serial
    from serial.serialutil import SerialException
    from serial.tools import list_ports
except Exception:
    serial = SerialException = list_ports = None

# -----------------------
# CONSTANTS & CONFIG
# -----------------------
DEFAULT_SERVER_URL = os.environ.get("SERVER_URL", "https://python.printhex.in")
REGISTRY_KEY_NAME = "PrintHexAgent"
APP_CONFIG = {}

# ==========================================
# 1. SYSTEM UTILITIES (Startup, Reset, Config)
# ==========================================
def get_config_path():
    # यह डेटा को AppData में सेव करेगा जहाँ परमिशन की कोई समस्या नहीं होती
    app_data = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'PrintHex')
    if not os.path.exists(app_data):
        os.makedirs(app_data)
    return os.path.join(app_data, 'config.json')

def load_config():
    try:
        with open(get_config_path(), 'r') as f: return json.load(f)
    except: return None

def setup_startup():
    """Adds the agent to Windows Startup Registry."""
    if not winreg: return
    try:
        exe = sys.executable
        if getattr(sys, 'frozen', False):
            # If running as compiled exe
            cmd = f'"{exe}" --background'
        else:
            # If running as python script
            cmd = f'"{exe}" "{os.path.abspath(__file__)}" --background'
            
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, REGISTRY_KEY_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        logging.info("Startup Registry Updated.")
    except Exception as e:
        logging.error(f"Startup Error: {e}")

def full_reset_agent():
    """SECURITY: Deletes config and stops agent if server bans device."""
    logging.warning("⛔ DEVICE UNAUTHORIZED! Resetting Agent...")
    try:
        path = get_config_path()
        if os.path.exists(path):
            os.remove(path)
    except: pass
    
    # Force kill the process
    os._exit(0) 

# ==========================================
# 2. CLIENT DASHBOARD (Status Window)
# ==========================================
def show_status_gui(conf):
    """
    Shows this window when user clicks Desktop Shortcut.
    It runs the agent in background thread, but shows UI to user.
    """
    if not tk: return
    
    root = tk.Tk()
    root.title("PrintHex Agent Status")
    root.geometry("450x420")
    root.resizable(False, False)
    
    # Modern Dark Theme
    BG = "#0f172a"
    CARD = "#1e293b"
    TEXT = "#f1f5f9"
    root.configure(bg=BG)

    # # Start Agent Logic in Background
    add_row("Agent Mode:", "Running in Background ✅")
    # t = threading.Thread(target=run_agent_process, args=(conf,), daemon=True)
    # t.start()

    # UI Header
    tk.Label(root, text="PRINTHEX IOT", bg=BG, fg="white", font=("Segoe UI", 18, "bold")).pack(pady=(30, 5))
    tk.Label(root, text="System is Active", bg=BG, fg="#4ade80", font=("Segoe UI", 10)).pack(pady=(0, 20))
    
    # Info Card
    card = tk.Frame(root, bg=CARD, padx=20, pady=20)
    card.pack(fill="x", padx=30)

    def add_row(label, value):
        f = tk.Frame(card, bg=CARD)
        f.pack(fill="x", pady=5)
        tk.Label(f, text=label, bg=CARD, fg="#94a3b8", width=15, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        tk.Label(f, text=value, bg=CARD, fg="white", font=("Segoe UI", 10, "bold")).pack(side="right")

    add_row("Device ID:", conf.get('device_id', 'Unknown')[:18] + "...")
    add_row("Machine Type:", conf.get('machine_type', 'Flex').upper())
    add_row("Connection:", "Online 🟢")
    
    # Buttons
    def on_reset():
        if messagebox.askyesno("Reset", "Are you sure? This will disconnect the device and delete settings."):
            full_reset_agent()

    tk.Label(root, text="This application runs silently in the background.", bg=BG, fg="#64748b", font=("Segoe UI", 9)).pack(pady=(30, 10))
    
    btn_frame = tk.Frame(root, bg=BG)
    btn_frame.pack(fill="x", padx=30)

    tk.Button(btn_frame, text="Hide Dashboard", command=root.destroy, bg="#3b82f6", fg="white", 
              relief="flat", font=("Segoe UI", 10, "bold"), pady=8).pack(fill="x", pady=5)
    
    tk.Button(btn_frame, text="Reset / Logout", command=on_reset, bg="#ef4444", fg="white", 
              relief="flat", font=("Segoe UI", 9), pady=5).pack(fill="x", pady=5)

    root.mainloop()

# ==========================================
# 3. SETUP GUI (Configuration)
# ==========================================
def create_config_gui(default_server=DEFAULT_SERVER_URL):
    if tk is None: sys.exit("Tkinter library not found.")

    root = tk.Tk()
    root.title(f"PrintHex Setup v{VERSION}")
    root.geometry("500x750")
    root.resizable(False, False)
    
    # Theme
    BG_COLOR = "#0f172a"
    CARD_COLOR = "#1e293b"
    TEXT_COLOR = "#f1f5f9"
    ACCENT_COLOR = "#3b82f6"
    INPUT_BG = "#334155"
    INPUT_FG = "#ffffff"
    
    root.configure(bg=BG_COLOR)
    
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TLabel", background=CARD_COLOR, foreground=TEXT_COLOR)

    result_queue = queue.Queue()

    # --- Connection Check Logic (Your Original Logic Restored) ---
    def attempt_connection_thread(device_id, jwt_token, server_url):
        temp_sio = Client(reconnection=False, request_timeout=10)
        auth_success = threading.Event()

        @temp_sio.event(namespace='/agent')
        def connect():
            try: temp_sio.emit("auth", {"device_id": device_id, "jwt": jwt_token}, namespace='/agent')
            except: pass

        @temp_sio.on('auth_result', namespace='/agent')
        def on_auth_result(data):
            if isinstance(data, dict) and data.get('status') == 'success':
                auth_success.set()
            else:
                msg = data.get('message', 'Invalid Credentials')
                result_queue.put(f"ERROR: {msg}")
            temp_sio.disconnect()

        try:
            temp_sio.connect(server_url, namespaces=['/agent'])
            if auth_success.wait(timeout=8):
                result_queue.put("SUCCESS")
            else:
                result_queue.put("ERROR: Server did not respond (Timeout)")
        except Exception as e:
            result_queue.put(f"ERROR: Connection Failed ({str(e)})")
        finally:
            if temp_sio.connected: temp_sio.disconnect()

    def check_queue():
        try:
            msg = result_queue.get_nowait()
            if msg == "SUCCESS":
                status_label.config(text="✅ Success! Saving...", fg="#4ade80")
                save_and_close()
            else:
                error_text = msg.replace("ERROR: ", "")
                messagebox.showerror("Connection Failed", error_text)
                status_label.config(text="Validation Failed", fg="#f87171")
                btn_save.config(state='normal', text="Validate & Save")
        except queue.Empty:
            root.after(100, check_queue)

    def on_validate_click():
        d_id = ent_dev_id.get().strip()
        tok = ent_token.get().strip()
        url = ent_url.get().strip()
        
        if not d_id or not tok:
            messagebox.showwarning("Input Missing", "Device ID and Token are required.")
            return

        btn_save.config(state='disabled', text="Connecting...")
        status_label.config(text="Verifying with Server...", fg="#60a5fa")

        global APP_CONFIG
        APP_CONFIG = {
            'device_id': d_id, 'jwt_token': tok, 'server_url': url or default_server,
            'machine_type': cmb_type.get(), 'ip_address': ent_ip.get().strip(),
            'log_file_path': ent_log.get().strip(), 'serial_port': ent_serial.get().strip(),
            'baudrate': ent_baud.get().strip()
        }

        threading.Thread(target=attempt_connection_thread, args=(d_id, tok, APP_CONFIG['server_url']), daemon=True).start()
        root.after(100, check_queue)

    def save_and_close():
        try:
            with open(get_config_path(), 'w') as f:
                json.dump(APP_CONFIG, f, indent=4)

            setup_startup()

            messagebox.showinfo(
                "Success",
                "Configuration Saved!\nAgent will now run in background."
            )

            # ✅ Start background agent immediately
            subprocess.Popen([sys.executable, "--background"], creationflags=subprocess.DETACHED_PROCESS)

            root.destroy()

        except Exception as e:
            messagebox.showerror("File Error", f"Could not write config: {e}")
            btn_save.config(state='normal', text="Try Again")

    def browse_log():
        path = filedialog.askopenfilename(filetypes=(("Log files", "*.log"), ("All files", "*.*")))
        if path:
            ent_log.delete(0, tk.END)
            ent_log.insert(0, path)

    # --- UI Layout ---
    tk.Label(root, text="PRINTHEX SETUP", bg=BG_COLOR, fg="white", font=("Segoe UI", 22, "bold")).pack(pady=(20, 10))
    
    card = ttk.Frame(root, style="Card.TFrame", padding=20)
    card.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # --- Authentication Section ---
    tk.Label(card, text="AUTHENTICATION", bg=CARD_COLOR, fg=ACCENT_COLOR, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
    
    tk.Label(card, text="Device ID", bg=CARD_COLOR, fg="white").pack(anchor="w")
    ent_dev_id = tk.Entry(card, bg=INPUT_BG, fg=INPUT_FG, insertbackground="white", relief="flat", font=("Consolas", 10))
    ent_dev_id.pack(fill="x", pady=(0, 10), ipady=5)

    tk.Label(card, text="Secret Token", bg=CARD_COLOR, fg="white").pack(anchor="w")
    ent_token = tk.Entry(card, bg=INPUT_BG, fg=INPUT_FG, show="•", insertbackground="white", relief="flat")
    ent_token.pack(fill="x", pady=(0, 10), ipady=5)

    tk.Label(card, text="Server URL", bg=CARD_COLOR, fg="white").pack(anchor="w")
    ent_url = tk.Entry(card, bg=INPUT_BG, fg=INPUT_FG, insertbackground="white", relief="flat")
    ent_url.insert(0, default_server)
    ent_url.pack(fill="x", pady=(0, 15), ipady=5)

    # --- Machine Config ---
    tk.Label(card, text="MACHINE CONFIGURATION", bg=CARD_COLOR, fg=ACCENT_COLOR, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 5))
    
    tk.Label(card, text="Machine Type", bg=CARD_COLOR, fg="white").pack(anchor="w")
    cmb_type = ttk.Combobox(card, values=["flex", "konica", "laser"], state="readonly")
    cmb_type.set("flex"); cmb_type.pack(fill="x", pady=(0, 10), ipady=5)

    # Flex
    f_log = tk.Frame(card, bg=CARD_COLOR); f_log.pack(fill="x", pady=2)
    tk.Label(f_log, text="Flex Log File:", bg=CARD_COLOR, fg="white", width=15, anchor="w").pack(side="left")
    ent_log = tk.Entry(f_log, bg=INPUT_BG, fg=INPUT_FG, relief="flat"); ent_log.pack(side="left", fill="x", expand=True, ipady=4)
    tk.Button(f_log, text="...", command=browse_log, bg=ACCENT_COLOR, fg="white", relief="flat").pack(side="right", padx=(5,0))

    # Konica
    f_ip = tk.Frame(card, bg=CARD_COLOR); f_ip.pack(fill="x", pady=5)
    tk.Label(f_ip, text="Konica IP:", bg=CARD_COLOR, fg="white", width=15, anchor="w").pack(side="left")
    ent_ip = tk.Entry(f_ip, bg=INPUT_BG, fg=INPUT_FG, relief="flat"); ent_ip.pack(side="left", fill="x", expand=True, ipady=4)

    # Laser
    f_ser = tk.Frame(card, bg=CARD_COLOR); f_ser.pack(fill="x", pady=2)
    tk.Label(f_ser, text="Laser Serial:", bg=CARD_COLOR, fg="white", width=15, anchor="w").pack(side="left")
    ent_serial = tk.Entry(f_ser, bg=INPUT_BG, fg=INPUT_FG, relief="flat", width=15); ent_serial.pack(side="left", ipady=4)
    tk.Label(f_ser, text="Baud:", bg=CARD_COLOR, fg="white").pack(side="left", padx=5)
    ent_baud = tk.Entry(f_ser, bg=INPUT_BG, fg=INPUT_FG, relief="flat", width=10); ent_baud.pack(side="left", ipady=4)

    status_label = tk.Label(root, text="Ready to connect.", bg=BG_COLOR, fg="#64748b", font=("Segoe UI", 9))
    status_label.pack(pady=(0, 5))

    btn_save = tk.Button(root, text="VALIDATE & SAVE", command=on_validate_click,
                         bg=ACCENT_COLOR, fg="white", font=("Segoe UI", 11, "bold"),
                         relief="flat", cursor="hand2", pady=10)
    btn_save.pack(fill="x", padx=20, pady=(0, 20))

    root.mainloop()
    return True

# ==========================================
# 4. AGENT LOGIC (All Features Preserved)
# ==========================================
def run_agent_process(conf):
    log_folder = os.path.dirname(get_config_path())
    log_path = os.path.join(log_folder, 'agent.log')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                        handlers=[logging.FileHandler(log_path, mode='a'), logging.StreamHandler(sys.stdout)])

    logging.info(">>> Agent Starting Up...")

    # Start Updater
    try: threading.Thread(target=check_update_loop, daemon=True).start()
    except: pass

    SERVER = conf.get("server_url")
    DEV_ID = conf.get("device_id")
    TOKEN = conf.get("jwt_token")
    TYPE = conf.get("machine_type", "flex")
    LOG_PATH = conf.get("log_file_path")
    SERIAL = conf.get("serial_port")
    BAUD = int(conf.get("baudrate") or 9600)
    IP_ADDR = conf.get("ip_address")

    PARSER = load_parser(TYPE)
    sio = Client(reconnection=True, reconnection_delay=5)
    auth_event = threading.Event()
    stop_event = threading.Event()
    _serial_open = False

    # --- Helper: Send Event ---
    def send_event(evt_type, payload={}):
        if sio.connected and auth_event.is_set():
            sio.emit("device_event", {
                "type": evt_type, "device_id": DEV_ID, 
                "payload": payload, "created_at": int(time.time()*1000)
            }, namespace='/agent')

    # --- Heartbeat (Fast) ---
    def heartbeat_loop():
        while not stop_event.is_set():
            if auth_event.wait(timeout=1) and sio.connected:
                try: sio.emit("heartbeat", {"device_id": DEV_ID, "ts": int(time.time()*1000)}, namespace='/agent')
                except: pass
            stop_event.wait(10)

    # --- Status Loop ---
    def status_loop():
        while not stop_event.is_set():
            if auth_event.wait(timeout=1):
                send_event("device_status", {
                    "serial_connected": bool(_serial_open),
                    "log_monitored": bool(LOG_PATH and os.path.exists(LOG_PATH)),
                    "ip_configured": bool(IP_ADDR),
                    "mode": TYPE
                })
            stop_event.wait(60)

    # --- 1. LASER MONITOR ---
    def start_serial():
        nonlocal _serial_open
        if not SERIAL or not serial: return
        logging.info(f"Starting Serial: {SERIAL}")
        while not stop_event.is_set():
            try:
                with serial.Serial(SERIAL, BAUD, timeout=1) as ser:
                    _serial_open = True
                    while not stop_event.is_set():
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line: send_event("serial", {"raw": line})
            except:
                _serial_open = False
                time.sleep(5)

    # --- 2. FLEX MONITOR (Robust Size-Based) ---
    def start_log_monitor():
        if not LOG_PATH or not os.path.exists(LOG_PATH):
            logging.error(f"Log file not found: {LOG_PATH}")
            return
        
        logging.info(f"Starting Log Monitor: {LOG_PATH}")
        last_pos = 0
        try: last_pos = os.path.getsize(LOG_PATH)
        except: pass

        while not stop_event.is_set():
            time.sleep(1) # Check every 1s
            if not os.path.exists(LOG_PATH): continue

            try:
                curr = os.path.getsize(LOG_PATH)
                if curr < last_pos: last_pos = 0 # File reset
                
                if curr > last_pos:
                    with open(LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_pos)
                        data = f.read()
                        last_pos = f.tell()
                        
                        if data:
                            for line in data.splitlines():
                                line = line.strip()
                                if line:
                                    send_event("LOG_RAW", {"line": line})
                                    # Parse if needed
                                    if PARSER:
                                        res = PARSER.parse(line)
                                        if res:
                                            if isinstance(res, list):
                                                for r in res: send_event(r.get('event'), r.get('payload'))
                                            else:
                                                send_event(res['event'], res['payload'])
            except Exception as e:
                logging.error(f"Log Read Error: {e}")

    # --- 3. KONICA MONITOR (SNMP) ---
    def start_snmp_monitor():
        if not SnmpParser or not IP_ADDR: return
        logging.info(f"Starting SNMP: {IP_ADDR}")
        parser = SnmpParser(IP_ADDR)
        while not stop_event.is_set():
            try:
                events = parser.parse()
                if events:
                    for ev in events: send_event(ev['event'], ev['payload'])
            except: pass
            time.sleep(5)

    # --- 4. SYSTEM HEALTH (New) ---
    def monitor_health():
        if not psutil: return
        while not stop_event.is_set():
            time.sleep(60)
            try:
                send_event("SYSTEM_HEALTH", {
                    "cpu": psutil.cpu_percent(),
                    "ram": psutil.virtual_memory().percent
                })
            except: pass

    # --- Socket Events ---
    @sio.event(namespace='/agent')
    def connect():
        logging.info("Socket Connected.")
        sio.emit("auth", {"device_id": DEV_ID, "jwt": TOKEN}, namespace='/agent')

    @sio.on('auth_result', namespace='/agent')
    def on_auth(data):
        if data.get('status') == 'success':
            auth_event.set()
            sio.emit("machine_state", {"device_id": DEV_ID, "running": True, "reason": "startup"}, namespace='/agent')
        else:
            logging.error("⛔ AUTH FAILED: Device Banned/Invalid.")
            sio.disconnect()
            full_reset_agent() # KILL SWITCH

    @sio.on('disconnect', namespace='/agent')
    def on_disconnect():
        auth_event.clear()

    # --- START THREADS ---
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=status_loop, daemon=True).start()
    threading.Thread(target=monitor_health, daemon=True).start()

    if TYPE == "konica": threading.Thread(target=start_snmp_monitor, daemon=True).start()
    elif TYPE == "flex": threading.Thread(target=start_log_monitor, daemon=True).start()
    elif TYPE == "laser" and SERIAL: threading.Thread(target=start_serial, daemon=True).start()

    logging.info("Agent Running...")
    
    while not stop_event.is_set():
        try:
            if not sio.connected: sio.connect(SERVER, namespaces=["/agent"])
            sio.wait()
        except: time.sleep(5)

# ==========================================
# 5. BOOTSTRAP (Entry Point)
# ==========================================
if __name__ == "__main__":

    cfg = load_config()

    # ✅ Always ensure startup entry exists
    setup_startup()

    # -----------------------------
    # MODE 1: Background Silent Mode
    # -----------------------------
    if "--background" in sys.argv:
        if cfg:
            run_agent_process(cfg)
        sys.exit()

    # -----------------------------
    # MODE 2: Dashboard Mode
    # -----------------------------
    if "--dashboard" in sys.argv:
        if cfg:
            show_status_gui(cfg)
        else:
            create_config_gui(DEFAULT_SERVER_URL)
        sys.exit()

    # -----------------------------
    # MODE 3: Normal User Double Click
    # -----------------------------
    if not cfg:
        # First time run → open setup
        create_config_gui(DEFAULT_SERVER_URL)

    else:
        # Config already exists → just open dashboard
        show_status_gui(cfg)
