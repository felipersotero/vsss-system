

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

#### `processImg(img, debug)`
Gerencia o modo de operação:
- **Modo Imagem**: Processamento completo único
- **Modo Vídeo**: Alterna entre processamento completo e predição

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

#### `detect_field(img, debug)`
Detecta e transforma o campo usando homografia

#### `detect_ball(img, colorBall, debug)`
Detecta a bola por cor HSV e aplica filtros morfológicos

#### `detect_players(img, debug, isT)`
Identifica robôs por forma geométrica e cores dos times

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
- Identificação por time (aliado/inimigo) e função
- Filtro de Kalman para suavização de movimento
- Detecção de direção e orientação

### 4. `Field` - Classe do Campo

**Elementos Mapeados**:
- Extremidades do campo virtual
- Pontos de pivô (PA1, PA2, PA3, PE1, PE2, PE3)
- Áreas de gol (aliado/inimigo)
- Áreas dos goleiros

## 🔧 Sistema de Coordenadas e Transformações

### Transformações Geométricas

O sistema usa duas etapas principais para converter medidas da imagem para o sistema de controle:

#### 1. **Homografia** - Correção de Perspectiva
```
[px_real (camera)] --(transformPoint/H)--> [px_virtual]
```

**Funções Principais**:
- `getHomographyMatrix(ptsSrc, ptsFinal)`: Calcula matriz H
- `transformPoint(ptSrc)`: Aplica H para mapear px_real → px_virtual
- `invTransformPoint(ptSrc)`: Mapeia px_virtual → px_real (H⁻¹)

#### 2. **Virtualização** - Conversão para Métricas
```
[px_virtual] --(getPointVirtual)--> [x_cm, y_cm]
```

**Fórmulas de Conversão**:
```python
x_cm = (x_px - xnv) / pixels_por_cm      # pixels_por_cm = 3
y_cm = (ynv - y_px) / pixels_por_cm      # inverte eixo Y
```

**Parâmetros do Sistema Virtual**:
```
Campo Virtual: 645×413 pixels
Proporção: 3 pixels/cm  
Origem O': (67, 402) pixels
```

### Pipeline Completo de Transformação

```python
# Exemplo de uso no detector
(xb, yb), rb = cv2.minEnclosingCircle(ballContour)      # px_real
xv, yv = self.transformPoint(np.array([xb, yb]))        # px_virtual  
xcm, ycm = self.getPointVirtual(np.array([xv, yv]))     # cm
self.ball.setPosition(xcm, ycm, rb, timestamp)          # atualiza KF
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

## 🔮 Filtro de Kalman no Sistema de Visão VSS

### 📊 Visão Geral

O sistema implementa **filtros de Kalman** para rastreamento da bola e robôs, proporcionando estimativas suavizadas de posição, velocidade e orientação.

### 🎯 Modelo de Estado

**Vetor de Estado** (6 dimensões):
```
x = [x, y, θ, vx, vy, ω]ᵀ
```

### 📈 Equações de Predição

**Matriz de Transição**:
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

### 🎛️ Parâmetros do Filtro

```python
# Covariância do Processo
self.kalman_Q = np.diag([0.01, 0.01, 0.01, 5.0, 5.0, 1.0])

# Covariância da Medição  
self.kalman_R = np.diag([3.0, 3.0, 0.5])  # x, y, θ
```

## 🔍 Filtered Detection

O método `filtered_detection` localiza robôs de forma **otimizada**, usando o filtro de Kalman para reduzir a área de busca.

### Fluxo de Rastreamento:

1. **Predição do Kalman** - Define ROI ao redor da posição prevista
2. **Detecção na ROI** - Busca otimizada em área reduzida  
3. **Atualização/ Fallback** - Atualiza Kalman ou usa predição

### Benefícios:
- **Processamento mais rápido**: Detecção em janelas reduzidas
- **Robustez em oclusões**: Kalman mantém posição plausível
- **Integração simples**: Compatível com métodos existentes

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

## ⚠️ Considerações Técnicas

### Limitações e Recomendações:

1. **Homografia**: Só válida para pontos no plano do campo
2. **Distorção de lente**: Calibração de câmera recomendada
3. **Condicionamento de H**: Verificar `cond(H)` antes de inverter
4. **Escala consistente**: Manter `pixels_por_cm` único no sistema

### Validação:
- Testar homografia com pontos de referência
- Verificar precisão em diferentes regiões do campo
- Monitorar condicionamento da matriz H em runtime

Este sistema fornece uma base robusta para detecção em tempo real em ambientes dinâmicos, com arquitetura escalável e precisão adequada para competições robóticas.