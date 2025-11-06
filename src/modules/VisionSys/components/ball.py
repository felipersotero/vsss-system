import numpy as np
from modules.VisionSys.components.objects import *

class Ball:
    '''
    Classe responsável por representar a bola no sistema de visão, com suporte
    ao Filtro de Kalman linear clássico (posição + velocidade).
    '''
    def __init__(self, x=0.0, y=0.0, r=0.0):
        # --- Estado inicial (x, y, vx, vy)
        self._x = np.array([[x], [y], [0.0], [0.0]])  # estado estimado
        self._P = np.eye(4) * 1.0                     # covariância inicial

        # --- Modelo de ruído
        self._Q = np.eye(4) * 0.1   # ruído do processo
        self._R = np.eye(2) * 5.0   # ruído da medição (visão)

        # --- Matriz de medição
        self._H = np.zeros((2, 4))
        self._H[0, 0] = 1
        self._H[1, 1] = 1

        # --- Matriz de transição (atualizada com Δt a cada passo)
        self._A = np.eye(4)

        # --- Medição mais recente
        self._z = np.zeros((2, 1))

        # --- Atributos geométricos e visuais
        self._radius = r
        self._position = np.array([x, y])
        self._velocity = np.array([0.0, 0.0])
        self._direction = np.array([0.0, 0.0])

        self.objLimit = Circle(Point2D(x, y), self._radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)
        self.viewBall = ViewBot(Point2D(self._position[0], self._position[1]), int(r + 14))

        self.ObjType = ObjTypeMove.MOVING
        self.objTypeSystem = ObjTypeVision.BALL

        # --- Coordenadas da bola na imagem (para debug)
        self._xi = 0
        self._yi = 0
        self._ri = 0

        # --- Controle temporal
        self.lastTimestamp = 0
        self.newTimestamp = 0
        self.dT = 0

        # --- Estado de detecção
        self.status = False

    # ===============================================================
    #                       PROPRIEDADES (Getters e Setters)
    # ===============================================================

    # posição x (real)
    @property
    def x(self): return float(self._x[0])
    @x.setter
    def x(self, value): self._x[0, 0] = float(value)

    # posição y (real)
    @property
    def y(self): return float(self._x[1])
    @y.setter
    def y(self, value): self._x[1, 0] = float(value)

    # velocidade vx
    @property
    def vx(self): return float(self._x[2])
    @vx.setter
    def vx(self, value): self._x[2, 0] = float(value)

    # velocidade vy
    @property
    def vy(self): return float(self._x[3])
    @vy.setter
    def vy(self, value): self._x[3, 0] = float(value)

    # coordenadas na imagem
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

    # raio (em campo real)
    @property
    def radius(self): return self._radius
    @radius.setter
    def radius(self, value):
        self._radius = float(value)
        self.updateBbox()

    # posição e velocidade vetoriais
    @property
    def position(self): return self._position
    @property
    def velocity(self): return self._velocity

    # ===============================================================
    #                       FILTRO DE KALMAN
    # ===============================================================

    def kalman_predict(self, dt: float):
        '''
        Etapa de predição do filtro de Kalman.
        Atualiza o estado e a covariância com base no modelo de movimento.
        '''
        self.dT = dt
        self._A = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0 ],
            [0, 0, 0, 1 ]
        ])

        # Predição
        self._x = self._A @ self._x
        self._P = self._A @ self._P @ self._A.T + self._Q

        # Atualiza atributos derivados
        self._position = self._x[0:2, 0]
        self._velocity = self._x[2:4, 0]
        self.viewBall.updateViewBot(Point2D(self._position[0], self._position[1]))

    def kalman_update(self, z_meas: np.ndarray):
        '''
        Etapa de atualização (correção) do filtro de Kalman.
        '''
        self._z = z_meas.reshape((2, 1))
        y = self._z - self._H @ self._x                           # inovação
        S = self._H @ self._P @ self._H.T + self._R                # cov. da inovação
        K = self._P @ self._H.T @ np.linalg.inv(S)                 # ganho de Kalman

        self._x = self._x + K @ y
        self._P = (np.eye(4) - K @ self._H) @ self._P

        self._position = self._x[0:2, 0]
        self._velocity = self._x[2:4, 0]

        self.updateBbox()
        self.viewBall.updateViewBot(Point2D(self._position[0], self._position[1]))

    # ===============================================================
    #                        OUTROS MÉTODOS
    # ===============================================================

    def updateBbox(self):
        self.objLimit = Circle(Point2D(self._position[0], self._position[1]), self._radius)
        self.bbox = BorderBox(GeometryType.CIRCLE, self.objLimit)

    def predictPosition(self, timestamp):
        self.kalman_predict(timestamp - self.newTimestamp)
        self.newTimestamp = timestamp

    def setPosition(self, x, y, r, timestamp=0):
        self.kalman_update(np.array([x, y]))
        self._radius = r
        self.newTimestamp = timestamp
        self.status = True

    def getPredictPosition(self):
        return self.viewBall.Pe1, self.viewBall.DimMatrix

    def getStatus(self):
        return self.status
