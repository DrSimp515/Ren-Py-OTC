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
    Procesar el archivo de entrada para limpiarlo y escribir la salida en otro archivo.

    Args:
    - input_file (str): Ruta al archivo de entrada.
    - output_file (str): Ruta al archivo de salida donde se guardará el contenido limpio.
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
    Función contenedora para procesar un archivo en un hilo separado.

    Args:
    - input_file (str): Ruta al archivo de entrada.
    - output_file (str): Ruta al archivo de salida donde se guardará el contenido limpio.
    """
    process_file(input_file, output_file)


def process_file_content(file_path, language, compiled_patterns, console_output):
    """
    Procesar el contenido de un archivo para agregar comentarios basados en patrones específicos del idioma.

    Args:
    - file_path (str): Ruta al archivo a procesar.
    - language (str): Identificador del idioma.
    - compiled_patterns (dict): Patrones regex compilados para identificar bloques específicos del idioma.
    - console_output (tk.Text): Widget de texto para mostrar mensajes y errores de procesamiento.
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
        console_output.insert(tk.END, f"Archivo procesado: {file_path}\n")
        console_output.config(state=tk.DISABLED)
    except Exception as e:
        console_output.config(state=tk.NORMAL)
        console_output.insert(tk.END, f"Error procesando el archivo {file_path}: {e}\n")
        console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def add_comments(language, identifiers, console_output):
    """
    Agregar comentarios a todos los archivos en el directorio actual basados en identificadores específicos del idioma.

    Args:
    - language (str): Identificador del idioma.
    - identifiers (list): Lista de identificadores a buscar en los archivos.
    - console_output (tk.Text): Widget de texto para mostrar mensajes de procesamiento.
    """
    identifiers_set = set(identifiers)
    compiled_patterns = {
        identifier: re.compile(rf"(?m)^translate\s+{re.escape(language)}\s+{re.escape(identifier)}:(.*?)^(?=\S|\Z)", re.DOTALL)
        for identifier in identifiers_set
    }
    files = [os.path.join(root, name) for root, _, filenames in os.walk('.')
                for name in filenames if name.endswith('.rpy') or name.endswith('.rpym')]
    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, f"Iniciando el proceso de agregar comentarios para el idioma {language}...\n\n")
    console_output.config(state=tk.DISABLED)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file_content, file, language, compiled_patterns, console_output): file for file in files}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console_output.config(state=tk.NORMAL)
                console_output.insert(tk.END, f"Error procesando el archivo {futures[future]}: {e}\n")
                console_output.config(state=tk.DISABLED)
            console_output.see(tk.END)

    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, "\nProceso completado. Comentarios agregados a todos los archivos.\n")
    console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def create_gui():
    """
    Crear la ventana principal de la GUI.
    """
    root = tk.Tk()
    root.title("Limpiador de Traducciones Huérfanas")
    icon_path = 'icon.ico'
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    else:
        messagebox.showwarning("Advertencia de Icono", f"Archivo de icono '{icon_path}' no encontrado.")

    return root


def browse_file(entry):
    """
    Abrir un cuadro de diálogo para buscar y seleccionar un archivo.

    Args:
    - entry (tk.Entry): Widget de entrada para establecer la ruta del archivo seleccionado.
    """
    filename = filedialog.askopenfilename(title="Seleccionar un archivo", filetypes=[("Archivos de texto", "*.txt")])
    entry.delete(0, tk.END)
    entry.insert(0, filename)


def clear_lint(lint_entry, clear_button):
    """
    Procesar el archivo lint para limpiarlo y mostrar la ruta del archivo limpio en la GUI.
    """
    lint_file = lint_entry.get()
    if not lint_file:
        messagebox.showerror("Error", "Por favor seleccione un archivo lint")
        return

    clear_button.config(state="disabled")
    process_file(lint_file, "lint_limpio.txt")
    lint_entry.delete(0, tk.END)
    lint_entry.insert(0, os.path.abspath("lint_limpio.txt"))
    clear_button.config(state="normal")


def start_processing(language_entry, lint_entry, console_output):
    """
    Iniciar el proceso de agregar comentarios basados en los parámetros seleccionados.
    """
    cleaned_lint_path = lint_entry.get()
    if not cleaned_lint_path:
        messagebox.showerror("Error", "Por favor seleccione un archivo lint limpio")
        return

    console_output.insert(tk.END, "\nLeyendo archivo de IDs...\n")
    try:
        with open(cleaned_lint_path, 'r', encoding='utf-8') as f:
            identifiers = [id.strip() for id in f.read().split(',') if id.strip()]
    except Exception as e:
        console_output.insert(tk.END, f"No se pudo leer el archivo lint limpio: {e}\n")
        return

    add_comments(language_entry.get(), identifiers, console_output)


def main():
    """
    Función principal para crear la GUI y manejar las interacciones del usuario.
    """
    root = create_gui()

    language_label = tk.Label(root, text="Idioma:")
    language_label.grid(row=0, column=0, sticky="w")
    ToolTip(language_label, "Seleccione el idioma exactamente como está en la traducción.")
    language_entry = tk.Entry(root)
    language_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="Archivo Lint:").grid(row=1, column=0, sticky="w")
    lint_entry = tk.Entry(root)
    lint_entry.grid(row=1, column=1, padx=5, pady=5)
    lint_button = tk.Button(root, text="Buscar", command=lambda: browse_file(lint_entry))
    ToolTip(lint_button, "Seleccione el Lint para limpiarlo más tarde o simplemente elija un archivo donde tenga los ids separados por \",\".")
    lint_button.grid(row=1, column=2, padx=5, pady=5)

    clear_button = tk.Button(root, text="Limpiar", command=lambda: clear_lint(lint_entry, clear_button))
    ToolTip(clear_button, "Limpie el archivo lint seleccionado.\n(Solo se mantienen los ids)")
    clear_button.grid(row=2, column=0, columnspan=3, pady=10)

    process_button = tk.Button(root, text="Iniciar Procesamiento", command=lambda: start_processing(language_entry, lint_entry, console_output))
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
