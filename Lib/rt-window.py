import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import tkinter.font as tkfont
import socket
import threading
import paramiko
import zmq
import cv2
import numpy as np
from PIL import Image, ImageTk
import re
import os

# =========================================================
# CONSTANTS
# =========================================================
FRAME_H = 480
FRAME_W = 640
FULL_W = FRAME_W * 4

SSH_ROUTER_IP = "192.168.2.1"
SSH_ROUTER_USER = "root"
SSH_CAMERA_USER = "pi"

CAMERA_IP = None
ZMQ_ADDR = None

# =========================================================
# GET LOCAL LAN IP
# =========================================================
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unknown"

# =========================================================
# FILE LOADERS
# =========================================================
def load_ini(entry):
    path = filedialog.askopenfilename(
        title="Select INI File",
        filetypes=[("INI files", "*.ini")]
    )
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

def load_joblib(entry):
    path = filedialog.askopenfilename(
        title="Select Classification Model",
        filetypes=[("Joblib files", "*.joblib")]
    )
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

# =========================================================
# BASED FOLDER GENERATION
# =========================================================
def ensure_data_folders():
    base = "Data"
    os.makedirs(os.path.join(base, "Raw"), exist_ok=True)
    os.makedirs(os.path.join(base, "Raster"), exist_ok=True)
    os.makedirs(os.path.join(base, "Classification"), exist_ok=True)

# =========================================================
# CAMERA IP DISCOVERY (ROUTER)
# =========================================================
def detect_camera_ip():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=SSH_ROUTER_IP,
            username=SSH_ROUTER_USER,
            password="admin",
            timeout=5
        )

        stdin, stdout, stderr = client.exec_command("nslookup qbc.lan")
        output = stdout.read().decode()
        client.close()

        ips = re.findall(r"Address:\s+(\d+\.\d+\.\d+\.\d+)", output)

        if not ips:
            raise RuntimeError("Camera IP not found in nslookup output")

        cam_ip_entry.delete(0, tk.END)
        cam_ip_entry.insert(0, ips[-1])  # ← 192.168.2.106

    except Exception as e:
        messagebox.showerror("Camera Detection Failed", str(e))

# =========================================================
# SSH CHECK TO CAMERA
# =========================================================
def ssh_check_camera(ip, on_success):
    global CAMERA_IP
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=ip, username=SSH_CAMERA_USER, timeout=5)
        client.close()
        CAMERA_IP = ip
        root.after(0, on_success)
    except Exception as e:
        root.after(0, lambda: messagebox.showerror("SSH Failed", str(e)))

# =========================================================
# ZMQ RECEIVER
# =========================================================
def zmq_receiver(label_list, stop_event):
    context = zmq.Context()
    sock = context.socket(zmq.SUB)
    sock.setsockopt(zmq.CONFLATE, 1)
    sock.bind(ZMQ_ADDR)
    sock.setsockopt_string(zmq.SUBSCRIBE, "")

    while not stop_event.is_set():
        try:
            data = sock.recv(flags=zmq.NOBLOCK)
        except zmq.Again:
            continue

        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None or img.shape != (FRAME_H, FULL_W):
            continue

        for i in range(4):
            tile = img[:, i*FRAME_W:(i+1)*FRAME_W]          # shape: (H, W), uint8

            # Convert grayscale to RGB
            tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)   # shape: (H, W, 3) [web:2][web:10]

            # Mask of pixels >= 255
            mask = tile >= 255

            # Set those pixels to red
            tile_rgb[mask] = [255, 0, 0]                        # [web:2]

            # Convert to PIL Image and then to ImageTk
            pil_img = Image.fromarray(tile_rgb)                 # [web:3][web:7]
            imgtk = ImageTk.PhotoImage(pil_img)                 # [web:9]

            label_list[i].config(image=imgtk)
            label_list[i].image = imgtk

