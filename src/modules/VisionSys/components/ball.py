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

        self.kalman_state = np.zeros((5, 1))
        self.kalman_P = np.eye(5) * 500.0

        self.kalman_Q = np.eye(5) * 0.05
        self.kalman_R = np.eye(3)
        self.kalman_R[0, 0] = 3.0     # x
        self.kalman_R[1, 1] = 3.0     # y
        self.kalman_R[2, 2] = 300.0   # theta é ruidoso

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

    def setPositionNoKalman(self, x, y, r, timestamp=0.0, theta=None):
        self.radius = float(r)

        self.lastPosition = self.position.copy()
        self.position = np.array([x, y], dtype=float)
        self.newPosition = self.position.copy()

        if theta is not None:
            self.theta = theta   # atualiza direction internamente
        else:
            # mantém direção atual
            pass

        self.oldTimestamp = self.newTimestamp
        self.newTimestamp = timestamp
        self.dT = max(self.newTimestamp - self.oldTimestamp, 1e-3)

        self.updateBbox()
        self.viewBall.updateViewBot(Point2D(x, y))

        # NÃO CHAMA update_kalman
        self.status = False

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
            [1, 0, 0, dt, 0],   # x
            [0, 1, 0, 0, dt],   # y
            [0, 0, 1, 0, 0],    # theta (constante)
            [0, 0, 0, 1, 0],    # vx
            [0, 0, 0, 0, 1],    # vy
        ])

        # Matriz de observação H
        H = np.array([
            [1, 0, 0, 0, 0, 0], #x
            [0, 1, 0, 0, 0, 0], #y
            [0, 0, 1, 0, 0, 0] #theta
        ])

        # Predição
        self.kalman_state = F @ self.kalman_state
        self.kalman_P = F @ self.kalman_P @ F.T + self.kalman_Q

        # Inovação
        y_res = z - (H @ self.kalman_state)
        y_res[2, 0] = (y_res[2, 0] + np.pi) % (2 * np.pi) - np.pi

        # Ganho
        S = H @ self.kalman_P @ H.T + self.kalman_R
        K = self.kalman_P @ H.T @ np.linalg.inv(S)

        # Atualização
        self.kalman_state += K @ y_res
        self.kalman_P = (np.eye(5) - K @ H) @ self.kalman_P

        # Atualiza θ interno
        self.theta = float(self.kalman_state[2, 0])


    # ======================================================================
    # 🔹 Propriedades filtradas
    # ======================================================================

    @property
    def position_filtered(self):
        return self.kalman_state[0:2, 0]

    @property
    def theta_filtered(self):
        return self.kalman_state[2, 0]

    @property
    def direction_filtered(self):
        th = self.theta_filtered
        return np.array([np.cos(th), np.sin(th)])

    @property
    def velocity_filtered(self):
        return self.kalman_state[3:5, 0]

    # ======================================================================
    # 🔹 Previsão
    # ======================================================================
    def predict(self, timestamp):
        # Se o Kalman nunca foi inicializado, devolve estado atual sem previsão
        if not self.kalman_initialized or self.kalman_last_time is None:
            return self.position[0], self.position[1], self.theta

        # dt relativo ao último UPDATE real, não altera estado
        dt = timestamp - self.kalman_last_time
        if dt < 0:
            dt = 0.0
        elif dt < 1e-3:
            dt = 1e-3

        F = np.array([
            [1, 0, 0, dt, 0],
            [0, 1, 0, 0, dt],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 1, 0],
            [0, 0, 0, 0, 1],
        ])

        # Predição *sem alterar o filtro*
        x_pred = F @ self.kalman_state

        return x_pred[0,0], x_pred[1,0], x_pred[2,0]




    def get_roi(self, image_shape, t_now, scale_std=3):
        """
        Retorna as dimensões do ROI centrado na previsão do Kalman,
        baseado nas variâncias do Kalman.

        Parâmetros:
            image_shape : tuple(int, int)
                (altura, largura) da imagem
            scale_std : float
                Multiplicador da raiz quadrada da variância para definir o ROI
            t_now = timestamp atual para realizar a predição
        Retorna:
            tuple: (x, y, w, h) coordenadas do topo-esquerdo e tamanho do ROI
        """
        # --- 1) Posição predita ---
        x_pred, y_pred, _ = self.predict(t_now)
        x_c, y_c = x_pred, y_pred

        # --- 2) Calcula desvio padrão das coordenadas x e y ---
        if self.kalman_initialized:
            std_x = np.sqrt(self.kalman_P[0, 0])
            std_y = np.sqrt(self.kalman_P[1, 1])
        else:
            std_x = std_y = 20.0  # fallback se Kalman não inicializado

        # --- 3) Define tamanho do ROI ---
        w_roi = int(scale_std * std_x * 2)  # multiplicado por 2 para pegar ±std
        h_roi = int(scale_std * std_y * 2)

        # Impor valores mínimos para impedir estrangulamento
        w_roi = max(w_roi, 12)
        h_roi = max(w_roi, 14)
        
        # --- 4) Topo-esquerdo ---
        x = int(x_c - w_roi // 2)
        y = int(y_c - h_roi // 2)

        # --- 5) Ajusta limites à imagem ---
        h_img, w_img = image_shape[:2]
        x = max(0, min(x, w_img - 1))
        y = max(0, min(y, h_img - 1))
        w_roi = min(w_roi, w_img - x)
        h_roi = min(h_roi, h_img - y)

        return x, y, w_roi, h_roi


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
