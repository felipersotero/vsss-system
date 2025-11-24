## 📘 README — Arquitetura PFOX + ESPHUB + Robôs

Este documento descreve o funcionamento do **protocolo PFOX**, o papel do **ESPHub** como gateway de comunicação e o fluxo completo de mensagens entre **PC**, **HUB** e **Robôs**.

O objetivo é ter um sistema **determinístico, seguro e rastreável** de envio e recebimento de comandos para um conjunto de robôs que se comunicam via **ESP-NOW**, com o PC utilizando **Serial USB**.

---

## 🏗️ 1. Arquitetura Geral do Sistema

O ESPHub atua como a espinha dorsal de comunicação, roteando e garantindo a entrega de comandos.



### 🔄 Comunicação Bidirecional Resumida

1.  **PC $\rightarrow$ Robô:** PC (Serial) $\rightarrow$ HUB (Gateway) $\rightarrow$ Robô (ESP-NOW).
2.  **Robô $\rightarrow$ PC:** Robô (ESP-NOW) $\rightarrow$ HUB (Gateway) $\rightarrow$ PC (Serial).

---

## 🛡️ 2. Protocolo PFOX (Packet FOX)

O PFOX é um protocolo compacto, binário e orientado a comando, projetado para oferecer **confiabilidade** e **rastreabilidade** sobre Serial e ESP-NOW.

### 📦 2.1 Estrutura do Pacote PFOX

Cada pacote possui um cabeçalho fixo (7 bytes), o payload variável e o **CRC16-CCITT** para validação de integridade.

| Byte | Campo | Descrição |
| :--- | :--- | :--- |
| 0 | PREAMBLE | Valor fixo **`0xF0`** (Marcador de Início de Pacote) |
| 1 | VERSION | Versão do protocolo (`0x01`) |
| 2 | SRC | **Endereço de origem** |
| 3 | DST | **Endereço de destino** |
| 4 | TYPE | Tipo da mensagem |
| 5 | SEQ | **Número da sequência** (0-255) |
| 6 | LEN | Tamanho do payload |
| 7... | PAYLOAD | Dados diversos |
| end-2 | CRC\_H | **CRC16-CCITT** (high byte) |
| end-1 | CRC\_L | **CRC16-CCITT** (low byte) |

### 🏷️ 2.2 Endereços e Tipos de Mensagem

| Endereço | Valor | Representa | | Tipo | Código | Descrição |
| :--- | :--- | :--- | - | :--- | :--- | :--- |
| **PC** | `0x00` | Computador | | **CMD\_SET\_SPEED** | `0x10` | Comando de velocidade |
| **ROBOT1** | `0x01` | Robô 1 | | **ACK** | `0x20` | Confirmação de recebimento |
| **ROBOT3** | `0x03` | Robô 3 | | **STATUS** | `0x30` | Telemetria/Estado do robô |
| **ESPMAIN** | `0xFE` | **ESPHUB** (Origem/Destino Interno) | | **HEARTBEAT** | `0x40` | Sinal de vida |
| **BROADCAST** | `0xFF` | Todos os robôs | | **ERROR** | `0x50` | Erro reportado pelo HUB/Robô |

### 🔢 2.3 Garantias de Rastreamento (SEQ)

O número de sequência (**SEQ** de 0 a 255) é crucial para:
* **Correlacionar ACKs:** O ACK do robô deve carregar o mesmo SEQ do comando original.
* **Detectar Duplicatas:** Robôs ou o HUB podem ignorar pacotes com SEQ repetido.
* **Timeouts:** Usado pelo HUB para identificar comandos não confirmados.

---

## 🔧 3. Funções do ESPHub (Gateway Inteligente)

O ESPHub é o intermediário que realiza a tradução de protocolos e gerencia o estado das comunicações.

### 🧠 3.1 Gerenciamento de Filas (Otimizado)

O HUB utiliza **duas filas (FIFO)** baseadas em `std::queue` para operações **O(1)** (rapidez) na adição e remoção de pacotes, garantindo que o processamento (lento) não bloqueie a recepção (rápida).

* **`incoming`:** Armazena pacotes recém-chegados (via Serial e ESP-NOW) antes de serem processados pelo `loop()`.
* **`outgoing`:** Armazena comandos do PC para serem enviados via ESP-NOW.

### ⏱️ 3.2 Mecanismo de Confirmação e Timeout

Este é o coração da **confiabilidade** *end-to-end*:

1.  **ACK Serial Imediato:** Ao receber um pacote PFOX do PC, o HUB envia um **ACK** imediato via Serial. Este ACK significa: "O HUB recebeu seu pacote PFOX do Serial corretamente e com CRC OK."
2.  **ACK ESP-NOW Pendente:** Antes de enviar o pacote ao robô, o HUB armazena o comando na lista **`pendingAcks`** (usando SEQ e `timestamp`).
3.  **Robô Responde:** O robô, após executar o comando, envia um **ACK (PFOX)** de volta ao HUB via ESP-NOW.
4.  **Remoção e Envio ao PC:** O HUB recebe o ACK, remove o comando da lista **`pendingAcks`** e **encaminha o ACK PFOX do robô para o PC via Serial**.
5.  **Timeout:** Se o ACK do robô não chegar dentro de **150ms** (configurável), o HUB gera um pacote **PFOX ERROR** com código de timeout e o envia ao PC.

---

## 🛣️ 4. Fluxo de Execução Principal (`ESPHub::loop()`)

A função `loop()` executa em sequência, de forma não-bloqueante:

1.  **`receiveSerial()`:** Lê todos os bytes disponíveis da porta Serial e os anexa ao `serialBuffer`.
2.  **`processSerialBytes()`:** **(Otimizado)** Decodifica pacotes PFOX completos e válidos do buffer Serial. **Implementação usa shifting de memória (em vez de `erase`)** para descarte de dados inválidos, evitando gargalos de CPU.
3.  **`processTimeouts()`:** Verifica se há comandos na lista **`pendingAcks`** que excederam o tempo de espera (150ms) e envia ERROR ao PC, se necessário.
4.  **Processamento de Filas (`while (incoming.pop(pkt))`):**
    * **Se Origem = PC:** Envia o pacote ao robô (`sendToRobot`) e envia ACK Serial ao PC (`sendAckToPC`).
    * **Se Origem = Robô:** Se for ACK, remove o item de `pendingAcks`. Em seguida, encaminha o pacote (ACK, STATUS, HEARTBEAT, etc.) ao PC (`forwardToPC`).