# =========================================================
# MAIN WINDOW (ALL TABS RESTORED)
# =========================================================
def open_main_window():
    root.destroy()

    main = tk.Tk()
    main.title("Camera Application")

    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(size=12)
    entry_font = tkfont.Font(size=12)

    notebook = ttk.Notebook(main)
    notebook.pack(fill="both", expand=True)

    # =====================================================
    # TAB 1 — CAMERA VIEWER
    # =====================================================
    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="Camera Viewer")

    cam_grid = tk.Frame(tab1)
    cam_grid.pack(padx=6, pady=6)

    image_labels = []

    for r, c in [(0,0),(0,1),(1,0),(1,1)]:
        f = tk.Frame(cam_grid)
        f.grid(row=r*2, column=c, padx=6, pady=6)

        lbl = tk.Label(f)
        lbl.grid(row=0, column=0)
        image_labels.append(lbl)

        tk.Scale(f, from_=100, to=0, orient="vertical",
                 length=FRAME_H, label="Gain").grid(row=0, column=1)
        tk.Scale(f, from_=100, to=0, orient="vertical",
                 length=FRAME_H, label="Expo").grid(row=0, column=2)

    warp_frame = tk.Frame(cam_grid)
    warp_frame.grid(row=3, column=0, sticky="w")

    tk.Button(warp_frame, text="Warp Images").grid(row=0, column=0)
    warp_entry = tk.Entry(warp_frame, width=55, font=entry_font)
    warp_entry.grid(row=0, column=1, padx=4)
    tk.Button(
        warp_frame,
        text="Load File",
        command=lambda: load_ini(warp_entry)
    ).grid(row=0, column=2)
    tk.Checkbutton(warp_frame, text="Warp").grid(row=0, column=3)

    save_frame = tk.Frame(cam_grid)
    save_frame.grid(row=3, column=1, sticky="w")

    tk.Entry(save_frame, width=73, font=entry_font).grid(row=0, column=0)
    tk.Button(save_frame, text="Save Folder").grid(row=0, column=1)
    tk.Checkbutton(save_frame, text="Save").grid(row=0, column=2)

    # =====================================================
    # TAB 2 — RASTER CALCULATION
    # =====================================================
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="Raster Calculation")

    top = tk.Frame(tab2)
    top.pack(fill="x", padx=20, pady=10)

    left = tk.Frame(top)
    left.grid(row=0, column=0, sticky="w")

    tk.Label(left, text="Reference Radiance",
             font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0)

    rad_entry = tk.Entry(left, width=40, font=entry_font)
    rad_entry.grid(row=1, column=0, pady=4)

    tk.Button(left, text="Load",
              command=lambda: load_ini(rad_entry)).grid(row=1, column=1, padx=6)

    camf = tk.Frame(left)
    camf.grid(row=2, column=0, columnspan=2, pady=10)

    for i in range(4):
        tk.Label(camf, text=f"CAM {i+1}").grid(row=i//2, column=(i%2)*2)
        tk.Entry(camf, width=15, font=entry_font).grid(row=i//2, column=(i%2)*2+1)

    right = tk.Frame(top)
    right.grid(row=0, column=1, padx=40)

    tk.Button(right, text="Reflectance Calculation",
              width=22, height=4).grid(row=0, column=0, padx=6)
    tk.Button(right, text="Raster Calculation",
              width=22, height=4).grid(row=0, column=1, padx=6)

    center = tk.Frame(tab2)
    center.pack(expand=True, fill="both")

    ph = tk.Frame(center, width=640, height=480, relief="solid", borderwidth=1)
    ph.place(relx=0.5, rely=0.5, anchor="center")
    ph.pack_propagate(False)
    tk.Label(ph, text="480 x 640",
             font=("TkDefaultFont", 12, "bold")).place(relx=0.5, rely=0.5, anchor="center")

    save2 = tk.Frame(tab2)
    save2.place(relx=1, rely=1, anchor="se", x=-20, y=-20)
    tk.Entry(save2, width=75, font=entry_font).grid(row=0, column=0)
    tk.Button(save2, text="Save Folder").grid(row=0, column=1)
    tk.Checkbutton(save2, text="Save").grid(row=0, column=2)

    # =====================================================
    # TAB 3 — CLASSIFICATION
    # =====================================================
    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text="Classification")

    top3 = tk.Frame(tab3)
    top3.pack(fill="x", padx=20, pady=10)

    model_frame = tk.Frame(top3)
    model_frame.grid(row=0, column=0, sticky="w")

    tk.Label(model_frame, text="Classification Model",
             font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, sticky="w")

    cls_entry = tk.Entry(model_frame, width=40, font=entry_font)
    cls_entry.grid(row=1, column=0, pady=4)

    tk.Button(model_frame, text="Load",
              command=lambda: load_joblib(cls_entry)).grid(row=1, column=1, padx=6)

    src_frame = tk.Frame(top3)
    src_frame.grid(row=0, column=1, sticky="e", padx=(40, 0))

    tk.Button(src_frame, text="From Calculated Reflectance",
              width=26, height=4).grid(row=0, column=0, padx=6)
    tk.Button(src_frame, text="From Calculated Raster",
              width=26, height=4).grid(row=0, column=1, padx=6)

    center3 = tk.Frame(tab3)
    center3.pack(expand=True, fill="both")

    ph3 = tk.Frame(center3, width=640, height=480, relief="solid", borderwidth=1)
    ph3.place(relx=0.5, rely=0.5, anchor="center")
    ph3.pack_propagate(False)
    tk.Label(ph3, text="480 x 640",
             font=("TkDefaultFont", 12, "bold")).place(relx=0.5, rely=0.5, anchor="center")

    save3 = tk.Frame(tab3)
    save3.place(relx=1, rely=1, anchor="se", x=-20, y=-20)
    tk.Entry(save3, width=75, font=entry_font).grid(row=0, column=0)
    tk.Button(save3, text="Save Folder").grid(row=0, column=1)
    tk.Checkbutton(save3, text="Save").grid(row=0, column=2)

    stop = threading.Event()
    threading.Thread(
        target=zmq_receiver,
        args=(image_labels, stop),
        daemon=True
    ).start()

    main.protocol("WM_DELETE_WINDOW",
                  lambda: (stop.set(), main.destroy()))
    main.mainloop()

# =========================================================
# STARTUP WINDOW
# =========================================================
root = tk.Tk()
root.title("Connecting Camera")
root.geometry("420x240")
root.resizable(False, False)

default_font = tkfont.nametofont("TkDefaultFont")
default_font.configure(size=12)

lan_ip = get_lan_ip()

tk.Label(root, text="Connecting Camera",
         font=("TkDefaultFont", 12, "bold")).pack(pady=8)
tk.Label(root, text=f"Laptop LAN Address: {lan_ip}").pack(pady=4)

mid = tk.Frame(root)
mid.pack(pady=12)

tk.Label(mid, text="Camera IP:").grid(row=0, column=0, padx=6)

cam_ip_entry = tk.Entry(mid, width=20, font=tkfont.Font(size=12))
cam_ip_entry.grid(row=0, column=1)

tk.Button(
    mid,
    text="Detect",
    command=lambda: threading.Thread(
        target=detect_camera_ip,
        daemon=True
    ).start()
).grid(row=0, column=2, padx=6)

def on_ok():
    global ZMQ_ADDR
    ip = cam_ip_entry.get().strip()
    if not ip:
        messagebox.showwarning("Input Required", "Camera IP is empty")
        return

    # ensure Data/Raw, Data/Raster, Data/Classification exist
    ensure_data_folders()

    ZMQ_ADDR = f"tcp://{lan_ip}:5555"

    threading.Thread(
        target=ssh_check_camera,
        args=(ip, open_main_window),
        daemon=True
    ).start()

btns = tk.Frame(root)
btns.pack(pady=18)

tk.Button(btns, text="OK", width=10, command=on_ok).grid(row=0, column=0, padx=10)
tk.Button(btns, text="Cancel", width=10, command=root.destroy).grid(row=0, column=1)

root.mainloop()
