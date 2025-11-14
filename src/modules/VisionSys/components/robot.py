import numpy as np
import cv2
from modules.VisionSys.components.objects import *

class Robot:
    def __init__(self, id: ID_Robots, team: ID_Team, x=0, y=0, r=0, 
                 image=cv2.imread('src/images/dark_screen.png'),
                 colorTeam=None, colorCar1=None, colorCar2=None,
                 differential_filter=False):  # ADICIONADO
        '''
        Classe Robot utilizada no algoritmo de detecção para representar os robôs.
        '''
        # --- Identificadores ---
        self.id = id
        self.team = team

        # --- Posição e movimento ---
        self.position = np.array([round(x, 2), round(y, 2)])
        self.lastPosition = self.position
        self.newPosition = self.position
        self.direction = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])
        self.theta = 0.0  # ADICIONADO: ângulo do robô
        self.omega = 0.0  # ADICIONADO: velocidade angular

        # --- Informação na imagem ---
        self.xi = 0
        self.yi = 0
        self.ri = 0

        # --- Geometria ---
        self.radius = round(r, 2)
        self.objLimit = Circle(self.radius, Point2D(x, y))
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.ROBOT

        # --- Status ---
        self.detected = False
        self.possessionBall = False

        # --- Imagem e janela ---
        self.image = image
        self.dimMatrix = image.shape[1] if image is not None else 0
        self.viewRect = ViewBot(Point2D(self.position[0], self.position[1]), self.dimMatrix)

        # --- Cores ---
        self.colorTeam = colorTeam
        self.colorCar1 = colorCar1
        self.colorCar2 = colorCar2

        # --- Tempo ---
        self.lastTimestamp = 0
        self.newTimestamp = 0
        self.dT = 0

        # --- Filtro de Kalman ---
        self.differential_filter = differential_filter  # ADICIONADO
        self._init_kalman()  # ADICIONADO

    # ===========================
    # 🔹 Inicialização do filtro
    # ===========================
    def _init_kalman(self):  # ADICIONADO
        if self.differential_filter:
            # Estado [x, y, theta]
            self.kalman_state = np.zeros((3, 1))
            self.kalman_P = np.eye(3) * 1000.0
            self.kalman_Q = np.eye(3) * 0.01
            self.kalman_R = np.eye(3) * 5.0
        else:
            # Estado linear [x, y, vx, vy]
            self.kalman_state = np.zeros((4, 1))
            self.kalman_P = np.eye(4) * 1000.0
            self.kalman_Q = np.eye(4) * 0.01
            self.kalman_R = np.eye(2) * 5.0

        self.kalman_initialized = False
        self.kalman_last_time = None

    # ===========================
    # 🔹 Setter para tipo de filtro
    # ===========================
    def set_differential_filter(self, differential: bool):  # ADICIONADO
        """
        Define se o filtro deve ser diferencial (True) ou linear (False).
        """
        self.differential_filter = differential
        self._init_kalman()

    # ===========================
    # 🔹 Atualização de posição
    # ===========================
    def setPosition(self, x, y, r, image, time, wheel_velocities=None):  # ADICIONADO wheel_velocities
        self.lastTimestamp = self.newTimestamp
        self.newTimestamp = time
        self.dT = self.newTimestamp - self.lastTimestamp if self.lastTimestamp != 0 else 0.0

        self.lastPosition = self.position
        if np.linalg.norm([x - self.lastPosition[0], y - self.lastPosition[1]]) > 0.5:
            self.position = np.array([round(x, 2), round(y, 2)])
        else:
            self.position = self.lastPosition

        self.radius = round(r, 2)
        self.image = image
        if image is not None:
            self.viewRect.setDimension(image.shape[1])

        self.newPosition = self.position
        self.direction = self.newPosition - self.lastPosition
        self.objLimit = Circle(self.radius, Point2D(x, y))
        self.viewRect.updateViewBot(Point2D(x, y))
        self.updateBbox()

        # Atualiza filtro de Kalman
        if self.differential_filter:
            theta_meas = self.theta
            self.update_kalman([x, y, theta_meas], time, wheel_velocities)
        else:
            self.update_kalman([x, y], time)

    def updatePosition(self, x, y, r, image, time, wheel_velocities=None):  # ADICIONADO wheel_velocities
        self.setPosition(x, y, r, image, time, wheel_velocities)

    # ===========================
    # 🔹 Filtro de Kalman
    # ===========================
    def update_kalman(self, measured_pos, timestamp, wheel_velocities=None):  # ADICIONADO wheel_velocities
        if self.differential_filter:
            # EKF [x, y, theta]
            x, y, theta_meas = measured_pos
            z = np.array([[x], [y], [theta_meas]])

            if not self.kalman_initialized:
                self.kalman_state[:, 0] = [x, y, theta_meas]
                self.kalman_initialized = True
                self.kalman_last_time = timestamp
                return

            dt = max(timestamp - self.kalman_last_time, 1e-3)
            self.kalman_last_time = timestamp

            if wheel_velocities is None:
                v, omega = 0, 0
            else:
                v_l, v_r = wheel_velocities
                L = 7.5  # distância entre rodas, ajustar conforme necessário
                v = (v_r + v_l) / 2
                omega = (v_r - v_l) / L

            theta = self.kalman_state[2, 0]
            x_pred = self.kalman_state[0, 0] + v * np.cos(theta) * dt
            y_pred = self.kalman_state[1, 0] + v * np.sin(theta) * dt
            theta_pred = theta + omega * dt
            self.kalman_state[:, 0] = [x_pred, y_pred, theta_pred]

            F = np.array([
                [1, 0, -v * np.sin(theta) * dt],
                [0, 1,  v * np.cos(theta) * dt],
                [0, 0, 1]
            ])

            self.kalman_P = F @ self.kalman_P @ F.T + self.kalman_Q

            H = np.eye(3)
            y_residual = z - H @ self.kalman_state
            S = H @ self.kalman_P @ H.T + self.kalman_R
            K = self.kalman_P @ H.T @ np.linalg.inv(S)

            self.kalman_state += K @ y_residual
            self.kalman_P = (np.eye(3) - K @ H) @ self.kalman_P

        else:
            # Filtro linear [x, y, vx, vy]
            x, y = measured_pos
            z = np.array([[x], [y]])

            if not self.kalman_initialized:
                self.kalman_state[:2, 0] = [x, y]
                self.kalman_initialized = True
                self.kalman_last_time = timestamp
                return

            dt = max(timestamp - self.kalman_last_time, 1e-3)
            self.kalman_last_time = timestamp

            F = np.array([
                [1, 0, dt, 0],
                [0, 1, 0, dt],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ])

            self.kalman_state = F @ self.kalman_state
            self.kalman_P = F @ self.kalman_P @ F.T + self.kalman_Q

            H = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0]
            ])

            y_residual = z - H @ self.kalman_state
            S = H @ self.kalman_P @ H.T + self.kalman_R
            K = self.kalman_P @ H.T @ np.linalg.inv(S)

            self.kalman_state += K @ y_residual
            self.kalman_P = (np.eye(4) - K @ H) @ self.kalman_P

    # ===========================
    # 🔹 Propriedades
    # ===========================
    @property
    def position_filtered(self):
        if not self.kalman_initialized:
            return self.newPosition
        return self.kalman_state[:2, 0]

    @property
    def theta_filtered(self):
        if not self.kalman_initialized or not self.differential_filter:
            return self.theta
        return self.kalman_state[2, 0]

    # ======================================================================
    # 🔹 Previsão de posição
    # ======================================================================
    def predict_position(self, dt=0.05):
        """
        Retorna a posição prevista pelo filtro de Kalman.
        Se diferencial, retorna [x, y, theta]; se linear, retorna [x, y].
        """
        if not self.kalman_initialized:
            return np.array([*self.newPosition, self.theta]) if self.differential_filter else self.newPosition

        if self.differential_filter:
            x, y, theta = self.kalman_state[:, 0]
            # Predição simples para dt usando modelo diferencial
            predicted_x = x + np.cos(theta) * dt * self.velocity_filtered[0]  # aprox. v * dt
            predicted_y = y + np.sin(theta) * dt * self.velocity_filtered[0]
            predicted_theta = theta + self.omega * dt
            return np.array([predicted_x, predicted_y, predicted_theta])
        else:
            F = np.array([
                [1, 0, dt, 0],
                [0, 1, 0, dt],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ])
            predicted = F @ self.kalman_state
            return predicted[:2, 0]

    # ======================================================================
    # 🔹 Informações auxiliares
    # ======================================================================
    def updtPositionImg(self, xi, yi, ri):
        self.xi = xi
        self.yi = yi
        self.ri = ri

    def setStatus(self, status):
        self.detected = status

    def setColor(self, colorT=None, colorP=None, colorS=None):
        self.colorTeam = colorT
        self.colorCar1 = colorP
        self.colorCar2 = colorS

    def setTeamColor(self, colorTeam=None):
        self.colorTeam = colorTeam

    def setRadius(self, radius):
        self.radius = round(radius, 2)

    def getVelocity(self, timestamp=None):
        if not self.kalman_initialized:
            return np.array([0.0, 0.0])
        if self.differential_filter:
            # Aproximação simples: derivada de x,y
            dx = self.kalman_state[0, 0] - self.lastPosition[0]
            dy = self.kalman_state[1, 0] - self.lastPosition[1]
            return np.array([dx, dy])
        else:
            return self.velocity_filtered

    def updateBbox(self):
        self.objLimit = Circle(Point2D(self.position[0], self.position[1]), self.radius)
        self.bbox.attPosition(self.objLimit)

    def getPredictPosition(self):
        return self.viewRect.Pe1, self.viewRect.DimMatrix

    def getStatus(self):
        return self.detected

    def getColors(self):
        return self.colorTeam, self.colorCar1, self.colorCar2

    # ======================================================================
    # 🔹 Reset de estado parcial
    # ======================================================================
    def resetState(self):
        """
        Reinicia apenas o estado transitório do robô,
        sem apagar o histórico do filtro de Kalman.
        """
        self.direction = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])
        self.detected = False
        self.possessionBall = False
        self.dT = 0.0

        self.lastPosition = self.position
        self.newPosition = self.position

        self.objLimit = Circle(self.radius, Point2D(self.position[0], self.position[1]))
        self.updateBbox()
        self.viewRect.updateViewBot(Point2D(self.position[0], self.position[1]))

    # ======================================================================
    # 🔹 Reset completo
    # ======================================================================
    def reset(self):
        """
        Reset completo — limpa todos os estados, incluindo o filtro de Kalman.
        """
        self.position = np.array([0.0, 0.0])
        self.lastPosition = self.position
        self.newPosition = self.position
        self.direction = np.array([0.0, 0.0])
        self.velocity = np.array([0.0, 0.0])
        self.theta = 0.0
        self.omega = 0.0
        self.detected = False
        self.possessionBall = False
        self.dT = 0.0
        self.lastTimestamp = 0
        self.newTimestamp = 0

        self._init_kalman()  # Reinicializa o filtro conforme o tipo

        self.objLimit = Circle(self.radius, Point2D(0, 0))
        self.updateBbox()
        self.viewRect.updateViewBot(Point2D(0, 0))
