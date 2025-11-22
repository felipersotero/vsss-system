# Classe Emulator - Documentação Técnica Completa

## 1. Visão Geral do Sistema

### 1.1 Propósito e Contexto
A classe `Emulator` constitui o **núcleo arquitetural** do Sistema de Visão Computacional para Futebol de Robôs VSSS (Very Small Size Soccer). Atua como **orquestrador principal**, gerenciando o pipeline completo de aquisição, processamento, controle e comunicação em ambiente de competição em tempo real.

### 1.2 Especificações Técnicas
- **Versão:** 3.0.1 (Estável em Produção)
- **Última Revisão:** 14/02/2024
- **Arquitetura:** Multi-thread com separação de responsabilidades
- **Latência Alvo:** < 16ms por frame
- **Suporte a GPU:** CUDA (Opcional)

## 2. Arquitetura do Sistema

### 2.1 Diagrama de Componentes
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CAPTURA       │    │    PROCESSAMENTO  │    │   COMUNICAÇÃO   │
│   (Capture)     │───▶│    (VisionSystem) │───▶│  (Communication)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FILA UI       │    │   FILA COMM      │    │   CONTROLE      │
│   (ui_queue)    │    │   (comm_queue)   │    │   (Control)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ATUALIZAÇÃO   │    │   THREAD COMM    │    │   ENVIO DADOS   │
│   UI (Tkinter)  │    │   (Leve)         │    │   (send_data)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 2.2 Padrões de Projeto Implementados
- **Producer-Consumer** (Filas entre threads)
- **Strategy Pattern** (Múltiplos modos de operação)
- **Observer Pattern** (Atualização da UI)
- **Facade Pattern** (Interface unificada para subsistemas)

## 3. Especificações de Inicialização

### 3.1 Sequência de Boot
```python
# Fluxo hierárquico de inicialização
Emulator(App)
├── _init_app_references()      # Referências da UI
├── _init_state_variables()     # Máquina de estados
├── _init_parallel_processing() # Sistema de threads
├── _init_control_system()      # Lógica de controle
├── _init_capture_and_vision()  # Pipeline de visão
└── _init_communication()       # Camada de comunicação
```

### 3.2 Dependências Críticas
| Módulo | Função | Criticalidade |
|--------|--------|---------------|
| `VisionSystem` | Processamento de imagem | Alta |
| `Capture` | Aquisição de frames | Alta |
| `Control` | Estratégia e controle | Média |
| `Communication` | Interface externa | Média |

## 4. Sistema de Processamento Paralelo

### 4.1 Thread de Visão Computacional (`visionThread`)

#### 4.1.1 Especificações de Performance
- **Frequência:** Máxima disponível da câmera
- **Prioridade:** Alta (processamento intensivo)
- **Buffer:** Fila circular com descarte seletivo

#### 4.1.2 Pipeline de Processamento
```python
def visionThread(self):
    while self.cameraIsRunning:
        # 1. Aquisição
        frame = self.capture.getImage()
        
        # 2. Processamento (GPU/CPU)
        result = self.vs.processImg(frame, self.DEBUGA)
        objects = self.vs.getObjects()
        
        # 3. Atualização de Estado
        self._update_objects(objects)
        
        # 4. Distribuição
        self._distribute_to_queues(processed_data)
```

#### 4.1.3 Métricas Coletadas
- `frameTime`: Tempo de processamento puro (ms)
- `totalTime`: Tempo total do ciclo (ms)
- `realTime`: Timestamp absoluto do sistema

### 4.2 Thread de Comunicação (`communicationThread`)

#### 4.2.1 Características Operacionais
- **Frequência:** 200-500Hz (configurável)
- **Prioridade:** Média-Baixa
- **Estratégia:** Último frame disponível

#### 4.2.2 Protocolo de Comunicação
```python
def communicationThread(self):
    while self.cameraIsRunning:
        # Estratégia: último frame disponível
        if not self.comm_queue.empty():
            data = self.comm_queue.queue[-1]  # Último pacote
            
        # Processamento leve
        self.control.update(data)
        self.strategy.evaluate(data)
        
        # Log periódico (1Hz)
        self._periodic_logging()
```

### 4.3 Thread de Interface (`updateUI`)

