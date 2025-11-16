# Sistema de Visão VSS (Vision System Soccer) v2.2.40

## 📋 Visão Geral

O **Sistema de Visão VSS** é um módulo de detecção de objetos em tempo real desenvolvido para competições de futebol de robôs. O sistema processa imagens de campo, detectando bola, robôs aliados e inimigos, utilizando técnicas avançadas de visão computacional e filtros de Kalman para rastreamento.

### 🎯 Características Principais
- Detecção em tempo real de múltiplos objetos
- Suporte a processamento CPU/GPU
- Sistema de coordenadas virtual para mapeamento preciso
- Filtros de Kalman para predição de movimento
- Arquitetura multi-thread para alto desempenho

## 🏗️ Arquitetura do Sistema

### Classes Principais

### 1. `VisionSystem` - Classe Principal

**Responsabilidade**: Orquestrar todo o pipeline de processamento de visão

**Métodos Principais**:

#### `proc(img, debug, isT)`
Pipeline principal de processamento:
```python
1. Reset do estado de execução
2. Detecção do campo → detect_field()
3. Detecção da bola → detect_ball()
4. Detecção de jogadores → detect_players()
5. Renderização de debug
6. Atualização temporal
```

#### `processImg(img, debug)`
Gerencia o modo de operação:
- **Modo Imagem**: Processamento completo único
- **Modo Vídeo**: Alterna entre processamento completo e predição

#### `detect_field(img, debug)`
Detecta e transforma o campo usando homografia:

**Equação de Homografia**:
```
H = findHomography(ptsSrc, ptsFinal)
ponto_virtual = H × ponto_real
```

#### `detect_ball(img, colorBall, debug)`
Detecta a bola por cor HSV e aplica filtros morfológicos.

#### `detect_players(img, debug, isT)`
Identifica robôs por:
- Forma geométrica (quadrados)
- Cores dos times
- Cores secundárias para identificação individual

### 2. `Ball` - Classe da Bola

**Modelo de Estado**:
```python
Estado Kalman: [x, y, θ, vx, vy, ω]
Medição: [x, y, θ]
```

**Métodos Principais**:
- `setPosition(x, y, r, timestamp)`: Define posição inicial
- `updatePosition()`: Atualiza com filtro de Kalman
- `predict_position(dt)`: Prediz posição futura

### 3. `Robot` - Classe dos Robôs

**Características**:
- Identificação por time (aliado/inimigo) e função (goleiro/atacante)
- Filtro de Kalman para suavização de movimento
- Detecção de direção e orientação

**Métodos de Movimento**:
```python
# Atualização com Kalman
robot.setPosition(x, y, r, image, time)

# Predição
position_predicted = robot.predict_position(dt)
```

### 4. `Field` - Classe do Campo

**Elementos Mapeados**:
- Extremidades do campo virtual
- Pontos de pivô (PA1, PA2, PA3, PE1, PE2, PE3)
- Áreas de gol (aliado/inimigo)
- Áreas dos goleiros

### 5. `ViewCapture` - Gerenciamento de Janelas

Controla a região de interesse (ROI) para processamento otimizado.

## 🔧 Sistema de Coordenadas

### Transformações Geométricas

#### 1. Sistema Virtual
```
Campo Virtual: 645×413 pixels
Proporção: 3 pixels/cm
Origem O': (67, 402) pixels
```

#### 2. Conversão para Coordenadas Reais
```python
def getPointVirtual(ptSrc):
    x_cm = (ptSrc[0] - self.xnv) / 3
    y_cm = (self.ynv - ptSrc[1]) / 3
    return x_cm, y_cm
```

#### 3. Homografia
```python
# Matriz de transformação campo real → virtual
H = findHomography(pts_campo_real, pts_campo_virtual)

# Transformação de ponto
ponto_virtual = cv2.perspectiveTransform(ponto_real, H)
```

## 🎨 Sistema de Cores e Detecção

