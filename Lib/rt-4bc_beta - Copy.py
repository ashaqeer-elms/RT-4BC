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
from datetime import datetime


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

save_tab1 = False
last_fullframe = None

# Gain / Exposure scales stored for CAM1..4
gain_scales = []
expo_scales = []
status_labels = []  # G/E display labels per frame
CAM_DEVICES = [0, 2, 4, 6]  # -d0, -d2, -d4, -d6 for CAM1..4

# Exposure level -> exposure_time_absolute (driver units)
EXPO_ABS = [1, 2, 5, 10, 20, 39, 78, 156, 312, 625, 1250, 2500]

# Exposure level -> display value in ms
EXPO_MS = [
    0.04,
    0.15,
    0.52,
    1.08,
    2.24,
    4.48,
    9.03,
    18.14,
    36.04,
    72.99,
    146.05,
    292.21,
]

# Background noise tiles and widgets (Tab 2)
bg_tiles = [None, None, None, None]
bg_labels = []
bg_cam_entries = []

# Reference tiles and widgets (Tab 3)
ref_tiles = [None, None, None, None]
ref_labels = []
ref_cam_entries = []
ref_entry_widget = None

# Reflectance display (Tab 4)
refl_labels = [None, None, None, None]

# Calculated raster (Tab 4)
calc_label = None
current_raster_expression = None
current_raster_band = None  # "R1".."R4"

save_tab4 = False
save4_entry = None  # will hold the Entry widget reference

warning_invalid_params_shown = False


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
        title="Select INI File", filetypes=[("INI files", "*.ini")]
    )
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


def load_joblib(entry):
    path = filedialog.askopenfilename(
        title="Select Classification Model", filetypes=[("Joblib files", "*.joblib")]
    )
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


# =========================================================
# BASED FOLDER GENERATION
# =========================================================
def ensure_data_folders():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(script_dir, "Data")

    os.makedirs(os.path.join(base, "Raw"), exist_ok=True)
    os.makedirs(os.path.join(base, "Raster"), exist_ok=True)
    os.makedirs(os.path.join(base, "Classification"), exist_ok=True)
    os.makedirs(os.path.join(base, "Background"), exist_ok=True)  # new
    os.makedirs(os.path.join(base, "Reference"), exist_ok=True)  # new


# =========================================================
# SAVED FOLDER GENERATION
# =========================================================
def select_timestamp_folder_into_entry(entry):
    base = filedialog.askdirectory(title="Select Base Folder")
    if not base:
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(base, stamp)
    os.makedirs(target, exist_ok=False)

    entry.delete(0, tk.END)
    entry.insert(0, target)


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
            timeout=5,
        )

        stdin, stdout, stderr = client.exec_command("nslookup qbc.lan")
        output = stdout.read().decode()
        client.close()

        ips = re.findall(r"Address:\s+(\d+\.\d+\.\d+\.\d+)", output)

        if not ips:
            raise RuntimeError("Camera IP not found in nslookup output")

        cam_ip_entry.delete(0, tk.END)
        cam_ip_entry.insert(0, ips[-1])

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
# READ CURRENT GAINS FROM CAMERA
# =========================================================
def get_camera_gains():
    gains = []
    if CAMERA_IP is None:
        return [1, 1, 1, 1]

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=5)

        for dev in CAM_DEVICES:
            cmd = f"v4l2-ctl -d{dev} -C gain"
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode().strip()
            m = re.search(r"(\d+)", out)
            if m:
                gains.append(int(m.group(1)))
            else:
                gains.append(1)

        client.close()
    except Exception as e:
        print("Gain query error:", e)
        gains = [1, 1, 1, 1]

    return gains


# =========================================================
# READ CURRENT EXPOSURES FROM CAMERA
# =========================================================
def get_camera_exposures():
    levels = []
    if CAMERA_IP is None:
        return [1, 1, 1, 1]

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=5)

        for dev in CAM_DEVICES:
            cmd = f"v4l2-ctl -d{dev} -C exposure_time_absolute"
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode().strip()
            m = re.search(r"(\d+)", out)
            if m:
                val = int(m.group(1))
                diffs = [abs(val - ev) for ev in EXPO_ABS]
                level = diffs.index(min(diffs)) + 1
                levels.append(level)
            else:
                levels.append(1)

        client.close()
    except Exception as e:
        print("Exposure query error:", e)
        levels = [1, 1, 1, 1]

    return levels


