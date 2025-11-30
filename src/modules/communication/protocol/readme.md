# Protocolo PFOX - Documentação

## Visão Geral

O protocolo PFOX (Protocol Fox) foi desenvolvido para comunicação bidirecional entre um sistema de controle central (PC) e múltiplos robôs ESP32 via um gateway central denominado ESPMain. Suporta transporte Serial (PC ↔ ESPMain) e ESPNOW (ESPMain ↔ robôs), mantendo o mesmo formato de aplicação para ambos os meios.

## Arquitetura do Sistema

```
Sistema de Controle (PC) ↔ Serial ↔ ESPMain (Gateway) ↔ ESPNOW ↔ Robôs ESP32 (IDs: 1,2,3)
```

### Componentes Principais

- **PC**: Sistema de controle principal que envia comandos ao ESPMain
- **ESPMain**: Gateway central que roteia pacotes entre Serial e ESPNOW
- **ESPSlaves**: Robôs individuais que executam comandos e enviam telemetria

## Formato do Pacote PFOX

Cada pacote PFOX possui a seguinte estrutura:

```
[Preamble][Version][Src][Dst][Type][Seq][Len][Payload][CRC16]
  (1B)     (1B)    (1B) (1B) (1B)  (1B) (1B)   (N)     (2B)
```

### Campos Detalhados

| Campo | Tamanho | Descrição |
|-------|---------|-----------|
| Preamble | 1 byte | Identificador de início de pacote (0xFO) |
| Version | 1 byte | Versão do protocolo |
| Src | 1 byte | Endereço do dispositivo de origem |
| Dst | 1 byte | Endereço do dispositivo de destino |
| Type | 1 byte | Tipo de mensagem (comando, ACK, status, etc.) |
| Seq | 1 byte | Número de sequência para rastreamento |
| Len | 1 byte | Comprimento do payload em bytes |
| Payload | N bytes | Dados da mensagem |
| CRC16 | 2 bytes | Checksum para verificação de integridade |

## Tabelas do Protocolo

### Tabela de Endereçamento

| Endereço | Valor | Descrição |
|----------|-------|-----------|
| PC | 0x00 | Sistema de controle principal |
| ESPMain | 0xFE | Gateway central |
| Robô 1 | 0x01 | Primeiro robô do swarm |
| Robô 2 | 0x02 | Segundo robô do swarm |
| Robô 3 | 0x03 | Terceiro robô do swarm |
| Broadcast | 0xFF | Todos os dispositivos |

### Tipos de Mensagem

| Tipo | Valor | Descrição |
|------|-------|-----------|
| CMD_SET_SPEED | 0x10 | Controle de velocidade [robot_id, left, right] |
| CMD_FLOW_CTRL | 0x11 | Controle de sessão: start=0, pause=1, stop=2 |
| ACK | 0x20 | Confirmação de recebimento [orig_seq, code] |
| STATUS | 0x30 | Telemetria e status do robô |
| HEARTBEAT | 0x40 | Sinal periódico de operacionalidade |
| ERROR | 0x50 | Mensagem de erro ou falha |

## ESPMain - Gateway Central

### Responsabilidades

- **Bridge Serial-ESPNOW**: Conversão entre interfaces Serial e ESPNOW
- **Roteamento**: Encaminhamento baseado em endereços de destino
- **Controle de Fluxo**: Gerenciamento de filas e prioridades
- **Monitoramento**: Detecção de falhas via heartbeats
- **Retransmissão**: Retentativa de pacotes não confirmados
- **Logging**: Registro de mensagens para depuração

### Processo Interno

1. Recebimento contínuo de pacotes via Serial do PC
2. Validação de CRC e estrutura do pacote
3. Consulta à tabela de endereços para determinar destino
4. Transmissão ESPNOW para robôs destino
5. Atualização de estados e filas de retransmissão

## ESPSlaves - Robôs Autônomos

### Responsabilidades

- **Execução de Comandos**: Aplicação de velocidades aos motores
- **Coleta de Telemetria**: Leitura de sensores e estado do robô
- **Confirmação**: Envio de ACK para pacotes recebidos
- **Monitoramento**: Manutenção de heartbeat ativo
- **Tratamento de Erros**: Detecção e reporte de falhas locais

### Fluxo de Operação

1. Aguarda comandos do ESPMain
2. Valida CRC e estrutura do pacote
3. Executa ação conforme tipo de mensagem
4. Envia confirmação (ACK) ou telemetria
5. Mantém heartbeat periódico ativo

## Fluxo de Comunicação