### Esquema de Cores HSV
```python
# Bola - Laranja
ball_lower_bound = np.array([h-6, max(0, s-50), max(0, v-50)])
ball_upper_bound = np.array([h+6, min(255, s+50), min(255, v+50)])

# Objetos gerais
objectsDarkColor = np.array([0, 10, 130])
objectsLightColor = np.array([179, 255, 255])
```

### Pipeline de Detecção

#### 1. Pré-processamento
```python
gray = gray_scale(img)
blur = median_blur(gray, 3)
highlighted = highlight_img(blur, dimMatrix)
binary = binarize_up(highlighted, Thrashhold)
```

#### 2. Detecção de Formas
- **Campo**: Maior contorno com 4 vértices
- **Robôs**: Contornos quadrados com tamanho mínimo
- **Bola**: Contorno circular com cor específica

#### 3. Classificação
```python
# Verificação de time por dominância de cor
ally_ratio = ally_area / total_area
enemy_ratio = enemy_area / total_area

if ally_ratio > 0.55: team = "ally"
elif enemy_ratio > 0.55: team = "enemy"
```

## ⚡ Otimizações e Performance

### 1. Sistema Multi-thread
```python
# Processamento paralelo
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [
        executor.submit(self._processAlliesAndBall, timestamp),
        executor.submit(self._processEnemies, timestamp)
    ]
```

### 2. Modos de Operação
- **Processamento Completo**: Detecção completa a cada `newProcTime`
- **Predição Leve**: Usa Kalman entre processamentos completos

### 3. Gestão de Recursos
```python
def resetExecutionState(self):
    """Limpeza eficiente entre frames"""
    # Reset de imagens temporárias
    # Manutenção do estado persistente
    # Limpeza de threads finalizadas
```

# 🔮 Filtro de Kalman no Sistema de Visão VSS

## 📊 Visão Geral do Filtro de Kalman

O sistema implementa **filtros de Kalman estendidos** para rastreamento da bola e robôs, proporcionando estimativas suavizadas de posição, velocidade e orientação.

## 🎯 Filtro de Kalman para a Bola

### 🧮 Modelo de Estado da Bola

**Vetor de Estado** (6 dimensões):
```
x = [x, y, θ, vx, vy, ω]ᵀ
```

Onde:
- `x, y`: Posição em centímetros
- `θ`: Orientação (ângulo) em radianos
- `vx, vy`: Velocidade linear (cm/s)
- `ω`: Velocidade angular (rad/s)

### 📈 Equações de Predição

**Matriz de Transição de Estado**:
```python
F = np.array([
    [1, 0, 0, dt, 0,  0],  # x = x + vx·dt
    [0, 1, 0, 0,  dt, 0],  # y = y + vy·dt  
    [0, 0, 1, 0,  0, dt],  # θ = θ + ω·dt
    [0, 0, 0, 1,  0,  0],  # vx = vx (modelo velocidade constante)
    [0, 0, 0, 0,  1,  0],  # vy = vy
    [0, 0, 0, 0,  0,  1]   # ω = ω
])
```

**Equação de Predição**:
```
x̂ₖ⁻ = F · xₖ₋₁
Pₖ⁻ = F · Pₖ₋₁ · Fᵀ + Q
```

### 📉 Equações de Atualização

**Matriz de Observação** (medimos apenas posição e orientação):
```python
H = np.array([
    [1, 0, 0, 0, 0, 0],    # Medimos x
    [0, 1, 0, 0, 0, 0],    # Medimos y
    [0, 0, 1, 0, 0, 0]     # Medimos θ (derivado do movimento)
])
```

**Inovação e Ganho de Kalman**:
```
y = z - H · x̂ₖ⁻
S = H · Pₖ⁻ · Hᵀ + R
K = Pₖ⁻ · Hᵀ · S⁻¹
```

**Atualização Final**:
```
xₖ = x̂ₖ⁻ + K · y
Pₖ = (I - K · H) · Pₖ⁻
```

### 🎛️ Parâmetros do Filtro para Bola

