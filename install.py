import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import importlib
import os
import threading

# Pacotes e módulos correspondentes
PACKAGE_MODULE_MAP = {
    "annotated-types": "annotated_types",
    "anyio": "anyio",
    "appdirs": "appdirs",
    "certifi": "certifi",
    "colorama": "colorama",
    "distro": "distro",
    "h11": "h11",
    "httpcore": "httpcore",
    "httpx": "httpx",
    "idna": "idna",
    "jiter": "jiter",
    "llvmlite": "llvmlite",
    "Mako": "mako",
    "MarkupSafe": "markupsafe",
    "numpy": "numpy",
    "openai": "openai",
    "paho-mqtt": "paho.mqtt",
    "pillow": "PIL",
    "platformdirs": "platformdirs",
    "pydantic": "pydantic",
    "pydantic_core": "pydantic_core",
    "pyglet": "pyglet",
    "pyserial": "serial",
    "pytools": "pytools",
    "pytube": "pytube",
    "pywin32": "win32api",
    "setuptools": "setuptools",
    "sniffio": "sniffio",
    "tk": "tkinter",
    "tqdm": "tqdm",
    "ttkthemes": "ttkthemes",
    "typing_extensions": "typing_extensions",
    "Unidecode": "unidecode",
    "WMI": "wmi",
    "yt-dlp": "yt_dlp",
}

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VSSS Project Installer")
        self.configure(bg="#2b2b2b")
        self.geometry("600x450")
        self.center_window()
        self.installing = False
        self.cancel_requested = False

        # Ícone (coloque installer_icon.ico na mesma pasta)
        icon_path = os.path.join(os.path.dirname(__file__), "installer_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Título
        tk.Label(self, text="VSSS Project Installer", font=("Segoe UI", 16, "bold"), fg="#f0f0f0", bg="#2b2b2b").pack(pady=10)

        # Barra de progresso
        self.progress = ttk.Progressbar(self, length=500, mode="determinate")
        self.progress.pack(pady=10)

        # Status
        self.status_text = tk.StringVar()
        self.status_label = tk.Label(self, textvariable=self.status_text, font=("Segoe UI", 11), fg="#e0e0e0", bg="#2b2b2b")
        self.status_label.pack(pady=5)

        # Log detalhado
        self.log_box = tk.Text(self, height=12, width=70, bg="#1e1e1e", fg="#d0d0d0", state="disabled", font=("Consolas", 10))
        self.log_box.pack(pady=10)

        # Botões
        self.button_frame = tk.Frame(self, bg="#2b2b2b")
        self.button_frame.pack(pady=10)

        self.install_button = tk.Button(self.button_frame, text="Instalar", command=self.start_install_thread, width=12)
        self.install_button.pack(side="left", padx=10)

        self.cancel_button = tk.Button(self.button_frame, text="Cancelar", command=self.cancel_install, width=12, state="disabled")
        self.cancel_button.pack(side="left", padx=10)

        self.start_button = tk.Button(self.button_frame, text="Iniciar Aplicação", command=self.run_main, width=16, state="disabled")
        self.start_button.pack(side="left", padx=10)

        # Estilo da barra de progresso
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TProgressbar", thickness=25, troughcolor="#444444", background="#00bfff")

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def start_install_thread(self):
        self.install_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.progress["value"] = 0
        self.status_text.set("Iniciando instalação...")
        self.cancel_requested = False
        threading.Thread(target=self.install_packages, daemon=True).start()

    def cancel_install(self):
        if self.installing:
            self.cancel_requested = True
            self.status_text.set("Cancelando instalação...")

    def install_packages(self):
        self.installing = True
        total = len(PACKAGE_MODULE_MAP)
        self.progress["maximum"] = total

        for i, (pkg, module) in enumerate(PACKAGE_MODULE_MAP.items(), start=1):
            if self.cancel_requested:
                self.status_text.set("Instalação cancelada.")
                self.log("[!] Instalação cancelada pelo usuário")
                self.installing = False
                self.install_button.config(state="normal")
                self.cancel_button.config(state="disabled")
                return

            self.status_text.set(f"Verificando {pkg}...")
            self.update()
            if not self.is_installed(module):
                self.status_text.set(f"Instalando {pkg}...")
                self.update()
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    self.log(f"[✔] {pkg} instalado com sucesso")
                except subprocess.CalledProcessError:
                    self.log(f"[✖] Falha ao instalar {pkg}")
            else:
                self.log(f"[i] {pkg} já está instalado")

            self.progress["value"] = i
            self.update()

        self.status_text.set("Instalação concluída!")
        self.log("[✔] Todos os pacotes estão prontos")
        messagebox.showinfo("Concluído", "Todos os pacotes necessários foram instalados.")
        self.installing = False
        self.cancel_button.config(state="disabled")
        self.start_button.config(state="normal")

    @staticmethod
    def is_installed(module_name):
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False

    def run_main(self):
        main_path = os.path.join(os.path.dirname(__file__), "main.py")
        if os.path.exists(main_path):
            # Inicia o main.py
            subprocess.Popen([sys.executable, main_path])
            # Fecha a janela do instalador
            self.destroy()
        else:
            messagebox.showerror("Erro", "main.py não encontrado!")


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
