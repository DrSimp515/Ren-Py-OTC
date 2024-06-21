import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import json

CONFIG_FILE = 'config.json'
ICON_PATH = 'icon.ico'
WINDOW_TITLE = "Language"
WINDOW_SIZE = '300x250'
LANGUAGE_OPTIONS = {
    "English": "en",
    "Español": "es",
    "Français": "fr",
    "Italiano": "it",
    "Português (Brasil)": "pt_BR"
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as file:
                return json.load(file)
    except (IOError, json.JSONDecodeError) as e:
        messagebox.showerror("Error", f"Failed to load config: {e}")
    return {"selected_language": None}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as file:
            json.dump(config, file)
    except IOError as e:
        messagebox.showerror("Error", f"Failed to save config: {e}")

def set_window_icon(root):
    # Set the window icon
    if os.path.exists(ICON_PATH):
        root.iconbitmap(ICON_PATH)
    else:
        messagebox.showwarning("Icon Warning", f"Icon file '{ICON_PATH}' not found.")

def open_language_script(language, root=None):
    script_path = os.path.join("locales", language, "main.py")
    if os.path.exists(script_path):
        # Update the config file with the selected language
        config = load_config()
        config['selected_language'] = language
        save_config(config)

        # Close the main window if it exists
        if root is not None:
            root.destroy()

        # Run the script for the selected language
        try:
            subprocess.run(["python", script_path], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to run script: {e}")
    else:
        messagebox.showerror("Error", f"Script not found for {language}")

def show_language_selection():
    # Create the main window
    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.geometry(WINDOW_SIZE)
    root.resizable(False, False)

    # Set window icon
    set_window_icon(root)

    # Create the welcome message
    label = tk.Label(root, text="Select a language to continue:")
    label.pack(pady=10)

    # Create buttons for each language
    for lang_text, lang_code in LANGUAGE_OPTIONS.items():
        btn = tk.Button(root, text=lang_text, command=lambda lc=lang_code: open_language_script(lc, root))
        btn.pack(pady=5)

    # Run the main application loop
    root.mainloop()

def main():
    # Load the config
    config = load_config()

    # Check if the selected language is None
    selected_language = config.get("selected_language", None)
    if selected_language is None:
        show_language_selection()
    else:
        open_language_script(selected_language)

if __name__ == "__main__":
    main()