# =========================================================
# STATUS LABEL UPDATE
# =========================================================
def update_status_label(idx):
    if idx >= len(gain_scales) or idx >= len(expo_scales) or idx >= len(status_labels):
        return
    g = int(gain_scales[idx].get())
    level = int(expo_scales[idx].get())
    level = max(1, min(12, level))
    ms = EXPO_MS[level - 1]
    status_labels[idx].config(text=f"G={g}  E={ms:.2f} ms")


# =========================================================
# GAIN CALLBACK (AUTOMATIC SEND)
# =========================================================
def on_gain_changed(value, cam_index):
    if CAMERA_IP is None:
        update_status_label(cam_index)
        return

    try:
        gain_val = int(float(value))
        dev = CAM_DEVICES[cam_index]

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=3)
        cmd = f"v4l2-ctl -d{dev} -c gain={gain_val}"
        client.exec_command(cmd)
        client.close()
    except Exception as e:
        print("Gain set error:", e)

    update_status_label(cam_index)


# =========================================================
# EXPOSURE CALLBACK (AUTOMATIC SEND)
# =========================================================
def on_expo_changed(value, cam_index):
    if CAMERA_IP is None:
        update_status_label(cam_index)
        return

    try:
        level = int(float(value))
        level = max(1, min(12, level))
        expo_val = EXPO_ABS[level - 1]
        dev = CAM_DEVICES[cam_index]

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=CAMERA_IP, username=SSH_CAMERA_USER, timeout=3)
        cmd = f"v4l2-ctl -d{dev} -c exposure_time_absolute={expo_val}"
        client.exec_command(cmd)
        client.close()
    except Exception as e:
        print("Exposure set error:", e)

    update_status_label(cam_index)


# =========================================================
# ZMQ RECEIVER
# =========================================================
def zmq_receiver(label_list, stop_event, save1_entry):
    global last_fullframe, save_tab1

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

        last_fullframe = img.copy()

        for i in range(4):
            tile = img[:, i * FRAME_W : (i + 1) * FRAME_W]

            tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
            mask = tile >= 255
            tile_rgb[mask] = [255, 0, 0]

            pil_img = Image.fromarray(tile_rgb)
            imgtk = ImageTk.PhotoImage(pil_img)

            label_list[i].config(image=imgtk)
            label_list[i].image = imgtk

        if save_tab1 and save1_entry.get().strip():
            save_dir = save1_entry.get().strip()
            if os.path.isdir(save_dir):
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # exposure levels from sliders → ms → *100 → int (for filename)
                exp_ms100 = []
                for idx in range(4):
                    if idx < len(expo_scales):
                        level = int(expo_scales[idx].get())
                        level = max(1, min(12, level))
                        ms = EXPO_MS[level - 1]
                        exp_ms100.append(int(round(ms * 100)))
                    else:
                        exp_ms100.append(0)

                fname = os.path.join(
                    save_dir,
                    f"{stamp}_{exp_ms100[0]}_{exp_ms100[1]}_{exp_ms100[2]}_{exp_ms100[3]}.png",
                )

                cv2.imwrite(fname, last_fullframe)


# =========================================================
# TAB 2/3: REFERENCE/BACKGROUND IMAGE LOADER
# =========================================================
def load_reference_image(entry, ref_labels_local, tiles_store=None, path=None):
    # If path is not provided, use file dialog (manual mode)
    if path is None:
        path = filedialog.askopenfilename(
            title="Select Reference Image", filetypes=[("PNG files", "*.png")]
        )
        if not path:
            return

    entry.delete(0, tk.END)
    entry.insert(0, path)

    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        messagebox.showerror("Load Error", "Failed to load image as grayscale.")
        return

    if img.shape != (FRAME_H, FULL_W):
        messagebox.showerror(
            "Shape Error", f"Expected shape (480, {FULL_W}), got {img.shape}."
        )
        return

    for i in range(4):
        tile = img[:, i * FRAME_W : (i + 1) * FRAME_W]
        if tiles_store is not None:
            tiles_store[i] = tile.copy()
        tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
        pil_img = Image.fromarray(tile_rgb)
        imgtk = ImageTk.PhotoImage(pil_img)
        ref_labels_local[i].config(image=imgtk)
        ref_labels_local[i].image = imgtk


