#!/usr/bin/env python3

import os
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# config management
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

config = load_config()

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".alac", ".wma",
    ".aiff", ".ape", ".opus", ".mid", ".midi", ".dsf", ".dff", ".mp2",
    ".mpc", ".ra", ".rm", ".au", ".snd", ".oga"
}

NON_AUDIO_EXTENSIONS = set(config.get("junk_extensions", [
    ".jpg", ".png", ".cue", ".m3u", ".log", ".txt", ".nfo", ".sfv", ".db"
]))
PROCESS_EMPTY = config.get("process_empty", True)
LAST_PATH = config.get("last_path", "")

# logic
def clean_folders(root_folder, move_to_backup=False):
    processed_items = []
    main_backup = os.path.join(root_folder, "_for_delete")
    empty_backup = os.path.join(main_backup, "_empty_folders")
    junk_backup = os.path.join(main_backup, "_junk_folders")

    audio_folders = set()
    for dirpath, dirnames, filenames in os.walk(root_folder):
        if dirpath.startswith(main_backup):
            continue
        if any(os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS for f in filenames):
            audio_folders.add(dirpath)

    protected_folders = set(audio_folders)
    for folder in list(audio_folders):
        parent = os.path.dirname(folder)
        while parent and parent.startswith(root_folder):
            protected_folders.add(parent)
            if parent == root_folder:
                break
            parent = os.path.dirname(parent)

    for dirpath, dirnames, filenames in os.walk(root_folder, topdown=False):
        if dirpath.startswith(main_backup):
            continue

        if dirpath in protected_folders:
            for f in filenames:
                ext = os.path.splitext(f)[1].lower()
                if ext in NON_AUDIO_EXTENSIONS:
                    file_path = os.path.join(dirpath, f)
                    try:
                        if move_to_backup:
                            os.makedirs(junk_backup, exist_ok=True)
                            rel_path = os.path.relpath(file_path, root_folder)
                            target = os.path.join(junk_backup, rel_path)
                            if not os.path.exists(target):
                                os.makedirs(os.path.dirname(target), exist_ok=True)
                                shutil.move(file_path, target)
                                action = "moved junk file"
                            else:
                                action = "skipped junk file (already exists)"
                            processed_items.append((file_path, action))
                        else:
                            os.remove(file_path)
                            processed_items.append((file_path, "deleted junk file"))
                    except Exception as e:
                        processed_items.append((file_path, f"error: {e}"))
            continue

        if PROCESS_EMPTY and not filenames and not dirnames:
            action = "moved (empty)" if move_to_backup else "deleted (empty)"
            try:
                if move_to_backup:
                    os.makedirs(empty_backup, exist_ok=True)
                    rel_path = os.path.relpath(dirpath, root_folder)
                    target = os.path.join(empty_backup, rel_path)
                    if not os.path.exists(target):
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        shutil.move(dirpath, target)
                    else:
                        action = "skipped (already exists)"
                else:
                    shutil.rmtree(dirpath)
                processed_items.append((dirpath, action))
            except Exception as e:
                processed_items.append((dirpath, f"error: {e}"))

        elif not any(os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS for f in filenames):
            action = "moved (junk folder)" if move_to_backup else "deleted (junk folder)"
            try:
                if move_to_backup:
                    os.makedirs(junk_backup, exist_ok=True)
                    rel_path = os.path.relpath(dirpath, root_folder)
                    target = os.path.join(junk_backup, rel_path)
                    if not os.path.exists(target):
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        shutil.move(dirpath, target)
                    else:
                        action = "skipped (already exists)"
                else:
                    shutil.rmtree(dirpath)
                processed_items.append((dirpath, action))
            except Exception as e:
                processed_items.append((dirpath, f"error: {e}"))

    return processed_items

def count_items(root_folder):
    count = 0
    main_backup = os.path.join(root_folder, "_for_delete")
    for dirpath, dirnames, filenames in os.walk(root_folder, topdown=False):
        if dirpath.startswith(main_backup):
            continue
        if PROCESS_EMPTY and not filenames and not dirnames:
            count += 1
        elif not any(os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS for f in filenames):
            count += 1
        else:
            for f in filenames:
                ext = os.path.splitext(f)[1].lower()
                if ext in NON_AUDIO_EXTENSIONS:
                    count += 1
    return count

# that message that lets you know is processing or finished or whatever
def show_status(message):
    status_label.config(text=message)
    status_label.after(5000, lambda: status_label.config(text="Waiting for something to happen."))

