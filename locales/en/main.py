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
    Process the input file to clean and write the output to another file.

    Args:
    - input_file (str): Path to the input file.
    - output_file (str): Path to the output file where cleaned content will be saved.
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
    Wrapper function to process a file in a separate thread.

    Args:
    - input_file (str): Path to the input file.
    - output_file (str): Path to the output file where cleaned content will be saved.
    """
    process_file(input_file, output_file)


def process_file_content(file_path, language, compiled_patterns, console_output):
    """
    Process the content of a file to add comments based on language-specific patterns.

    Args:
    - file_path (str): Path to the file to be processed.
    - language (str): Language identifier.
    - compiled_patterns (dict): Compiled regex patterns for identifying language-specific blocks.
    - console_output (tk.Text): Text widget to display processing messages and errors.
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
        console_output.insert(tk.END, f"File processed: {file_path}\n")
        console_output.config(state=tk.DISABLED)
    except Exception as e:
        console_output.config(state=tk.NORMAL)
        console_output.insert(tk.END, f"Error processing file {file_path}: {e}\n")
        console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def add_comments(language, identifiers, console_output):
    """
    Add comments to all files in the current directory based on language-specific identifiers.

    Args:
    - language (str): Language identifier.
    - identifiers (list): List of identifiers to search for in files.
    - console_output (tk.Text): Text widget to display processing messages.
    """
    identifiers_set = set(identifiers)
    compiled_patterns = {
        identifier: re.compile(rf"(?m)^translate\s+{re.escape(language)}\s+{re.escape(identifier)}:(.*?)^(?=\S|\Z)", re.DOTALL)
        for identifier in identifiers_set
    }
    files = [os.path.join(root, name) for root, _, filenames in os.walk('.')
                for name in filenames if name.endswith('.rpy') or name.endswith('.rpym')]
    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, f"Starting process of adding comments for language {language}...\n\n")
    console_output.config(state=tk.DISABLED)

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file_content, file, language, compiled_patterns, console_output): file for file in files}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                console_output.config(state=tk.NORMAL)
                console_output.insert(tk.END, f"Error processing file {futures[future]}: {e}\n")
                console_output.config(state=tk.DISABLED)
            console_output.see(tk.END)

    console_output.config(state=tk.NORMAL)
    console_output.insert(tk.END, "\nProcess completed. Comments added to all files.\n")
    console_output.config(state=tk.DISABLED)
    console_output.see(tk.END)


def create_gui():
    """
    Create the main GUI window.
    """
    root = tk.Tk()
    root.title("Orphaned Translations Cleaner")
    icon_path = 'icon.ico'
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    else:
        messagebox.showwarning("Icon Warning", f"Icon file '{icon_path}' not found.")

    return root


def browse_file(entry):
    """
    Open a file dialog to browse and select a file.

    Args:
    - entry (tk.Entry): Entry widget to set the selected file path.
    """
    filename = filedialog.askopenfilename(title="Select a file", filetypes=[("Text files", "*.txt")])
    entry.delete(0, tk.END)
    entry.insert(0, filename)


def clear_lint(lint_entry, clear_button):
    """
    Process the lint file to clean it and display the path to the cleaned file in the GUI.
    """
    lint_file = lint_entry.get()
    if not lint_file:
        messagebox.showerror("Error", "Please select a lint file")
        return

    clear_button.config(state="disabled")
    process_file(lint_file, "cleaned_lint.txt")
    lint_entry.delete(0, tk.END)
    lint_entry.insert(0, os.path.abspath("cleaned_lint.txt"))
    clear_button.config(state="normal")


def start_processing(language_entry, lint_entry, console_output):
    """
    Start the process of adding comments based on selected parameters.
    """
    cleaned_lint_path = lint_entry.get()
    if not cleaned_lint_path:
        messagebox.showerror("Error", "Please select a cleaned lint file")
        return

    console_output.insert(tk.END, "\nReading IDs file...\n")
    try:
        with open(cleaned_lint_path, 'r', encoding='utf-8') as f:
            identifiers = [id.strip() for id in f.read().split(',') if id.strip()]
    except Exception as e:
        console_output.insert(tk.END, f"Could not read cleaned lint file: {e}\n")
        return

    add_comments(language_entry.get(), identifiers, console_output)


def main():
    """
    Main function to create the GUI and handle user interactions.
    """
    root = create_gui()

    language_label = tk.Label(root, text="Language:")
    language_label.grid(row=0, column=0, sticky="w")
    ToolTip(language_label, "Select the language exactly as it is in the translation.")
    language_entry = tk.Entry(root)
    language_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="Lint File:").grid(row=1, column=0, sticky="w")
    lint_entry = tk.Entry(root)
    lint_entry.grid(row=1, column=1, padx=5, pady=5)
    lint_button = tk.Button(root, text="Browse", command=lambda: browse_file(lint_entry))
    ToolTip(lint_button, "Select the Lint to clean it later or simply choose a file where you have the ids separated by \",\".")
    lint_button.grid(row=1, column=2, padx=5, pady=5)

    clear_button = tk.Button(root, text="Clear", command=lambda: clear_lint(lint_entry, clear_button))
    ToolTip(clear_button, "Clear the selected lint file.\n(Only the ids are left)")
    clear_button.grid(row=2, column=0, columnspan=3, pady=10)

    process_button = tk.Button(root, text="Start Processing", command=lambda: start_processing(language_entry, lint_entry, console_output))
    process_button.grid(row=3, column=0, columnspan=3, pady=10)

    console_frame = tk.Frame(root)
    console_frame.grid(row=4, column=0, columnspan=3, pady=10)
    console_label = tk.Label(console_frame, text="Log:")
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
