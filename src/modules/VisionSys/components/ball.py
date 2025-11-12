import numpy as np
from modules.VisionSys.components.objects import *

class Ball:
    """
    Classe responsável por representar a bola no sistema de visão,
    incluindo posição, velocidade, geometria e filtro de Kalman.
    """

    def __init__(self, x=0, y=0, r=0):
        # --- Posição, raio e direção ---
        self.position = np.array([x, y], dtype=float)
        self.radius = float(r)
        self.direction = np.array([0.0, 0.0], dtype=float)

        # --- Estruturas geométricas ---
        self.objLimit = Circle(Point2D(x, y), self.radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)
        self.viewBall = ViewBot(Point2D(x, y), int(r + 14))

        # --- Status e identificação ---
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.BALL
        self.status = False

        # --- Controle temporal ---
        self.oldTimestamp = 0.0
        self.newTimestamp = 0.0
        self.dT = 0.0

        # --- Posição e movimento ---
        self.lastPosition = self.position.copy()
        self.newPosition = self.position.copy()
        self.velocity = np.array([0.0, 0.0], dtype=float)

        # --- Filtro de Kalman ---
        self.kalman_initialized = False
        self.kalman_state = np.zeros((4, 1))  # [x, y, vx, vy]
        self.kalman_P = np.eye(4) * 1000.0
        self.kalman_Q = np.eye(4) * 0.01
        self.kalman_R = np.eye(2) * 5.0
        self.kalman_last_time = None

        # --- Cor da bola (opcional) ---
        self.color = None

    # ======================================================================
    # 🔹 Atualização de posição
    # ======================================================================

    def setPosition(self, x, y, r, timestamp=0.0):
        """Define a posição inicial da bola (sem deslocamento anterior)."""
        self.radius = float(r)
        self.position = np.array([x, y], dtype=float)
        self.newPosition = self.position.copy()
        self.lastPosition = self.position.copy()
        self.direction = np.array([0.0, 0.0])

        self.oldTimestamp = timestamp
        self.newTimestamp = timestamp
        self.dT = 0.0

        self.updateBbox()
        self.status = True

        # Inicializa o filtro de Kalman
        self.update_kalman(self.position, timestamp)

    def updatePosition(self, x, y, r, timestamp):
        """Atualiza posição da bola e aplica filtro de Kalman."""
        self.radius = float(r)
        self.lastPosition = self.position.copy()
        self.newPosition = np.array([x, y], dtype=float)
        self.position = self.newPosition.copy()
        self.direction = self.newPosition - self.lastPosition

        self.dT = max(timestamp - self.newTimestamp, 1e-3)
        self.oldTimestamp = self.newTimestamp
        self.newTimestamp = timestamp

        # Atualiza filtro de Kalman
        self.update_kalman(self.position, timestamp)

        self.updateBbox()
        self.status = True

    # ======================================================================
    # 🔹 Filtro de Kalman
    # ======================================================================

    def update_kalman(self, measured_pos, timestamp):
        """Atualiza o filtro de Kalman com uma nova medição."""
        x, y = measured_pos
        z = np.array([[x], [y]])

        # Inicialização
        if not self.kalman_initialized:
            self.kalman_state[:2, 0] = [x, y]
            self.kalman_initialized = True
            self.kalman_last_time = timestamp
            return

        dt = max(timestamp - self.kalman_last_time, 1e-3)
        self.kalman_last_time = timestamp

        # Matriz de transição de estado
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])

        # Predição
        self.kalman_state = F @ self.kalman_state
        self.kalman_P = F @ self.kalman_P @ F.T + self.kalman_Q

        # Observação
        H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])

        # Atualização
        y_residual = z - H @ self.kalman_state
        S = H @ self.kalman_P @ H.T + self.kalman_R
        K = self.kalman_P @ H.T @ np.linalg.inv(S)

        self.kalman_state += K @ y_residual
        self.kalman_P = (np.eye(4) - K @ H) @ self.kalman_P

    @property
    def position_filtered(self):
        """Retorna a posição suavizada pelo filtro de Kalman."""
        if not self.kalman_initialized:
            return self.position
        return self.kalman_state[:2, 0]

    @property
    def velocity_filtered(self):
        """Retorna a velocidade estimada pelo filtro de Kalman."""
        if not self.kalman_initialized:
            return np.array([0.0, 0.0])
        return self.kalman_state[2:, 0]

    def predict_position(self, dt=0.05):
        """Prediz a próxima posição da bola com base no filtro de Kalman."""
        if not self.kalman_initialized:
            return self.position
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        predicted = F @ self.kalman_state
        return predicted[:2, 0]

    # ======================================================================
    # 🔹 Outras funções utilitárias
    # ======================================================================

    def getVelocity(self, timestamp):
        """Retorna a velocidade atual da bola."""
        return self.velocity_filtered

    def updateBbox(self):
        """Atualiza a bounding box e geometria da bola."""
        self.objLimit = Circle(Point2D(self.position[0], self.position[1]), self.radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)

    def getPredictPosition(self):
        """Retorna o ponto de predição e o tamanho da view da bola."""
        return self.viewBall.Pe1, self.viewBall.DimMatrix

    def getStatus(self):
        """Retorna se a bola foi detectada."""
        return self.status

    def setImgPosition(self, xb, yb, rb):
        """Define a posição da bola na imagem reduzida."""
        self.xb, self.yb, self.rb = xb, yb, rb

    def setBallColor(self, colorBall):
        """Define a cor da bola para segmentação."""
        self.color = colorBall

    # ======================================================================
    # 🔹 Reset
    # ======================================================================
    def resetState(self):
        """
        Reinicia apenas o estado transitório da bola,
        preservando o filtro de Kalman e a posição atual.
        """
        self.direction = np.array([0.0, 0.0])
        self.dT = 0.0
        self.status = False

        # Mantém a posição e o filtro de Kalman
        self.lastPosition = self.position
        self.newPosition = self.position

        # Atualiza limites e geometria
        self.objLimit = Circle(Point2D(self.position[0], self.position[1]), self.radius)
        self.updateBbox()
        self.viewBall.updateViewBot(Point2D(self.position[0], self.position[1]))


    def reset(self):
        """
        Reset completo — zera tudo, incluindo o filtro de Kalman.
        Usado apenas no modo imagem.
        """
        self.position = np.array([0.0, 0.0])
        self.lastPosition = self.position
        self.newPosition = self.position
        self.direction = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])
        self.status = False
        self.radius = 0.0
        self.dT = 0.0
        self.newTimestamp = 0
        self.oldTimestamp = 0

        # Reset Kalman
        self.kalman_initialized = False
        self.kalman_state = np.zeros((4, 1))
        self.kalman_P = np.eye(4) * 1000.0
        self.kalman_last_time = None

        # Atualiza geometria
        self.objLimit = Circle(Point2D(0, 0), 0)
        self.updateBbox()
        self.viewBall.updateViewBot(Point2D(0, 0))

