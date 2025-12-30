# 🦊 FoxCom - VSSS Communication Module

O **FoxCom** é o módulo responsável por toda a camada de comunicação e controle de baixo nível do sistema VSSS (Very Small Size Soccer). Ele gerencia a troca de dados entre a Inteligência Artificial (no PC) e os robôs em campo, garantindo **baixa latência**, **confiabilidade** e **monitoramento em tempo real**.

## 📡 Arquitetura do Sistema

O sistema opera em uma arquitetura híbrida para maximizar a velocidade:

1.  **Nível de Software (PC):** A IA calcula as trajetórias e envia comandos via **Serial (USB)** ou **MQTT**.
2.  **Nível de Gateway (ESPHUB):** Um ESP32 central recebe os dados da Serial e os converte para ondas de rádio.
3.  **Nível Físico (Robôs):** Os robôs recebem os comandos via **ESP-NOW** (protocolo de rádio proprietário de baixa latência) e executam o controle de motores.

### Fluxo de Dados

`[IA/Strategy]` $\leftrightarrow$ `[FoxCom Python]` $\leftrightarrow$ `[USB Serial]` $\leftrightarrow$ `[ESPHUB]` $\leftrightarrow$ `[ESP-NOW]` $\leftrightarrow$ `[ESPSlave Robots]`

-----

## 📦 Componentes do Módulo

O FoxCom é dividido em três grandes pilares:

### 1\. Software Core (`communication.py`)

O coração do sistema no lado do computador, implementado na classe `Communication`.

  * **Multithreading:** Gerencia threads separadas para envio e recepção de dados para não bloquear a IA.
  * **Dual-Protocol:** Suporta conexão via **Serial** (para jogos, latência mínima) e **MQTT** (para telemetria remota/debug).
  * **Protocolo PFOX:** Implementa o empacotamento binário (Structs C-like), cálculo de CRC16 e validação de pacotes.
  * **Gerenciamento de Estado:** Monitora RTT (Round Trip Time), perda de pacotes e status de conexão.
  * **Métodos de Controle:** Inclui métodos como `connect()`, `start()`, `pause()`, `resume()`, `stop()`, `send_robot_velocity()`, `send_heartbeat()`, etc.
  * **Flag de Envio:** Possui flag `sending_enabled` para controlar dinamicamente o envio de comandos.

### 2\. Interface de Debug (`interface.py`)

Uma GUI robusta construída em **Tkinter** para facilitar o desenvolvimento, implementada na classe `CommunicationDebugWindow`.

  * **Monitor Serial em Tempo Real:** Visualização de logs hexadecimais e ASCII.
  * **Dashboard de Telemetria:** Gráficos de latência (Ping) e status dos robôs.
  * **Controle Manual:** Permite enviar comandos de velocidade e trocar configurações sem rodar a IA completa.
  * **Controles Atualizados:** Inclui dropdowns para tipo de mensagem (MsgType), endereço (Address), ações específicas, e checkbox para controle dinâmico via teclas W/A/S/D.
  * **Singleton:** Garante que apenas uma janela de debug exista para não conflitar portas.

### 3\. Protocolo PFOX (`protocolHeader.py`)

Define o protocolo de comunicação binário.

  * **Estrutura de Pacote:** Preamble, version, src, dst, type, seq, len, payload, CRC16.
  * **Tipos de Mensagem:** CMD_SET_SPEED, CMD_FLOW_CTRL, ACK, STATUS, HEARTBEAT, ERROR.
  * **Endereços:** PC, ROBOT1, ROBOT2, ROBOT3, ESPMAIN, BROADCAST.
  * **Controle de Pacotes:** Classe PFOXController para criar e gerenciar pacotes.

### 4\. Firmware Embarcado

Código C++ otimizado rodando nos microcontroladores ESP32.

  * **ESPHUB (Gateway):** Atua como mestre. Possui filas (Queues) inteligentes para cada robô e sistema de **ARQ** (Retransmissão automática em caso de falha).
  * **ESPSlave (Robôs):** Recebe comandos, executa o controle PID dos motores L298N e envia feedback de bateria/status.
  * **MACADDRESS:** Utilitário para configurar endereços MAC dos ESP32.