#### 4.3.1 Restrições Técnicas
- **Execução:** Thread principal do Tkinter
- **Frequência:** 60 FPS (16ms/frame)
- **Latência Máxima:** 33ms para evitar stuttering

#### 4.3.2 Pipeline de Renderização
```python
def updateUI(self):
    if self.ui_queue.not_empty:
        data = self.ui_queue.get_nowait()
        
        # Renderização segura (thread principal)
        self.viewer.show(data['frame'])
        self.resultViewer.show(data['result'])
        
        # Atualização de métricas
        self._update_performance_metrics(data)
        self._update_robot_cards()
    
    # Agendamento recursivo
    self.viewer.window.after(16, self.updateUI)
```

## 5. Sistema de Configuração

### 5.1 Estrutura de Parâmetros

#### 5.1.1 Parâmetros de Hardware
```python
# Configuração de captura
self.CamUSB = int(get('I003'))           # ID da câmera
self.FocusMode = self.format_var(get('I00C'))  # Modo foco
self.FocusValue = float(get('I00D'))     # Valor foco manual

# Parâmetros de processamento
self.OffSetBord = int(get('I008'))       # Offset de borda
self.BINThresh = int(get('I00A'))        # Threshold binário
self.MatrixTop = int(get('I00B'))        # Tamanho da matriz
```

#### 5.1.2 Configuração de Campo e Cores
```python
# Dimensões do campo
self.fieldWidth = int(get('I00F'))
self.fieldHeight = int(get('I010'))

# Paleta de cores (HSV/RGB)
self.teamMainColor = str_to_int_array(self.mainColor)
self.ballColor = str_to_int_array(self.ballColor)
self.playersAllColors = np.array([...])  # Matriz 3x2 de cores
```

### 5.2 Sistema de Modos de Operação

#### 5.2.1 Modo Câmera USB (`MODE_USB_CAM`)
- **Uso:** Competição em tempo real
- **Threads:** Visão + Comunicação + UI
- **Performance:** Máxima latência 16ms

#### 5.2.2 Modo Imagem (`MODE_IMAGE`)
- **Uso:** Debug e desenvolvimento
- **Threads:** Nenhuma (processamento síncrono)
- **Output:** Análise estática

#### 5.2.3 Modo Vídeo (`MODE_VIDEO_CAM`)
- **Uso:** Testes com dados pré-gravados
- **Threads:** UI apenas
- **Taxa:** Delay configurável (14ms padrão)

## 6. Gerenciamento de Recursos

### 6.1 Controle de Memória
```python
# Filas com tamanho limitado
self.ui_queue = queue.Queue(maxsize=1)      # Evita acumulação
self.comm_queue = queue.Queue(maxsize=1)    # Último frame válido
self.capture_deque = deque(maxlen=4)        # Buffer circular

# Limpeza explícita no stop()
def stop(self):
    self.cameraIsRunning = False
    self._cleanup_queues()
    self._release_capture()
    self._stop_timer()
```

### 6.2 Gerenciamento de Threads
```python
# Inicialização segura
self.vision_thread = threading.Thread(
    target=self.visionThread, 
    daemon=True
)

# Finalização controlada
def stop(self):
    self.cameraIsRunning = False
    if self.vision_thread.is_alive():
        self.vision_thread.join(timeout=1.0)
```

## 7. Sistema de Comunicação

### 7.1 Protocolos Suportados

#### 7.1.1 MQTT
```python
if com_mode == 'mqtt':
    self.communication = Communication(
        use_mqtt=True, 
        broker_address=broker, 
        port=port
    )
    # Tópico: vsss-ifal-pin/robots
```

#### 7.1.2 Serial
```python
elif com_mode == 'serial':
    self.communication = Communication(
        use_mqtt=False, 
        serial_port=port
    )
    # Porta padrão: /dev/ttyUSB0
```

### 7.2 Formato de Dados
```python
# Pacote de comunicação
data_packet = {
    'timestamp': self.realTime,
    'field': self.field.get_state(),
    'ball': self.ball.get_position(),
    'allies': [ally.get_state() for ally in self.allies],
    'enemies': [enemy.get_state() for enemy in self.enemies],
    'performance': {
        'fps': self.FPStime,
        'proc_time': self.frameTime
    }
}
```

