from shapely.geometry import LineString, Point
import matplotlib.pyplot as plt
from copy import deepcopy
from queue import Queue
import numpy as np
 
class Navigation():
    # def __init__(self, Control) -> None:
    #     pass
        
    def dist_and_ang(self, pointA, pointB):
        difference = (pointB) - (pointA)
        
        dist = np.linalg.norm(difference)
        angle = (np.arctan2(difference[1], difference[0]))
        
        return dist, angle

    def calculateForce(self, source, target, obstacles):
        # Constantes
        s = 20 # Área de influência dos obstáculos. Padrão: 50
        betta = 2
        alpha = 3
        maxx = 200
        r = 10

        # Cálculo da força repulsiva
        Fr = np.zeros(2)

        # Robôs
        for obstacle in obstacles:
            if obstacle is not None:
                d, theta = self.dist_and_ang(source, obstacle)

                # print(f"{d} cm, {theta} rad")

                if d < r:
                    Fr += ([-maxx, -maxx])
                elif (d >= r) and (d <= (s+r)):
                    Fr += ([(-betta*(s+r-d)*np.cos(theta)), (-betta*(s+r-d)*np.sin(theta))])
                elif d > (s+r):
                    Fr += np.zeros(2)

        # Paredes
        w = 50
        h = 30
        a = 5 # Proximidade de influência dos limites do campo
        if source[0] < a:
            Fr += ([20, 0])
        if source[0] > (w-a):
            Fr += ([-20, 0])
        if source[1] < a:
            Fr += ([0, 20])
        if source[1] > (h-a):
            Fr += ([0, -20])

        # Cálculo da força atrativa
        Fa = np.zeros(2)

        d, theta = self.dist_and_ang(source, target)
        # print(f"{d} cm, {theta} rad")
        # rb = 2
        # sb = 120
        rb = 3
        sb = 50 # Área de influência da bola. Padrão: 50

        if d < rb:
            Fa = np.zeros(2)
            Fr = np.zeros(2)
        elif (d >= rb) and (d <= (sb+rb)):
            Fa = ([(alpha*(d-rb)*np.cos(theta)), (alpha*(d-rb)*np.sin(theta))])
            Fr = Fr*d/100
        elif d > (sb+rb):
            Fa = ([alpha*sb*np.cos(theta), alpha*sb*np.sin(theta)])

        # Força resultante
        F = np.zeros(2)
        F = Fr + Fa
        return F

    # Discretização da trajetória

    def estimatePath(self, player_coordinates, obstacles_coordinates, target_coordinates):
        # Cópia dos jogadores
        # obstacles= deepcopy(players)
        # del obstacles[chosen_player]

        # target = ball.position
    
        initial_point = player_coordinates
        source = player_coordinates

        path_points = []
        path_points.append(source)
        n_it = 100
        rep = 0

        distance_limit = 5

        for it in range(n_it):
            rep += 1

            if np.linalg.norm((target_coordinates) - (source)) < distance_limit:
                break
            
            F = self.calculateForce(source, target_coordinates, obstacles_coordinates)
            new_point = path_points[-1] + F/10
            path_points.append(new_point)

            if len(path_points) > 2:
                difference1 = (new_point) - (path_points[-2])
                difference2 = (path_points[-2]) - (path_points[-3])
                angle1 = np.arctan2(difference1[1], difference1[0])
                angle2 = np.arctan2(difference2[1], difference2[0])

                if abs(angle1 - angle2) < np.pi / 8:
                    path_points.pop(-2)

            source = new_point

        # print(f"{rep} repetições")
        # print(f"{len(path_points)} pontos de trajetória")

        return path_points
