import sys
import subprocess
import pkg_resources
import os

# Função para verificar e instalar os pacotes do requirements.txt
def install_requirements(requirements_file='src/data/requirements.txt'):
    if not os.path.isfile(requirements_file):
        print(f"[ERRO] Arquivo '{requirements_file}' não encontrado!")
        sys.exit(1)
    
    # Lê o requirements.txt
    with open(requirements_file) as f:
        required = f.read().splitlines()
    
    # Verifica o que já está instalado
    installed = {pkg.key for pkg in pkg_resources.working_set}

    # Trata nomes e ignora linhas vazias ou comentários
    required_clean = [pkg.split('==')[0].strip().lower() for pkg in required if pkg.strip() and not pkg.startswith('#')]

    # Descobre o que está faltando
    missing = [pkg for pkg in required_clean if pkg.lower() not in installed]

    # Instala os pacotes faltantes, se houver
    if missing:
        print(f"[INFO] Instalando pacotes necessários: {missing}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
    else:
        print("[INFO] Todos os pacotes já estão instalados!")

# ⚙️ 1. Verifica e instala pacotes
install_requirements()

# ⚙️ 2. Continua com o seu app normalmente
sys.path.append('./src/')  # Caminho para os módulos

from app import App

# ⚙️ 3. Inicia o app
app = App()
