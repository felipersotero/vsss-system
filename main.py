import sys
import os
import importlib.util
import subprocess
import tkinter as tk
from tkinter import messagebox

REQUIREMENTS_FILE = "src/data/requirements.txt"
INSTALATOR_SCRIPT = "install.py"

PACKAGE_MODULE_MAP = {
    "annotated-types": "annotated_types",
    "anyio": "anyio",
    "appdirs": "appdirs",
    "certifi": "certifi",
    "colorama": "colorama",
    "distro": "distro",
    "h11": "h11",

    # Ferramentas de análise / lint (presentes no requirements)
    "astroid": "astroid",
    "isort": "isort",
    "lazy-object-proxy": "lazy_object_proxy",
    "mccabe": "mccabe",
    "pylint": "pylint",
    "six": "six",
    "toml": "toml",
    "wrapt": "wrapt",

    # Serialização / comunicação
    "protobuf": "google.protobuf",

    # HTTP / async
    "httpcore": "httpcore",
    "httpx": "httpx",
    "idna": "idna",
    "sniffio": "sniffio",

    # Core numérico / científico
    "numpy": "numpy",
    "llvmlite": "llvmlite",

    # Templates / utils
    "Mako": "mako",
    "MarkupSafe": "markupsafe",

    # APIs / SDKs
    "openai": "openai",
    "jiter": "jiter",
    "pydantic": "pydantic",
    "pydantic_core": "pydantic_core",
    "typing_extensions": "typing_extensions",

    # Comunicação / IO
    "paho-mqtt": "paho.mqtt",
    "pyserial": "serial",

    # Multimídia / GUI
    "pillow": "PIL",
    "pyglet": "pyglet",
    "ttkthemes": "ttkthemes",
    "tk": "tkinter",  # OBS: tkinter não é instalado via pip

    # Utilidades
    "platformdirs": "platformdirs",
    "pytools": "pytools",
    "tqdm": "tqdm",
    "Unidecode": "unidecode",

    # Download / mídia
    "pytube": "pytube",
    "yt-dlp": "yt_dlp",

    # Sistema / Windows
    "pywin32": "win32api",
    "WMI": "wmi",

    # Build
    "setuptools": "setuptools",
}

def parse_requirements(file_path):
    if not os.path.isfile(file_path):
        messagebox.showerror("Erro", f"Arquivo de requirements não encontrado:\n{file_path}")
        sys.exit(1)

    packages = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pkg = line.split("==")[0]
                packages.append(pkg)
    return packages

def is_installed(package_name):
    module_name = PACKAGE_MODULE_MAP.get(package_name, package_name.replace("-", "_").lower())
    return importlib.util.find_spec(module_name) is not None

def check_missing_packages():
    packages = parse_requirements(REQUIREMENTS_FILE)
    missing = [pkg for pkg in packages if not is_installed(pkg)]
    return missing

def prompt_install():
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal
    missing = check_missing_packages()
    if missing:
        msg = "Alguns pacotes necessários não estão instalados:\n\n"
        msg += ", ".join(missing[:10])
        if len(missing) > 10:
            msg += f", ... (+{len(missing)-10} outros)"
        msg += "\n\nDeseja instalar agora?"
        if messagebox.askyesno("Dependências faltando", msg):
            root.destroy()
            # Chama o instalador
            subprocess.call([sys.executable, INSTALATOR_SCRIPT])
        else:
            messagebox.showwarning("Atenção", "O programa pode não funcionar corretamente sem os pacotes necessários.")
            root.destroy()
    else:
        root.destroy()

# Primeiro verifica e instala se necessário
prompt_install()

# Agora adiciona src/ ao path e inicia a aplicação
sys.path.append("./src/")
from app import App

app = App()
