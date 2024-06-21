import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tip_window = None

    def enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()


def process_file(input_file, output_file):
    """
    Elaborare il file di input per pulirlo e scrivere l'output in un altro file.

    Args:
    - input_file (str): Percorso del file di input.
    - output_file (str): Percorso del file di output dove verrà salvato il contenuto pulito.
    """
    with open(output_file, 'w', encoding='utf-8') as outfile:
        with open(input_file, 'r', encoding='utf-8') as infile:
            for line in infile:
                if '(id' in line:
                    line = re.sub(r'game/.+? \(id ', '', line)
                    line = re.sub(r'\), .+? \(id ', ',', line)
                    line = re.sub(r'\)\.', ',', line)
                    outfile.write(line)


def process_file_in_thread(input_file, output_file):
    """
    Funzione contenitore per elaborare un file in un thread separato.

    Args:
    - input_file (str): Percorso del file di input.
    - output_file (str): Percorso del file di output dove verrà salvato il contenuto pulito.
    """
    process_file(input_file, output_file)


def process_file_content(file_path, language, compiled_patterns, console_output):
    """
    Elaborare il contenuto di un file per aggiungere commenti basati su modelli specifici della lingua.

    Args:
    - file_path (str): Percorso del file da elaborare.
    - language (str): Identificatore della lingua.
    - compiled_patterns (dict): Modelli regex compilati per identificare blocchi specifici della lingua.
    - console_output (tk.Text): Widget di testo per visualizzare messaggi ed errori di elaborazione.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for identifier, block_pattern in compiled_patterns.items():
            block_match = block_pattern.search(content)
            if block_match:
                complete_block = block_match.group(0)
                block_lines = complete_block.strip().split("\n")
                modified_lines = ["# " + line if line.strip() else "" for line in block_lines]
                modified_block = "\n".join(modified_lines) + "\n\n"
                content = content.replace(complete_block, modified_block)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        console_output.config(state=tk.NORMAL)
        console_output.insert(tk.END, f"File elaborato: {file_path}\n")
        console_output.config(state=tk.DISABLED)
    except Exception as e:
        console_output.config(state=tk.NORMAL)
        console_output.insert(tk.END, f"Errore durante l'elaborazione del file {file_path}: {e}\n")
        console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def add_comments(language, identifiers, console_output):
    """
    Aggiungere commenti a tutti i file nella directory corrente basati su identificatori specifici della lingua.

    Args:
    - language (str): Identificatore della lingua.
    - identifiers (list): Elenco di identificatori da cercare nei file.
    - console_output (tk.Text): Widget di testo per visualizzare messaggi di elaborazione.
    """
    identifiers_set = set(identifiers)
    compiled_patterns = {
        identifier: re.compile(rf"(?m)^translate\s+{re.escape(language)}\s+{re.escape(identifier)}:(.*?)^(?=\S|\Z)", re.DOTALL)
        for identifier in identifiers_set
    }
    files = [os.path.join(root, name) for root, _, filenames in os.walk('.')
                for name in filenames if name.endswith('.rpy') or name.endswith('.rpym')]
    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, f"Inizio del processo di aggiunta commenti per la lingua {language}...\n\n")
    console_output.config(state=tk.DISABLED)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file_content, file, language, compiled_patterns, console_output): file for file in files}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console_output.config(state=tk.NORMAL)
                console_output.insert(tk.END, f"Errore durante l'elaborazione del file {futures[future]}: {e}\n")
                console_output.config(state=tk.DISABLED)
            console_output.see(tk.END)

    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, "\nProcesso completato. Commenti aggiunti a tutti i file.\n")
    console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def create_gui():
    """
    Creare la finestra principale della GUI.
    """
    root = tk.Tk()
    root.title("Pulitore di Traduzioni Orfane")
    icon_path = 'icon.ico'
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    else:
        messagebox.showwarning("Avviso Icona", f"File icona '{icon_path}' non trovato.")

    return root


def browse_file(entry):
    """
    Aprire una finestra di dialogo per cercare e selezionare un file.

    Args:
    - entry (tk.Entry): Widget di input per impostare il percorso del file selezionato.
    """
    filename = filedialog.askopenfilename(title="Selezionare un file", filetypes=[("File di testo", "*.txt")])
    entry.delete(0, tk.END)
    entry.insert(0, filename)


def clear_lint(lint_entry, clear_button):
    """
    Elaborare il file lint per pulirlo e visualizzare il percorso del file pulito nella GUI.
    """
    lint_file = lint_entry.get()
    if not lint_file:
        messagebox.showerror("Errore", "Selezionare un file lint")
        return

    clear_button.config(state="disabled")
    process_file(lint_file, "lint_pulito.txt")
    lint_entry.delete(0, tk.END)
    lint_entry.insert(0, os.path.abspath("lint_pulito.txt"))
    clear_button.config(state="normal")


def start_processing(language_entry, lint_entry, console_output):
    """
    Avviare il processo di aggiunta commenti basati sui parametri selezionati.
    """
    cleaned_lint_path = lint_entry.get()
    if not cleaned_lint_path:
        messagebox.showerror("Errore", "Selezionare un file lint pulito")
        return

    console_output.insert(tk.END, "\nLettura del file di ID...\n")
    try:
        with open(cleaned_lint_path, 'r', encoding='utf-8') as f:
            identifiers = [id.strip() for id in f.read().split(',') if id.strip()]
    except Exception as e:
        console_output.insert(tk.END, f"Impossibile leggere il file lint pulito: {e}\n")
        return

    add_comments(language_entry.get(), identifiers, console_output)


def main():
    """
    Funzione principale per creare la GUI e gestire le interazioni dell'utente.
    """
    root = create_gui()

    language_label = tk.Label(root, text="Lingua:")
    language_label.grid(row=0, column=0, sticky="w")
    ToolTip(language_label, "Selezionare la lingua esattamente come appare nella traduzione.")
    language_entry = tk.Entry(root)
    language_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="File Lint:").grid(row=1, column=0, sticky="w")
    lint_entry = tk.Entry(root)
    lint_entry.grid(row=1, column=1, padx=5, pady=5)
    lint_button = tk.Button(root, text="Cerca", command=lambda: browse_file(lint_entry))
    ToolTip(lint_button, "Selezionare il Lint per pulirlo successivamente o semplicemente scegliere un file che contiene gli id separati da \",\".")
    lint_button.grid(row=1, column=2, padx=5, pady=5)

    clear_button = tk.Button(root, text="Pulire", command=lambda: clear_lint(lint_entry, clear_button))
    ToolTip(clear_button, "Pulire il file lint selezionato.\n(Saranno mantenuti solo gli id)")
    clear_button.grid(row=2, column=0, columnspan=3, pady=10)

    process_button = tk.Button(root, text="Avviare Elaborazione", command=lambda: start_processing(language_entry, lint_entry, console_output))
    process_button.grid(row=3, column=0, columnspan=3, pady=10)

    console_frame = tk.Frame(root)
    console_frame.grid(row=4, column=0, columnspan=3, pady=10)
    console_label = tk.Label(console_frame, text="Registro:")
    console_label.pack(side=tk.TOP, anchor="w")
    console_output = tk.Text(console_frame, height=10, width=60)
    console_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    console_scrollbar = tk.Scrollbar(console_frame, orient=tk.VERTICAL, command=console_output.yview)
    console_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    console_output.config(yscrollcommand=console_scrollbar.set)
    console_output.config(state=tk.DISABLED)

    root.mainloop()


if __name__ == "__main__":
    main()