# folder selection and processing stuff
def select_folder():
    global LAST_PATH
    folder = filedialog.askdirectory(initialdir=LAST_PATH if LAST_PATH else None)
    if not folder or not os.path.isdir(folder):
        show_status("Invalid folder selected.")
        return

    LAST_PATH = folder
    config["last_path"] = LAST_PATH
    save_config(config)

    move_to_backup = backup_var.get()
    total_items = count_items(folder)

    if total_items == 0:
        show_status("No folders or junk files were found in this folder.")
        return

    confirm = messagebox.askyesno("Confirm", f"Do you wish to continue?")
    if not confirm:
        return

    processed = clean_folders(folder, move_to_backup)

    if not processed:
        show_status("No folders or junk files were found in this folder.")
        return

    action = "moved to backup" if move_to_backup else "deleted"
    show_status(f"Cleanup finished successfully! {len(processed)} items {action}.")

# settings
def open_settings():
    settings_win = tb.Toplevel(app)
    settings_win.title("Settings")
    settings_win.resizable(False, False)

    frame = tb.Frame(settings_win, padding=10)
    frame.pack(expand=True, fill="both")

    junk_label = tb.Label(frame, text="File extensions (separate with commas)", font=("Ubuntu", 12))
    junk_label.pack(pady=5)
    junk_entry = tb.Entry(frame, width=50)
    junk_entry.insert(0, ", ".join(ext.lstrip(".") for ext in NON_AUDIO_EXTENSIONS))
    junk_entry.pack(pady=10)

    empty_var = tk.BooleanVar(value=PROCESS_EMPTY)
    empty_checkbox = tb.Checkbutton(frame, text="Process empty folders", variable=empty_var, bootstyle="success-round-toggle")
    empty_checkbox.pack(pady=10)

    def save_settings():
        global NON_AUDIO_EXTENSIONS, PROCESS_EMPTY
        try:
            NON_AUDIO_EXTENSIONS = {
                "." + ext.strip().lstrip(".")
                for ext in junk_entry.get().split(",")
                if ext.strip()
            }
            PROCESS_EMPTY = empty_var.get()

            config["junk_extensions"] = list(NON_AUDIO_EXTENSIONS)
            config["process_empty"] = PROCESS_EMPTY
            save_config(config)

            show_status("Settings updated successfully!")
        except Exception as e:
            show_status(f"Error updating settings: {e}")
        settings_win.destroy()

    def cancel_settings():
        settings_win.destroy()

    def restore_defaults():
        global NON_AUDIO_EXTENSIONS
        NON_AUDIO_EXTENSIONS = {".jpg", ".png", ".cue", ".m3u", ".log", ".txt", ".nfo", ".sfv", ".db"}
        junk_entry.delete(0, tk.END)
        junk_entry.insert(0, ", ".join(ext.lstrip(".") for ext in NON_AUDIO_EXTENSIONS))
        config["junk_extensions"] = list(NON_AUDIO_EXTENSIONS)
        save_config(config)
        show_status("Junk file extensions restored to default!")

    btn_frame = tb.Frame(frame)
    btn_frame.pack(pady=5)

    save_btn = tb.Button(btn_frame, text="Save", command=save_settings, bootstyle="success-outline", width=12)
    save_btn.pack(side="left", padx=5)

    cancel_btn = tb.Button(btn_frame, text="Cancel", command=cancel_settings, bootstyle="danger-outline", width=12)
    cancel_btn.pack(side="left", padx=5)

    restore_btn = tb.Button(btn_frame, text="Restore", command=restore_defaults, bootstyle="info-outline", width=12)
    restore_btn.pack(side="left", padx=5)

    settings_win.update_idletasks()
    settings_win.geometry(f"500x{settings_win.winfo_height()}")

# ui setup
app = tb.Window(themename="darkly")
app.title("Hkefp's music folder cleaner")
app.resizable(False, False)

frame = tb.Frame(app, padding=10)
frame.pack(expand=True, fill="both", anchor="center", pady=20)

# main label
main_label = tb.Label(frame, text=":D", font=("Ubuntu", 20, "bold"))
main_label.pack(pady=0)

# status label
status_label = tb.Label(frame, font=("Ubuntu", 12), bootstyle="info", text="Waiting for something to happen.")
status_label.pack(anchor="center", pady=10)

# backup toggle
backup_var = tk.BooleanVar()
checkbox = tb.Checkbutton(frame, text="Backup", variable=backup_var, bootstyle="success-round-toggle")
checkbox.pack(pady=5)

# folder button
btn = tb.Button(frame, text="Choose Folder", command=select_folder, bootstyle="success-outline", width=12)
btn.pack(pady=5)

# settings button
settings_btn = tb.Button(frame, text="Settings", command=open_settings, bootstyle="info-outline", width=12)
settings_btn.pack(pady=5)

# footer
footer = tb.Label(app, text="Created by Hkefp", font=("Ubuntu", 8), bootstyle="secondary")
footer.pack(side="bottom", pady=0)

img = tk.PhotoImage(file='/home/hkefp/Desktop/projects/bulk_delete/ico.png')
app.iconphoto(False, img)

app.geometry(f"500x300")
app.mainloop()

