
# ⚽ VSSS Communication System (PFOX Protocol)

Este repositório contém o ecossistema completo de firmware para o sistema de comunicação do VSSS (Very Small Size Soccer). O sistema foi projetado para alta performance, baixa latência e confiabilidade robusta usando **ESP-NOW**.

O sistema é dividido em dois firmwares distintos:

1.  **ESPHUB (Gateway):** A ponte entre o Computador (IA) e o rádio.
2.  **ESPSlave (Robô):** O firmware embarcado nos robôs que controla motores e executa comandos.3.  **MACADDRESS (Utilitário):** Ferramenta para configurar endereços MAC dos ESP32.
-----

## 📡 Arquitetura do Sistema

O fluxo de dados segue o caminho:
`[PC/IA]` $\xrightarrow{\text{USB Serial}}$ `[ESPHUB]` $\xrightarrow{\text{ESP-NOW (Rádio)}}$ `[ESPSlave]`

### Destaques Técnicos

  * **Protocolo PFOX:** Protocolo binário customizado com CRC16 para integridade de dados.
  * **ARQ (Automatic Repeat Request):** O Hub reenvia pacotes automaticamente se o Robô não enviar um ACK (confirmação) em 60ms.
  * **Controle PID:** Os robôs possuem controle de malha fechada (ou aberta) para garantir velocidades precisas.
  * **Filas de Prioridade:** O Hub mantém filas independentes para cada robô, evitando gargalos.

-----

## 1️⃣ Firmware do Gateway (ESPHUB)

O **ESPHUB** é o mestre da rede. Ele não toma decisões de jogo, apenas gerencia o tráfego de dados para garantir que os comandos do PC cheguem aos robôs.

### 📋 Responsabilidades

  * Receber *bytes* da Serial e montar pacotes PFOX.
  * Gerenciar o envio via rádio e aguardar confirmação (ACK).
  * Receber telemetria (Status/Bateria) dos robôs e repassar ao PC via Serial.
  * Manter filas por robô com sistema de retry em caso de falha.

### ⚙️ Funcionalidades Principais (ESPHub.cpp)

- **Inicialização:** Configura WiFi, obtém MAC próprio, inicializa ESP-NOW e registra peers (robôs).
- **Recepção Serial:** Recebe dados da Serial do PC, monta pacotes PFOX e os enfileira.
- **Envio para Robôs:** Processa filas de cada robô, envia via ESP-NOW, aguarda ACK com timeout.
- **Retransmissão:** Se ACK não chega em 60ms, reenvia até 3 vezes.
- **Callbacks ESP-NOW:** Trata envio e recepção de dados via rádio.

### ⚙️ Configuração Obrigatória (Antes de gravar)

No arquivo `ESPHUB.cpp`, você deve cadastrar os endereços MAC dos robôs que receberão os comandos.

```cpp
// ESPHUB.cpp
static const uint8_t ROBOT_MACS[][6] = {
    {0x94, 0xB9, 0x7E, 0xC2, 0xCA, 0xA8}, // Endereço MAC do Robô 1
    {0x32, 0xAE, 0x11, 0x22, 0x33, 0x44}, // Endereço MAC do Robô 2
    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00}  // Endereço MAC do Robô 3
};
```

> **Nota:** Se você não souber o MAC dos robôs ainda, grave o código `ESPSlave` neles primeiro; eles imprimirão o MAC na Serial ao ligar.

### 🚀 Como Usar

1.  Conecte o ESP32 do Hub ao PC via USB.
2.  Abra a Serial (Baudrate **115200**).
3.  O Hub imprimirá: `[INIT] MAC Address deste HUB: XX:XX:XX...`.
4.  **Copie este endereço\!** Você precisará dele para configurar os robôs.

-----

## 2️⃣ Firmware do Robô (ESPSlave)

O **ESPSlave** é o firmware que roda dentro do robô. Ele recebe pacotes de velocidade, calcula o PID e aciona a Ponte H.

### 📋 Responsabilidades

  * Escutar o rádio por pacotes endereçados ao seu ID.
  * Responder imediatamente com um **ACK** (mesmo número de sequência).
  * Executar o controle PID dos motores.
  * Monitorar Failsafe (para os motores se perder conexão).

### 🔌 Hardware & Pinagem (Ponte H L298N)

A configuração padrão (arquivo `Control.cpp`) utiliza 3 pinos por motor (IN1, IN2 e ENABLE/PWM).

| Motor | Função | Pino ESP32 (GPIO) |
| :--- | :--- | :--- |
| **Esquerdo** | IN1 (Direção A) | 2 |
| | IN2 (Direção B) | 4 |
| | ENA (PWM) | 15 |
| **Direito** | IN3 (Direção A) | 25 |
| | IN4 (Direção B) | 26 |
| | ENB (PWM) | 32 |

