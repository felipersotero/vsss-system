# 📚 Documentação do Sistema - VSSS (Very Small Size Soccer)

## 📌 Visão Geral

Este projeto é um sistema completo para competições de **Very Small Size Soccer (VSSS)**, englobando **visão computacional**, **interface gráfica**, **processamento de imagens**, **teoria do controle** e **simulação/emulação**.

O **arquivo principal** de execução é `main.py`, que inicia a aplicação principal (`app.py`). O sistema processa imagens capturadas pela câmera, detecta a posição da bola e dos robôs, e fornece essas informações para tomada de decisões estratégicas.

## 🚀 Como Executar o Projeto

### 1️⃣ Instalar as Dependências

Certifique-se de que possui o Python instalado (versão 3.8 ou superior). Para instalar as bibliotecas necessárias, utilize:

```bash
pip install -r src/data/requirements.txt
```

### 2️⃣ Rodar a Aplicação

Execute o arquivo principal:

```bash
python main.py
```

## 📂 Estrutura do Projeto

```plaintext
📁 Projeto-VSSS/
│-- main.py                # Arquivo principal para rodar a aplicação
│-- requirements.txt       # Lista de dependências do projeto
│-- 📂 src/                # Diretório principal do código
|   |--📂 data             # Arquivos principais para configuração e backup
|   |--📂 imagens          # Imagens para testar processamento
|   |--📂 videos           # Videos para testar processamento
|   |--📂 theme            # Arquivos de tema importantes para a interface
│   │-- app.py             # Inicializa a interface gráfica (GUI)
│   │-- cards.py           # Configura cards para interface gráfica (GUI)
│   │-- communication.py   # Gerencia a comunicação do sistema
│   │-- control.py         # Funções e lógica de controle do sistema
│   │-- detector.py        # Módulo de detecção legado
│   │-- detectorV2.py      # Módulo de detecção e interpretação do sistema atual
│   │-- emulator.py        # Engine da aplicação
│   │-- modules.py         # Organização dos módulos utilizados em todo o projeto
│   │-- objects.py         # Definição dos objetos básicos do projeto
│   │-- settingsMenu.py    # Configuração do menu inteligente da interface
│   │-- strategy.py        # Arquivo com as funções de estratégia
│   │-- viewer.py          # Configuração da tela de exibição de imagens
│   │-- windowControl.py   # Controle da interface dos robôs
```

## 🖥️ Módulos do Sistema

### 📌 `main.py`
Arquivo principal do projeto. Ele:
- Inicializa a interface gráfica.
- Verifica e instala as dependências automaticamente.
- Gerencia a execução do `app.py`.

### 📌 `app.py`
Gerencia a **tela principal** da aplicação e a classe `App`, responsável por:
- Criar e configurar a janela principal (`configure_window()`).
- Criar os **frames** principais da interface gráfica (`create_main_frames()`).
- Criar **subframes** específicos de configuração (`create_settings_frame()`).
- Gerenciar **widgets** da interface (botões, imagens, menus, etc.).
- Inicializar o **Emulador (`Emulator`)**.

### 📌 `settingsMenu.py`
Gerencia a lista de configurações do sistema. Contém:
- Funções para adicionar e acessar nós (`add_node`, `att_node_id`).
- Manipulação da interface ao clicar em um campo (`on_double_click`).
- Leitura e salvamento de dados (`save_to_json`, `load_from_json`).

### 📌 `viewer.py`
Cria telas para **visualização das imagens de depuração**. Contém a classe `MyViewer`, que possui funções como:
- `config()` - Configuração inicial.
- `reset_config()` - Reset das configurações.
- `default_mode()` - Modo padrão de exibição.
- `show()` - Exibição das imagens processadas.

### 📌 `emulator.py`
Arquivo com a lógica da Engine da aplicação, organizando-se em:
1. **Construtor:** Define as variáveis principais.
2. **Funções Gerais:**
   - `load_vars()`: Carrega as variáveis do JSON.
   - `format_var()`: Formata os dados carregados.
   - `init()`, `stop()`: Inicializa e encerra a simulação.
3. **Funções de Execução:**
   - `processUSB()`, `processImage()`, `processVideo()`

### 📌 `detectorV2.py`
Módulo de **visão computacional**, responsável por detectar a **bola, os robôs e o campo** em tempo real.
- Compatível com **GPU (OpenCV CUDA)** para acelerar processamento.
- Detecta objetos e prevê suas posições.
- Suporte a filtros avançados e transformações de imagem.

### 📌 `control.py`
Contém **algoritmos de controle** dos robôs, incluindo:
- Controle PID básico.
- Ajuste de velocidade e direção.
- Cálculo de trajetória para movimentação eficiente.

### 📌 `strategy.py`
Gerencia a **inteligência dos robôs** e estratégia de jogo.
- Define comportamento ofensivo/defensivo.
- Implementação de FSM (Finite State Machine) para tomadas de decisão.

## ⚙️ Melhorias Futuras
- Implementação de **Filtro de Kalman** para melhorar a precisão na detecção.
- Melhorias na estratégia com **aprendizado de máquina (Reinforcement Learning)**.
- Integração com **simuladores avançados (Gazebo, Webots, etc.)**.

## 📄 Licença
Este projeto está sob a licença **MIT**. Sinta-se à vontade para modificar e contribuir! 🤖⚽

---

💡 **Sugestão:** Caso precise de mais detalhes técnicos sobre um módulo específico, consulte os arquivos individuais dentro da pasta `src/`.