-----

## 🛠️ Tecnologias Utilizadas

| Escopo | Tecnologia | Função |
| :--- | :--- | :--- |
| **Linguagem PC** | Python 3.10+ | Lógica de comunicação e Interface |
| **GUI** | Tkinter (CustomTkinter Style) | Interface Gráfica de Debug |
| **Comunicação PC** | PySerial & Paho-MQTT | Drivers de transporte de dados |
| **Firmware** | C++ / Arduino Core | Código dos ESP32 |
| **Protocolo Rádio** | **ESP-NOW** | Comunicação sem fio (\< 4ms latência) |
| **Integridade** | CRC-16 CCITT | Verificação de erros nos pacotes |

-----

## 🚀 Como Funciona o Protocolo (PFOX)

O **FoxCom** utiliza um protocolo binário customizado chamado **PFOX**. Diferente de enviar strings (ex: "v=100"), enviamos bytes brutos para economizar tempo de transmissão.

**Estrutura do Pacote:**
`[PREAMBLE 0xF0] [VERSION] [SRC] [DST] [TYPE] [SEQ_ID] [LEN] [PAYLOAD...] [CRC16]`

1.  **Handshake:** O PC envia um comando.
2.  **Processamento:** O ESPHUB recebe, valida o CRC e coloca na fila do robô específico.
3.  **Envio Rádio:** O ESPHUB envia via ESP-NOW.
4.  **Execução:** O Robô recebe, aplica no PID e responde com um **ACK**.
5.  **Confirmação:** Se o Hub não receber o ACK em 60ms, ele reenvia o pacote automaticamente.

-----

## 🔌 Pinagem e Hardware

[Image of ESP32 pinout diagram]

Para o correto funcionamento do firmware **ESPSlave**, utilize a seguinte ligação com a Ponte H L298N:

  * **Motor Esquerdo:** GPIO 2 (IN1), GPIO 4 (IN2), GPIO 15 (PWM).
  * **Motor Direito:** GPIO 25 (IN3), GPIO 26 (IN4), GPIO 32 (PWM).

-----

## ✅ Checklist de Desenvolvimento

### Estado Atual (v1.0.0)

  - [x] **Core Python:** Comunicação Serial estável com Threads.
  - [x] **Protocolo:** Empacotamento PFOX com CRC16 implementado.
  - [x] **Firmware HUB:** Conversão Serial -\> ESP-NOW funcionando com filas.
  - [x] **Firmware Robô:** Controle de motores (L298N) e recepção de comandos.
  - [x] **Interface:** Janela de Debug recebendo logs e enviando comandos.
  - [x] **Failsafe:** Robôs param se perderem conexão (Timeout).

### Futuras Atualizações (Roadmap)

  - [ ] **Otimização MQTT:** Melhorar a latência para telemetria via WiFi.
  - [ ] **Gráficos Avançados:** Plotar PID (Setpoint vs Real) na interface Python em tempo real.
  - [ ] **OTA (Over-the-Air):** Permitir atualizar o firmware dos robôs via rádio através do Hub.
  - [ ] **Auto-Discovery:** O Hub detectar automaticamente quais robôs estão ligados e informar o Python.
  - [ ] **Log em Arquivo:** Salvar logs de partidas para análise posterior (Blackbox).

-----

## 👨‍💻 Como Rodar (Dev Mode)

1.  **Firmware:**
      * Grave o `ESPHUB` em um ESP32.
      * Grave o `ESPSlave` nos robôs (configurando os IDs corretamente).
2.  **Dependências Python:**
    ```bash
    pip install pyserial paho-mqtt
    ```
3.  **Executar Interface de Teste:**
    Para abrir apenas o módulo de comunicação sem a IA completa:
    ```python
    # Crie um script main_test.py
    import tkinter as tk
    from modules.communication.communication import FoxCom
    from modules.communication.interface import CommunicationDebugWindow

    root = tk.Tk()
    comm = FoxCom()
    debug_window = CommunicationDebugWindow(root, comm)
    root.mainloop()
    ```