### ⚙️ Configuração Obrigatória (Antes de gravar)

No arquivo `ESPSlave.ino`, configure a identidade do robô e o endereço do Hub:

```cpp
// ESPSlave.ino
// 1. Quem sou eu? (ROBOT1, ROBOT2 ou ROBOT3)
#define MY_IDENTITY  PFOXAddress::ROBOT1 

// 2. Para quem devo enviar o ACK? (Endereço do Hub copiado anteriormente)
uint8_t HUB_MAC_ADDR[] = {0x30, 0xAE, 0xA4, 0x07, 0x0D, 0x64}; 
```

### 🧠 Ajuste do PID

No arquivo `Control.cpp`, você pode ajustar as constantes do controlador:

```cpp
#define K_P  2.0   // Aumente se o robô estiver lento para reagir
#define K_I  0.5   // Aumente se o robô não atingir a velocidade máxima
#define K_D  0.1   // Aumente se o robô estiver vibrando/oscilando
```

-----

## 3️⃣ Utilitário MACADDRESS

O **MACADDRESS** é um sketch simples para configurar ou verificar o endereço MAC de um ESP32.

### 📋 Responsabilidades

  * Ler o MAC atual do ESP32.
  * Permitir definir um novo MAC para teste ou configuração.
  * Imprimir o MAC em formato legível para copiar.

### ⚙️ Funcionalidades Principais (MACADDRESS.ino)

- **Leitura de MAC:** Usa `WiFi.macAddress()` para obter o MAC atual.
- **Definição de MAC:** Permite definir um novo MAC via `esp_wifi_set_mac()`.
- **Reinicialização WiFi:** Necessária para validar mudanças no MAC.
- **Formato de Saída:** Imprime MAC em formato hexadecimal para fácil cópia.

### 🚀 Como Usar

1.  Grave o sketch `MACADDRESS.ino` no ESP32.
2.  Abra o Monitor Serial (115200 baud).
3.  O ESP32 imprimirá o MAC original.
4.  Opcionalmente, defina um novo MAC no código e regrave para testar.
5.  Use o MAC impresso para configurar no ESPHUB ou ESPSlave.

> **Nota:** Mudanças de MAC persistem até o próximo reset ou regravação do firmware.

-----

## 📦 Bibliotecas Compartilhadas (Core)

Para garantir que o Hub e o Robô falem a mesma língua, ambos utilizam os mesmos arquivos de definição de protocolo. **Não altere estes arquivos em apenas um lado\!**

  * **`PFOXPacket.h/.cpp`**: Define a estrutura do pacote PFOX, incluindo encode/decode, CRC16 e validação.
  * **`PFOXQueue.h/.cpp`**: Implementação de fila circular para buffering de mensagens (usada no Hub e Slave).
  * **`RobotChannel.h/.cpp`**: Gerencia canais de comunicação por robô no Hub, incluindo retries e timeouts.

-----

## 👣 Guia de Instalação Passo-a-Passo

1.  **Preparar IDE:** Instale o Arduino IDE e configure o suporte a **ESP32 versão 3.0.0+** (necessário para a nova API de PWM `ledcAttach`).
2.  **Gravar HUB:**
      * Abra a pasta `ESPHub`.
      * Grave no primeiro ESP32.
      * Abra o Monitor Serial e anote o MAC Address: `[INIT] MAC: AA:BB:CC...`
3.  **Configurar Robô:**
      * Abra a pasta `ESPSlave`.
      * Edite `ESPSlave.ino`: Cole o MAC do Hub em `HUB_MAC_ADDR`.
      * Defina `#define MY_IDENTITY PFOXAddress::ROBOT1`.
4.  **Gravar Robô:**
      * Grave no segundo ESP32.
      * Abra o Monitor Serial e anote o MAC Address dele.
5.  **Finalizar HUB:**
      * Volte ao `ESPHUB.cpp`.
      * Atualize a lista `ROBOT_MACS` com o endereço real do Robô 1 que você acabou de gravar.
      * Regrave o Hub.
6.  **Jogar:** Agora o sistema está pareado e pronto.

-----

## ❓ Troubleshooting (Solução de Problemas)

| Sintoma | Causa Provável | Solução |
| :--- | :--- | :--- |
| **Erro de Compilação `ledcAttach`** | Versão antiga do ESP32 Core | Atualize o Board Manager do ESP32 para versão **3.0.0** ou superior. |
| **Robô não mexe e Hub dá erro de ACK** | Endereços MAC errados | Verifique se o Hub tem o MAC do Robô e o Robô tem o MAC do Hub. |
| **Robô gira ao contrário** | Fios do motor invertidos | Inverta os fios na Ponte H ou troque os pinos IN1/IN2 no `Control.cpp`. |
| **Robô fica "tremendo" parado** | Ruído no PID | Aumente a "Zona Morta" no código ou diminua o `K_P`. |