```
PC → ESPMain → ESPSlave → ESPMain → PC
    Comando      Execução    ACK
```

1. **PC → ESPMain**: Envio de comando CMD_SET_SPEED via Serial
2. **ESPMain → ESPSlave**: Encaminhamento do pacote via ESPNOW
3. **ESPSlave → ESPMain**: Confirmação de recebimento (ACK)
4. **ESPMain → PC**: Repasse do ACK via Serial

**Heartbeats**: Envio periódico (1 segundo) dos robôs para o ESPMain

## Controlador de Comunicação

### Funções Principais

| Função | Descrição |
|--------|-----------|
| Gerenciamento de Interfaces | Inicialização e monitoramento de Serial e MQTT |
| Envio/Recebimento | Encapsulação/decapsulação de pacotes PFOX |
| Filas e Retransmissões | Organização de filas e retentativas automáticas |
| Logs | Registro detalhado de mensagens e eventos |
| Estatísticas | Cálculo de taxa de sucesso, latência, etc. |
| Listeners Externos | Interface para sistemas externos (GUI, monitoramento) |

### Benefícios

- Abstrai complexidade das diferentes interfaces
- Permite monitoramento em tempo real
- Aumenta confiabilidade com ACKs, heartbeats e retries
- Facilita integração com ferramentas externas

## Mecanismos de Confiabilidade

- **ACK/Retransmissão**: Timeout de 200-500ms, máximo 3 tentativas
- **Stop-and-wait**: Sincronização simples de pacotes
- **Heartbeat**: 1 segundo para detecção de falhas
- **Priorização**: Comandos de fluxo > comandos de velocidade
- **CRC16**: Verificação de integridade completa

## Estados do Sistema

| Estado | ESPMain | ESPSlave |
|--------|---------|----------|
| INIT | Configura interfaces | Aguarda pairing |
| READY | Interfaces prontas | Pareado com ESPMain |
| RUNNING | Processando comandos | Executando movimentos |
| PAUSED | Comandos enfileirados | Motores parados |
| ERROR | Falha de comunicação | Falha local detectada |

## Tratamento de Erros

| Falha | Ação de Recuperação |
|-------|---------------------|
| Timeout ACK | Retransmissão (3x), marca como offline |
| CRC Inválido | Descarta pacote, aguarda retransmissão |
| Heartbeat perdido | Marca robô como inativo, notifica PC |
| ESPNOW ocupado | Reenfileira pacote, retenta após delay |
| Serial desconectada | Reconexão automática |

## Componentes de Software

```
PFOXProtocol → CommunicationManager → Transport Adapter
    ↓               ↓                     ↓
Serialização   Filas/Retransmissões   Serial/ESPNOW
```

## Organização do Código

```
pfox/
  protocol/
    __init__.py
    protocol.py          # Serialização/deserialização
    manager.py           # Filas, retransmissões e estado
    transport/
      __init__.py
      serial_transport.py
      espnow_transport.py
    utils.py
  tests/
  examples/
```

## Implementação

### Exemplo de Pacote

```python
# Comando: Mover robô 1 - velocidade esquerda: 200, direita: 150
pacote = PFOXPacket(
    preamble=0xFO,
    version=0x01,
    src=0x00,      # PC
    dst=0x01,      # Robô 1
    type=0x10,     # CMD_SET_SPEED
    seq=0x05,
    len=0x03,
    payload=[0x01, 0xC8, 0x96],  # [robot_id, left, right]
    crc16=0x1234   # Calculado
)
```

### Exemplo de Uso

```python
# No PC (Python)
controller = PFOXController()
controller.send_speed_command(robot_id=1, left_speed=200, right_speed=150)

# No ESPMain (C++)
pfox.process_incoming_packet(serial_data);
pfox.forward_to_robot(robot_id, espnow_data);

# No ESPSlave (C++)
if (pfox.validate_packet(incoming_data)) {
    pfox.execute_command(incoming_data);
    pfox.send_ack();
}
```

## Conclusão

O protocolo PFOX fornece uma arquitetura clara e confiável para comunicação entre PC e robôs ESP32 via ESPMain. A separação entre gateway central e robôs permite controle eficiente, monitoramento em tempo real e recuperação automática de falhas, oferecendo uma base sólida para aplicações de swarm de robôs e projetos acadêmicos de controle embarcado.

**Características Principais**:
- ✅ Formato binário eficiente (6-12 bytes por comando)
- ✅ Suporte a unicast e broadcast
- ✅ Mecanismos robustos de confiabilidade
- ✅ Arquitetura escalável para múltiplos robôs
- ✅ Interface unificada para diferentes transportes