def auto_load_background_and_estimate(bg_entry_local):
    """
    On first opening the main window, try to load the first PNG from
    Data/Background into Tab 2 and auto-estimate background noise.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bg_dir = os.path.join(script_dir, "Data", "Background")
        if not os.path.isdir(bg_dir):
            return

        candidates = [f for f in os.listdir(bg_dir) if f.lower().endswith(".png")]
        if not candidates:
            return

        bg_path = os.path.join(bg_dir, candidates[0])

        # Load that image into Tab 2
        load_reference_image(
            bg_entry_local, bg_labels, tiles_store=bg_tiles, path=bg_path
        )

        # Immediately estimate and fill CAM entries
        estimate_background_noise()
    except Exception as e:
        print("Auto background load error:", e)


def auto_load_reference(ref_entry_local):
    """
    On first opening the main window, try to load the first PNG from
    Data/Reference into Tab 3.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ref_dir = os.path.join(script_dir, "Data", "Reference")
        if not os.path.isdir(ref_dir):
            return

        candidates = [f for f in os.listdir(ref_dir) if f.lower().endswith(".png")]
        if not candidates:
            return

        ref_path = os.path.join(ref_dir, candidates[0])

        # Load that image into Tab 3 (and fill ref_tiles)
        load_reference_image(
            ref_entry_local, ref_labels, tiles_store=ref_tiles, path=ref_path
        )

        # Immediately estimate and fill CAM entries
        estimate_reference_radiance()
    except Exception as e:
        print("Auto reference load error:", e)


