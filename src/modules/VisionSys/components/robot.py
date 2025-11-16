# Updated Robot class with simple Kalman for [x, y, theta]
# (Canvas version; user requested refactor while keeping old API)

import numpy as np
import cv2
from modules.VisionSys.components.objects import *

class Robot:
    def __init__(self, id: ID_Robots, team: ID_Team, x=0, y=0, r=0,
                 image=cv2.imread('src/images/dark_screen.png'),
                 colorTeam=None, colorCar1=None, colorCar2=None,
                 differential_filter=False):

        # Identifiers
        self.id = id
        self.team = team

        # Position
        self.position = np.array([float(x), float(y)])
        self.lastPosition = self.position.copy()
        self.newPosition = self.position.copy()

        # Direction & angle
        self._direction = np.array([1.0, 0.0])
        self._theta = 0.0

        # Geometry
        self.radius = float(r)
        self.objLimit = Circle(self.radius, Point2D(x, y))
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)
        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.ROBOT

        # Status
        self.detected = False
        self.possessionBall = False

        # Image-space coordinates (DO NOT CHANGE)
        self.xi = 0
        self.yi = 0
        self.ri = 0

        # Image & view window
        self.image = image
        self.dimMatrix = image.shape[1] if image is not None else 0
        self.viewRect = ViewBot(Point2D(self.position[0], self.position[1]), self.dimMatrix)

        # Colors
        self.colorTeam = colorTeam
        self.colorCar1 = colorCar1
        self.colorCar2 = colorCar2

        # Time
        self.lastTimestamp = 0
        self.newTimestamp = 0
        self.dT = 0.0

        # Kalman
        self.kalman_initialized = False
        self.kalman_last_time = None
        self._init_kalman()

    # --------------------------
    # Kalman init
    # --------------------------
    def _init_kalman(self):
        # State: [x, y, theta, vx, vy, omega]
        self.kalman_state = np.zeros((6, 1), float)

        # Covariances
        self.kalman_P = np.eye(6) * 400.0

        # Processo (acelerações pequenas)
        self.kalman_Q = np.diag([0.01, 0.01, 0.01, 5.0, 5.0, 1.0])

        # Ruído de medição do sistema de visão
        # Medimos apenas x, y, theta  → tamanho 3x3
        self.kalman_R = np.diag([3.0, 3.0, 0.5])

        self.kalman_initialized = False
        self.kalman_last_time = None

    # --------------------------
    # Properties
    # --------------------------
    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, vec):
        vec = np.asarray(vec, dtype=float)
        norm = np.linalg.norm(vec)
        if norm < 1e-6:
            return
        self._direction = vec / norm
        self._theta = np.arctan2(self._direction[1], self._direction[0])

    @property
    def theta(self):
        return self._theta

    @theta.setter
    def theta(self, ang):
        self._theta = float(ang)
        self._direction = np.array([np.cos(self._theta), np.sin(self._theta)])

    @property
    def position_filtered(self):
        if not self.kalman_initialized:
            return self.position
        return self.kalman_state[:2, 0]

    @property
    def theta_filtered(self):
        if not self.kalman_initialized:
            return self.theta
        return float(self.kalman_state[2, 0])

    @property
    def velocity_filtered(self):
        if not self.kalman_initialized:
            return np.array([0.0, 0.0])
        return self.kalman_state[3:5, 0]

    @property
    def omega_filtered(self):
        if not self.kalman_initialized:
            return 0.0
        return float(self.kalman_state[5, 0])


    # --------------------------
    # Position update
    # --------------------------
    def setPosition(self, x, y, r, image, time, wheel_velocities=None):
        self.lastTimestamp = self.newTimestamp
        self.newTimestamp = time
        self.dT = self.newTimestamp - self.lastTimestamp if self.lastTimestamp != 0 else 0.0

        # Position update (with noise guard)
        self.lastPosition = self.position.copy()
        raw_move = np.array([x - self.lastPosition[0], y - self.lastPosition[1]])
        if np.linalg.norm(raw_move) > 0.1:  # 0.1 cm threshold
            self.position = np.array([x, y], float)
        # else: ignore noise

        self.newPosition = self.position.copy()
        movement = self.newPosition - self.lastPosition

        if np.linalg.norm(movement) > 0.1:
            self.direction = movement

        self.radius = float(r)
        self.image = image
        if image is not None:
            self.viewRect.setDimension(image.shape[1])

        # Geometry
        self.objLimit = Circle(self.radius, Point2D(x, y))
        self.viewRect.updateViewBot(Point2D(x, y))
        self.updateBbox()

        # Update Kalman
        self.update_kalman([x, y, self.theta], time)

    def updatePosition(self, x, y, r, image, time, wheel_velocities=None):
        self.setPosition(x, y, r, image, time)

    # --------------------------
    # Kalman update
    # --------------------------
    def update_kalman(self, z_list, timestamp):
        """
        Kalman completo para estado: [x, y, theta, vx, vy, omega]
        Medição: [x, y, theta]
        """
        x, y, theta_meas = z_list
        z = np.array([[x], [y], [theta_meas]])

        # Inicialização
        if not self.kalman_initialized:
            self.kalman_state[:3, 0] = [x, y, theta_meas]
            self.kalman_initialized = True
            self.kalman_last_time = timestamp
            return

        dt = max(timestamp - self.kalman_last_time, 1e-3)
        self.kalman_last_time = timestamp

        # -----------------------------------------------------------
        # 1) PREDICTION
        # -----------------------------------------------------------

        # Modelo constante-velocidade
        F = np.array([
            [1, 0, 0, dt, 0,  0],
            [0, 1, 0, 0,  dt, 0],
            [0, 0, 1, 0,  0, dt],
            [0, 0, 0, 1,  0,  0],
            [0, 0, 0, 0,  1,  0],
            [0, 0, 0, 0,  0,  1],
        ], float)

        self.kalman_state = F @ self.kalman_state
        self.kalman_P = F @ self.kalman_P @ F.T + self.kalman_Q

        # -----------------------------------------------------------
        # 2) UPDATE (measurement)
        # -----------------------------------------------------------

        H = np.array([
            [1, 0, 0, 0, 0, 0],    # x
            [0, 1, 0, 0, 0, 0],    # y
            [0, 0, 1, 0, 0, 0],    # theta
        ])

        y_residual = z - H @ self.kalman_state
        S = H @ self.kalman_P @ H.T + self.kalman_R
        K = self.kalman_P @ H.T @ np.linalg.inv(S)

        # Atualiza
        self.kalman_state = self.kalman_state + K @ y_residual
        self.kalman_P = (np.eye(6) - K @ H) @ self.kalman_P

        # --------------------------
    # Aux
    # --------------------------
    def updateBbox(self):
        self.objLimit = Circle(Point2D(self.position[0], self.position[1]), self.radius)
        self.bbox.attPosition(self.objLimit)

    def updtPositionImg(self, xi, yi, ri):
        self.xi = xi
        self.yi = yi
        self.ri = ri

    def getAngle(self):
        return float(self.theta)

    def getColors(self):
        return self.colorTeam, self.colorCar1, self.colorCar2

    def getStatus(self):
        return self.detected 
    
    def setStatus(self, status):
        self.detected = status

    def setColor(self, colorT=None, colorP=None, colorS=None):
        self.colorTeam = colorT
        self.colorCar1 = colorP
        self.colorCar2 = colorS

    def setColorTeam(self, colorT=None):
        self.colorTeam = colorT
    
    def setDirection(self, direction):
        self.direction = direction 

    def setTeamColor(self, color):
        """
        Define a cor lógica do time do robô.
        Mantém API antiga, não interfere na física ou posição.
        """
        self.teamColor = color

    def reset(self):
        self.position = np.array([0.0, 0.0])
        self.lastPosition = self.position.copy()
        self.newPosition = self.position.copy()
        self.direction = np.array([1.0, 0.0])
        self.theta = 0.0
        self.detected = False
        self.possessionBall = False
        self.dT = 0.0
        self.lastTimestamp = 0
        self.newTimestamp = 0
        self._init_kalman()

    def resetState(self):
        self.position = np.array([0.0, 0.0])
        self.lastPosition = self.position.copy()
        self.newPosition = self.position.copy()
        self.direction = np.array([1.0, 0.0])
        self.theta = 0.0
        self.detected = False
        self.possessionBall = False
        self.dT = 0.0
        self.lastTimestamp = 0
        self.newTimestamp = 0

