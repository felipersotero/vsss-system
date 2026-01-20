# API de Controle - Vision Listener

## 📋 Visão Geral

Este módulo fornece uma **API bidirecional de comunicação** baseada em **Protobuff + UDP** para gerenciar:

- **Transmissão de frames de visão** (envio de dados de campo/bola/robôs)
- **Recebimento de decisões/comandos** (recepção de controle)

A comunicação é **assíncrona e não-bloqueante**, usando threads daemon para processamento contínuo.

---

## 🎯 Componentes Principais

### `vision_listener.py`

Contém as classes principais:

#### **ControlInterface**
Orquestra a comunicação bidirecional.

```python
from modules.control.vision_listener import ControlInterface

# Criar interface (modo teste local)
control = ControlInterface(
    tx_ip='127.0.0.1', tx_port=10002,    # Envio de frames
    rx_ip='127.0.0.1', rx_port=10003,    # Recebimento de decisões
    use_multicast=False
)

# No loop principal
decisions = control.update()  # Recebe frames e extrai decisões

# Enviar frames
control.send_frame(vision_system)

# Finalizar
control.close()
```

#### **VisionTransmitter**
Envia frames de visão via UDP.

```python
from modules.control.vision_listener import VisionTransmitter

tx = VisionTransmitter(transmitter_ip='127.0.0.1', transmitter_port=10002)
tx.send_frame(vision_system)
tx.close()
```

#### **VisionReceiver**
Recebe frames em thread separada (Job).

```python
from modules.control.vision_listener import VisionReceiver

rx = VisionReceiver(
    receiver_ip='127.0.0.1', 
    receiver_port=10003,
    use_multicast=False
)
rx.start_listening()
frame = rx.receive_frame(blocking=True, timeout=1.0)
rx.close()
```

---

## 🔌 Configuração de IP e Porta

A comunicação usa **4 endpoints**:

| Direção | IP | Porta | Uso |
|---------|----|----|-----|
| TX Frames | 127.0.0.1 | 10002 | Enviar dados de visão |
| RX Decisões | 127.0.0.1 | 10003 | Receber comandos |

### Modo Teste (Localhost)
```python
control = ControlInterface(
    tx_ip='127.0.0.1', tx_port=10002,
    rx_ip='127.0.0.1', rx_port=10003,
    use_multicast=False
)
```

### Modo Produção (Multicast em Rede)
```python
control = ControlInterface(
    tx_ip='224.0.0.1', tx_port=10002,
    rx_ip='224.0.0.1', rx_port=10003,
    use_multicast=True
)
```

---

## 📦 Estrutura dos Frames

Os frames usam **Protobuff** com a seguinte estrutura:

```
Frame {
    ball {
        x, y, z              # Posição
        vx, vy, vz          # Velocidade
    }
    
    robots_blue[] {         # Robôs aliados
        robot_id
        x, y                # Posição
        orientation         # Orientação
        vx, vy              # Velocidade
        vorientation        # Velocidade angular
    }
    
    robots_yellow[] {       # Robôs inimigos
        (mesma estrutura)
    }
}
```

---

## 🚀 Uso no Sistema Principal (Emulator)

### 1. Inicializar
```python
from modules.control.vision_listener import ControlInterface

class Emulator:
    def __init__(self, ...):
        # Inicializar ControlInterface
        self.control = ControlInterface(
            tx_ip='127.0.0.1', tx_port=10002,
            rx_ip='127.0.0.1', rx_port=10003,
            use_multicast=False
        )
    
    def visionThread(self):
        """Thread de visão - envia frames"""
        while self.cameraIsRunning:
            # ... processar visão ...
            self.control.send_frame(self.vs)
    
    def communicationThread(self):
        """Thread de comunicação - recebe decisões"""
        while self.cameraIsRunning:
            decisions = self.control.update()
            
            # decisions contém as decisões para cada robô
            for robot_id in range(3):
                cmd = decisions[robot_id]
                # cmd = {"left": velocidade, "right": velocidade}
                self.enviar_comando_robo(robot_id, cmd)
    
    def stop(self):
        self.control.close()
```

### 2. Conectar Sistema Externo

Qualquer sistema externo (AI, controle manual, etc) pode se conectar:

```python
# Sistema externo
import socket
from lib.VSSProtoComm.comm.protocols import common_pb2

# Receber frames de visão
rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_sock.bind(('127.0.0.1', 10003))  # ← Escuta em 10003

while True:
    data, _ = rx_sock.recvfrom(65535)
    frame = common_pb2.Frame()
    frame.ParseFromString(data)
    
    # Processar frame
    # ... lógica de decisão ...
    
    # Enviar comando
    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    decision = common_pb2.Frame()
    # ... preencher decisão ...
    tx_sock.sendto(decision.SerializeToString(), ('127.0.0.1', 10002))
```

---

## 🧪 Testes Disponíveis

Todos os testes estão na pasta `test/`:

| Teste | Descrição |
|-------|-----------|
| `test_simulation.py` | Simula vision_listener.py - exibe frames recebidos |
| `test_vision_sender.py` | Envia frames de teste |
| `test_diagnostic.py` | Diagnóstico rápido |
| `test_deep_diagnostic.py` | Diagnóstico completo com 4 testes |
| `test_integrated.py` | Sender + Receiver no mesmo processo |
| `test_parallel.py` | Teste de performance paralela |

### Executar Testes

**Teste Rápido:**
```bash
python test/test_diagnostic.py
```

**Teste Completo:**
```bash
python test/test_deep_diagnostic.py
```

**Simulação (requer sender em outro terminal):**
```bash
# Terminal 1
python test/test_simulation.py

# Terminal 2
python test/test_vision_sender.py
```

---

## ⚙️ Performance

- **Taxa de Frames**: ~30 fps
- **Tamanho Médio**: 66-364 bytes por frame
- **Latência**: < 100ms (socket timeout 0.1s)
- **Buffer RX**: 1MB para melhor performance
- **Threading**: Daemon threads com Job class (pause/resume/stop)

---

## ✅ Checklist de Integração

Ao integrar este módulo no seu sistema:

- [ ] IP e porta configurados corretamente
- [ ] VisionSystem implementa `getFrameProtobuff()`
- [ ] Loop principal chama `control.update()` periodicamente
- [ ] Sistema externo envia para porta correta (10003 por padrão)
- [ ] Sistema externo recebe de porta correta (10002 por padrão)
- [ ] `control.close()` chamado ao finalizar
- [ ] Testes passando com `test_deep_diagnostic.py`

---

## 🔧 Troubleshooting

### "Port already in use"
```bash
# Verificar porta em uso
netstat -ano | findstr 10003
# Matar processo (Windows)
taskkill /PID <PID> /F
```

### "Module not found"
```bash
# Garantir que sys.path está correto
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### "No frames received"
```bash
# 1. Verificar se sender está rodando
# 2. Executar test_deep_diagnostic.py para diagnóstico
# 3. Confirmar IP e porta corretos
# 4. Verificar firewall
```

---

## 📖 Referências

- **Protocol Buffers**: `lib/VSSProtoComm/comm/protocols/common_pb2.py`
- **Threading**: Usa classe `Job` do `lib/VSSProtoComm/comm/thread_job.py`
- **UDP Socket**: Python `socket` module (std library)

---

**Versão**: 1.0 | **Última atualização**: Jan 2026 | **Status**: ✅ Produção
