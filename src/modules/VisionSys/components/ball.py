import numpy as np
from modules.VisionSys.components.objects import *

class Ball:
    """
    Classe da bola com suporte a direção, orientação e filtro de Kalman.
    OBS: a visão NÃO detecta theta. Ele é derivado do movimento.
    """

    def __init__(self, x=0, y=0, r=0):
        # --- Estado geométrico ---
        self.position = np.array([x, y], dtype=float)
        self.radius = float(r)

        # Direção (unitária)
        self._direction = np.array([0.0, 0.0], dtype=float)

        # Orientação (derivada *somente* do movimento)
        self._theta = 0.0  # rad

        # --- Estruturas geométricas ---
        self.objLimit = Circle(Point2D(x, y), self.radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)
        self.viewBall = ViewBot(Point2D(x, y), int(r + 14))

        # --- Status ---
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.BALL
        self.status = False

        # --- Tempo ---
        self.oldTimestamp = 0.0
        self.newTimestamp = 0.0
        self.dT = 0.0

        # --- Movimento ---
        self.lastPosition = self.position.copy()
        self.newPosition = self.position.copy()
        self.velocity = np.array([0.0, 0.0], dtype=float)
        self.omega = 0.0  # Velocidade angular derivada (não observada)

        # --- Kalman: estado [x, y, theta, vx, vy, omega] ---
        self.kalman_initialized = False
        self.kalman_last_time = None

        self.kalman_state = np.zeros((6, 1))
        self.kalman_P = np.eye(6) * 500.0

        # Ruído do processo
        self.kalman_Q = np.eye(6) * 0.05

        # Ruído da medição: x, y, theta (theta tem alta incerteza!)
        self.kalman_R = np.eye(3)
        self.kalman_R[0, 0] = 3.0
        self.kalman_R[1, 1] = 3.0
        self.kalman_R[2, 2] = 200.0  # θ é só derivado da posição

        # Cor da bola (médio HSV)
        self.color = None

    # ============================================================
    #         DIRECTION  <->  THETA (ANGULO)
    # ============================================================

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, d):
        d = np.asarray(d, dtype=float)
        norm = np.linalg.norm(d)

        if norm < 1e-6:
            return

        d = d / norm
        self._direction = d
        self._theta = float(np.arctan2(d[1], d[0]))

    @property
    def theta(self):
        return self._theta

    @theta.setter
    def theta(self, ang):
        self._theta = float(ang)
        self._direction = np.array([np.cos(self._theta),
                                    np.sin(self._theta)], dtype=float)

    # ======================================================================
    # 🔹 Atualização de posição
    # ======================================================================

    def setPosition(self, x, y, r, timestamp=0.0, theta=None):
        """
        Define posição inicial da bola.
        A BOLA NÃO TEM θ MEDIDO — sempre ignorar theta externo.
        """

        self.radius = float(r)

        self.position = np.array([x, y], dtype=float)
        self.lastPosition = self.position.copy()
        self.newPosition = self.position.copy()

        # direção e theta zerados, pois não há movimento
        self.direction = np.array([0.0, 0.0])
        self.theta = 0.0

        self.oldTimestamp = timestamp
        self.newTimestamp = timestamp
        self.dT = 0.0

        self.updateBbox()
        self.status = True

        # Inicializa Kalman com (x, y, θ=0)
        self.update_kalman(np.array([x, y, self.theta]), timestamp)

    def updatePosition(self, x, y, r, timestamp, theta=None):
        """
        Atualiza posição da bola e aplica filtro de Kalman.
        A bola NÃO recebe theta externo. Sempre derivamos do movimento.
        """

        self.radius = float(r)

        self.lastPosition = self.position.copy()
        self.newPosition = np.array([x, y], dtype=float)
        self.position = self.newPosition.copy()

        # --- Direção e orientação derivadas do deslocamento ---
        delta = self.newPosition - self.lastPosition
        n = np.linalg.norm(delta)

        if n > 1e-6:
            self.direction = delta / n
            self.theta = float(np.arctan2(self.direction[1], self.direction[0]))
        # se não houver deslocamento, mantém direção e theta

        # --- Tempo ---
        self.dT = max(timestamp - self.newTimestamp, 1e-3)
        self.oldTimestamp = self.newTimestamp
        self.newTimestamp = timestamp

        # --- Kalman usa x, y e theta derivado ---
        self.update_kalman(np.array([x, y, self.theta]), timestamp)

        self.updateBbox()
        self.status = True

    # ======================================================================
    # 🔹 Filtro de Kalman (estado completo)
    # ======================================================================

    def update_kalman(self, meas_xyz, timestamp):
        """
        Filtro de Kalman com estado:
            [x, y, theta, vx, vy, omega]
        Medição:
            [x, y, theta]
        θ NÃO é observado diretamente, é derivado.
        """

        mx, my, mtheta = meas_xyz.reshape(3,)
        z = np.array([[mx], [my], [mtheta]])

        # Inicialização
        if not self.kalman_initialized:
            self.kalman_state[0, 0] = mx
            self.kalman_state[1, 0] = my
            self.kalman_state[2, 0] = mtheta
            self.kalman_last_time = timestamp
            self.kalman_initialized = True
            return

        dt = max(timestamp - self.kalman_last_time, 1e-3)
        self.kalman_last_time = timestamp

        # Modelo de transição F
        F = np.array([
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1],
        ])

        # Predição
        self.kalman_state = F @ self.kalman_state
        self.kalman_P = F @ self.kalman_P @ F.T + self.kalman_Q

        # Matriz de observação H
        H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ])

        # Inovação
        y_res = z - (H @ self.kalman_state)

        # Normaliza erro angular
        y_res[2, 0] = (y_res[2, 0] + np.pi) % (2 * np.pi) - np.pi

        # Cálculo do ganho
        S = H @ self.kalman_P @ H.T + self.kalman_R
        K = self.kalman_P @ H.T @ np.linalg.inv(S)

        # Atualização
        self.kalman_state += K @ y_res
        self.kalman_P = (np.eye(6) - K @ H) @ self.kalman_P

        # sincroniza θ interno com θ filtrado
        self.theta = float(self.kalman_state[2, 0])

    # ======================================================================
    # 🔹 Propriedades filtradas
    # ======================================================================

    @property
    def position_filtered(self):
        if not self.kalman_initialized:
            return self.position
        return self.kalman_state[0:2, 0]

    @property
    def theta_filtered(self):
        if not self.kalman_initialized:
            return self.theta
        return self.kalman_state[2, 0]

    @property
    def direction_filtered(self):
        th = self.theta_filtered
        return np.array([np.cos(th), np.sin(th)])

    @property
    def velocity_filtered(self):
        if not self.kalman_initialized:
            return np.array([0.0, 0.0])
        return self.kalman_state[3:5, 0]

    @property
    def omega_filtered(self):
        if not self.kalman_initialized:
            return 0.0
        return self.kalman_state[5, 0]

    # ======================================================================
    # 🔹 Previsão
    # ======================================================================

    def predict_position(self, dt=0.05):
        """Prediz próxima posição considerando também theta."""
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
        return predicted[:2, 0]

    # ======================================================================
    # 🔹 Utilitários
    # ======================================================================

    def updateBbox(self):
        self.objLimit = Circle(Point2D(self.position[0], self.position[1]), self.radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)

    def setImgPosition(self, xb, yb, rb):
        self.xb, self.yb, self.rb = xb, yb, rb

    def setBallColor(self, c):
        self.color = c

    # ======================================================================
    # 🔹 Reset
    # ======================================================================

    def resetState(self):
        self.direction = np.array([0.0, 0.0])
        self.status = False
        self.lastPosition = self.position.copy()
        self.newPosition = self.position.copy()
        self.updateBbox()
        self.viewBall.updateViewBot(Point2D(self.position[0], self.position[1]))

    def reset(self):
        self.position[:] = 0
        self.lastPosition[:] = 0
        self.newPosition[:] = 0
        self.direction[:] = 0
        self.velocity[:] = 0
        self.theta = 0
        self.omega = 0
        self.status = False
        self.radius = 0

        self.kalman_initialized = False
        self.kalman_state[:] = 0
        self.kalman_P = np.eye(6) * 500
        self.kalman_last_time = None

        self.objLimit = Circle(Point2D(0, 0), 0)
        self.updateBbox()
        self.viewBall.updateViewBot(Point2D(0, 0))
