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
    Traiter le fichier d'entrée pour le nettoyer et écrire la sortie dans un autre fichier.

    Args:
    - input_file (str): Chemin vers le fichier d'entrée.
    - output_file (str): Chemin vers le fichier de sortie où le contenu nettoyé sera enregistré.
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
    Fonction de conteneur pour traiter un fichier dans un fil séparé.

    Args:
    - input_file (str): Chemin vers le fichier d'entrée.
    - output_file (str): Chemin vers le fichier de sortie où le contenu nettoyé sera enregistré.
    """
    process_file(input_file, output_file)


def process_file_content(file_path, language, compiled_patterns, console_output):
    """
    Traiter le contenu d'un fichier pour ajouter des commentaires basés sur des motifs spécifiques à la langue.

    Args:
    - file_path (str): Chemin vers le fichier à traiter.
    - language (str): Identifiant de la langue.
    - compiled_patterns (dict): Modèles regex compilés pour identifier des blocs spécifiques à la langue.
    - console_output (tk.Text): Widget de texte pour afficher les messages et erreurs de traitement.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for identifier, block_pattern in compiled_patterns.items():
            block_match = block_pattern.search(content)
            if (block_match):
                complete_block = block_match.group(0)
                block_lines = complete_block.strip().split("\n")
                modified_lines = ["# " + line if line.strip() else "" for line in block_lines]
                modified_block = "\n".join(modified_lines) + "\n\n"
                content = content.replace(complete_block, modified_block)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        console_output.config(state=tk.NORMAL)
        console_output.insert(tk.END, f"Fichier traité: {file_path}\n")
        console_output.config(state=tk.DISABLED)
    except Exception as e:
        console_output.config(state=tk.NORMAL)
        console_output.insert(tk.END, f"Erreur lors du traitement du fichier {file_path}: {e}\n")
        console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def add_comments(language, identifiers, console_output):
    """
    Ajouter des commentaires à tous les fichiers du répertoire actuel en fonction des identifiants spécifiques à la langue.

    Args:
    - language (str): Identifiant de la langue.
    - identifiers (list): Liste des identifiants à rechercher dans les fichiers.
    - console_output (tk.Text): Widget de texte pour afficher les messages de traitement.
    """
    identifiers_set = set(identifiers)
    compiled_patterns = {
        identifier: re.compile(rf"(?m)^translate\s+{re.escape(language)}\s+{re.escape(identifier)}:(.*?)^(?=\S|\Z)", re.DOTALL)
        for identifier in identifiers_set
    }
    files = [os.path.join(root, name) for root, _, filenames in os.walk('.')
                for name in filenames if name.endswith('.rpy') or name.endswith('.rpym')]
    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, f"Début du processus d'ajout de commentaires pour la langue {language}...\n\n")
    console_output.config(state=tk.DISABLED)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file_content, file, language, compiled_patterns, console_output): file for file in files}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console_output.config(state=tk.NORMAL)
                console_output.insert(tk.END, f"Erreur lors du traitement du fichier {futures[future]}: {e}\n")
                console_output.config(state=tk.DISABLED)
            console_output.see(tk.END)

    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, "\nProcessus terminé. Commentaires ajoutés à tous les fichiers.\n")
    console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def create_gui():
    """
    Créer la fenêtre principale de l'interface graphique.
    """
    root = tk.Tk()
    root.title("Nettoyeur de Traductions Orphelines")
    icon_path = 'icon.ico'
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    else:
        messagebox.showwarning("Avertissement d'icône", f"Fichier d'icône '{icon_path}' non trouvé.")

    return root


def browse_file(entry):
    """
    Ouvrir une boîte de dialogue pour rechercher et sélectionner un fichier.

    Args:
    - entry (tk.Entry): Widget d'entrée pour définir le chemin du fichier sélectionné.
    """
    filename = filedialog.askopenfilename(title="Sélectionner un fichier", filetypes=[("Fichiers texte", "*.txt")])
    entry.delete(0, tk.END)
    entry.insert(0, filename)


def clear_lint(lint_entry, clear_button):
    """
    Traiter le fichier lint pour le nettoyer et afficher le chemin du fichier nettoyé dans l'interface graphique.
    """
    lint_file = lint_entry.get()
    if not lint_file:
        messagebox.showerror("Erreur", "Veuillez sélectionner un fichier lint")
        return

    clear_button.config(state="disabled")
    process_file(lint_file, "lint_nettoye.txt")
    lint_entry.delete(0, tk.END)
    lint_entry.insert(0, os.path.abspath("lint_nettoye.txt"))
    clear_button.config(state="normal")


def start_processing(language_entry, lint_entry, console_output):
    """
    Démarrer le processus d'ajout de commentaires basés sur les paramètres sélectionnés.
    """
    cleaned_lint_path = lint_entry.get()
    if not cleaned_lint_path:
        messagebox.showerror("Erreur", "Veuillez sélectionner un fichier lint nettoyé")
        return

    console_output.insert(tk.END, "\nLecture du fichier d'IDs...\n")
    try:
        with open(cleaned_lint_path, 'r', encoding='utf-8') as f:
            identifiers = [id.strip() for id in f.read().split(',') if id.strip()]
    except Exception as e:
        console_output.insert(tk.END, f"Impossible de lire le fichier lint nettoyé: {e}\n")
        return

    add_comments(language_entry.get(), identifiers, console_output)


def main():
    """
    Fonction principale pour créer l'interface graphique et gérer les interactions utilisateur.
    """
    root = create_gui()

    language_label = tk.Label(root, text="Langue:")
    language_label.grid(row=0, column=0, sticky="w")
    ToolTip(language_label, "Sélectionnez la langue exactement comme elle apparaît dans la traduction.")
    language_entry = tk.Entry(root)
    language_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="Fichier Lint:").grid(row=1, column=0, sticky="w")
    lint_entry = tk.Entry(root)
    lint_entry.grid(row=1, column=1, padx=5, pady=5)
    lint_button = tk.Button(root, text="Parcourir", command=lambda: browse_file(lint_entry))
    ToolTip(lint_button, "Sélectionnez le Lint pour le nettoyer plus tard ou choisissez simplement un fichier contenant les ids séparés par \",\".")
    lint_button.grid(row=1, column=2, padx=5, pady=5)

    clear_button = tk.Button(root, text="Nettoyer", command=lambda: clear_lint(lint_entry, clear_button))
    ToolTip(clear_button, "Nettoyez le fichier lint sélectionné.\n(Seuls les ids sont conservés)")
    clear_button.grid(row=2, column=0, columnspan=3, pady=10)

    process_button = tk.Button(root, text="Démarrer le traitement", command=lambda: start_processing(language_entry, lint_entry, console_output))
    process_button.grid(row=3, column=0, columnspan=3, pady=10)

    console_frame = tk.Frame(root)
    console_frame.grid(row=4, column=0, columnspan=3, pady=10)
    console_label = tk.Label(console_frame, text="Journal:")
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