```python
# Covariância do Processo (incerteza no modelo)
self.kalman_Q = np.diag([0.01, 0.01, 0.01, 5.0, 5.0, 1.0])

# Covariância da Medição (incerteza nas medidas)
self.kalman_R = np.diag([3.0, 3.0, 0.5])  # x, y, θ
```

## 🤖 Filtro de Kalman para Robôs

### 🧮 Modelo de Estado do Robô

**Vetor de Estado** (6 dimensões - mesmo da bola):
```
x = [x, y, θ, vx, vy, ω]ᵀ
```

### 📈 Matriz de Transição para Robôs

```python
F = np.array([
    [1, 0, 0, dt, 0,  0],  # x = x + vx·dt
    [0, 1, 0, 0,  dt, 0],  # y = y + vy·dt
    [0, 0, 1, 0,  0, dt],  # θ = θ + ω·dt
    [0, 0, 0, 1,  0,  0],  # vx = vx
    [0, 0, 0, 0,  1,  0],  # vy = vy  
    [0, 0, 0, 0,  0,  1]   # ω = ω
])
```

### 🎛️ Parâmetros do Filtro para Robôs

```python
# Covariância do Processo
self.kalman_Q = np.diag([0.01, 0.01, 0.01, 5.0, 5.0, 1.0])

# Covariância da Medição  
self.kalman_R = np.diag([3.0, 3.0, 0.5])  # x, y, θ
```

## 🔧 Implementação no Código

### Para Bola (`ball.py`):

```python
def update_kalman(self, z_list, timestamp):
    # z_list = [x_medido, y_medido, θ_medido]
    z = np.array([[x], [y], [theta_meas]])
    
    # PREDIÇÃO
    dt = timestamp - self.kalman_last_time
    F = self._compute_transition_matrix(dt)
    
    self.kalman_state = F @ self.kalman_state
    self.kalman_P = F @ self.kalman_P @ F.T + self.kalman_Q
    
    # ATUALIZAÇÃO
    H = np.array([[1,0,0,0,0,0], [0,1,0,0,0,0], [0,0,1,0,0,0]])
    y_residual = z - H @ self.kalman_state
    
    # Normalização angular para θ
    y_residual[2, 0] = (y_residual[2, 0] + np.pi) % (2 * np.pi) - np.pi
    
    S = H @ self.kalman_P @ H.T + self.kalman_R
    K = self.kalman_P @ H.T @ np.linalg.inv(S)
    
    self.kalman_state = self.kalman_state + K @ y_residual
    self.kalman_P = (np.eye(6) - K @ H) @ self.kalman_P
```

### Para Robôs (`robot.py`):

```python
def update_kalman(self, z_list, timestamp):
    # Implementação similar à da bola
    # Com mesma estrutura de matrizes e equações
```

## 🎯 Derivação da Orientação (θ)

### Para Bola:
```python
# θ é derivado do movimento entre frames
delta = self.newPosition - self.lastPosition
norm = np.linalg.norm(delta)

if norm > 1e-6:
    self.direction = delta / norm
    self.theta = float(np.arctan2(self.direction[1], self.direction[0]))
```

### Para Robôs:
```python
# θ é derivado da direção entre centro do robô e cor principal
direction = np.array([xi, -yi]) - np.array([x_m, -y_m])
norm = np.linalg.norm(direction)

if norm > 1e-6:
    direction = direction / norm
    self.theta = np.arctan2(direction[1], direction[0])
```

## 📊 Propriedades Filtradas

### Acesso às Estimativas Suavizadas:

```python
# Posição filtrada
ball.position_filtered      # [x, y] suavizados
robot.position_filtered     # [x, y] suavizados

# Orientação filtrada  
ball.theta_filtered         # θ suavizado
robot.theta_filtered        # θ suavizado

# Velocidades filtradas
ball.velocity_filtered      # [vx, vy] suavizados
robot.velocity_filtered     # [vx, vy] suavizados

# Velocidade angular filtrada
ball.omega_filtered         # ω suavizado
robot.omega_filtered        # ω suavizado
```