## 8. Monitoramento e Métricas

### 8.1 Indicadores de Performance
| Métrica | Descrição | Valor Ideal |
|---------|-----------|-------------|
| `FPStime` | Frames por segundo | > 60 FPS |
| `frameTime` | Processamento de visão | < 8ms |
| `totalTime` | Ciclo completo | < 16ms |
| `sendTime` | Tempo de comunicação | < 2ms |

### 8.2 Sistema de Logging
```python
# Log estruturado
def _periodic_logging(self):
    if (time.time() - last_log) > 1.0:  # 1Hz
        print(f"""
        [PERFORMANCE METRICS]
        Vision FPS: {self.FPStime}
        Processing: {self.frameTime:.2f}ms
        Total Cycle: {self.totalTime:.2f}ms
        Communication: {self.sendTime:.2f}ms
        Objects Detected: {detected_count}
        """)
        last_log = time.time()
```

## 9. Tratamento de Erros e Exceções

### 9.1 Categorias de Erro
```python
# Códigos de erro
ERROR_CODES = {
    0: "Operação normal",
    1: "Falha na câmera",
    2: "Erro de processamento",
    3: "Falha de comunicação",
    4: "Configuração inválida"
}
```

### 9.2 Estratégias de Recuperação
```python
def visionThread(self):
    while self.cameraIsRunning:
        try:
            # Processamento normal
            self._process_frame()
        except CameraError as e:
            self.errorCode = 1
            self._reinitialize_camera()
        except VisionError as e:
            self.errorCode = 2
            self._reset_vision_system()
        except Exception as e:
            self.errorCode = 99
            logging.error(f"Erro não tratado: {e}")
            time.sleep(0.01)  # Prevenção de busy loop
```

## 10. Interface com Outros Módulos

### 10.1 Sistema de Visão (`VisionSystem`)
```python
# Configuração
self.vs = VisionSystem(
    capture=self.capture, 
    UseCuda=self.CUDAselected,
    GPUType=self.CudaDevice
)

# Processamento
result = self.vs.processImg(frame, self.DEBUGA)
objects = self.vs.getObjects()
debug_imgs = self.vs.getDebugImages()
```

### 10.2 Sistema de Controle (`Control`)
```python
# Inicialização
self.control = Control(self)

# Atualização em tempo real
self.control.updateObjectsValues(
    self.field, 
    self.ball, 
    self.allies, 
    self.enemies
)
```

## 11. Procedimentos Operacionais

### 11.1 Inicialização do Sistema
```python
# Sequência recomendada
emulator = Emulator(main_app)
emulator.load_vars()        # Carregar configurações
emulator.show_variables()   # Verificar parâmetros
emulator.init()             # Inicializar sistemas
```

### 11.2 Shutdown Controlado
```python
# Sequência de parada
emulator.stop()             # Sinalizar parada
# → Threads finalizam graceful
# → Recursos são liberados
# → UI é atualizada
```

## 12. Considerações de Performance

### 12.1 Otimizações Implementadas
- **Filas não-bloqueantes** com `get_nowait()`
- **Buffer circular** para captura de frames
- **Seleção seletiva** do último frame para comunicação
- **Atualização condicional** da UI

### 12.2 Limitações Conhecidas
- Dependência do GIL do Python para threads
- Latência variável em sistemas não-RTOS
- Overhead do Tkinter para renderização

## 13. Manutenção e Extensibilidade

### 13.1 Adição de Novos Modos
```python
# Padrão para extensão
def _init_novo_modo(self):
    # 1. Configurar recursos específicos
    # 2. Inicializar threads necessárias
    # 3. Definir estratégia de processamento

# Registrar no método init()
if self.Mode == NOVO_MODO:
    self._init_novo_modo()
```

### 13.2 Monitoramento de Saúde
```python
# Health check periódico
def health_check(self):
    return {
        'threads_alive': self._check_threads(),
        'camera_ok': self.capture.is_operational(),
        'queue_health': self._check_queues(),
        'performance_ok': self.FPStime > 30
    }
```

---

*Documentação técnica revisada e aprovada para versão 3.0.1 - Sistema de Visão VSSS*