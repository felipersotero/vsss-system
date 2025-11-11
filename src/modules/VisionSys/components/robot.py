import numpy as np
import cv2
from modules.VisionSys.components.objects import *

class Robot:
    def __init__(self, id: ID_Robots, team: ID_Team, x=0, y=0, r=0, 
                 image=cv2.imread('src/images/dark_screen.png'),
                 colorTeam=None, colorCar1=None, colorCar2=None):
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
        self.kalman_initialized = False
        self.kalman_state = np.zeros((4, 1))  # [x, y, vx, vy]
        self.kalman_P = np.eye(4) * 1000.0
        self.kalman_Q = np.eye(4) * 0.01
        self.kalman_R = np.eye(2) * 5.0
        self.kalman_last_time = None

    # ======================================================================
    # 🔹 Atualização de posição
    # ======================================================================

    def setPosition(self, x, y, r, image, time):
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
        self.update_kalman(self.position, time)

    def updatePosition(self, x, y, r, image, time):
        self.setPosition(x, y, r, image, time)

    # ======================================================================
    # 🔹 Filtro de Kalman
    # ======================================================================

    def update_kalman(self, measured_pos, timestamp):
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
        if not self.kalman_initialized:
            return self.newPosition
        return self.kalman_state[:2, 0]

    @property
    def velocity_filtered(self):
        if not self.kalman_initialized:
            return np.array([0.0, 0.0])
        return self.kalman_state[2:, 0]

    def predict_position(self, dt=0.05):
        if not self.kalman_initialized:
            return self.newPosition
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

    def getVelocity(self, timestamp):
        if not self.kalman_initialized:
            return np.array([0.0, 0.0])
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
