import numpy as np
from modules.VisionSys.components.objects import *

class Robot:
    def __init__(self, id, team, x=0, y=0, theta=0, r=0,
                 image=cv2.imread('src/images/dark_screen.png'),
                 colorTeam=None, colorCar1=None, colorCar2=None):
        """
        Classe Robot com suporte a Filtro de Kalman (EKF)
        - (x, y, θ): coordenadas reais no campo
        - (xi, yi, ri): coordenadas na imagem de detecção
        """
        self.id = id
        self.team = team

        # Estado físico real
        self._x = float(x)
        self._y = float(y)
        self._theta = float(theta)

        # Posição de imagem (detecção visual)
        self._xi = 0
        self._yi = 0
        self._ri = 0

        # Raio real e imagem
        self.radius = float(r)
        self.image = image

        # Direção e velocidade
        self.direction = np.array([np.cos(theta), np.sin(theta)])
        self.velocity = np.zeros(2)

        # Tempo
        self.lastTimestamp = 0.0
        self.newTimestamp = 0.0
        self.dT = 0.0

        # Estado de detecção
        self.detected = False

        # Cores do robô
        self.colorTeam = colorTeam
        self.colorCar1 = colorCar1
        self.colorCar2 = colorCar2

        # Kalman Filter
        self.kf_initialized = False
        self.x_hat = np.array([[self._x], [self._y], [self._theta]])
        self.P = np.eye(3) * 1e-2
        self.Q = np.eye(3) * 1e-3
        self.R = np.eye(3) * 1e-2

        # Imagem de detecção do carro
        self.image = image 
        self.dimMatrix = image.shape[1]

        # Janela para informar a posição do jogador:
        self.viewRect = ViewBot(Point2D(self._x, self._y), int(self.radius + 14))
    

    # -------------------------------
    # PROPRIEDADES - COORDENADAS REAIS
    # -------------------------------
    @property
    def x(self): return self._x

    @x.setter
    def x(self, value):
        self._x = round(float(value), 3)
        self._update_direction()

    @property
    def y(self): return self._y

    @y.setter
    def y(self, value):
        self._y = round(float(value), 3)
        self._update_direction()

    @property
    def theta(self): return self._theta

    @theta.setter
    def theta(self, value):
        self._theta = float(value) % (2 * np.pi)
        self._update_direction()

    # -------------------------------
    # PROPRIEDADES - COORDENADAS DE IMAGEM
    # -------------------------------
    @property
    def xi(self): return self._xi

    @xi.setter
    def xi(self, value): self._xi = int(value)

    @property
    def yi(self): return self._yi

    @yi.setter
    def yi(self, value): self._yi = int(value)

    @property
    def ri(self): return self._ri

    @ri.setter
    def ri(self, value): self._ri = int(value)

    # -------------------------------
    # DIREÇÃO E VELOCIDADE
    # -------------------------------
    def _update_direction(self):
        """Atualiza vetor de direção com base no ângulo atual."""
        self.direction = np.array([np.cos(self._theta), np.sin(self._theta)])

    # -------------------------------
    # FILTRO DE KALMAN
    # -------------------------------
    def init_kalman(self, P0=None, Q=None, R=None):
        """Inicializa o EKF"""
        self.kf_initialized = True
        if P0 is not None: self.P = P0
        if Q is not None: self.Q = Q
        if R is not None: self.R = R
        self.x_hat = np.array([[self._x], [self._y], [self._theta]])

    def ekf_predict(self, wl, wr, L, Rw, dt):
        """
        Predição (modelo diferencial)
        wl, wr: velocidades das rodas
        L: distância entre rodas
        Rw: raio das rodas
        """
        if not self.kf_initialized:
            self.init_kalman()

        v = (Rw / 2.0) * (wr + wl)
        w = (Rw / L) * (wr - wl)
        theta = self.x_hat[2, 0]

        # Predição do estado
        x_pred = self.x_hat[0, 0] + v * np.cos(theta) * dt
        y_pred = self.x_hat[1, 0] + v * np.sin(theta) * dt
        theta_pred = theta + w * dt
        self.x_hat = np.array([[x_pred], [y_pred], [theta_pred]])

        # Jacobiano A_k
        A = np.eye(3)
        A[0, 2] = -v * np.sin(theta) * dt
        A[1, 2] =  v * np.cos(theta) * dt

        # Covariância
        self.P = A @ self.P @ A.T + self.Q

        # Atualiza estado real
        self._x, self._y, self._theta = x_pred, y_pred, theta_pred
        self._update_direction()

    def ekf_update(self, z):
        """Atualização com medida z = [x, y, θ]"""
        if not self.kf_initialized:
            self.init_kalman()

        H = np.eye(3)
        y_tilde = z.reshape(3, 1) - H @ self.x_hat
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)

        self.x_hat += K @ y_tilde
        self.P = (np.eye(3) - K @ H) @ self.P

        self._x, self._y, self._theta = self.x_hat.flatten()
        self._update_direction()

    # -------------------------------
    # PREDIÇÃO E JANELA DE BUSCA
    # -------------------------------
    def predictPosition(self, wl=None, wr=None, L=0.1, Rw=0.02, timestamp=0.0):
        """Prevê posição do robô usando EKF"""
        if self.lastTimestamp == 0:
            self.lastTimestamp = timestamp
            return

        self.dT = timestamp - self.lastTimestamp
        self.lastTimestamp = timestamp

        if self.kf_initialized and wl is not None and wr is not None:
            self.ekf_predict(wl, wr, L, Rw, self.dT)

    def getSearchWindow(self, scale_factor=2.0):
        """Define a janela adaptativa baseada na incerteza (P)."""
        if not self.kf_initialized:
            return (int(self._xi), int(self._yi), 40, 40)

        sigma_x = np.sqrt(self.P[0, 0])
        sigma_y = np.sqrt(self.P[1, 1])
        w = int(scale_factor * sigma_x * 100)
        h = int(scale_factor * sigma_y * 100)
        return (int(self._xi - w / 2), int(self._yi - h / 2), w, h)

    # -------------------------------
    # MÉTODOS DE STATUS
    # -------------------------------
    def setDetected(self, status: bool):
        self.detected = status

    def getStatus(self):
        return self.detected

    def setImagePosition(self, xi, yi, ri):
        """Atualiza posição detectada na imagem."""
        self._xi, self._yi, self._ri = int(xi), int(yi), int(ri)

    def getImagePosition(self):
        """Retorna (xi, yi, ri)."""
        return self._xi, self._yi, self._ri

    def updatePosition(self, x, y, r, image, time):
        return 1

    def setColor(self, colorTeam, colorCar1, colorCar2):
        """Define as cores do robô."""
        self.colorTeam = colorTeam
        self.colorCar1 = colorCar1
        self.colorCar2 = colorCar2

    def getColor(self):
        return self.colorTeam, self.colorCar1, self.colorCar2