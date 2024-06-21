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
    Processa o arquivo de entrada para limpar e escrever o conteúdo no arquivo de saída.

    Args:
    - input_file (str): Caminho do arquivo de entrada.
    - output_file (str): Caminho do arquivo de saída onde o conteúdo limpo será salvo.
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
    Função que envolve o processamento de um arquivo em uma thread separada.

    Args:
    - input_file (str): Caminho do arquivo de entrada.
    - output_file (str): Caminho do arquivo de saída onde o conteúdo limpo será salvo.
    """
    process_file(input_file, output_file)


def process_file_content(file_path, language, compiled_patterns, console_output):
    """
    Processa o conteúdo de um arquivo para adicionar comentários baseados em padrões específicos do idioma.

    Args:
    - file_path (str): Caminho do arquivo a ser processado.
    - language (str): Identificador do idioma.
    - compiled_patterns (dict): Padrões regex compilados para identificar blocos específicos do idioma.
    - console_output (tk.Text): Widget de texto para exibir mensagens e erros de processamento.
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
        console_output.insert(tk.END, f"Arquivo processado: {file_path}\n")
        console_output.config(state=tk.DISABLED)
    except Exception as e:
        console_output.config(state=tk.NORMAL)
        console_output.insert(tk.END, f"Erro ao processar o arquivo {file_path}: {e}\n")
        console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def add_comments(language, identifiers, console_output):
    """
    Adiciona comentários a todos os arquivos no diretório atual com base em identificadores específicos do idioma.

    Args:
    - language (str): Identificador do idioma.
    - identifiers (list): Lista de identificadores a serem procurados nos arquivos.
    - console_output (tk.Text): Widget de texto para exibir mensagens de processamento.
    """
    identifiers_set = set(identifiers)
    compiled_patterns = {
        identifier: re.compile(rf"(?m)^translate\s+{re.escape(language)}\s+{re.escape(identifier)}:(.*?)^(?=\S|\Z)", re.DOTALL)
        for identifier in identifiers_set
    }
    files = [os.path.join(root, name) for root, _, filenames in os.walk('.')
                for name in filenames if name.endswith('.rpy') or name.endswith('.rpym')]
    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, f"Iniciando o processo de adicionar comentários para o idioma {language}...\n\n")
    console_output.config(state=tk.DISABLED)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file_content, file, language, compiled_patterns, console_output): file for file in files}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console_output.config(state=tk.NORMAL)
                console_output.insert(tk.END, f"Erro ao processar o arquivo {futures[future]}: {e}\n")
                console_output.config(state=tk.DISABLED)
            console_output.see(tk.END)

    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, "\nProcesso concluído. Comentários adicionados a todos os arquivos.\n")
    console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def create_gui():
    """
    Cria a janela principal da GUI.
    """
    root = tk.Tk()
    root.title("Limpador de Traduções Órfãs")
    icon_path = 'icon.ico'
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    else:
        messagebox.showwarning("Aviso de Ícone", f"Arquivo de ícone '{icon_path}' não encontrado.")

    return root


def browse_file(entry):
    """
    Abre uma caixa de diálogo para procurar e selecionar um arquivo.

    Args:
    - entry (tk.Entry): Widget de entrada para definir o caminho do arquivo selecionado.
    """
    filename = filedialog.askopenfilename(title="Selecionar um arquivo", filetypes=[("Arquivos de texto", "*.txt")])
    entry.delete(0, tk.END)
    entry.insert(0, filename)


def clear_lint(lint_entry, clear_button):
    """
    Processa o arquivo lint para limpar e exibe o caminho do arquivo limpo na GUI.
    """
    lint_file = lint_entry.get()
    if not lint_file:
        messagebox.showerror("Erro", "Por favor selecione um arquivo lint")
        return

    clear_button.config(state="disabled")
    process_file(lint_file, "lint_limpo.txt")
    lint_entry.delete(0, tk.END)
    lint_entry.insert(0, os.path.abspath("lint_limpo.txt"))
    clear_button.config(state="normal")


def start_processing(language_entry, lint_entry, console_output):
    """
    Inicia o processo de adicionar comentários com base nos parâmetros selecionados.
    """
    cleaned_lint_path = lint_entry.get()
    if not cleaned_lint_path:
        messagebox.showerror("Erro", "Por favor selecione um arquivo lint limpo")
        return

    console_output.insert(tk.END, "\nLendo arquivo de IDs...\n")
    try:
        with open(cleaned_lint_path, 'r', encoding='utf-8') as f:
            identifiers = [id.strip() for id in f.read().split(',') if id.strip()]
    except Exception as e:
        console_output.insert(tk.END, f"Não foi possível ler o arquivo lint limpo: {e}\n")
        return

    add_comments(language_entry.get(), identifiers, console_output)


def main():
    """
    Função principal para criar a GUI e lidar com as interações do usuário.
    """
    root = create_gui()

    language_label = tk.Label(root, text="Idioma:")
    language_label.grid(row=0, column=0, sticky="w")
    ToolTip(language_label, "Selecione o idioma exatamente como está na tradução.")
    language_entry = tk.Entry(root)
    language_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="Arquivo Lint:").grid(row=1, column=0, sticky="w")
    lint_entry = tk.Entry(root)
    lint_entry.grid(row=1, column=1, padx=5, pady=5)
    lint_button = tk.Button(root, text="Procurar", command=lambda: browse_file(lint_entry))
    ToolTip(lint_button, "Selecione o Lint para limpar mais tarde ou simplesmente escolha um arquivo onde tenha os IDs separados por \",\".")
    lint_button.grid(row=1, column=2, padx=5, pady=5)

    clear_button = tk.Button(root, text="Limpar", command=lambda: clear_lint(lint_entry, clear_button))
    ToolTip(clear_button, "Limpa o arquivo lint selecionado.\n(Apenas IDs são mantidos)")
    clear_button.grid(row=2, column=0, columnspan=3, pady=10)

    process_button = tk.Button(root, text="Iniciar Processamento", command=lambda: start_processing(language_entry, lint_entry, console_output))
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