# =========================================================
# BACKGROUND NOISE ESTIMATION
# =========================================================
def estimate_background_noise():
    if len(bg_labels) != 4 or len(bg_cam_entries) != 4:
        return

    for i in range(4):
        tile = bg_tiles[i]
        if tile is None:
            continue

        h, w = tile.shape
        win_size = 100
        cx, cy = w // 2, h // 2
        x1 = max(0, cx - win_size // 2)
        y1 = max(0, cy - win_size // 2)
        x2 = min(w, cx + win_size // 2)
        y2 = min(h, cy + win_size // 2)

        roi = tile[y1:y2, x1:x2]
        if roi.size == 0:
            mean_val = 0.0
        else:
            mean_val = float(np.mean(roi))

        tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
        cv2.rectangle(tile_rgb, (x1, y1), (x2 - 1, y2 - 1), (255, 0, 0), 2)

        pil_img = Image.fromarray(tile_rgb)
        imgtk = ImageTk.PhotoImage(pil_img)
        bg_labels[i].config(image=imgtk)
        bg_labels[i].image = imgtk

        bg_cam_entries[i].delete(0, tk.END)
        bg_cam_entries[i].insert(0, f"{mean_val:.2f}")


# =========================================================
# REFERENCE RADIANCE ESTIMATION (Tab 3)
# =========================================================
def estimate_reference_radiance():
    global ref_entry_widget

    if len(ref_labels) != 4 or len(ref_cam_entries) != 4:
        return

    if ref_entry_widget is None:
        messagebox.showwarning(
            "No Reference Image", "Please load a reference image first."
        )
        return

    ref_path = ref_entry_widget.get().strip()
    if not ref_path:
        messagebox.showwarning(
            "No Reference Image", "Please load a reference image first."
        )
        return

    base = os.path.basename(ref_path)
    root_name, ext = os.path.splitext(base)
    parts = root_name.split("_")
    if len(parts) < 6:
        messagebox.showwarning(
            "Filename Error", "Reference filename does not contain 4 exposure values."
        )
        return

    # Last 4 parts are exposures * 100
    try:
        expo100_vals = [int(parts[-4]), int(parts[-3]), int(parts[-2]), int(parts[-1])]
    except Exception:
        messagebox.showwarning(
            "Filename Error", "Failed to parse exposure values from filename."
        )
        return

    for i in range(4):
        tile = ref_tiles[i]
        if tile is None:
            continue

        h, w = tile.shape
        win_size = 100
        cx, cy = w // 2, h // 2
        x1 = max(0, cx - win_size // 2)
        y1 = max(0, cy - win_size // 2)
        x2 = min(w, cx + win_size // 2)
        y2 = min(h, cy + win_size // 2)

        roi = tile[y1:y2, x1:x2]
        if roi.size == 0:
            mean_val = 0.0
        else:
            mean_val = float(np.mean(roi))

        # Background noise for this CAM from Tab 2 (fallback 0)
        try:
            bg_val = float(bg_cam_entries[i].get())
        except Exception:
            bg_val = 0.0

        # Exposure in original units (divide 100 from filename)
        exp_ms = expo100_vals[i] / 100.0 if expo100_vals[i] != 0 else 1.0

        # Reference radiance: (mean - background) / exposure
        ref_rad = (mean_val - bg_val) / exp_ms

        tile_rgb = cv2.cvtColor(tile, cv2.COLOR_GRAY2RGB)
        cv2.rectangle(tile_rgb, (x1, y1), (x2 - 1, y2 - 1), (255, 0, 0), 2)

        pil_img = Image.fromarray(tile_rgb)
        imgtk = ImageTk.PhotoImage(pil_img)
        ref_labels[i].config(image=imgtk)
        ref_labels[i].image = imgtk

        ref_cam_entries[i].delete(0, tk.END)
        ref_cam_entries[i].insert(0, f"{ref_rad:.2f}")


# =========================================================
# TARGET REFLECTANCE ESTIMATION (Tab 4)
# =========================================================


def reflectance_calculation():
    """
    For each CAM i:
      reflectance_i = (CAM_i - BG_i) / exposure_i / ref_radiance_i
    """
    global last_fullframe, warning_invalid_params_shown

    if last_fullframe is None:
        return None

    reflectance_tiles = []

    for i in range(4):
        if bg_tiles[i] is None:
            return None

        cam_tile = last_fullframe[:, i * FRAME_W : (i + 1) * FRAME_W].astype(np.float32)
        bg_tile = bg_tiles[i].astype(np.float32)

        if i < len(expo_scales):
            level = int(expo_scales[i].get())
            level = max(1, min(12, level))
            exp_ms = EXPO_MS[level - 1]
        else:
            exp_ms = 1.0

        try:
            ref_rad = float(ref_cam_entries[i].get())
        except Exception:
            ref_rad = 0.0

        if exp_ms == 0 or ref_rad == 0:
            if not warning_invalid_params_shown:
                messagebox.showwarning(
                    "Invalid Parameters",
                    f"Exposure or reference radiance is zero for CAM {i+1}.",
                )
                warning_invalid_params_shown = True
            return None

        num = cam_tile - bg_tile
        refl = num / exp_ms / ref_rad
        reflectance_tiles.append(refl)

    return reflectance_tiles


def update_reflectance_view(main_window):
    """
    Periodically compute reflectance and display it as 2x2 tiles on Tab 4.
    """
    global refl_labels

    tiles = None
    try:
        tiles = reflectance_calculation()
    except Exception:
        tiles = None

    if tiles is not None and len(refl_labels) == 4:
        for i in range(4):
            if tiles[i] is None:
                continue

            t = tiles[i]
            t_min, t_max = np.min(t), np.max(t)
            if t_max > t_min:
                norm = (t - t_min) / (t_max - t_min) * 255.0
            else:
                norm = np.zeros_like(t)

            norm_u8 = norm.astype(np.uint8)
            rgb = cv2.cvtColor(norm_u8, cv2.COLOR_GRAY2RGB)
            pil_img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(pil_img)

            refl_labels[i].config(image=imgtk)
            refl_labels[i].image = imgtk

    # Schedule next update (e.g. every 500 ms)
    main_window.after(500, lambda: update_reflectance_view(main_window))


def update_raster_expression(main_window):
    """
    Periodically re-evaluate the current raster expression on reflectance tiles
    and update calc_label.
    """
    global calc_label, current_raster_expression, current_raster_band

    if calc_label is None or not current_raster_expression:
        # Nothing to update
        main_window.after(500, lambda: update_raster_expression(main_window))
        return

    tiles = reflectance_calculation()
    if tiles is not None:
        local_vars = {
            "R1": tiles[0],
            "R2": tiles[1],
            "R3": tiles[2],
            "R4": tiles[3],
            "np": np,
        }
        expr = current_raster_expression

        try:
            result = eval(expr, {"__builtins__": {}}, local_vars)
        except Exception as e:
            # For continuous updates, just log and keep trying next cycle
            print("Raster eval error:", e)
            result = None

        if result is not None:
            t = result
            t_min, t_max = np.min(t), np.max(t)
            if t_max > t_min:
                norm = (t - t_min) / (t_max - t_min) * 255.0
            else:
                norm = np.zeros_like(t)

            norm_u8 = norm.astype(np.uint8)
            rgb = cv2.cvtColor(norm_u8, cv2.COLOR_GRAY2RGB)
            pil_img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(pil_img)

            calc_label.config(image=imgtk)
            calc_label.image = imgtk

            # Save PNG if enabled and folder is valid
            if save_tab4 and save4_entry is not None:
                folder = save4_entry.get().strip()
                if folder and os.path.isdir(folder):
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    fname = os.path.join(folder, f"raster_{stamp}.png")
                    # use OpenCV to save RGB image
                    cv2.imwrite(fname, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))

    main_window.after(500, lambda: update_raster_expression(main_window))


# =========================================================
# COMMON CAM ENTRIES BLOCK
# =========================================================
def create_cam_entries(parent, entry_font):
    cam_entries = []
    camf = tk.Frame(parent)
    camf.grid(row=2, column=0, columnspan=2, pady=10, sticky="w")

    for i in range(4):
        tk.Label(camf, text=f"CAM {i + 1}").grid(
            row=i // 2, column=(i % 2) * 2, sticky="w"
        )
        e = tk.Entry(camf, width=15, font=entry_font)
        e.grid(row=i // 2, column=(i % 2) * 2 + 1, padx=4, pady=2, sticky="w")
        cam_entries.append(e)

    return cam_entries


def open_raster_dialog(parent):
    global current_raster_expression, current_raster_band

    dlg = tk.Toplevel(parent)
    dlg.title("Raster Calculation")
    dlg.transient(parent)
    dlg.grab_set()

    # dialog font (size 12)
    dlg_font = tkfont.Font(size=12)

    dlg.geometry("800x800")
    dlg.columnconfigure(0, weight=1)
    dlg.rowconfigure(1, weight=1)

    # CAM selection (Listbox)
    tk.Label(dlg, text="Raster band (CAM):", font=dlg_font).grid(
        row=0, column=0, padx=10, pady=8, sticky="nw"
    )
    cam_list = tk.Listbox(
        dlg,
        height=3,
        width=25,
        selectmode="single",
        exportselection=False,
        font=dlg_font,
    )
    for item in ["R1", "R2", "R3", "R4"]:
        cam_list.insert(tk.END, item)
    cam_list.grid(row=1, column=0, padx=10, pady=8, sticky="nsew")
    cam_list.selection_set(0)

    # Expression
    dlg.columnconfigure(1, weight=1)
    dlg.rowconfigure(3, weight=1)

    tk.Label(dlg, text="Raster calculator expression:", font=dlg_font).grid(
        row=2, column=0, columnspan=2, padx=10, pady=(8, 2), sticky="nw"
    )
    expr_var = tk.StringVar()
    expr_entry = tk.Entry(dlg, textvariable=expr_var, font=dlg_font)
    expr_entry.grid(row=3, column=0, columnspan=2, padx=10, pady=4, sticky="nsew")

    # When CAM is double-clicked, append it to the expression entry
    def on_cam_double_click(event):
        sel = cam_list.curselection()
        if not sel:
            return
        text = cam_list.get(sel[0])  # "R1", "R2", ...
        expr_entry.insert(tk.END, text)

    cam_list.bind("<Double-Button-1>", on_cam_double_click)

    # Buttons
    def on_ok():
        global current_raster_expression, current_raster_band

        sel = cam_list.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a raster band (CAM).")
            return
        selected_cam = cam_list.get(sel[0])  # "R1".."R4"

        expression = expr_var.get().strip()
        if not expression:
            messagebox.showwarning("Empty Expression", "Please enter an expression.")
            return

        allowed = re.compile(r"^[\w\s\+\-\*\/\%\(\)\.,]+$")
        if not allowed.match(expression):
            messagebox.showerror(
                "Invalid Expression", "Expression contains invalid characters."
            )
            return

        current_raster_expression = expression
        current_raster_band = selected_cam

        dlg.destroy()

    def on_cancel():
        dlg.destroy()

    btn_frame = tk.Frame(dlg)
    btn_frame.grid(row=5, column=1, columnspan=1, pady=10)
    tk.Button(btn_frame, text="OK", width=10, command=on_ok, font=dlg_font).grid(
        row=0, column=0, padx=5
    )
    tk.Button(
        btn_frame, text="Cancel", width=10, command=on_cancel, font=dlg_font
    ).grid(row=0, column=1, padx=0)

    expr_entry.focus_set()
    parent.wait_window(dlg)


# =========================================================
# MAIN WINDOW (ALL TABS)
# =========================================================
def open_main_window():
    global bg_labels, bg_cam_entries, ref_labels, ref_cam_entries, ref_entry_widget

    root.destroy()

    main = tk.Tk()
    main.title("Camera Application")

    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(size=12)
    entry_font = tkfont.Font(size=12)

    notebook = ttk.Notebook(main)
    notebook.pack(fill="both", expand=True)

    # -----------------------------------------------------
    # TAB 1 — CAMERA VIEWER
    # -----------------------------------------------------
    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="Camera Viewer")

    cam_grid = tk.Frame(tab1)
    cam_grid.pack(padx=6, pady=6)

    image_labels = []
    gain_scales.clear()
    expo_scales.clear()
    status_labels.clear()

    initial_gains = get_camera_gains()
    initial_expos = get_camera_exposures()

    for idx, (r, c) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
        f = tk.Frame(cam_grid)
        f.grid(row=r * 2, column=c, padx=6, pady=6)

        status = tk.Label(f, text="")
        status.grid(row=0, column=0, columnspan=3, sticky="w")
        status_labels.append(status)

        lbl = tk.Label(f)
        lbl.grid(row=1, column=0)
        image_labels.append(lbl)

        tk.Label(f, text="Gain").grid(row=0, column=1, sticky="w")
        tk.Label(f, text="Exp").grid(row=0, column=2, sticky="w")

        gain_scale = tk.Scale(
            f,
            from_=33,
            to=0,
            orient="vertical",
            length=FRAME_H,
            resolution=1,
            command=lambda v, i=idx: on_gain_changed(v, i),
        )
        g0 = initial_gains[idx] if idx < len(initial_gains) else 0
        g0 = max(0, min(33, g0))
        gain_scale.set(g0)
        gain_scale.grid(row=1, column=1)
        gain_scales.append(gain_scale)

        expo_scale = tk.Scale(
            f,
            from_=12,
            to=1,
            orient="vertical",
            length=FRAME_H,
            resolution=1,
            command=lambda v, i=idx: on_expo_changed(v, i),
        )
        e0 = initial_expos[idx] if idx < len(initial_expos) else 1
        e0 = max(1, min(12, e0))
        expo_scale.set(e0)
        expo_scale.grid(row=1, column=2)
        expo_scales.append(expo_scale)

        update_status_label(idx)

    warp_frame = tk.Frame(cam_grid)
    warp_frame.grid(row=3, column=0, sticky="w")

    tk.Button(warp_frame, text="Warp Images").grid(row=0, column=0)
    warp_entry = tk.Entry(warp_frame, width=55, font=entry_font)
    warp_entry.grid(row=0, column=1, padx=4)
    tk.Button(warp_frame, text="Load File", command=lambda: load_ini(warp_entry)).grid(
        row=0, column=2
    )
    tk.Checkbutton(warp_frame, text="Warp").grid(row=0, column=3)

    save_frame = tk.Frame(cam_grid)
    save_frame.grid(row=3, column=1, sticky="w")

    save1_entry = tk.Entry(save_frame, width=73, font=entry_font)
    save1_entry.grid(row=0, column=0)

    tk.Button(
        save_frame,
        text="Save Folder",
        command=lambda e=save1_entry: select_timestamp_folder_into_entry(e),
    ).grid(row=0, column=1)

    save1_var = tk.BooleanVar(value=False)

    def on_save1_toggle():
        global save_tab1
        save_tab1 = save1_var.get()

    tk.Checkbutton(
        save_frame, text="Save", variable=save1_var, command=on_save1_toggle
    ).grid(row=0, column=2)

    # -----------------------------------------------------
    # TAB 2 — BACKGROUND NOISE ESTIMATION
    # -----------------------------------------------------
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="Background Noise Estimation")

    bg_top = tk.Frame(tab2)
    bg_top.pack(fill="x", padx=20, pady=10)

    tk.Label(bg_top, text="Background Image", font=("TkDefaultFont", 12, "bold")).grid(
        row=0, column=0, sticky="w"
    )

    bg_entry = tk.Entry(bg_top, width=50, font=entry_font)
    bg_entry.grid(row=1, column=0, pady=4, sticky="w")

    tk.Button(
        bg_top,
        text="Load Background Image",
        command=lambda: load_reference_image(bg_entry, bg_labels, tiles_store=bg_tiles),
    ).grid(row=1, column=1, padx=10, sticky="w")

    bg_est_btn = tk.Button(
        bg_top,
        text="Estimate Background Noise",
        width=22,
        height=4,
        command=estimate_background_noise,
    )
    bg_est_btn.grid(row=1, column=2, padx=10, sticky="w")

    bg_cam_frame = tk.LabelFrame(bg_top, text="Background Noise CAM Settings")
    bg_cam_frame.grid(row=1, column=3, padx=20, sticky="nw")

    bg_cam_top = tk.Frame(bg_cam_frame)
    bg_cam_top.grid(row=0, column=0, sticky="w")

    tk.Label(
        bg_cam_top,
        text="Background Noise Parameters",
        font=("TkDefaultFont", 11, "bold"),
    ).grid(row=0, column=0, sticky="w")

    bg_cam_entries = create_cam_entries(bg_cam_frame, entry_font)

    bg_frame = tk.Frame(tab2)
    bg_frame.pack(padx=6, pady=6)

    bg_labels = []
    for r, c in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        f = tk.Frame(bg_frame)
        f.grid(row=r, column=c, padx=6, pady=6)
        lbl = tk.Label(f)
        lbl.pack()
        bg_labels.append(lbl)

    # Auto-load first background from Data/Background and estimate once
    main.after(0, lambda: auto_load_background_and_estimate(bg_entry))

    # -----------------------------------------------------
    # TAB 3 — REFERENCE CALCULATION
    # -----------------------------------------------------
    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text="Reference Calculation")

    ref_top = tk.Frame(tab3)
    ref_top.pack(fill="x", padx=20, pady=10)

    tk.Label(ref_top, text="Reference Image", font=("TkDefaultFont", 12, "bold")).grid(
        row=0, column=0, sticky="w"
    )

    ref_entry = tk.Entry(ref_top, width=50, font=entry_font)
    ref_entry.grid(row=1, column=0, pady=4, sticky="w")
    ref_entry_widget = ref_entry

    tk.Button(
        ref_top,
        text="Load Reference Image",
        command=lambda: load_reference_image(
            ref_entry, ref_labels, tiles_store=ref_tiles
        ),
    ).grid(row=1, column=1, padx=10, sticky="w")

    ref_est_btn = tk.Button(
        ref_top,
        text="Estimate Reference Radiance",
        width=22,
        height=4,
        command=estimate_reference_radiance,
    )
    ref_est_btn.grid(row=1, column=2, padx=10, sticky="w")

    ref_cam_frame = tk.LabelFrame(ref_top, text="Reference Radiance CAM Settings")
    ref_cam_frame.grid(row=1, column=3, padx=20, sticky="nw")

    ref_cam_top = tk.Frame(ref_cam_frame)
    ref_cam_top.grid(row=0, column=0, sticky="w")

    tk.Label(
        ref_cam_top,
        text="Reference Radiance Parameters",
        font=("TkDefaultFont", 11, "bold"),
    ).grid(row=0, column=0, sticky="w")

    ref_cam_entries = create_cam_entries(ref_cam_frame, entry_font)

    ref_frame = tk.Frame(tab3)
    ref_frame.pack(padx=6, pady=6)

    ref_labels = []
    for r, c in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        f = tk.Frame(ref_frame)
        f.grid(row=r, column=c, padx=6, pady=6)
        lbl = tk.Label(f)
        lbl.pack()
        ref_labels.append(lbl)

    main.after(0, lambda: auto_load_reference(ref_entry))

    # -----------------------------------------------------
    # TAB 4 — RASTER / REFLECTANCE
    # -----------------------------------------------------
    tab4 = ttk.Frame(notebook)
    notebook.add(tab4, text="Raster Calculation")

    # Grid: col 0 = reflectance area, col 1 = raster area
    tab4.rowconfigure(0, weight=0)  # buttons
    tab4.rowconfigure(1, weight=1)  # tiles / calc
    tab4.rowconfigure(2, weight=0)  # save bar
    tab4.columnconfigure(0, weight=1)
    tab4.columnconfigure(1, weight=1)

    # Left: reflectance controls + tiles (column 0)
    left = tk.Frame(tab4)
    left.grid(row=0, column=0, padx=20, pady=10, sticky="nw")

    tk.Button(
        left,
        text="Reflectance Calculation",
        width=22,
        height=4,
        command=lambda: reflectance_calculation(),
    ).grid(row=0, column=0, padx=6)

    # Center: 2x2 reflectance tiles (row 1, col 0)
    center = tk.Frame(tab4)
    center.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")

    global refl_labels
    refl_labels = []
    for r, c in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        f = tk.Frame(center)
        f.grid(row=r, column=c, padx=6, pady=6)
        lbl = tk.Label(f)
        lbl.pack()
        refl_labels.append(lbl)

    # Right: raster button above calc_frame (column 1)
    right_top = tk.Frame(tab4)
    right_top.grid(row=0, column=1, padx=10, pady=10, sticky="nw")

    tk.Button(
        right_top,
        text="Raster Calculation",
        width=22,
        height=4,
        command=lambda: open_raster_dialog(main),
    ).grid(row=0, column=0, padx=6)

    global calc_label
    calc_frame = tk.Frame(tab4)
    calc_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

    calc_label = tk.Label(calc_frame)
    calc_label.pack(fill="both", expand=True)

    global save4_entry
    save4 = tk.Frame(tab4)
    save4.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="e")

    save4_entry = tk.Entry(save4, width=75, font=entry_font)
    save4_entry.grid(row=0, column=0)

    tk.Button(
        save4,
        text="Save Folder",
        command=lambda e=save4_entry: select_timestamp_folder_into_entry(e),
    ).grid(row=0, column=1, padx=5)

    save4_var = tk.BooleanVar(value=False)

    def on_save4_toggle():
        global save_tab4
        save_tab4 = save4_var.get()

    tk.Checkbutton(
        save4, text="Save", variable=save4_var, command=on_save4_toggle
    ).grid(row=0, column=2, padx=5)

    # -----------------------------------------------------
    # TAB 5 — CLASSIFICATION
    # -----------------------------------------------------
    tab5 = ttk.Frame(notebook)
    notebook.add(tab5, text="Classification")

    top5 = tk.Frame(tab5)
    top5.pack(fill="x", padx=20, pady=10)

    model_frame = tk.Frame(top5)
    model_frame.grid(row=0, column=0, sticky="w")

    tk.Label(
        model_frame, text="Classification Model", font=("TkDefaultFont", 12, "bold")
    ).grid(row=0, column=0, sticky="w")

    cls_entry = tk.Entry(model_frame, width=40, font=entry_font)
    cls_entry.grid(row=1, column=0, pady=4)

    tk.Button(model_frame, text="Load", command=lambda: load_joblib(cls_entry)).grid(
        row=1, column=1, padx=6
    )

    src_frame = tk.Frame(top5)
    src_frame.grid(row=0, column=1, sticky="e", padx=(40, 0))

    tk.Button(src_frame, text="From Calculated Reflectance", width=26, height=4).grid(
        row=0, column=0, padx=6
    )
    tk.Button(src_frame, text="From Calculated Raster", width=26, height=4).grid(
        row=0, column=1, padx=6
    )

    center5 = tk.Frame(tab5)
    center5.pack(expand=True, fill="both")

    ph5 = tk.Frame(center5, width=640, height=480, relief="solid", borderwidth=1)
    ph5.place(relx=0.5, rely=0.5, anchor="center")
    ph5.pack_propagate(False)
    tk.Label(ph5, text="480 x 640", font=("TkDefaultFont", 12, "bold")).place(
        relx=0.5, rely=0.5, anchor="center"
    )

    save5 = tk.Frame(tab5)
    save5.place(relx=1, rely=1, anchor="se", x=-20, y=-20)

    save5_entry = tk.Entry(save5, width=75, font=entry_font)
    save5_entry.grid(row=0, column=0)

    tk.Button(
        save5,
        text="Save Folder",
        command=lambda e=save5_entry: select_timestamp_folder_into_entry(e),
    ).grid(row=0, column=1)

    tk.Checkbutton(save5, text="Save").grid(row=0, column=2)

    # Start ZMQ receiver
    stop = threading.Event()
    threading.Thread(
        target=zmq_receiver, args=(image_labels, stop, save1_entry), daemon=True
    ).start()

    main.protocol("WM_DELETE_WINDOW", lambda: (stop.set(), main.destroy()))

    # Start periodic reflectance display updates
    update_reflectance_view(main)
    update_raster_expression(main)

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

tk.Label(root, text="Connecting Camera", font=("TkDefaultFont", 12, "bold")).pack(
    pady=8
)
tk.Label(root, text=f"Laptop LAN Address: {lan_ip}").pack(pady=4)

mid = tk.Frame(root)
mid.pack(pady=12)

tk.Label(mid, text="Camera IP:").grid(row=0, column=0, padx=6)

cam_ip_entry = tk.Entry(mid, width=20, font=tkfont.Font(size=12))
cam_ip_entry.grid(row=0, column=1)

tk.Button(
    mid,
    text="Detect",
    command=lambda: threading.Thread(target=detect_camera_ip, daemon=True).start(),
).grid(row=0, column=2, padx=6)


def on_ok():
    global ZMQ_ADDR
    ip = cam_ip_entry.get().strip()
    if not ip:
        messagebox.showwarning("Input Required", "Camera IP is empty")
        return

    ensure_data_folders()

    ZMQ_ADDR = f"tcp://{lan_ip}:5555"

    threading.Thread(
        target=ssh_check_camera, args=(ip, open_main_window), daemon=True
    ).start()


btns = tk.Frame(root)
btns.pack(pady=18)

tk.Button(btns, text="OK", width=10, command=on_ok).grid(row=0, column=0, padx=10)
tk.Button(btns, text="Cancel", width=10, command=root.destroy).grid(row=0, column=1)

root.mainloop()