## 🔮 Predição de Posição Futura

### Método de Predição:

```python
def predict_position(self, dt=0.05):
    """Prediz posição após dt segundos"""
    if not self.kalman_initialized:
        return self.position
    
    F = np.array([
        [1, 0, 0, dt, 0, 0],
        [0, 1, 0, 0, dt, 0], 
        [0, 0, 1, 0, 0, dt],
        [0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 1]
    ])
    
    predicted = F @ self.kalman_state
    return predicted[:2, 0]  # Retorna [x_pred, y_pred]
```

## 🎪 Exemplo de Uso no Sistema

### No Processamento Principal:

```python
def predictObjects(self, img, tms):
    # Para cada robô e bola
    self.predictBall(timestamp)
    self.predictRobot(ID_Team.TEAM_ALLY, ID_Robots.ROBOT_ALLY_GOAL, timestamp)
    
def predictBall(self, timestamp):
    if ball.getStatus():
        ball.predictPosition(timestamp)
        P1, Dim = ball.getPredictPosition()
        # Usa posição predita para busca otimizada
```

## 📈 Análise das Matrizes de Covariância

### Matriz Q (Processo):
- **Posição (0.01)**: Baixa incerteza - modelo de movimento é confiável
- **Velocidade (5.0)**: Alta incerteza - acelerações podem ocorrer
- **Orientação (0.01)**: Baixa incerteza - mudanças graduais
- **Velocidade Angular (1.0)**: Incerteza moderada

### Matriz R (Medição):
- **Posição (3.0)**: Incerteza de ~3cm - típico de visão computacional
- **Orientação (0.5)**: Alta incerteza - θ é derivado, não medido diretamente

## 🎯 Vantagens desta Implementação

1. **Suavização**: Remove ruído das medidas de visão
2. **Predição**: Antecipa posições futuras para busca otimizada
3. **Estimação de Velocidade**: Deriva velocidades não medidas diretamente
4. **Robustez**: Lida com occlusões temporárias
5. **Consistência**: Mantém estimativas mesmo com medidas ruidosas

Este sistema de filtragem permite que o sistema de visão forneça estimativas suaves e preditivas essenciais para o controle em tempo real dos robôs no futebol robótico.

## 🎯 Configuração

### Objeto `EConfig`
```python
config = EConfig(
    offSetWindow=10,      # Margem da janela
    offSetErode=0,        # Iterações de erosão
    dimMatrix=25,         # Tamanho do kernel morfológico
    Thrashhold=235,       # Limiar de binarização
    fieldWidth=150,       # Largura do campo (cm)
    fieldHeight=130,      # Altura do campo (cm)
    # Cores em HSV...
)
```

## 📊 Saída do Sistema

### Estrutura de Dados
```python
objects = {
    ID_Objects.ALLIES: [robotAllyG, robotAlly1, robotAlly2],
    ID_Objects.ENEMIES: [robotEnemyG, robotEnemy1, robotEnemy2],
    ID_Objects.BALL: ball_object,
    ID_Objects.FIELD: field_object,
    'timestamp': self.dT
}
```

### Imagens de Debug
- `binaryObjects`: Objetos detectados
- `binaryBall`: Bola isolada
- `binaryPlayers`: Todos os jogadores
- `binaryAllTeam`: Time completo

## 🚀 Uso Básico

```python
# Inicialização
config = EConfig()
capture = Capture()
vs = VisionSystem(config=config, debug=True, capture=capture)

# Processamento contínuo
while True:
    img = capture.getImage()
    result = vs.processImg(img, debug=True)
    
    # Obter dados processados
    objects = vs.getObjects()
    ball_pos = objects[ID_Objects.BALL].position
```

Este sistema fornece uma base robusta para detecção em tempo real em ambientes dinâmicos, com arquitetura escalável e precisão adequada para competições robóticas.